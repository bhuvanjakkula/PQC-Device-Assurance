"""
End-to-end integration test verifying the exact developer snippet:
decision = assess(
    device_family="controller-x7",
    firmware="firmware-4.18.2.bin",
    target_policy="hybrid-pqc",
)

print(decision.status)
# CAN_MIGRATE_WITH_CONSTRAINTS

print(decision.constraints)
# [
#   "OTA slot exceeds available flash by 84 KiB with ML-DSA-65",
#   "ML-KEM-768 fits RAM budget",
#   "Bootloader verification path requires modification"
# ]

print(decision.changed_since_previous_release)
# True
"""

from __future__ import annotations

import unittest
from decision.engine import assess
from models.decision import MigrationStatus


class TestAssessAPI(unittest.TestCase):
    def test_controller_x7_assessment(self):
        decision = assess(
            device_family="controller-x7",
            firmware="firmware-4.18.2.bin",
            target_policy="hybrid-pqc",
        )

        # 1. Verify Status
        self.assertEqual(decision.status, MigrationStatus.CAN_MIGRATE_WITH_CONSTRAINTS)
        self.assertEqual(str(decision.status), "CAN_MIGRATE_WITH_CONSTRAINTS")

        # 2. Verify Constraints
        expected_constraints = [
            "OTA slot exceeds available flash by 84 KiB with ML-DSA-65",
            "ML-KEM-768 fits RAM budget",
            "Bootloader verification path requires modification",
        ]
        self.assertEqual(decision.constraints, expected_constraints)

        # 3. Verify Changed Since Previous Release
        self.assertTrue(decision.changed_since_previous_release)

    def test_acme_pump_blocked_state(self):
        # Acme pump has ROM locked verification and single bank
        decision = assess(
            device_family="acme-pump-m3-revc",
            firmware="pump-firmware-2.5.0.bin",
            target_policy="ml-dsa-65",
        )
        self.assertEqual(decision.status, MigrationStatus.BLOCKED)

    def test_controller_x7_baseline_scenario2(self):
        decision = assess(
            device_family="controller-x7",
            firmware="firmware-4.18.1.bin",
            target_policy="hybrid-pqc",
        )
        self.assertEqual(decision.status, MigrationStatus.CAN_MIGRATE)
        self.assertEqual(decision.constraints, [])
        self.assertFalse(decision.changed_since_previous_release)
        self.assertEqual(str(decision.filing_impact), "NO_REOPEN")


if __name__ == "__main__":
    unittest.main()

