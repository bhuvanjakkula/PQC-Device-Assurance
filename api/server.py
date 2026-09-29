"""
REST API and Web Server for Continuous PQC Updateability Assurance.
Provides endpoints for CI/CD runners, dashboard telemetry, and interactive assessment.
Strictly gated by authentication and commercial payment licensing:
- Unauthenticated users cannot access the website.
- Customers without active paid subscription cannot access the website.
- Only owner bhuvanjakkula@gmail.com can access without paying money.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional, Dict, Any

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.catalog import FAMILY_CATALOG, get_device_family
from decision.engine import assess, DEFAULT_DB_PATH
from decision.regression import ReleaseHistoryStore
from models.decision import MigrationStatus, FilingImpact
from models.device import (
    DeviceFamily,
    HardwareConstraints,
    BootArchitecture,
    CertificationBaseline,
    RegulatoryRegime,
)
from certification.cbom import CBOMGenerator
from certification.letter_to_file import LetterToFileGenerator
from decision.compensating_controls import CompensatingControlAdvisor
from simulator.matrix import AlgorithmMatrixEngine
from api.auth import AuthManager, OWNER_EMAIL


WEB_DIR = PROJECT_ROOT / "web"
auth_mgr = AuthManager(DEFAULT_DB_PATH)


class AssuranceAPIHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler providing REST API and serving Web Assets."""

    def _set_headers(self, status_code: int = 200, content_type: str = "application/json"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Auth-Token, X-Device-Family, X-Target-Policy, X-Filename")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def _get_authenticated_user(self) -> Optional[Dict[str, Any]]:
        """Extract and validate session token from Authorization header, X-Auth-Token or Cookie."""
        token = ""
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        if not token:
            token = self.headers.get("X-Auth-Token", "").strip()
        if not token:
            cookie_hdr = self.headers.get("Cookie", "")
            if "pqc_token=" in cookie_hdr:
                for part in cookie_hdr.split(";"):
                    if "pqc_token=" in part:
                        token = part.split("pqc_token=")[1].strip()
                        break
        if not token:
            parsed = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(parsed.query)
            if "token" in q:
                token = q["token"][0].strip()

        if not token:
            return None
        return auth_mgr.get_user_from_token(token)

    def _require_access(self) -> Optional[Dict[str, Any]]:
        """
        Enforce strict access control:
        - Must be signed in.
        - Must be paying customer OR owner (bhuvanjakkula@gmail.com).
        """
        user = self._get_authenticated_user()
        if not user:
            self._set_headers(401)
            self.wfile.write(json.dumps({
                "error": "Authentication required. You must sign up or sign in to access the website.",
                "code": "AUTH_REQUIRED"
            }).encode("utf-8"))
            return None

        # Check payment requirement: Only owner (bhuvanjakkula@gmail.com) is exempt!
        if not user["is_owner"] and not user["is_paid"]:
            self._set_headers(402)
            self.wfile.write(json.dumps({
                "error": "Active commercial subscription required. Customers cannot access without payment.",
                "code": "PAYMENT_REQUIRED",
                "email": user["email"],
                "plan": user.get("plan", "Starter")
            }).encode("utf-8"))
            return None

        return user

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # -------------------------------------------------------------
        # Public Endpoints
        # -------------------------------------------------------------
        if path == "/api/auth/me":
            user = self._get_authenticated_user()
            if user:
                self._set_headers(200)
                self.wfile.write(json.dumps({"authenticated": True, "user": user}).encode("utf-8"))
            else:
                self._set_headers(200)
                self.wfile.write(json.dumps({"authenticated": False, "user": None}).encode("utf-8"))
            return

        if path == "/api/plans":
            plans = [
                {
                    "plan": "Starter",
                    "best_for": "Startups / small embedded teams",
                    "device_families": "1–3",
                    "monthly_recurring_usd": 1500,
                    "monthly_recurring_str": "$1,500/mo",
                    "stripe_payment_url": "https://buy.stripe.com/test_bJe7sDdBQ9y50azbwy2oE0m",
                    "features": [
                        "1–3 Device Families",
                        "Continuous binary CI/CD assessment",
                        "MCUboot & partition budget tracking",
                        "CycloneDX 1.6 CBOM export",
                        "Standard email support"
                    ],
                },
                {
                    "plan": "Professional",
                    "best_for": "Growing IoT / hardware companies",
                    "device_families": "Up to 10",
                    "monthly_recurring_usd": 4000,
                    "monthly_recurring_str": "$4,000/mo",
                    "stripe_payment_url": "https://buy.stripe.com/test_6oUcMX41g25De1p6ce2oE0n",
                    "popular": True,
                    "features": [
                        "Up to 10 Device Families",
                        "Everything in Starter",
                        "NIST Algorithm Substitution Matrix",
                        "Self-Healing Migration Advisor (.patch)",
                        "Release History & Regression tracking",
                        "Priority SLA support"
                    ],
                },
                {
                    "plan": "Enterprise",
                    "best_for": "Automotive, medical, industrial OEMs",
                    "device_families": "Up to 30",
                    "monthly_recurring_usd": 10000,
                    "monthly_recurring_str": "$10,000/mo",
                    "stripe_payment_url": "https://buy.stripe.com/test_14AcMXapE39He1p9oq2oE0o",
                    "features": [
                        "Up to 30 Device Families",
                        "Everything in Professional",
                        "Autonomous Letter-to-File (Zero Reopen)",
                        "FDA 524B / ISO 21434 / IEC 62443 Dossiers",
                        "Hardware OTP ROM keystore verification",
                        "Air-gapped on-premise runner support",
                        "Dedicated security architect"
                    ],
                },
                {
                    "plan": "Enterprise+",
                    "best_for": "Large OEMs / critical infrastructure",
                    "device_families": "100+ / negotiated",
                    "monthly_recurring_usd": 25000,
                    "monthly_recurring_str": "$25,000+/mo",
                    "stripe_payment_url": "https://buy.stripe.com/test_cNifZ90P425D2iH4462oE0p",
                    "features": [
                        "100+ Device Families / Negotiated",
                        "Everything in Enterprise",
                        "Custom silicon ASIC / FPGA envelope modeling",
                        "Dedicated regulatory legal defense packages",
                        "Tailored dual-signing bootloader kernels",
                        "Executive audit sign-off attestation"
                    ],
                },
            ]
            self._set_headers(200)
            self.wfile.write(json.dumps(plans, indent=2).encode("utf-8"))
            return

        # -------------------------------------------------------------
        # Protected Data & Simulation Endpoints
        # -------------------------------------------------------------
        if path == "/api/families":
            user = self._require_access()
            if not user:
                return
            families_data = [f.to_dict() for f in FAMILY_CATALOG.values()]
            self._set_headers(200)
            self.wfile.write(json.dumps(families_data).encode("utf-8"))
            return

        if path == "/api/history":
            user = self._require_access()
            if not user:
                return
            family_id = query.get("family", ["controller-x7"])[0]
            store = ReleaseHistoryStore(DEFAULT_DB_PATH)
            history = store.get_all_for_family(family_id)
            self._set_headers(200)
            self.wfile.write(json.dumps([h.to_dict() for h in history]).encode("utf-8"))
            return

        if path == "/api/history-item":
            user = self._require_access()
            if not user:
                return
            family_id = query.get("family", ["controller-x7"])[0]
            firmware_id = query.get("firmware", [""])[0]
            store = ReleaseHistoryStore(DEFAULT_DB_PATH)
            history = store.get_all_for_family(family_id)
            match = next((h for h in history if h.firmware == firmware_id), None)
            if match:
                self._set_headers(200)
                self.wfile.write(match.to_json().encode("utf-8"))
            else:
                decision = assess(family_id, firmware_id, "hybrid-pqc")
                self._set_headers(200)
                self.wfile.write(decision.to_json().encode("utf-8"))
            return

        if path == "/api/sample-assessment":
            user = self._require_access()
            if not user:
                return
            decision = assess("controller-x7", "firmware-4.18.2.bin", "hybrid-pqc")
            self._set_headers(200)
            self.wfile.write(decision.to_json().encode("utf-8"))
            return

        if path == "/api/samples":
            user = self._require_access()
            if not user:
                return
            samples_dir = PROJECT_ROOT / "samples"
            samples_list = []
            if samples_dir.exists():
                for f in sorted(samples_dir.glob("*.bin")):
                    samples_list.append({
                        "filename": f.name,
                        "path": str(f.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                        "size_bytes": f.stat().st_size,
                        "size_kb": round(f.stat().st_size / 1024),
                    })
            self._set_headers(200)
            self.wfile.write(json.dumps(samples_list).encode("utf-8"))
            return

        if path == "/api/cbom":
            user = self._require_access()
            if not user:
                return
            family_id = query.get("family", ["controller-x7"])[0]
            firmware_id = query.get("firmware", ["firmware-4.18.2.bin"])[0]
            policy = query.get("policy", ["hybrid-pqc"])[0]
            decision = assess(family_id, firmware_id, policy)
            cbom = CBOMGenerator.generate_cyclonedx_1_6(decision)
            self._set_headers(200)
            self.wfile.write(json.dumps(cbom, indent=2).encode("utf-8"))
            return

        if path == "/api/letter-to-file":
            user = self._require_access()
            if not user:
                return
            family_id = query.get("family", ["controller-x7"])[0]
            firmware_id = query.get("firmware", ["firmware-4.18.2.bin"])[0]
            policy = query.get("policy", ["hybrid-pqc"])[0]
            decision = assess(family_id, firmware_id, policy)
            dossier = LetterToFileGenerator.generate_dossier(decision)
            self._set_headers(200)
            self.wfile.write(json.dumps(dossier, indent=2).encode("utf-8"))
            return

        if path == "/api/remediation":
            user = self._require_access()
            if not user:
                return
            family_id = query.get("family", ["controller-x7"])[0]
            firmware_id = query.get("firmware", ["firmware-4.18.2.bin"])[0]
            policy = query.get("policy", ["hybrid-pqc"])[0]
            decision = assess(family_id, firmware_id, policy)
            remeds = CompensatingControlAdvisor.analyze_and_advise(decision)
            self._set_headers(200)
            self.wfile.write(json.dumps(remeds, indent=2).encode("utf-8"))
            return

        if path == "/api/algorithm-matrix":
            user = self._require_access()
            if not user:
                return
            family_id = query.get("family", ["controller-x7"])[0]
            size_kb = int(query.get("size_kb", ["380"])[0])
            family = get_device_family(family_id)
            matrix = AlgorithmMatrixEngine.evaluate_matrix(family, size_kb)
            self._set_headers(200)
            self.wfile.write(json.dumps(matrix, indent=2).encode("utf-8"))
            return

        # -------------------------------------------------------------
        # Static Assets
        # -------------------------------------------------------------
        if path == "/" or path == "/index.html":
            file_path = WEB_DIR / "index.html"
        else:
            rel_path = path.lstrip("/")
            file_path = WEB_DIR / rel_path

        if file_path.exists() and file_path.is_file():
            mime_type, _ = mimetypes.guess_type(str(file_path))
            content_type = mime_type or "text/plain"
            self._set_headers(200, content_type=content_type)
            self.wfile.write(file_path.read_bytes())
        else:
            self._set_headers(404, "application/json")
            self.wfile.write(json.dumps({"error": "Resource not found"}).encode("utf-8"))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # -------------------------------------------------------------
        # Authentication & Licensing Endpoints
        # -------------------------------------------------------------
        if path == "/api/auth/login":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                payload = {}
            email = payload.get("email", "").strip()
            password = payload.get("password", "")

            if not email or not password:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Email and password are required."}).encode("utf-8"))
                return

            user = auth_mgr.authenticate(email, password)
            if not user:
                self._set_headers(401)
                self.wfile.write(json.dumps({"error": "Invalid email or password.", "code": "INVALID_CREDENTIALS"}).encode("utf-8"))
                return

            self._set_headers(200)
            self.wfile.write(json.dumps({"success": True, "user": user}).encode("utf-8"))
            return

        if path == "/api/auth/signup":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                payload = {}
            email = payload.get("email", "").strip()
            password = payload.get("password", "")
            mobile = payload.get("mobile", "").strip()
            org = payload.get("org", "Enterprise OEM")
            plan = payload.get("plan", "Professional")

            if not email or not password:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Email and password are required."}).encode("utf-8"))
                return

            try:
                user = auth_mgr.register(email=email, password=password, mobile=mobile, org=org, plan=plan)
                self._set_headers(201)
                self.wfile.write(json.dumps({"success": True, "user": user}).encode("utf-8"))
            except ValueError as ve:
                self._set_headers(409)
                self.wfile.write(json.dumps({"error": str(ve), "code": "USER_EXISTS"}).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": f"Registration failed: {str(e)}"}).encode("utf-8"))
            return

        if path == "/api/auth/confirm-payment":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                payload = {}

            # Identify target user from token or payload
            user = self._get_authenticated_user()
            email_or_token = user["token"] if user else payload.get("email", "").strip()
            plan = payload.get("plan")

            if not email_or_token:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Missing user identifier for payment activation."}).encode("utf-8"))
                return

            result = auth_mgr.confirm_payment(email_or_token, plan)
            if not result:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "User account not found."}).encode("utf-8"))
                return

            self._set_headers(200)
            self.wfile.write(json.dumps({"success": True, "user": result}).encode("utf-8"))
            return

        if path == "/api/auth/logout":
            user = self._get_authenticated_user()
            if user and "token" in user:
                auth_mgr.logout(user["token"])
            self._set_headers(200)
            self.wfile.write(json.dumps({"success": True, "message": "Logged out successfully."}).encode("utf-8"))
            return

        if path == "/api/auth/reset-password" or path == "/api/auth/forgot-password":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                payload = {}
            email = payload.get("email", "").strip()
            new_password = payload.get("new_password", "").strip()

            if not email or not new_password:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Email and new password are required."}).encode("utf-8"))
                return

            res = auth_mgr.reset_password(email, new_password)
            if not res:
                self._set_headers(404)
                self.wfile.write(json.dumps({
                    "error": "No account found registered with this email address.",
                    "code": "USER_NOT_FOUND"
                }).encode("utf-8"))
                return

            self._set_headers(200)
            self.wfile.write(json.dumps({
                "success": True,
                "message": f"Password for {email} updated successfully! Please sign in with your new password.",
                "user": res
            }).encode("utf-8"))
            return


        # -------------------------------------------------------------
        # Protected Mutation Endpoints
        # -------------------------------------------------------------
        if path == "/api/assess":
            user = self._require_access()
            if not user:
                return

            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode("utf-8"))
                return

            device_family = payload.get("device_family", "controller-x7")
            firmware = payload.get("firmware", "firmware-4.18.2.bin")
            target_policy = payload.get("target_policy", "hybrid-pqc")
            simulated_size_kb = payload.get("simulated_size_kb")
            if simulated_size_kb is not None:
                try:
                    simulated_size_kb = int(simulated_size_kb)
                except (ValueError, TypeError):
                    simulated_size_kb = None

            try:
                decision = assess(
                    device_family=device_family,
                    firmware=firmware,
                    target_policy=target_policy,
                    simulated_size_kb=simulated_size_kb,
                )
                self._set_headers(200)
                self.wfile.write(decision.to_json().encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        if path == "/api/upload":
            user = self._require_access()
            if not user:
                return

            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            family_id = self.headers.get("X-Device-Family", "controller-x7")
            target_policy = self.headers.get("X-Target-Policy", "hybrid-pqc")
            filename = self.headers.get("X-Filename", "uploaded-release.bin")

            try:
                decision = assess(
                    device_family=family_id,
                    firmware=body,
                    target_policy=target_policy,
                )
                decision.firmware = filename
                self._set_headers(200)
                self.wfile.write(decision.to_json().encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        if path == "/api/register-family" or path == "/api/families":
            user = self._require_access()
            if not user:
                return

            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {str(e)}"}).encode("utf-8"))
                return

            try:
                family_id = payload.get("family_id", "custom-device").strip().lower().replace(" ", "-")
                flash_total = int(payload.get("flash_total_kb", 1024)) * 1024
                flash_boot = int(payload.get("flash_bootloader_kb", 64)) * 1024
                flash_slot_b = int(payload.get("flash_slot_b_kb", 448)) * 1024
                flash_slot_a = flash_slot_b
                ram_total = int(payload.get("ram_total_kb", 128)) * 1024
                ram_boot = int(payload.get("ram_boot_kb", 32)) * 1024
                regime_str = payload.get("regime", "IEC-62443")

                try:
                    regime_enum = RegulatoryRegime(regime_str)
                except ValueError:
                    regime_enum = RegulatoryRegime.IEC_62443

                new_family = DeviceFamily(
                    family_id=family_id,
                    vendor=payload.get("vendor", "Custom OEM"),
                    module=payload.get("module", f"{family_id} Device"),
                    soc_arch=payload.get("soc_arch", "ARM Cortex-M4"),
                    hardware=HardwareConstraints(
                        flash_total=flash_total,
                        flash_bootloader=flash_boot,
                        flash_slot_a=flash_slot_a,
                        flash_slot_b=flash_slot_b,
                        ram_total=ram_total,
                        ram_at_boot=ram_boot,
                        otp_pubkey_max=int(payload.get("otp_pubkey_max", 512)),
                        mtu=int(payload.get("mtu", 1024)),
                        watchdog_timeout_ms=int(payload.get("watchdog_timeout_ms", 500)),
                        hardware_crypto=bool(payload.get("hardware_crypto", False)),
                    ),
                    boot=BootArchitecture(
                        bootloader_name=payload.get("bootloader_name", "CustomBoot-v1"),
                        verify_in_rom=bool(payload.get("verify_in_rom", False)),
                        dual_bank=bool(payload.get("dual_bank", True)),
                        header_max=int(payload.get("header_max", 1024)),
                        sig_field_max=int(payload.get("sig_field_max", 512)),
                        verification_path=payload.get("verification_path", "single_stage"),
                        allows_bootloader_ota=bool(payload.get("allows_bootloader_ota", True)),
                    ),
                    certification=CertificationBaseline(
                        regime=regime_enum,
                        standard_id=payload.get("standard_id", regime_str),
                        baseline_scheme=payload.get("baseline_scheme", "ECDSA-P256"),
                        filing_dossier_id=payload.get("filing_dossier_id", f"DOSSIER-{family_id.upper()}"),
                        last_certified_release=payload.get("last_certified_release", "firmware-1.0.0.bin"),
                        recertification_cost_estimate_usd=int(payload.get("recertification_cost_estimate_usd", 75000)),
                    ),
                    current_scheme=payload.get("baseline_scheme", "ECDSA-P256"),
                    description=payload.get("description", "Custom user-registered device family."),
                )

                FAMILY_CATALOG[family_id] = new_family
                self._set_headers(201)
                self.wfile.write(json.dumps(new_family.to_dict()).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": f"Registration failed: {str(e)}"}).encode("utf-8"))
            return

        self._set_headers(404)
        self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode("utf-8"))


def run_server(host: str = "127.0.0.1", port: int = 8000):
    server = HTTPServer((host, port), AssuranceAPIHandler)
    print(f"\n[+] PQC Device Assurance Server active at http://{host}:{port}/")
    print(f"[+] Security: Platform strictly locked. Owner bypass enabled for {OWNER_EMAIL}.")
    print("[+] Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server shutdown.")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    run_server(port=port)
