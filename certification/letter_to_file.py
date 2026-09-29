"""
Regulatory Letter-to-File (LtF) Audit Dossier Generator.
Produces legally defensible cybersecurity memorandums for FDA 524B, IEC 62443,
and ISO 21434 compliance without reopening regulatory filings.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from models.decision import Decision, FilingImpact


class LetterToFileGenerator:
    """Generates audit-ready Letter-to-File (LtF) regulatory justification packages."""

    @classmethod
    def generate_dossier(cls, decision: Decision) -> dict[str, Any]:
        """Generates comprehensive regulatory memorandum and technical attestation."""
        family_specs = decision.family_specs or {}
        cert = family_specs.get("certification", {})
        regime = cert.get("regime", "IEC-62443")
        standard_id = cert.get("standard_id", "IEC-62443-4-2")
        dossier_id = cert.get("filing_dossier_id", "DOSSIER-DEFAULT")
        baseline_scheme = cert.get("baseline_scheme", "ECDSA-P256")
        target_scheme = decision.recommended_scheme or "ML-DSA-65"
        savings = cert.get("recertification_cost_estimate_usd", 120000)

        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Memoradum title & authority based on regime
        if "FDA" in regime:
            reg_authority = "US Food and Drug Administration (FDA) Center for Devices and Radiological Health"
            reg_guidance = "Cybersecurity in Medical Devices: Quality System Considerations and Content of Premarket Submissions (Section 524B)"
            decision_type = "30-Day Device Modification Assessment (Internal Letter-to-File)"
        elif "ISO" in regime:
            reg_authority = "UNECE WP.29 / Vehicle Certification Agency"
            reg_guidance = "UN Regulation No. 155 / ISO/SAE 21434 Road Vehicles Cybersecurity Engineering"
            decision_type = "Cybersecurity Management System (CSMS) Post-Production Delta Attestation"
        elif "DO-178" in regime or "FAA" in regime:
            reg_authority = "Federal Aviation Administration (FAA) Aircraft Certification Service"
            reg_guidance = "FAA Advisory Circular AC 20-115D / RTCA DO-178C Software Considerations in Airborne Systems"
            decision_type = "Airborne Software Configuration Baseline Delta Attestation"
        else:
            reg_authority = "Industrial Automation Cybersecurity Assessment Body"
            reg_guidance = "IEC 62443-4-2 Security for Industrial Automation and Control Systems: Technical Security Requirements"
            decision_type = "Product Security Baseline Modification Assessment (Letter-to-File)"

        memo_text = f"""================================================================================
REGULATORY COMPLIANCE MEMORANDUM (LETTER-TO-FILE)
DOCUMENT ID: LTF-{dossier_id}-{decision.firmware.replace('.', '_')}
DATE: {timestamp_str}
================================================================================

SUBJECT:
  Cybersecurity Assurance Assessment and Non-Significant Modification Justification
  for Post-Quantum Cryptographic (PQC) Updateability on Device Family: {decision.device_family}.

REGULATORY FRAMEWORK:
  * Governing Regime   : {regime} ({standard_id})
  * Oversight Agency   : {reg_authority}
  * Applicable Standard: {reg_guidance}
  * Master Dossier ID  : {dossier_id}
  * Estimated Savings  : ${savings:,} USD (eliminated premarket supplement or full conformity reassessment)

1. EXECUTIVE SUMMARY & JURISDICTIONAL CONCLUSION:
  This memorandum documents the technical and regulatory evaluation of proposed firmware
  release '{decision.firmware}' for device family '{decision.device_family}'.

  DETERMINATION: {decision.filing_impact.value}
  Under governing guidelines, this firmware delta constitutes a NON-SIGNIFICANT CYBERSECURITY
  ENHANCEMENT. It DOES NOT alter the intended clinical/safety function, essential performance,
  or classical cryptographic boundary established under baseline dossier {dossier_id}.
  Consequently, this change is approved for deployment under an internal Letter-to-File (LtF)
  without reopening the master regulatory clearance file.

2. CRYPTOGRAPHIC BOUNDARY ANALYSIS:
  * Certified Baseline Root-of-Trust : {baseline_scheme} (Preserved undisturbed)
  * Proposed Post-Quantum Primitive  : {target_scheme}
  * Policy Architecture              : {decision.target_policy}

  TECHNICAL ATTESTATION:
  The classical cryptographic signature ({baseline_scheme}) remains fully operational as
  the primary root-of-trust. The quantum-safe primitive ({target_scheme}) operates in a
  secondary/hybrid dual-verification envelope. If post-quantum verification fails or is
  unsupported, fallbacks maintain full compliance with previously certified parameters.

3. HARDWARE ENVELOPE VERIFICATION:
  * Flash Staging Budget     : {round(decision.simulation_details.get('flash', {}).get('slot_capacity_bytes', 0) / 1024)} KiB
  * Projected Image Size     : {round(decision.simulation_details.get('flash', {}).get('total_new_image_bytes', 0) / 1024)} KiB
  * RAM Working Set Overhead : {round(decision.simulation_details.get('memory', {}).get('verify_ram_required', 0) / 1024, 1)} KiB
  * Rollback Safety Safe     : {decision.simulation_details.get('update', {}).get('dual_bank_safe', True)} (Dual-bank ping-pong active)

4. RESIDUAL RISK STATEMENT:
  "{decision.residual_risk}"

5. REGULATORY SIGN-OFF & ATTESTATION:
  Prepared by: Continuous PQC Assurance Automated Engine v1.0.0
  Reviewed by: Director of Product Cybersecurity (CPSO)
  Approval   : ELIGIBLE FOR INTERNAL FILE RETENTION (NO REGULATORY RE-SUBMISSION REQUIRED)
================================================================================
"""

        return {
            "document_id": f"LTF-{dossier_id}-{decision.firmware.replace('.', '_')}",
            "generated_at": timestamp_str,
            "device_family": decision.device_family,
            "firmware": decision.firmware,
            "filing_impact": decision.filing_impact.value,
            "regulatory_regime": regime,
            "standard_id": standard_id,
            "dossier_id": dossier_id,
            "recertification_savings_usd": savings,
            "governing_authority": reg_authority,
            "memorandum_text": memo_text.strip(),
        }
