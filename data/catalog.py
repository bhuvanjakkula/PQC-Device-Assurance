"""
Built-in device family catalog and benchmark device definitions.
Includes controller-x7, Acme infusion pumps, automotive ECUs, and grid gateways.
"""

from __future__ import annotations

from models.device import (
    BootArchitecture,
    CertificationBaseline,
    DeviceFamily,
    HardwareConstraints,
    RegulatoryRegime,
)

FAMILY_CATALOG: dict[str, DeviceFamily] = {
    # The flagship controller from user specification
    "controller-x7": DeviceFamily(
        family_id="controller-x7",
        vendor="Aegis Embedded Systems",
        module="Controller X7 Industrial Edge Gateway",
        soc_arch="ARM Cortex-M7 @ 400MHz",
        hardware=HardwareConstraints(
            flash_total=1024 * 1024,          # 1 MB Flash
            flash_bootloader=64 * 1024,       # 64 KB Bootloader
            flash_slot_a=448 * 1024,          # 448 KB Slot A
            flash_slot_b=448 * 1024,          # 448 KB Slot B (staging slot)
            ram_total=128 * 1024,             # 128 KB RAM
            ram_at_boot=32 * 1024,            # 32 KB at boot
            otp_pubkey_max=512,               # 512 B OTP for root pubkey
            mtu=1024,                         # 1 KB MTU
            watchdog_timeout_ms=500,
            hardware_crypto=True,
        ),
        boot=BootArchitecture(
            bootloader_name="MCUboot-X7-v2.3",
            verify_in_rom=False,              # Mutable bootloader
            dual_bank=True,                   # A/B slot rollback safe
            header_max=1024,                  # 1024 B header budget
            sig_field_max=512,                # 512 B sig field (insufficient for pure ML-DSA-65 3309B)
            verification_path="single_stage", # Requires staged SPL modification for PQC hook
            allows_bootloader_ota=True,
        ),
        certification=CertificationBaseline(
            regime=RegulatoryRegime.IEC_62443,
            standard_id="IEC-62443-4-2 SL3",
            baseline_scheme="ECDSA-P256",
            filing_dossier_id="CERT-IEC-2024-X7-088",
            last_certified_release="firmware-4.18.1.bin",
            recertification_cost_estimate_usd=120000,
        ),
        current_scheme="ECDSA-P256",
        description="High-reliability edge controller for substation automation and field telemetry.",
    ),

    # Acme Infusion Pump (FDA-524B regulated medical device, ROM locked)
    "acme-pump-m3-revc": DeviceFamily(
        family_id="acme-pump-m3-revc",
        vendor="Acme Medical",
        module="InfusionPump M3 Rev C",
        soc_arch="ARM Cortex-M3 @ 72MHz",
        hardware=HardwareConstraints(
            flash_total=512 * 1024,
            flash_bootloader=32 * 1024,
            flash_slot_a=256 * 1024,
            flash_slot_b=224 * 1024,
            ram_total=32 * 1024,
            ram_at_boot=16 * 1024,
            otp_pubkey_max=256,
            mtu=256,
            watchdog_timeout_ms=200,
            hardware_crypto=False,
        ),
        boot=BootArchitecture(
            bootloader_name="AcmeROM-2.1",
            verify_in_rom=True,               # ROM locked!
            dual_bank=False,                  # Single bank! Brick hazard!
            header_max=512,
            sig_field_max=384,
            verification_path="rom_locked",
            allows_bootloader_ota=False,
        ),
        certification=CertificationBaseline(
            regime=RegulatoryRegime.FDA_524B,
            standard_id="FDA-524B PMA",
            baseline_scheme="RSA-2048",
            filing_dossier_id="PMA-2022-PUMP-901",
            last_certified_release="pump-fw-2.4.0.bin",
            recertification_cost_estimate_usd=250000,
        ),
        current_scheme="RSA-2048",
        description="Class III ambulatory infusion pump with immutable mask-ROM secure boot.",
    ),

    # Automotive Telematics Control Unit (ISO-21434 / UN R155)
    "autonet-tcu-v3": DeviceFamily(
        family_id="autonet-tcu-v3",
        vendor="AutoNet Technologies",
        module="Telematics Control Unit Gen3",
        soc_arch="NXP S32G2 (Quad Cortex-A53 + Triple Cortex-M7)",
        hardware=HardwareConstraints(
            flash_total=16 * 1024 * 1024,     # 16 MB eMMC/eSPI
            flash_bootloader=512 * 1024,
            flash_slot_a=6 * 1024 * 1024,
            flash_slot_b=6 * 1024 * 1024,
            ram_total=512 * 1024 * 1024,      # 512 MB LPDDR4
            ram_at_boot=64 * 1024 * 1024,
            otp_pubkey_max=4096,
            mtu=4096,
            watchdog_timeout_ms=2000,
            hardware_crypto=True,
        ),
        boot=BootArchitecture(
            bootloader_name="TF-M / U-Boot 2024",
            verify_in_rom=False,
            dual_bank=True,
            header_max=4096,
            sig_field_max=4096,
            verification_path="staged_spl",
            allows_bootloader_ota=True,
        ),
        certification=CertificationBaseline(
            regime=RegulatoryRegime.ISO_21434,
            standard_id="UN R155 / ISO 21434",
            baseline_scheme="ECDSA-P256",
            filing_dossier_id="TARA-TCU-2024-V3",
            last_certified_release="tcu-fw-3.2.0.bin",
            recertification_cost_estimate_usd=180000,
        ),
        current_scheme="ECDSA-P256",
        description="Automotive vehicle-to-cloud telematics gateway with A/B dual partition rollback.",
    ),

    # Smart Grid AMI Electricity Meter (Resource-constrained utility meter)
    "grid-meter-nx5": DeviceFamily(
        family_id="grid-meter-nx5",
        vendor="GridMetrics Energy",
        module="GridMeter NX5 Smart Utility Meter",
        soc_arch="ARM Cortex-M0+ @ 48MHz",
        hardware=HardwareConstraints(
            flash_total=256 * 1024,           # 256 KB Flash
            flash_bootloader=32 * 1024,       # 32 KB Bootloader
            flash_slot_a=112 * 1024,          # 112 KB Slot A
            flash_slot_b=112 * 1024,          # 112 KB Slot B
            ram_total=16 * 1024,              # 16 KB RAM total
            ram_at_boot=8 * 1024,             # 8 KB RAM available at boot!
            otp_pubkey_max=128,               # 128 B OTP (insufficient for PQC pubkeys)
            mtu=512,
            watchdog_timeout_ms=150,
            hardware_crypto=False,
        ),
        boot=BootArchitecture(
            bootloader_name="GridBoot-M0-v1.4",
            verify_in_rom=False,
            dual_bank=True,
            header_max=512,
            sig_field_max=256,
            verification_path="single_stage",
            allows_bootloader_ota=True,
        ),
        certification=CertificationBaseline(
            regime=RegulatoryRegime.ANSI_C12,
            standard_id="ANSI C12.22 / DLMS-COSEM",
            baseline_scheme="ECDSA-P256",
            filing_dossier_id="AMI-GRID-2023-NX5",
            last_certified_release="meter-fw-1.2.0.bin",
            recertification_cost_estimate_usd=95000,
        ),
        current_scheme="ECDSA-P256",
        description="High-volume residential smart electricity meter; RAM and OTP envelope requires silicon redesign for lattice PQC.",
    ),

    # Aerospace Primary Flight Control Computer (DO-178C DAL-A safety-critical)
    "aero-fcc-700": DeviceFamily(
        family_id="aero-fcc-700",
        vendor="AeroDyn Avionics",
        module="FCC-700 Flight Control Computer",
        soc_arch="Lockstep Dual Cortex-R5 @ 600MHz",
        hardware=HardwareConstraints(
            flash_total=4096 * 1024,          # 4 MB NOR Flash
            flash_bootloader=256 * 1024,      # 256 KB Bootloader
            flash_slot_a=1800 * 1024,         # 1.8 MB Slot A
            flash_slot_b=1800 * 1024,         # 1.8 MB Slot B
            ram_total=1024 * 1024,            # 1 MB SRAM
            ram_at_boot=256 * 1024,           # 256 KB RAM at boot
            otp_pubkey_max=2048,
            mtu=2048,
            watchdog_timeout_ms=1000,
            hardware_crypto=True,
        ),
        boot=BootArchitecture(
            bootloader_name="AeroBoot-DAL-A-v4",
            verify_in_rom=False,
            dual_bank=True,
            header_max=2048,
            sig_field_max=1024,
            verification_path="staged_spl",
            allows_bootloader_ota=True,
        ),
        certification=CertificationBaseline(
            regime=RegulatoryRegime.FAA_DO_178C,
            standard_id="RTCA DO-178C DAL-A",
            baseline_scheme="LMS-SHA256",
            filing_dossier_id="FAA-ACO-FCC700-09",
            last_certified_release="fcc-fw-3.1.0.bin",
            recertification_cost_estimate_usd=450000,
        ),
        current_scheme="LMS-SHA256",
        description="FAA DO-178C DAL-A safety-critical fly-by-wire controller using stateful-hash signature authentication.",
    ),
}


def get_device_family(family_id: str) -> DeviceFamily:
    """Retrieves device family by ID or returns a realistic default."""
    if family_id in FAMILY_CATALOG:
        return FAMILY_CATALOG[family_id]
    
    # Generic fallback family
    return DeviceFamily(
        family_id=family_id,
        vendor="Generic Hardware",
        module=f"Device {family_id}",
        soc_arch="ARM Cortex-M4",
        hardware=HardwareConstraints(
            flash_total=1024 * 1024,
            flash_bootloader=64 * 1024,
            flash_slot_a=448 * 1024,
            flash_slot_b=448 * 1024,
            ram_total=128 * 1024,
            ram_at_boot=32 * 1024,
            otp_pubkey_max=512,
            mtu=1024,
            watchdog_timeout_ms=500,
            hardware_crypto=False,
        ),
        boot=BootArchitecture(
            bootloader_name="MCUboot-Generic",
            verify_in_rom=False,
            dual_bank=True,
            header_max=1024,
            sig_field_max=512,
            verification_path="single_stage",
            allows_bootloader_ota=True,
        ),
        certification=CertificationBaseline(
            regime=RegulatoryRegime.IEC_62443,
            standard_id="IEC-62443",
            baseline_scheme="ECDSA-P256",
            filing_dossier_id="CERT-GENERIC-001",
            last_certified_release="v1.0.0",
            recertification_cost_estimate_usd=50000,
        ),
        current_scheme="ECDSA-P256",
        description="Standard embedded target device family.",
    )
