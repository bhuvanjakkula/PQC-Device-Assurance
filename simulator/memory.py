"""
Memory & RAM/stack delta simulator: evaluates working set during boot verify,
stack frame allocation, and runtime heap budgets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from models.device import DeviceFamily
from models.firmware import FirmwareRelease


@dataclass
class MemorySimulationResult:
    scheme_name: str
    verify_ram_required: int
    ram_available_at_boot: int
    ram_headroom_bytes: int
    ram_exceeded: bool
    ram_utilization_pct: float
    kem_scheme: Optional[str] = None
    kem_fits_ram: bool = True
    constraint_message: Optional[str] = None


def simulate_memory_envelope(
    family: DeviceFamily,
    firmware: FirmwareRelease,
    profile_name: str,
    profile: dict,
    kem_profile: Optional[dict] = None,
    kem_name: str = "ML-KEM-768",
) -> MemorySimulationResult:
    """
    Simulates RAM requirements during secure boot verification and PQC key establishment.
    """
    verify_ram = profile.get("verify_ram", 20_000)
    ram_at_boot = family.hardware.ram_at_boot

    ram_headroom = ram_at_boot - verify_ram
    ram_exceeded = verify_ram > ram_at_boot
    ram_utilization = (verify_ram / ram_at_boot) * 100.0 if ram_at_boot > 0 else 100.0

    # Check companion KEM (e.g. ML-KEM-768 for transport)
    kem_ram_req = kem_profile.get("verify_ram", 16_000) if kem_profile else 16_000
    total_ram = family.hardware.ram_total
    kem_fits = (firmware.estimated_ram_usage + kem_ram_req) <= total_ram

    constraint_message = None
    if ram_exceeded:
        deficit_kib = int(round((verify_ram - ram_at_boot) / 1024))
        constraint_message = (
            f"Verify working set ({verify_ram} B) exceeds boot-time RAM ({ram_at_boot} B) by {deficit_kib} KiB"
        )
    elif kem_fits:
        constraint_message = f"{kem_name} fits RAM budget"

    return MemorySimulationResult(
        scheme_name=profile_name,
        verify_ram_required=verify_ram,
        ram_available_at_boot=ram_at_boot,
        ram_headroom_bytes=ram_headroom,
        ram_exceeded=ram_exceeded,
        ram_utilization_pct=round(ram_utilization, 1),
        kem_scheme=kem_name,
        kem_fits_ram=kem_fits,
        constraint_message=constraint_message,
    )
