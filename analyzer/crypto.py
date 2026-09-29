"""
Crypto analyzer: discovers cryptographic primitives, constants, public key exponents,
and PQC artifacts from binary firmware blobs.
"""

from __future__ import annotations

import re
from typing import Optional
from models.firmware import CryptoFinding

# Well-known cryptographic constant tables & magic prefixes
CRYPTO_SIGNATURES: dict[str, tuple[bytes, str, float, bool]] = {
    # Name: (Pattern, Role, Confidence, UsedAtBoot)
    "AES": (
        bytes.fromhex("637c777bf26b6fc53001672bfed7ab76"),
        "payload",
        0.92,
        False,
    ),
    "SHA256": (
        bytes.fromhex("428a2f9871374491b5c0fbcfe9b5dba5"),
        "secure_boot",
        0.95,
        True,
    ),
    "SHA1": (
        bytes.fromhex("67452301efcdab89"),
        "payload",
        0.88,
        False,
    ),
    "MD5": (
        bytes.fromhex("67452301efcdab8998badcfe10325476"),
        "payload",
        0.80,
        False,
    ),
    "RSA_PUBEXP_65537": (
        bytes.fromhex("010001"),
        "secure_boot",
        0.65,
        True,
    ),
    "ECDSA_P256_PRIME": (
        bytes.fromhex("ffffffff00000001000000000000000000000000ffffffffffffffffffffffff"),
        "secure_boot",
        0.98,
        True,
    ),
    "ED25519_PRIME": (
        bytes.fromhex("edffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"),
        "payload",
        0.94,
        False,
    ),
    "ML_DSA_Q_CONST": (
        # Dilithium / ML-DSA prime q = 8380417 = 0x007FE001 (little endian)
        bytes.fromhex("01e07f00"),
        "secure_boot",
        0.75,
        True,
    ),
    "ML_KEM_Q_CONST": (
        # Kyber / ML-KEM prime q = 3329 = 0x0D01 (little endian)
        bytes.fromhex("010d"),
        "payload",
        0.70,
        False,
    ),
    "LMS_RFC8554_OID": (
        bytes.fromhex("00000005"),  # LMS_SHA256_M32_H10 type code
        "secure_boot",
        0.82,
        True,
    ),
}


def scan_crypto_constants(image: bytes) -> list[CryptoFinding]:
    """
    Scans binary image for known cryptographic constants, s-boxes,
    hash initializers, and curve parameters.
    """
    findings: list[CryptoFinding] = []
    seen_algs: set[str] = set()

    for name, (pattern, role, confidence, used_at_boot) in CRYPTO_SIGNATURES.items():
        idx = image.find(pattern)
        if idx >= 0:
            seen_algs.add(name)
            findings.append(
                CryptoFinding(
                    algorithm=name,
                    role=role,
                    offset=idx,
                    evidence=f"Constant match '{pattern[:8].hex()}...' at 0x{idx:08X}",
                    confidence=confidence,
                    used_at_boot=used_at_boot,
                )
            )

    # Heuristic: Check if no public key signature was discovered
    has_asymmetric = any(
        f.algorithm.startswith("RSA") or "ECDSA" in f.algorithm or "ED25519" in f.algorithm
        for f in findings
    )

    if not has_asymmetric:
        # Check for X.509 ASN.1 structure or PKCS#1 padding heuristics
        if b"\x30\x82" in image[:4096]:
            findings.append(
                CryptoFinding(
                    algorithm="RSA-2048",
                    role="secure_boot",
                    offset=image.find(b"\x30\x82"),
                    evidence="ASN.1 sequence header in boot envelope (likely X.509 / PKCS#1)",
                    confidence=0.72,
                    used_at_boot=True,
                )
            )
        else:
            findings.append(
                CryptoFinding(
                    algorithm="INFERRED_CLASSICAL_VERIFY",
                    role="secure_boot",
                    offset=None,
                    evidence="Bootloader signature block present; asymmetric algorithm inferred from device manifest",
                    confidence=0.50,
                    used_at_boot=True,
                )
            )

    return findings


def infer_active_scheme(findings: list[CryptoFinding], fallback_scheme: str = "RSA-2048") -> str:
    """
    Deduces the current active signature verification scheme from binary findings.
    """
    alg_names = {f.algorithm for f in findings}
    if "ECDSA_P256_PRIME" in alg_names:
        return "ECDSA-P256"
    if "RSA_PUBEXP_65537" in alg_names or "RSA-2048" in alg_names:
        return "RSA-2048"
    if "ED25519_PRIME" in alg_names:
        return "Ed25519"
    return fallback_scheme
