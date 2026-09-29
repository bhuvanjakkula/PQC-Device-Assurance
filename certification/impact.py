"""
Certification Impact Engine: evaluates regulatory drift and recertification triggers.
Answers: Does this firmware release trigger unnecessary recertification, or can we deploy
under 'Letter-to-File' or 'No Reopen'?
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from models.decision import FilingImpact, MigrationStatus
from models.device import DeviceFamily, RegulatoryRegime


@dataclass
class CertificationImpactAssessment:
    regime: RegulatoryRegime
    filing_impact: FilingImpact
    dossier_id: str
    reopen_required: bool
    filing_rationale: str
    letter_to_file_justification: Optional[str]
    estimated_audit_savings_usd: int


class CertificationImpactEngine:
    """
    Evaluates regulatory compliance impact of proposed PQC firmware migrations.
    """

    @staticmethod
    def assess_impact(
        family: DeviceFamily,
        status: MigrationStatus,
        target_scheme: str,
        target_policy: str = "hybrid-pqc",
        previous_decision_status: Optional[MigrationStatus] = None,
        previous_scheme: Optional[str] = None,
    ) -> CertificationImpactAssessment:
        regime = family.certification.regime
        dossier_id = family.certification.filing_dossier_id
        savings = family.certification.recertification_cost_estimate_usd

        # If unregulated
        if regime == RegulatoryRegime.NONE:
            return CertificationImpactAssessment(
                regime=regime,
                filing_impact=FilingImpact.NO_REOPEN,
                dossier_id=dossier_id,
                reopen_required=False,
                filing_rationale="Device family operates in unregulated tier; no external filing required.",
                letter_to_file_justification=None,
                estimated_audit_savings_usd=0,
            )

        # Baseline certified release with status CAN_MIGRATE
        if status == MigrationStatus.CAN_MIGRATE and previous_decision_status is None:
            return CertificationImpactAssessment(
                regime=regime,
                filing_impact=FilingImpact.NO_REOPEN,
                dossier_id=dossier_id,
                reopen_required=False,
                filing_rationale="Baseline certified release fits all cryptographic and memory margins; zero regulatory reopen required.",
                letter_to_file_justification="Existing certification dossier remains fully active and unperturbed.",
                estimated_audit_savings_usd=0,
            )

        # If release didn't change migration posture or scheme from previously certified state
        if (
            previous_decision_status == status
            and previous_scheme == target_scheme
            and status == MigrationStatus.CAN_MIGRATE
        ):
            return CertificationImpactAssessment(
                regime=regime,
                filing_impact=FilingImpact.NO_REOPEN,
                dossier_id=dossier_id,
                reopen_required=False,
                filing_rationale="Firmware release delta remains within established PQC assurance envelope; no regulatory file reopen needed.",
                letter_to_file_justification="Baseline cybersecurity documentation remains valid; zero change to certified cryptographic boundary.",
                estimated_audit_savings_usd=savings,
            )

        # If device is BLOCKED or REQUIRES_REDESIGN, no on-device crypto change is shipped
        if status in (MigrationStatus.BLOCKED, MigrationStatus.REDESIGN_REQUIRED):
            return CertificationImpactAssessment(
                regime=regime,
                filing_impact=FilingImpact.NO_REOPEN,
                dossier_id=dossier_id,
                reopen_required=False,
                filing_rationale="No on-device cryptographic migration deployed; existing regulatory clearance remains undisturbed.",
                letter_to_file_justification=None,
                estimated_audit_savings_usd=0,
            )

        # If device can migrate with constraints under a HYBRID scheme:
        # Standard regulatory guidance (FDA, ISO 21434) allows Letter-to-File if classical signatures remain active
        is_hybrid = target_policy.startswith("hybrid") or target_scheme.startswith("hybrid")
        if is_hybrid:
            return CertificationImpactAssessment(
                regime=regime,
                filing_impact=FilingImpact.LETTER_TO_FILE,
                dossier_id=dossier_id,
                reopen_required=False,
                filing_rationale="Hybrid dual-signing preserves classical root-of-trust while adding post-quantum protection; eligible for internal Letter-to-File.",
                letter_to_file_justification=(
                    f"Firmware update adds secondary quantum-safe verification without degrading or replacing "
                    f"the certified {family.certification.baseline_scheme} root key. Evaluated under {regime.value} "
                    f"guidelines as a non-significant security enhancement."
                ),
                estimated_audit_savings_usd=savings,
            )

        # Pure PQC replacement (e.g. stripping classical RSA/ECDSA for pure ML-DSA):
        # Triggers full premarket regulatory submission
        return CertificationImpactAssessment(
            regime=regime,
            filing_impact=FilingImpact.PREMARKET_UPDATE,
            dossier_id=dossier_id,
            reopen_required=True,
            filing_rationale=(
                f"Full cryptographic boundary transition to {target_scheme} alters certified root-of-trust; "
                f"triggers mandatory {regime.value} premarket update."
            ),
            letter_to_file_justification=None,
            estimated_audit_savings_usd=0,
        )
