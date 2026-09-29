"""
Unit tests for the Analyzer component.
Tests cryptographic discovery, binary sections, and entropy estimation.
"""

from __future__ import annotations

import unittest
from analyzer.crypto import scan_crypto_constants, infer_active_scheme
from analyzer.binary import calculate_entropy, decompose_sections, detect_components
from analyzer.firmware import FirmwareAnalyzer


class TestAnalyzer(unittest.TestCase):
    def setUp(self):
        # Create a synthetic image with SHA-256 and ECC constants
        sha256_k = bytes.fromhex("428a2f9871374491b5c0fbcfe9b5dba5")
        p256_prime = bytes.fromhex("ffffffff00000001000000000000000000000000ffffffffffffffffffffffff")
        self.image = b"HDR" + (b"\x00" * 253) + sha256_k + p256_prime + (b"\x55" * 1024)

    def test_scan_crypto_constants(self):
        findings = scan_crypto_constants(self.image)
        algorithms = {f.algorithm for f in findings}
        self.assertIn("SHA256", algorithms)
        self.assertIn("ECDSA_P256_PRIME", algorithms)

    def test_infer_active_scheme(self):
        findings = scan_crypto_constants(self.image)
        scheme = infer_active_scheme(findings)
        self.assertEqual(scheme, "ECDSA-P256")

    def test_calculate_entropy(self):
        uniform_data = bytes([i % 256 for i in range(1024)])
        entropy = calculate_entropy(uniform_data)
        self.assertGreater(entropy, 7.5)

    def test_firmware_analyzer_pipeline(self):
        release = FirmwareAnalyzer.analyze_bytes(
            image=self.image,
            firmware_id="test-fw.bin",
            family_id="controller-x7",
            version="1.0.0",
        )
        self.assertEqual(release.firmware_id, "test-fw.bin")
        self.assertGreater(len(release.findings), 0)
        self.assertGreater(release.raw_size_bytes, 1000)


if __name__ == "__main__":
    unittest.main()
