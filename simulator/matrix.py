"""
Interactive NIST PQC Algorithm Substitution Matrix Engine.
Computes side-by-side feasibility of all standardized post-quantum schemes
against a specific device family's physical flash and RAM constraints.
"""

from __future__ import annotations

from typing import Any
from models.device import DeviceFamily
from simulator.pqc_profiles import PQC_PROFILES


class AlgorithmMatrixEngine:
    """Evaluates all candidate PQC schemes against a device's hardware budget."""

    @classmethod
    def evaluate_matrix(cls, family: DeviceFamily, base_firmware_size_kb: int = 380) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        slot_capacity = family.hardware.flash_slot_b
        ram_boot = family.hardware.ram_at_boot
        header_budget = family.boot.header_max

        for scheme_name, profile in PQC_PROFILES.items():
            sig_size = profile["sig"]
            pk_size = profile["pk"]
            code_delta = profile["code_size_delta"]
            verify_ram = profile["verify_ram"]
            nist_lvl = profile.get("nist_level", 2)
            algo_type = profile.get("type", "PQC")

            total_image_bytes = (base_firmware_size_kb * 1024) + code_delta + sig_size
            slot_util_pct = round((total_image_bytes / slot_capacity) * 100, 1) if slot_capacity > 0 else 999.0
            ram_util_pct = round((verify_ram / ram_boot) * 100, 1) if ram_boot > 0 else 999.0

            slot_overflow_bytes = max(0, total_image_bytes - slot_capacity)
            ram_overflow_bytes = max(0, verify_ram - ram_boot)
            header_overflow = sig_size > header_budget

            # Feasibility determination
            if slot_overflow_bytes > 0 and ram_overflow_bytes > 0:
                fit_status = "EXCEEDS_BOTH"
                score = 15
            elif slot_overflow_bytes > 0:
                fit_status = "SLOT_OVERFLOW"
                score = 45
            elif ram_overflow_bytes > 0:
                fit_status = "RAM_EXCEEDED"
                score = 30
            elif slot_util_pct > 92.0 or ram_util_pct > 90.0:
                fit_status = "TIGHT_MARGIN"
                score = 75
            else:
                fit_status = "CLEAN_FIT"
                score = 98

            results.append({
                "scheme": scheme_name,
                "type": algo_type,
                "nist_level": nist_lvl,
                "sig_bytes": sig_size,
                "pk_bytes": pk_size,
                "code_delta_kib": round(code_delta / 1024, 1),
                "verify_ram_kib": round(verify_ram / 1024, 1),
                "slot_utilization_pct": slot_util_pct,
                "ram_utilization_pct": ram_util_pct,
                "slot_overflow_kib": round(slot_overflow_bytes / 1024, 1),
                "ram_overflow_kib": round(ram_overflow_bytes / 1024, 1),
                "header_compatible": not header_overflow,
                "fit_status": fit_status,
                "feasibility_score": score,
            })

        # Sort by feasibility score descending
        results.sort(key=lambda x: x["feasibility_score"], reverse=True)
        return results
