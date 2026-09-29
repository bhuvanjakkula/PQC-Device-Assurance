"""
Flash memory delta simulator: checks flash partition headroom,
OTA staging slot (Slot B) pressure, header budgets, and code expansion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from models.device import DeviceFamily
from models.firmware import FirmwareRelease


@dataclass
class FlashSimulationResult:
    scheme_name: str
    code_expansion_bytes: int
    sig_expansion_bytes: int
    total_new_image_bytes: int
    slot_capacity_bytes: int
    slot_headroom_bytes: int
    slot_exceeded: bool
    overflow_bytes: int
    slot_pressure_pct: float
    header_consumed_bytes: int
    header_budget_bytes: int
    header_exceeded: bool
    sig_field_budget_bytes: int
    sig_field_exceeded: bool
    constraint_message: Optional[str] = None


def simulate_flash_envelope(
    family: DeviceFamily,
    firmware: FirmwareRelease,
    profile_name: str,
    profile: dict,
) -> FlashSimulationResult:
    """
    Computes flash delta and verifies slot fit when upgrading to target PQC scheme.
    """
    sig_size = profile["sig"]
    pk_size = profile["pk"]
    code_expansion = profile.get("code_size_delta", 16_384)

    # Current signature size baseline
    current_sig = 256  # Default RSA-2048 baseline
    if family.current_scheme.startswith("ECDSA"):
        current_sig = 64
    elif family.current_scheme.startswith("RSA-4096"):
        current_sig = 512

    sig_expansion = max(0, sig_size - current_sig)
    total_new_image = firmware.raw_size_bytes + code_expansion + sig_expansion

    # Header calculations
    header_consumed = sig_size + pk_size + 64  # 64 bytes for magic, version, flags, sha
    header_budget = family.boot.header_max
    header_exceeded = header_consumed > header_budget

    # Signature field calculations
    sig_field_budget = family.boot.sig_field_max
    sig_field_exceeded = sig_size > sig_field_budget

    # OTA Slot B calculation (active slot vs update slot)
    slot_capacity = family.hardware.flash_slot_b
    slot_headroom = slot_capacity - total_new_image
    slot_exceeded = total_new_image > slot_capacity
    overflow_bytes = max(0, total_new_image - slot_capacity)
    slot_pressure_pct = (total_new_image / slot_capacity) * 100.0 if slot_capacity > 0 else 100.0

    constraint_message = None
    if slot_exceeded:
        overflow_kib = int(round(overflow_bytes / 1024))
        constraint_message = (
            f"OTA slot exceeds available flash by {overflow_kib} KiB with {profile_name}"
        )
    elif header_exceeded and family.boot.verify_in_rom:
        constraint_message = (
            f"Image header ({header_consumed} B) exceeds bootloader budget ({header_budget} B)"
        )
    elif sig_field_exceeded and family.boot.verify_in_rom:
        constraint_message = (
            f"Signature ({sig_size} B) exceeds boot header field budget ({sig_field_budget} B)"
        )

    return FlashSimulationResult(
        scheme_name=profile_name,
        code_expansion_bytes=code_expansion,
        sig_expansion_bytes=sig_expansion,
        total_new_image_bytes=total_new_image,
        slot_capacity_bytes=slot_capacity,
        slot_headroom_bytes=slot_headroom,
        slot_exceeded=slot_exceeded,
        overflow_bytes=overflow_bytes,
        slot_pressure_pct=round(slot_pressure_pct, 1),
        header_consumed_bytes=header_consumed,
        header_budget_bytes=header_budget,
        header_exceeded=header_exceeded,
        sig_field_budget_bytes=sig_field_budget,
        sig_field_exceeded=sig_field_exceeded,
        constraint_message=constraint_message,
    )
