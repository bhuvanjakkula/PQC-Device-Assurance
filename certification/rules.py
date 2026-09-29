"""
Regulatory and certification rules engine.
Defines filing thresholds, change significance tests, and compliance rules
for FDA-524B, IEC-62443, ISO-21434, and EU-RED.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from models.device import RegulatoryRegime


@dataclass
class CertificationRule:
    rule_id: str
    regime: RegulatoryRegime
    title: str
    condition_description: str
    requires_premarket_update: bool
    rationale: str


REGULATORY_RULES: list[CertificationRule] = [
    CertificationRule(
        rule_id="FDA-524B-01",
        regime=RegulatoryRegime.FDA_524B,
        title="Removal of Primary Classical Digital Signature",
        condition_description="Switching exclusively to pure PQC without classical dual-signing",
        requires_premarket_update=True,
        rationale="Alters the certified cryptographic boundary and root-of-trust under Section 524B; requires 510(k) / PMA supplement.",
    ),
    CertificationRule(
        rule_id="FDA-524B-02",
        regime=RegulatoryRegime.FDA_524B,
        title="Hybrid PQC Dual-Signing Maintenance",
        condition_description="Adding PQC signature while retaining active classical ECDSA/RSA verification",
        requires_premarket_update=False,
        rationale="Retains certified security guarantees while adding defense-in-depth; qualifies for Letter-to-File under FDA Cybersecurity in Medical Devices guidance.",
    ),
    CertificationRule(
        rule_id="IEC-62443-01",
        regime=RegulatoryRegime.IEC_62443,
        title="Industrial Controller Secure Boot Path Modification",
        condition_description="Modifying Stage-1 SPL execution flow or security boundary",
        requires_premarket_update=False,
        rationale="Annual surveillance audit delta documentation sufficient if security level (SL-3) is not degraded.",
    ),
    CertificationRule(
        rule_id="ISO-21434-01",
        regime=RegulatoryRegime.ISO_21434,
        title="Automotive ECU OTA Cryptographic Envelope Expansion",
        condition_description="OTA framing packet change without changing vehicle gateway E/E architecture",
        requires_premarket_update=False,
        rationale="Internal TARA (Threat Analysis and Risk Assessment) update logged; no UNECE R155 type-approval renewal triggered.",
    ),
]
