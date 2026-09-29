"""
Compensating Controls and Automated Remediation Advisor.
Synthesizes concrete engineering patches and algorithm trade-offs
to resolve identified PQC migration constraints without hardware re-spins.
"""

from __future__ import annotations

from typing import Any
from models.decision import Decision, MigrationStatus


class CompensatingControlAdvisor:
    """Evaluates active constraints and synthesizes technical remediation recommendations."""

    @classmethod
    def analyze_and_advise(cls, decision: Decision) -> list[dict[str, Any]]:
        """Produces ordered remediation actions for active constraints."""
        recommendations: list[dict[str, Any]] = []
        constraints = decision.constraints or []
        family_specs = decision.family_specs or {}
        hw = family_specs.get("hardware", {})
        boot = family_specs.get("boot", {})

        # 1. Evaluate OTA slot bloat / algorithm optimization (Always available for PQC trade-offs)
        recommendations.append({
            "id": "REMED-FLASH-01",
            "title": "NIST Algorithm Substitution (ML-DSA-44 or LMS)",
            "category": "Algorithm Optimization",
            "impact": "Reclaims up to 16 KiB flash code space and 889 B signature envelope",
            "urgency": "High",
            "technical_details": (
                "ML-DSA-65 signature requires 3,309 bytes and 24.5 KiB verifier code. "
                "Substituting with NIST Level 2 ML-DSA-44 (2,420 B sig, 18.4 KiB code) or "
                "RFC 8554 LMS-SHA256 (1,864 B sig, 8.1 KiB code) brings total image size within budget."
            ),
            "remediation_patch": "target_policy: fips-204 (ML-DSA-44) OR stateful-hash (LMS-SHA256)",
        })

        recommendations.append({
            "id": "REMED-FLASH-02",
            "title": "Partition Table Re-allocation & Staging Asset Compression",
            "category": "Flash Partitioning",
            "impact": "Reallocates 48 KiB from diagnostic log partition to Slot B",
            "urgency": "Medium",
            "technical_details": (
                "Current partition layout allocates non-critical log space. By updating the DTS/dtsi "
                "flash map, Slot B can be expanded by 48 KiB while applying LZ4 compression to "
                "non-executable static telemetry tables."
            ),
            "remediation_patch": (
                "/* device-tree partition patch */\n"
                "slot1_partition: partition@70000 {\n"
                "    reg = <0x00070000 0x0007c000>; /* Expanded by 48 KiB */\n"
                "};"
            ),
        })

        # 2. Evaluate Bootloader verification path modifications (SPL hook)
        recommendations.append({
            "id": "REMED-BOOT-01",
            "title": "Second-Stage Bootloader (SPL) Verification Hook",
            "category": "Boot Architecture",
            "impact": "Preserves immutable primary stage while delegating PQC verification to mutable SPL",
            "urgency": "Medium",
            "technical_details": (
                "Primary stage bootloader verifies SPL using certified classical key (ECDSA-P256). "
                "The SPL contains the quantum-safe verifier library, verifying the OS kernel before execution. "
                "Ensures zero risk to first-stage recovery bootloader."
            ),
            "remediation_patch": (
                "// mcuboot / spl hook config\n"
                "#define MCUBOOT_SIGN_PQC_HYBRID 1\n"
                "#define MCUBOOT_VALIDATE_SECONDARY_SLOT 1"
            ),
        })

        # 3. Evaluate Boot-time RAM exhaustion
        ram_exceeded = any("exceeds boot-time RAM" in c or "ram" in c.lower() for c in constraints)
        if ram_exceeded or decision.status == MigrationStatus.REDESIGN_REQUIRED:
            recommendations.append({
                "id": "REMED-RAM-01",
                "title": "Streamed Chunk Verification & Stack Re-use",
                "category": "Memory Architecture",
                "impact": "Reduces boot-time RAM working set from 30 KiB down to 4 KiB",
                "urgency": "Critical",
                "technical_details": (
                    "Standard monolithic lattice verification requires holding polynomial vectors in SRAM. "
                    "Switching to Hash-based signatures (LMS/XMSS) or chunked SHA3-SHAKE streaming "
                    "allows verification on microcontrollers with as little as 6 KiB usable SRAM."
                ),
                "remediation_patch": "#define PQC_STREAMING_VERIFY_CHUNK_SIZE 512\n#define USE_RFC8554_LMS_LIGHTWEIGHT 1",
            })

        # 4. Evaluate ROM lock (Blocked state)
        rom_locked = boot.get("verify_in_rom", False) and not boot.get("allows_bootloader_ota", False)
        if rom_locked or decision.status == MigrationStatus.BLOCKED:
            recommendations.append({
                "id": "REMED-ROM-01",
                "title": "Cryptographic Perimeter Encapsulation (Gateway Proxy)",
                "category": "Compensating Control",
                "impact": "Protects un-patchable legacy silicon against quantum intercept-now-decrypt-later attacks",
                "urgency": "Mandatory",
                "technical_details": (
                    "Silicon mask-ROM cannot be modified via software OTA. "
                    "Enforce TLS 1.3 + ML-KEM-768 quantum encapsulation at the field gateway / edge firewall. "
                    "Firmware delivery tunnel is quantum-shielded before terminal verification."
                ),
                "remediation_patch": "Enforce Quantum-Safe Mutual TLS (mTLS) with ML-KEM-768 on Edge Gateway Proxy",
            })

        return recommendations
