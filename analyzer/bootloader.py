"""
Bootloader analyzer: evaluates boot architecture, stages, header layouts,
and execution constraints against device hardware specs.
"""

from __future__ import annotations

from typing import Any
from models.device import BootArchitecture, HardwareConstraints


def analyze_boot_envelope(
    header_bytes: bytes,
    boot: BootArchitecture,
    hardware: HardwareConstraints,
) -> dict[str, Any]:
    """
    Analyzes the firmware header envelope and verification path compatibility.
    """
    header_len = len(header_bytes)
    
    # Check if header exceeds bootloader budget
    header_exceeded = header_len > boot.header_max
    
    # Check if ROM verifier is immutable
    rom_locked = boot.verify_in_rom
    
    # Calculate available headroom in header for extended metadata & PQC signatures
    headroom = max(0, boot.header_max - header_len)

    return {
        "bootloader_name": boot.bootloader_name,
        "header_max": boot.header_max,
        "actual_header_size": header_len,
        "header_exceeded": header_exceeded,
        "header_headroom_bytes": headroom,
        "sig_field_budget": boot.sig_field_max,
        "verify_in_rom": rom_locked,
        "dual_bank_supported": boot.dual_bank,
        "verification_path": boot.verification_path,
        "watchdog_timeout_ms": hardware.watchdog_timeout_ms,
        "ram_at_boot": hardware.ram_at_boot,
        "otp_pubkey_max": hardware.otp_pubkey_max,
    }
