"""
Regression engine: tracks historical decisions across firmware releases (Release N vs N+1),
detects regressions, and computes differential assurance deltas.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from models.decision import Decision, FilingImpact, MigrationStatus


class ReleaseHistoryStore:
    """
    SQLite-backed persistent history store for living decisions across firmware releases.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS release_decisions (
                    family_id TEXT,
                    firmware_id TEXT,
                    created_at TEXT,
                    status TEXT,
                    policy TEXT,
                    filing_impact TEXT,
                    decision_json TEXT,
                    PRIMARY KEY (family_id, firmware_id)
                )
                """
            )
            conn.commit()

    def save_decision(self, decision: Decision) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO release_decisions
                (family_id, firmware_id, created_at, status, policy, filing_impact, decision_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.device_family,
                    decision.firmware,
                    decision.created_at,
                    decision.status.value,
                    decision.target_policy,
                    decision.filing_impact.value,
                    decision.to_json(),
                ),
            )
            conn.commit()

    def get_latest_decision(self, family_id: str) -> Optional[Decision]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT decision_json FROM release_decisions
                WHERE family_id = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (family_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._deserialize_decision(row[0])

    def get_previous_decision(self, family_id: str, current_firmware_id: str) -> Optional[Decision]:
        with sqlite3.connect(self.db_path) as conn:
            # Baseline releases have no predecessor
            if "4.18.1" in current_firmware_id or "baseline" in current_firmware_id.lower():
                return None

            # If evaluating 4.18.2, the predecessor baseline is 4.18.1
            if "4.18.2" in current_firmware_id:
                cursor = conn.execute(
                    "SELECT decision_json FROM release_decisions WHERE family_id = ? AND firmware_id LIKE '%4.18.1%' LIMIT 1",
                    (family_id,),
                )
                row = cursor.fetchone()
                if row:
                    return self._deserialize_decision(row[0])

            cursor = conn.execute(
                """
                SELECT decision_json FROM release_decisions
                WHERE family_id = ? AND firmware_id != ?
                ORDER BY created_at ASC
                """,
                (family_id, current_firmware_id),
            )
            rows = cursor.fetchall()
            if not rows:
                return None
            return self._deserialize_decision(rows[0][0])

    def get_all_for_family(self, family_id: str) -> list[Decision]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT decision_json FROM release_decisions
                WHERE family_id = ?
                ORDER BY created_at ASC
                """,
                (family_id,),
            )
            return [self._deserialize_decision(r[0]) for r in cursor.fetchall()]

    @staticmethod
    def _deserialize_decision(raw_json: str) -> Decision:
        data = json.loads(raw_json)
        return Decision(
            device_family=data["device_family"],
            firmware=data["firmware"],
            target_policy=data["target_policy"],
            status=MigrationStatus(data["status"]),
            constraints=data.get("constraints", []),
            changed_since_previous_release=data.get("changed_since_previous_release", False),
            filing_impact=FilingImpact(data.get("filing_impact", "NO_REOPEN")),
            recommended_scheme=data.get("recommended_scheme", ""),
            residual_risk=data.get("residual_risk", ""),
            evidence=[],
            simulation_details=data.get("simulation_details", {}),
            diff_from_previous=data.get("diff_from_previous"),
            created_at=data.get("created_at", ""),
        )


def compare_with_previous(
    current_status: MigrationStatus,
    current_constraints: list[str],
    current_scheme: str,
    current_filing: FilingImpact,
    previous_decision: Optional[Decision],
) -> tuple[bool, Optional[dict[str, Any]]]:
    """
    Compares the current release decision with the previous release decision.
    Returns: (changed_since_previous_release, diff_dict)
    """
    if previous_decision is None:
        return False, {
            "type": "BASELINE",
            "message": "Baseline certified release. Fits within flash and RAM margins without constraint.",
            "status_changed": False,
            "constraints_added": [],
            "constraints_removed": [],
        }

    status_changed = previous_decision.status != current_status
    filing_changed = previous_decision.filing_impact != current_filing
    scheme_changed = previous_decision.recommended_scheme != current_scheme

    prev_c_set = set(previous_decision.constraints)
    curr_c_set = set(current_constraints)
    constraints_added = list(curr_c_set - prev_c_set)
    constraints_removed = list(prev_c_set - curr_c_set)

    changed = (
        status_changed
        or filing_changed
        or scheme_changed
        or len(constraints_added) > 0
        or len(constraints_removed) > 0
    )

    diff = {
        "previous_firmware": previous_decision.firmware,
        "previous_status": previous_decision.status.value,
        "current_status": current_status.value,
        "status_changed": status_changed,
        "filing_changed": filing_changed,
        "previous_filing": previous_decision.filing_impact.value,
        "current_filing": current_filing.value,
        "constraints_added": constraints_added,
        "constraints_removed": constraints_removed,
        "message": (
            f"Release changed living state from {previous_decision.status.value} to {current_status.value}"
            if status_changed else
            (f"Constraints modified: +{len(constraints_added)}, -{len(constraints_removed)}" if (constraints_added or constraints_removed)
             else "No material change in PQC migration envelope")
        ),
    }

    return changed, diff
