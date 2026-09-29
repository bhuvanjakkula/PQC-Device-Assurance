"""
Continuous PQC Updateability Assurance - Command Line Interface (CLI)
======================================================================
"Every firmware release changes your PQC migration risk.
 We tell you whether you can still ship the quantum-safe update."
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from data.catalog import FAMILY_CATALOG, get_device_family
from decision.engine import assess, DEFAULT_DB_PATH
from decision.regression import ReleaseHistoryStore
from models.decision import Decision, MigrationStatus, FilingImpact


# Terminal ANSI Colors
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[38;5;48m"
AMBER = "\033[38;5;214m"
ORANGE = "\033[38;5;208m"
RED = "\033[38;5;196m"
CYAN = "\033[38;5;51m"
DIM = "\033[38;5;244m"


def status_color(status: MigrationStatus) -> str:
    if status == MigrationStatus.CAN_MIGRATE:
        return GREEN
    if status == MigrationStatus.CAN_MIGRATE_WITH_CONSTRAINTS:
        return AMBER
    if status == MigrationStatus.REDESIGN_REQUIRED:
        return ORANGE
    return RED


def filing_color(filing: FilingImpact) -> str:
    if filing == FilingImpact.NO_REOPEN:
        return GREEN
    if filing == FilingImpact.LETTER_TO_FILE:
        return AMBER
    return RED


def print_banner():
    banner = f"""{CYAN}{BOLD}
===================================================================================
                   CONTINUOUS PQC UPDATEABILITY ASSURANCE                          
  "Every firmware release changes your PQC migration risk.                         
   We tell you whether you can still ship the quantum-safe update."                
==================================================================================={RESET}
"""
    print(banner)


def render_decision(decision: Decision, format_json: bool = False):
    if format_json:
        print(decision.to_json(indent=2))
        return

    sc = status_color(decision.status)
    fc = filing_color(decision.filing_impact)

    print(f"\n{BOLD}==============================================================================={RESET}")
    print(f"{BOLD}DEVICE FAMILY :{RESET} {CYAN}{decision.device_family}{RESET}")
    print(f"{BOLD}FIRMWARE      :{RESET} {decision.firmware}")
    print(f"{BOLD}TARGET POLICY :{RESET} {decision.target_policy} ({decision.recommended_scheme})")
    print(f"{BOLD}LIVING STATE  :{RESET} {sc}{BOLD}[ {decision.status.value} ]{RESET}")
    print(f"{BOLD}FILING IMPACT :{RESET} {fc}{decision.filing_impact.value}{RESET}  <- 'without reopening the file' lives here")
    print(f"{BOLD}DIFF CHANGED  :{RESET} {'[!] YES (changed since previous release)' if decision.changed_since_previous_release else '[*] NO (consistent with baseline)'}")
    print(f"{BOLD}RESIDUAL RISK :{RESET} {decision.residual_risk}")
    print(f"{BOLD}==============================================================================={RESET}")

    print(f"\n{BOLD}IDENTIFIED CONSTRAINTS:{RESET}")
    if decision.constraints:
        for idx, c in enumerate(decision.constraints, 1):
            print(f"  {AMBER}[{idx}]{RESET} {c}")
    else:
        print(f"  {GREEN}[+] No hardware or memory constraints detected. Clear to deploy.{RESET}")

    if decision.diff_from_previous:
        print(f"\n{BOLD}DIFFERENTIAL FROM PREVIOUS RELEASE:{RESET}")
        diff = decision.diff_from_previous
        print(f"  * Previous Release : {diff.get('previous_firmware', 'N/A')}")
        print(f"  * Status Transition: {diff.get('previous_status', 'N/A')} -> {decision.status.value}")
        print(f"  * Summary Delta    : {diff.get('message', 'N/A')}")

    print(f"\n{BOLD}EVIDENCE PIPELINE SUMMARY:{RESET}")
    for ev in decision.evidence:
        ev_color = GREEN if ev.status == "PASS" else (AMBER if ev.status == "WARN" else RED)
        print(f"  [{ev_color}{ev.status:4s}{RESET}] {ev.category.upper():12s} : {ev.statement}")

    print(f"\n{DIM}Record timestamp: {decision.created_at}{RESET}\n")


def cmd_assess(args):
    decision = assess(
        device_family=args.device_family,
        firmware=args.firmware,
        target_policy=args.policy,
    )
    render_decision(decision, format_json=args.json)


def cmd_families(args):
    print(f"\n{BOLD}{CYAN}REGISTERED DEVICE FAMILIES:{RESET}\n")
    for fid, fam in FAMILY_CATALOG.items():
        print(f"  {BOLD}* {fid:20s}{RESET} | {fam.vendor:18s} | {fam.module:30s} | Reg: {fam.certification.regime.value}")
        print(f"    {DIM}SoC: {fam.soc_arch} | Flash: {fam.hardware.flash_total // 1024}KB | RAM: {fam.hardware.ram_total // 1024}KB | Boot: {fam.boot.bootloader_name}{RESET}")
    print()


def cmd_history(args):
    store = ReleaseHistoryStore(DEFAULT_DB_PATH)
    history = store.get_all_for_family(args.device_family)
    if not history:
        print(f"\n{AMBER}No evaluated releases recorded yet for family: {args.device_family}{RESET}\n")
        return

    print(f"\n{BOLD}{CYAN}EVALUATION TIMELINE FOR: {args.device_family}{RESET}\n")
    print(f"  {'FIRMWARE':24s} | {'STATUS':30s} | {'FILING':16s} | {'DATE':20s}")
    print("  " + "-" * 96)
    for h in history:
        sc = status_color(h.status)
        print(f"  {h.firmware:24s} | {sc}{h.status.value:30s}{RESET} | {h.filing_impact.value:16s} | {h.created_at[:19]}")
    print()


def cmd_serve(args):
    from api.server import run_server
    run_server(host=args.host, port=args.port)


def main():
    parser = argparse.ArgumentParser(
        description="Continuous PQC Updateability Assurance Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # assess command
    p_assess = subparsers.add_parser("assess", help="Assess a firmware release for a device family")
    p_assess.add_argument("device_family", help="Device family identifier (e.g. controller-x7)")
    p_assess.add_argument("firmware", help="Firmware file path or release ID (e.g. firmware-4.18.2.bin)")
    p_assess.add_argument("--policy", default="hybrid-pqc", help="Target PQC policy (default: hybrid-pqc)")
    p_assess.add_argument("--json", action="store_true", help="Output raw JSON decision record")
    p_assess.set_defaults(func=cmd_assess)

    # families command
    p_fam = subparsers.add_parser("families", help="List registered device families")
    p_fam.set_defaults(func=cmd_families)

    # history command
    p_hist = subparsers.add_parser("history", help="Show firmware release assurance history")
    p_hist.add_argument("device_family", help="Device family identifier")
    p_hist.set_defaults(func=cmd_history)

    # serve command
    p_serve = subparsers.add_parser("serve", help="Start the API and Web UI server")
    p_serve.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"), help="Bind host (default: 0.0.0.0 when PORT is set, else 127.0.0.1)")
    p_serve.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)), help="Bind port (default: $PORT or 8000)")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()

    if not args.command:
        print_banner()
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
