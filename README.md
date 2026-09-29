# Continuous PQC Updateability Assurance (`pqc-device-assurance`)

> **"Every firmware release changes your PQC migration risk.  
> We tell you whether you can still ship the quantum-safe update."**

---

## 1. Product Thesis

We maintain a continuously updated answer to one question:  
**Can this device family safely take a quantum-safe firmware update without bricking devices or triggering unnecessary recertification?** Every firmware release automatically re-evaluates that answer.

That gives you a strong product primitive: **continuous PQC updateability assurance**.

The inventory, binary crypto extraction, memory/flash simulation, boot-chain analysis, and certification impact analysis are all internal machinery. Customers aren't buying those outputs independently. They are buying a **living state**:

```
CAN_MIGRATE → CAN_MIGRATE_WITH_CONSTRAINTS → REDESIGN_REQUIRED → BLOCKED
```
...with concrete evidence showing *why* and *what changed since the previous firmware release*.

### "Without Reopening the File"
The compelling part of this formulation is **“without reopening the file.”** It turns what is normally a repeated consulting engagement—*new firmware, new analysis, new report, new decision*—into **continuous software**.  
The unit of value becomes the **device family over its 15-year lifecycle**, not a point-in-time scan or assessment.

---

## 2. The 9-Stage Assurance Pipeline

Every commit or firmware build automatically travels through this 9-stage verification pipeline:

```
Device Family
     │
     ├── Hardware constraints (Flash, RAM, OTP, MTU, Watchdog)
     ├── Boot/update architecture (ROM lock, Dual-bank A/B, Headers)
     └── Certification baseline (FDA-524B, IEC-62443, ISO-21434)
     │
Firmware Release N
     │
     ▼
[01] Firmware Ingestion
     │
     ▼
[02] Binary & Component Analysis (Sections, entropy, library detection)
     │
     ▼
[03] Crypto Evidence Extraction (Constants, S-boxes, public exponent heuristics)
     │
     ▼
[04] Device Constraint Evaluation (Hardware envelopes, ROM immutability)
     │
     ▼
[05] PQC Substitution Simulation (ML-DSA, ML-KEM, SLH-DSA, LMS deltas)
     │
     ▼
[06] Boot & Update Feasibility (Header budgets, MTU framing, rollback safety)
     │
     ▼
[07] Recertification Impact Engine (NO_REOPEN vs LETTER_TO_FILE vs PREMARKET_UPDATE)
     │
     ▼
[08] Living Decision & Evidence (Living state, constraints, residual risk)
     │
Firmware Release N+1 ─────► [09] Automatically recompute & diff
```

---

## 3. Developer Python API

Evaluate any device family release directly in CI/CD pipelines or Python scripts:

```python
from pqc_device_assurance import assess

decision = assess(
    device_family="controller-x7",
    firmware="firmware-4.18.2.bin",
    target_policy="hybrid-pqc",
)

print(decision.status)
# CAN_MIGRATE_WITH_CONSTRAINTS

print(decision.constraints)
# [
#   "OTA slot exceeds available flash by 84 KiB with ML-DSA-65",
#   "ML-KEM-768 fits RAM budget",
#   "Bootloader verification path requires modification"
# ]

print(decision.changed_since_previous_release)
# True

print(decision.filing_impact)
# PREMARKET_UPDATE (or LETTER_TO_FILE under compliant hybrid dual-signing)
```

---

## 4. Directory Structure

```
pqc-device-assurance/
├── api/
│   └── server.py              # REST API & Web dashboard server
├── analyzer/
│   ├── firmware.py            # Firmware ingestion & analysis orchestrator
│   ├── binary.py              # Section decomposition & entropy estimation
│   ├── crypto.py              # Stripped-binary heuristic crypto scanner
│   └── bootloader.py          # Bootloader envelope & verification analyzer
├── simulator/
│   ├── pqc_profiles.py        # FIPS 203/204/205 & LMS cryptographic profiles
│   ├── flash.py               # Flash slot delta & partition pressure simulator
│   ├── memory.py              # RAM/stack working set simulator
│   ├── update.py              # OTA framing, MTU, and rollback safety check
│   └── simulator.py           # Multi-engine simulation coordinator
├── certification/
│   ├── rules.py               # Regulatory rules (FDA 524B, IEC 62443, ISO 21434)
│   └── impact.py              # Recertification impact & Letter-to-File engine
├── decision/
│   ├── engine.py              # Living decision evaluator & assess() API
│   ├── evidence.py            # Structured technical evidence compiler
│   └── regression.py          # Differential release tracking (N vs N+1)
├── models/
│   ├── device.py              # Hardware, boot, and certification models
│   ├── firmware.py            # Firmware release & crypto finding models
│   └── decision.py            # Living decision, status, and evidence models
├── data/
│   └── catalog.py             # Pre-configured benchmark device families
├── tests/
│   ├── test_analyzer.py       # Binary & crypto extraction tests
│   ├── test_simulator.py      # Flash/RAM simulation tests
│   └── test_assess_api.py     # End-to-end assess() API tests
├── web/
│   ├── index.html             # High-aesthetic interactive telemetry dashboard
│   ├── style.css              # Cyber-engineering dark theme
│   └── app.js                 # Frontend application logic & CI simulator
├── cli.py                     # CLI tool for evaluations, history & diffs
└── README.md                  # This file
```

---

## 5. Command-Line Interface (CLI)

### Assess a firmware release:
```bash
python cli.py assess controller-x7 firmware-4.18.2.bin --policy hybrid-pqc
```

Output:
```
===============================================================================
DEVICE FAMILY : controller-x7
FIRMWARE      : firmware-4.18.2.bin
TARGET POLICY : hybrid-pqc (ML-DSA-65)
LIVING STATE  : [ CAN_MIGRATE_WITH_CONSTRAINTS ]
FILING IMPACT : PREMARKET_UPDATE  <- 'without reopening the file' lives here
DIFF CHANGED  : [!] YES (changed since previous release)
RESIDUAL RISK : Migration is feasible subject to identified constraints.
===============================================================================

IDENTIFIED CONSTRAINTS:
  [1] OTA slot exceeds available flash by 84 KiB with ML-DSA-65
  [2] ML-KEM-768 fits RAM budget
  [3] Bootloader verification path requires modification

DIFFERENTIAL FROM PREVIOUS RELEASE:
  * Previous Release : firmware-4.18.1.bin
  * Status Transition: CAN_MIGRATE -> CAN_MIGRATE_WITH_CONSTRAINTS
  * Summary Delta    : Release changed living state from CAN_MIGRATE to CAN_MIGRATE_WITH_CONSTRAINTS
```

### View device family evaluation history:
```bash
python cli.py history controller-x7
```

### List registered device families:
```bash
python cli.py families
```

### Launch API & Web UI:
```bash
python cli.py serve --port 8000
```
Open [http://localhost:8000/](http://localhost:8000/) in your browser.

---

## 6. Running Tests

Run the test suite using Python's standard unittest runner:
```bash
python -m unittest discover tests/
```

All tests execute with zero external dependencies in under 100 milliseconds.
