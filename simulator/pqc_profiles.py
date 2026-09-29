"""
PQC cryptographic parameter profiles for NIST FIPS 203, 204, 205,
stateful hash signatures (RFC 8554 LMS), and hybrid classical+quantum schemes.
"""

from __future__ import annotations

from typing import Any, Optional

PQC_PROFILES: dict[str, dict[str, Any]] = {
    "ML-DSA-44": {
        "standard": "FIPS 204",
        "type": "Lattice-based (Dilithium)",
        "pk": 1312,
        "sig": 2420,
        "verify_ram": 22_000,
        "code_size_delta": 18_432,   # Additional flash needed for verifier library
        "nist_level": 2,
        "est_verify_cycles_cortex_m4": 1_250_000,  # ~19.5 ms @ 64MHz
    },
    "ML-DSA-65": {
        "standard": "FIPS 204",
        "type": "Lattice-based (Dilithium)",
        "pk": 1952,
        "sig": 3309,
        "verify_ram": 30_000,
        "code_size_delta": 24_576,
        "nist_level": 3,
        "est_verify_cycles_cortex_m4": 2_100_000,  # ~32.8 ms @ 64MHz
    },
    "ML-DSA-87": {
        "standard": "FIPS 204",
        "type": "Lattice-based (Dilithium)",
        "pk": 2592,
        "sig": 4627,
        "verify_ram": 38_000,
        "code_size_delta": 28_672,
        "nist_level": 5,
        "est_verify_cycles_cortex_m4": 3_400_000,
    },
    "ML-KEM-512": {
        "standard": "FIPS 203",
        "type": "Lattice-based KEM (Kyber)",
        "pk": 800,
        "sig": 768,  # Ciphertext
        "verify_ram": 12_000,
        "code_size_delta": 14_336,
        "nist_level": 1,
        "est_verify_cycles_cortex_m4": 480_000,
    },
    "ML-KEM-768": {
        "standard": "FIPS 203",
        "type": "Lattice-based KEM (Kyber)",
        "pk": 1184,
        "sig": 1088,  # Ciphertext
        "verify_ram": 16_000,
        "code_size_delta": 16_384,
        "nist_level": 3,
        "est_verify_cycles_cortex_m4": 720_000,
    },
    "SLH-DSA-SHA2-128s": {
        "standard": "FIPS 205",
        "type": "Stateless Hash (SPHINCS+)",
        "pk": 32,
        "sig": 7856,
        "verify_ram": 8_000,
        "code_size_delta": 12_288,
        "nist_level": 2,
        "est_verify_cycles_cortex_m4": 4_800_000,  # ~75 ms @ 64MHz
    },
    "LMS-SHA256-M32-H10": {
        "standard": "RFC 8554 / SP 800-208",
        "type": "Stateful Hash (LMS)",
        "pk": 56,
        "sig": 1864,
        "verify_ram": 4_096,
        "code_size_delta": 8_192,
        "nist_level": 2,
        "est_verify_cycles_cortex_m4": 180_000,    # ~2.8 ms @ 64MHz
    },
    "hybrid-ECDSA-P256+ML-DSA-44": {
        "standard": "Draft Hybrid / IETF",
        "type": "Hybrid (Classical ECC + ML-DSA-44)",
        "pk": 64 + 1312,
        "sig": 64 + 2420,
        "verify_ram": 24_000,
        "code_size_delta": 22_528,
        "nist_level": 2,
        "est_verify_cycles_cortex_m4": 1_850_000,
    },
    "hybrid-ECDSA-P256+ML-DSA-65": {
        "standard": "Draft Hybrid / IETF",
        "type": "Hybrid (Classical ECC + ML-DSA-65)",
        "pk": 64 + 1952,
        "sig": 64 + 3309,
        "verify_ram": 32_000,
        "code_size_delta": 28_672,
        "nist_level": 3,
        "est_verify_cycles_cortex_m4": 2_700_000,
    },
}

CLASSICAL_SCHEMES: dict[str, dict[str, int]] = {
    "ECDSA-P256": {"pk": 64, "sig": 64, "verify_ram": 6_144},
    "RSA-2048": {"pk": 256, "sig": 256, "verify_ram": 8_192},
    "RSA-4096": {"pk": 512, "sig": 512, "verify_ram": 16_384},
    "Ed25519": {"pk": 32, "sig": 64, "verify_ram": 4_096},
}


def resolve_policy_profile(target_policy: str) -> tuple[str, dict[str, Any]]:
    """
    Maps a high-level policy or scheme name to its primary concrete PQC profile.
    e.g., 'hybrid-pqc' -> ('ML-DSA-65', profile)
    """
    policy_norm = target_policy.strip().lower()

    if policy_norm in ("hybrid-pqc", "hybrid"):
        name = "ML-DSA-65"
        return name, PQC_PROFILES[name]

    if policy_norm in ("fips-204", "ml-dsa", "ml-dsa-44"):
        name = "ML-DSA-44"
        return name, PQC_PROFILES[name]

    if policy_norm in ("ml-dsa-65", "fips-204-l3"):
        name = "ML-DSA-65"
        return name, PQC_PROFILES[name]

    if policy_norm in ("fips-205", "sphincs+", "slh-dsa", "slh-dsa-sha2-128s"):
        name = "SLH-DSA-SHA2-128s"
        return name, PQC_PROFILES[name]

    if policy_norm in ("stateful-hash", "lms", "rfc-8554"):
        name = "LMS-SHA256-M32-H10"
        return name, PQC_PROFILES[name]

    if target_policy in PQC_PROFILES:
        return target_policy, PQC_PROFILES[target_policy]

    # Default fallback
    name = "ML-DSA-44"
    return name, PQC_PROFILES[name]
