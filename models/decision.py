"""
Decision models representing the living PQC updateability assurance state.

Four Living States:
- CAN_MIGRATE
- CAN_MIGRATE_WITH_CONSTRAINTS
- REDESIGN_REQUIRED
- BLOCKED

Recertification Impact:
- NO_REOPEN
- LETTER_TO_FILE
- PREMARKET_UPDATE
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Optional


class MigrationStatus(str, Enum):
    CAN_MIGRATE = "CAN_MIGRATE"
    CAN_MIGRATE_WITH_CONSTRAINTS = "CAN_MIGRATE_WITH_CONSTRAINTS"
    REDESIGN_REQUIRED = "REDESIGN_REQUIRED"
    BLOCKED = "BLOCKED"

    def __str__(self) -> str:
        return self.value


class FilingImpact(str, Enum):
    NO_REOPEN = "NO_REOPEN"
    LETTER_TO_FILE = "LETTER_TO_FILE"
    PREMARKET_UPDATE = "PREMARKET_UPDATE"

    def __str__(self) -> str:
        return self.value


@dataclass
class EvidenceItem:
    category: str           # "flash", "ram", "bootloader", "ota", "crypto", "certification"
    status: str             # "PASS", "WARN", "FAIL"
    statement: str
    detail: str = ""
    current_value: Optional[Any] = None
    threshold_value: Optional[Any] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Decision:
    device_family: str
    firmware: str
    target_policy: str
    status: MigrationStatus
    constraints: list[str]
    changed_since_previous_release: bool
    filing_impact: FilingImpact
    recommended_scheme: str
    residual_risk: str
    evidence: list[EvidenceItem] = field(default_factory=list)
    simulation_details: dict[str, Any] = field(default_factory=dict)
    family_specs: dict[str, Any] = field(default_factory=dict)
    diff_from_previous: Optional[dict[str, Any]] = None
    created_at: str = ""

    def __repr__(self) -> str:
        return (
            f"<Decision family={self.device_family!r} firmware={self.firmware!r} "
            f"status={self.status.value!r} constraints={len(self.constraints)} "
            f"changed={self.changed_since_previous_release}>"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_family": self.device_family,
            "firmware": self.firmware,
            "target_policy": self.target_policy,
            "status": self.status.value,
            "constraints": self.constraints,
            "changed_since_previous_release": self.changed_since_previous_release,
            "filing_impact": self.filing_impact.value,
            "recommended_scheme": self.recommended_scheme,
            "residual_risk": self.residual_risk,
            "evidence": [e.to_dict() for e in self.evidence],
            "simulation_details": self.simulation_details,
            "family_specs": self.family_specs,
            "diff_from_previous": self.diff_from_previous,
            "created_at": self.created_at,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
