"""
CycloneDX 1.6 Cryptographic Bill of Materials (CBOM) Generator.
Compliant with CISA Post-Quantum Readiness guidelines and NIST SP 800-227.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from models.decision import Decision


class CBOMGenerator:
    """Generates CycloneDX 1.6 compliant Cryptographic Bill of Materials."""

    PQC_OIDS = {
        "ML-DSA-44": "2.16.840.1.101.3.4.3.17",
        "ML-DSA-65": "2.16.840.1.101.3.4.3.18",
        "ML-DSA-87": "2.16.840.1.101.3.4.3.19",
        "ML-KEM-768": "2.16.840.1.101.3.4.4.2",
        "SLH-DSA-SHA2-128f": "2.16.840.1.101.3.4.3.22",
        "LMS-SHA256": "1.2.840.113549.1.9.16.3.17",
    }

    NIST_LEVELS = {
        "ML-DSA-44": 2,
        "ML-DSA-65": 3,
        "ML-DSA-87": 5,
        "ML-KEM-768": 3,
        "SLH-DSA-SHA2-128f": 1,
        "LMS-SHA256": 1,
    }

    @classmethod
    def generate_cyclonedx_1_6(cls, decision: Decision) -> dict[str, Any]:
        """Produces a valid CycloneDX 1.6 CBOM document."""
        scheme = decision.recommended_scheme or "ML-DSA-65"
        oid = cls.PQC_OIDS.get(scheme, "2.16.840.1.101.3.4.3.18")
        nist_lvl = cls.NIST_LEVELS.get(scheme, 3)

        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.6",
            "serialNumber": f"urn:uuid:{uuid.uuid4()}",
            "version": 1,
            "metadata": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tools": [
                    {
                        "vendor": "Antigravity PQC Assurance",
                        "name": "pqc-device-assurance-engine",
                        "version": "1.0.0",
                    }
                ],
                "component": {
                    "type": "firmware",
                    "name": f"{decision.device_family}-release",
                    "version": decision.firmware,
                    "description": f"Target firmware image evaluated for post-quantum updateability on {decision.device_family}.",
                },
                "manufacture": {
                    "name": decision.family_specs.get("vendor", "Embedded OEM"),
                },
            },
            "components": [
                {
                    "type": "cryptographic-asset",
                    "name": scheme,
                    "version": "FIPS 204 Draft / Final",
                    "description": "Post-quantum digital signature algorithm deployed for secure boot and OTA verification.",
                    "cryptoProperties": {
                        "assetType": "algorithm",
                        "algorithmProperties": {
                            "primitive": "signature",
                            "parameterSetIdentifier": scheme,
                            "executionEnvironment": "bare-metal-bootloader",
                            "implementationPlatform": decision.family_specs.get("soc_arch", "ARM Embedded"),
                            "certificationLevel": f"NIST SP 800-227 Level {nist_lvl}",
                            "cryptoFunctions": ["verify", "authenticate"],
                            "classicalSecurityEquivalentBits": 128 if nist_lvl <= 2 else 192,
                        },
                        "oid": oid,
                        "nistQuantumSecurityLevel": nist_lvl,
                    },
                },
                {
                    "type": "cryptographic-asset",
                    "name": "Classical Baseline (Root-of-Trust)",
                    "version": "Pre-quantum",
                    "description": "Certified classical signature primitive before PQC migration.",
                    "cryptoProperties": {
                        "assetType": "algorithm",
                        "algorithmProperties": {
                            "primitive": "signature",
                            "parameterSetIdentifier": decision.family_specs.get("certification", {}).get("baseline_scheme", "ECDSA-P256"),
                            "executionEnvironment": "immutable-rom-or-spl",
                            "cryptoFunctions": ["verify"],
                        },
                        "nistQuantumSecurityLevel": 0,
                    },
                },
            ],
            "declarations": {
                "assessment": {
                    "pqc_migration_status": decision.status.value,
                    "regulatory_filing_impact": decision.filing_impact.value,
                    "constraints_identified": decision.constraints,
                    "residual_risk": decision.residual_risk,
                }
            },
        }
