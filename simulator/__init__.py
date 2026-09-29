"""
Simulator package initialization.
"""

from simulator.pqc_profiles import (
    PQC_PROFILES,
    CLASSICAL_SCHEMES,
    resolve_policy_profile,
)
from simulator.flash import FlashSimulationResult, simulate_flash_envelope
from simulator.memory import MemorySimulationResult, simulate_memory_envelope
from simulator.update import UpdateSimulationResult, simulate_update_envelope
from simulator.simulator import PQCMigrationSimulator, MigrationSimulationReport

__all__ = [
    "PQC_PROFILES",
    "CLASSICAL_SCHEMES",
    "resolve_policy_profile",
    "FlashSimulationResult",
    "simulate_flash_envelope",
    "MemorySimulationResult",
    "simulate_memory_envelope",
    "UpdateSimulationResult",
    "simulate_update_envelope",
    "PQCMigrationSimulator",
    "MigrationSimulationReport",
]
