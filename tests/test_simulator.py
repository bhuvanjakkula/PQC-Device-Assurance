"""
Unit tests for the Simulator component.
Tests flash delta, RAM/stack delta, update fit, and PQC profile mappings.
"""

from __future__ import annotations

import unittest
from data.catalog import get_device_family
from analyzer.firmware import FirmwareAnalyzer
from simulator.simulator import PQCMigrationSimulator
from simulator.pqc_profiles import PQC_PROFILES, resolve_policy_profile


class TestSimulator(unittest.TestCase):
    def setUp(self):
        self.family = get_device_family("controller-x7")
        self.small_image = b"HDR" + (b"\x00" * 253) + (b"\xFF" * (200 * 1024))
        self.fw_release = FirmwareAnalyzer.analyze_bytes(
            image=self.small_image,
            firmware_id="test-small.bin",
            family_id="controller-x7",
        )

    def test_resolve_policy_profile(self):
        name, prof = resolve_policy_profile("hybrid-pqc")
        self.assertEqual(name, "ML-DSA-65")
        self.assertIn("sig", prof)
        self.assertIn("pk", prof)

    def test_pqc_migration_simulation(self):
        report = PQCMigrationSimulator.simulate(
            family=self.family,
            firmware=self.fw_release,
            target_policy="hybrid-pqc",
        )
        self.assertEqual(report.evaluated_scheme, "ML-DSA-65")
        self.assertFalse(report.flash.slot_exceeded)
        self.assertTrue(report.memory.kem_fits_ram)
        self.assertTrue(report.update.dual_bank_safe)


if __name__ == "__main__":
    unittest.main()
