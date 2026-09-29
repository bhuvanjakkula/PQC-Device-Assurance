"""
Evidence generation: generates structured, auditable evidence items
spanning flash, RAM, bootloader, OTA, crypto findings, and regulatory status.
"""

from __future__ import annotations

from models.decision import EvidenceItem
from models.device import DeviceFamily
from models.firmware import FirmwareRelease
from simulator.simulator import MigrationSimulationReport


def compile_evidence(
    family: DeviceFamily,
    firmware: FirmwareRelease,
    sim: MigrationSimulationReport,
) -> list[EvidenceItem]:
    """
    Compiles detailed technical evidence for each dimension of the updateability assessment.
    """
    items: list[EvidenceItem] = []

    # 1. Flash evidence
    flash = sim.flash
    flash_status = "FAIL" if flash.slot_exceeded else ("WARN" if flash.slot_pressure_pct > 85.0 else "PASS")
    items.append(
        EvidenceItem(
            category="flash",
            status=flash_status,
            statement=(
                f"OTA staging slot utilization is {flash.slot_pressure_pct}% "
                f"({flash.total_new_image_bytes // 1024} KiB of {flash.slot_capacity_bytes // 1024} KiB capacity)."
            ),
            detail=f"Code expansion: +{flash.code_expansion_bytes} B, Signature delta: +{flash.sig_expansion_bytes} B",
            current_value=flash.total_new_image_bytes,
            threshold_value=flash.slot_capacity_bytes,
        )
    )

    # 2. Header budget evidence
    header_status = "FAIL" if flash.header_exceeded else "PASS"
    items.append(
        EvidenceItem(
            category="flash",
            status=header_status,
            statement=(
                f"Firmware header envelope consumes {flash.header_consumed_bytes} B of "
                f"{flash.header_budget_bytes} B allocated in bootloader."
            ),
            detail=f"Signature field allocated: {flash.sig_field_budget_bytes} B",
            current_value=flash.header_consumed_bytes,
            threshold_value=flash.header_budget_bytes,
        )
    )

    # 3. RAM / Bootloader stack evidence
    mem = sim.memory
    mem_status = "FAIL" if mem.ram_exceeded else "PASS"
    items.append(
        EvidenceItem(
            category="ram",
            status=mem_status,
            statement=(
                f"Boot-time RAM working set requires {mem.verify_ram_required} B "
                f"({mem.ram_utilization_pct}% of {mem.ram_available_at_boot} B usable SRAM)."
            ),
            detail=f"KEM companion ({mem.kem_scheme}) fits runtime memory: {mem.kem_fits_ram}",
            current_value=mem.verify_ram_required,
            threshold_value=mem.ram_available_at_boot,
        )
    )

    # 4. Bootloader path & Rollback evidence
    upd = sim.update
    boot_status = "FAIL" if upd.rom_locked else ("WARN" if upd.verification_path_requires_mod else "PASS")
    items.append(
        EvidenceItem(
            category="bootloader",
            status=boot_status,
            statement=(
                "ROM verifier is immutable" if upd.rom_locked else
                ("Bootloader verification path requires staged modification" if upd.verification_path_requires_mod
                 else "Bootloader verification path supports in-place PQC hook")
            ),
            detail=f"Dual-bank rollback protection: {'Enabled' if upd.dual_bank_safe else 'Disabled (Brick Hazard)'}",
            current_value=family.boot.bootloader_name,
            threshold_value="Mutable or Staged SPL",
        )
    )

    # 5. OTA transport MTU evidence
    ota_status = "WARN" if upd.mtu_exceeded else "PASS"
    items.append(
        EvidenceItem(
            category="ota",
            status=ota_status,
            statement=(
                f"PQC signature ({upd.sig_bytes} B) fragments across {upd.frame_count} MTU packets ({upd.mtu_bytes} B MTU)."
                if upd.mtu_exceeded else
                f"PQC signature ({upd.sig_bytes} B) fits within standard MTU ({upd.mtu_bytes} B)."
            ),
            detail=f"Watchdog verification timeout safe: {upd.watchdog_safe}",
            current_value=upd.sig_bytes,
            threshold_value=upd.mtu_bytes,
        )
    )

    # 6. Crypto discovery evidence
    boot_crypto = [f.algorithm for f in firmware.findings if f.used_at_boot]
    items.append(
        EvidenceItem(
            category="crypto",
            status="PASS",
            statement=f"Detected {len(firmware.findings)} cryptographic primitives ({', '.join(boot_crypto)} at boot).",
            detail=f"Active verification scheme inferred: {family.current_scheme}",
            current_value=", ".join(f.algorithm for f in firmware.findings),
            threshold_value=family.current_scheme,
        )
    )

    return items
