"""
Device models representing device families, hardware constraints,
boot architecture, and certification baselines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class RegulatoryRegime(str, Enum):
    FDA_524B = "FDA-524B"          # Medical devices - cybersecurity in medical devices
    IEC_62443 = "IEC-62443"        # Industrial automation & control systems
    ISO_21434 = "ISO-21434"        # Automotive cybersecurity engineering
    EU_RED = "EU-RED"              # European Radio Equipment Directive Art 3.3
    FAA_DO_178C = "FAA-DO-178C"    # Aerospace flight software DAL-A/B
    ANSI_C12 = "ANSI-C12.22"       # Smart grid AMI / utility metering
    NONE = "none"


@dataclass
class HardwareConstraints:
    flash_total: int                 # Total flash bytes
    flash_bootloader: int            # Bootloader partition bytes
    flash_slot_a: int                # Active firmware slot bytes
    flash_slot_b: int                # Inactive / OTA staging slot bytes
    ram_total: int                   # Total SRAM bytes
    ram_at_boot: int                 # Usable SRAM during bootloader execution
    otp_pubkey_max: int              # Max bytes for OTP / eFuse root public key
    mtu: int                         # OTA transport MTU packet size in bytes
    watchdog_timeout_ms: int = 250   # Hardware watchdog timeout during signature verification
    hardware_crypto: bool = False    # Dedicated HW crypto engine present (e.g. ATECC608, STM32 CSEC)


@dataclass
class BootArchitecture:
    bootloader_name: str             # e.g., "MCUboot-2.1", "TF-M-1.8", "AcmeROM-v2"
    verify_in_rom: bool              # True if root verification is burned in immutable silicon ROM
    dual_bank: bool                  # True if A/B ping-pong partition layout allows rollback
    header_max: int                  # Max allowed firmware header bytes
    sig_field_max: int               # Max bytes allocated for signature field in header
    verification_path: str = "single_stage"  # "single_stage" | "staged_spl" | "secure_enclave"
    allows_bootloader_ota: bool = False     # Can bootloader itself be updated OTA?


@dataclass
class CertificationBaseline:
    regime: RegulatoryRegime = RegulatoryRegime.FDA_524B
    standard_id: str = "FDA-524B"
    baseline_scheme: str = "RSA-2048"
    filing_dossier_id: str = "PMA-2023-CYBER-091"
    last_certified_release: str = "firmware-4.17.0.bin"
    recertification_cost_estimate_usd: int = 150000


@dataclass
class DeviceFamily:
    family_id: str
    vendor: str
    module: str
    soc_arch: str
    hardware: HardwareConstraints
    boot: BootArchitecture
    certification: CertificationBaseline
    current_scheme: str = "RSA-2048"
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "vendor": self.vendor,
            "module": self.module,
            "soc_arch": self.soc_arch,
            "hardware": {
                "flash_total": self.hardware.flash_total,
                "flash_bootloader": self.hardware.flash_bootloader,
                "flash_slot_a": self.hardware.flash_slot_a,
                "flash_slot_b": self.hardware.flash_slot_b,
                "ram_total": self.hardware.ram_total,
                "ram_at_boot": self.hardware.ram_at_boot,
                "otp_pubkey_max": self.hardware.otp_pubkey_max,
                "mtu": self.hardware.mtu,
                "watchdog_timeout_ms": self.hardware.watchdog_timeout_ms,
                "hardware_crypto": self.hardware.hardware_crypto,
            },
            "boot": {
                "bootloader_name": self.boot.bootloader_name,
                "verify_in_rom": self.boot.verify_in_rom,
                "dual_bank": self.boot.dual_bank,
                "header_max": self.boot.header_max,
                "sig_field_max": self.boot.sig_field_max,
                "verification_path": self.boot.verification_path,
                "allows_bootloader_ota": self.boot.allows_bootloader_ota,
            },
            "certification": {
                "regime": self.certification.regime.value,
                "standard_id": self.certification.standard_id,
                "baseline_scheme": self.certification.baseline_scheme,
                "filing_dossier_id": self.certification.filing_dossier_id,
                "last_certified_release": self.certification.last_certified_release,
            },
            "current_scheme": self.current_scheme,
            "description": self.description,
        }
