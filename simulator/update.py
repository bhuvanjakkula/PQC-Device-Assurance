"""
Update & Bootloader simulator: checks OTA framing, MTU fragmentation,
bootloader verification paths, dual-bank rollback safety, and watchdog cycle margins.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from models.device import DeviceFamily


@dataclass
class UpdateSimulationResult:
    scheme_name: str
    mtu_bytes: int
    sig_bytes: int
    pk_bytes: int
    mtu_exceeded: bool
    frame_count: int
    dual_bank_safe: bool
    rom_locked: bool
    otp_pubkey_exceeded: bool
    watchdog_safe: bool
    verification_path_requires_mod: bool
    constraint_message: Optional[str] = None


def simulate_update_envelope(
    family: DeviceFamily,
    profile_name: str,
    profile: dict,
) -> UpdateSimulationResult:
    """
    Evaluates update protocol feasibility, MTU framing, and bootloader execution path.
    """
    mtu = family.hardware.mtu
    sig_size = profile["sig"]
    pk_size = profile["pk"]

    # MTU fragmentation
    frame_count = max(1, (sig_size + mtu - 1) // mtu)
    mtu_exceeded = sig_size > mtu and mtu < 512

    # Verification path and ROM lock
    rom_locked = family.boot.verify_in_rom
    verification_path_requires_mod = False
    
    # If ROM is hardwired to classical verify, or bootloader verification path is single_stage without PQC hooks:
    if rom_locked or family.boot.verification_path == "single_stage" or not family.boot.allows_bootloader_ota:
        verification_path_requires_mod = True

    # OTP / eFuse root key space (only a blocker if root key is burned in immutable OTP/ROM)
    otp_pubkey_exceeded = (pk_size > family.hardware.otp_pubkey_max) if family.boot.verify_in_rom else False

    # Dual bank rollback safety
    dual_bank_safe = family.boot.dual_bank

    # Watchdog timing check
    est_cycles = profile.get("est_verify_cycles_cortex_m4", 2_000_000)
    # Estimate at 64MHz Cortex-M: 1ms = 64,000 cycles
    est_ms = est_cycles / 64_000
    watchdog_safe = est_ms < (family.hardware.watchdog_timeout_ms * 0.75)

    constraint_message = None
    if rom_locked and profile_name.startswith(("ML-DSA", "SLH-DSA")):
        constraint_message = "ROM verifier algorithm is locked to classical primitives"
    elif verification_path_requires_mod:
        constraint_message = "Bootloader verification path requires modification"
    elif not dual_bank_safe:
        constraint_message = "Single-bank flash: failed verify has no rollback slot (brick hazard)"
    elif otp_pubkey_exceeded:
        constraint_message = (
            f"Root key size ({pk_size} B) exceeds OTP hardware limit ({family.hardware.otp_pubkey_max} B)"
        )
    elif mtu_exceeded:
        constraint_message = f"OTA transport MTU ({mtu} B) requires {frame_count}-chunk fragmentation"

    return UpdateSimulationResult(
        scheme_name=profile_name,
        mtu_bytes=mtu,
        sig_bytes=sig_size,
        pk_bytes=pk_size,
        mtu_exceeded=mtu_exceeded,
        frame_count=frame_count,
        dual_bank_safe=dual_bank_safe,
        rom_locked=rom_locked,
        otp_pubkey_exceeded=otp_pubkey_exceeded,
        watchdog_safe=watchdog_safe,
        verification_path_requires_mod=verification_path_requires_mod,
        constraint_message=constraint_message,
    )
