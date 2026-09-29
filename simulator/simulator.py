"""
Simulator coordinator: executes migration simulation across Flash, RAM, Bootloader, and OTA.
Firmware Analyzer -> PQC Migration Simulator:
  Flash delta + RAM/stack delta + Bootloader fit + OTA/update fit + protocol/message-size impact
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from models.device import DeviceFamily
from models.firmware import FirmwareRelease
from simulator.flash import FlashSimulationResult, simulate_flash_envelope
from simulator.memory import MemorySimulationResult, simulate_memory_envelope
from simulator.pqc_profiles import PQC_PROFILES, resolve_policy_profile
from simulator.update import UpdateSimulationResult, simulate_update_envelope


@dataclass
class MigrationSimulationReport:
    target_policy: str
    evaluated_scheme: str
    profile: dict[str, Any]
    flash: FlashSimulationResult
    memory: MemorySimulationResult
    update: UpdateSimulationResult
    identified_constraints: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_policy": self.target_policy,
            "evaluated_scheme": self.evaluated_scheme,
            "flash": {
                "code_expansion_bytes": self.flash.code_expansion_bytes,
                "sig_expansion_bytes": self.flash.sig_expansion_bytes,
                "total_new_image_bytes": self.flash.total_new_image_bytes,
                "slot_capacity_bytes": self.flash.slot_capacity_bytes,
                "slot_headroom_bytes": self.flash.slot_headroom_bytes,
                "slot_exceeded": self.flash.slot_exceeded,
                "overflow_bytes": self.flash.overflow_bytes,
                "slot_pressure_pct": self.flash.slot_pressure_pct,
                "header_consumed_bytes": self.flash.header_consumed_bytes,
                "header_budget_bytes": self.flash.header_budget_bytes,
                "header_exceeded": self.flash.header_exceeded,
            },
            "memory": {
                "verify_ram_required": self.memory.verify_ram_required,
                "ram_available_at_boot": self.memory.ram_available_at_boot,
                "ram_headroom_bytes": self.memory.ram_headroom_bytes,
                "ram_exceeded": self.memory.ram_exceeded,
                "ram_utilization_pct": self.memory.ram_utilization_pct,
                "kem_scheme": self.memory.kem_scheme,
                "kem_fits_ram": self.memory.kem_fits_ram,
            },
            "update": {
                "mtu_bytes": self.update.mtu_bytes,
                "frame_count": self.update.frame_count,
                "dual_bank_safe": self.update.dual_bank_safe,
                "rom_locked": self.update.rom_locked,
                "otp_pubkey_exceeded": self.update.otp_pubkey_exceeded,
                "watchdog_safe": self.update.watchdog_safe,
                "verification_path_requires_mod": self.update.verification_path_requires_mod,
            },
            "identified_constraints": self.identified_constraints,
        }


class PQCMigrationSimulator:
    """
    Coordinates multi-dimensional hardware simulation for quantum-safe updates.
    """

    @staticmethod
    def simulate(
        family: DeviceFamily,
        firmware: FirmwareRelease,
        target_policy: str = "hybrid-pqc",
    ) -> MigrationSimulationReport:
        scheme_name, profile = resolve_policy_profile(target_policy)

        # 1. Flash delta simulation
        flash_res = simulate_flash_envelope(family, firmware, scheme_name, profile)

        # 2. RAM & working set simulation
        kem_profile = PQC_PROFILES.get("ML-KEM-768")
        memory_res = simulate_memory_envelope(
            family, firmware, scheme_name, profile, kem_profile=kem_profile, kem_name="ML-KEM-768"
        )

        # 3. Update & bootloader feasibility simulation
        update_res = simulate_update_envelope(family, scheme_name, profile)

        # Compile constraints
        constraints: list[str] = []
        if flash_res.constraint_message:
            constraints.append(flash_res.constraint_message)
        if memory_res.constraint_message:
            constraints.append(memory_res.constraint_message)
        if update_res.constraint_message:
            constraints.append(update_res.constraint_message)

        return MigrationSimulationReport(
            target_policy=target_policy,
            evaluated_scheme=scheme_name,
            profile=profile,
            flash=flash_res,
            memory=memory_res,
            update=update_res,
            identified_constraints=constraints,
        )
