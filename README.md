# Junction (Open) — SAP AP Rail Recommendation (SFTP-first)
<p align="left"><img src="brand/junction-top.png" width="120" alt="Junction mark"></p>



[![CodeQL](docs/codeql-badge.svg)](https://github.com/Junction-Engine/Junction-Open/actions/workflows/codeql.yml)


## Overview

```mermaid
flowchart TB
  s4["S/4HANA (AP open items)"]
  s4 -->|"CSV/OData (IDs, amounts, dates)"| jn["Junction (policy engine & dashboard)"]
  jn -->|"Recommendation File -> ZLSCH + reason + est. fee/ETA"| f110["S/4HANA Payment Run (F110/DMEE unchanged)"]
  f110 -->|"Bank files (NACHA / ISO 20022) go out as today"| banks["Banks / Rails"]
  banks -.->|"optional: acks/returns/statements -> Junction for auto-recon analytics"| jn
```


**Junction** is a lightweight policy engine that recommends the cheapest **safe** payment rail
(**ACH / Same-day ACH / RTP / Wire / Card**) for each AP line item and feeds the result back
into **SAP S/4HANA**. Pilot mode is **decision-only**: you keep your banks & F110 process.

> ⚠️ **Compliance:** Before using with real data, obtain appropriate approvals
> (OSS/IP, data handling). Do **not** upload bank details or PAN.

## Quick start (demo)
```bash
# 1) Clone and enter
git clone <your-repo-url>.git
cd Junction-Open

# 2) Run the demo on a sample file
python3 demo/demo_runner.py samples/payment_intent_logistics_example.csv out/recommendations_demo.csv

# 3) See the output
head -n 5 out/recommendations_demo.csv
```

**What you’ll see**
- A new CSV with columns: `recommended_rail`, `recommended_payment_method` (ZLSCH), `decision_reason`, `estimated_fee`, `expected_settlement_time`.
- A console summary with **rail mix** and **estimated fees** vs a baseline.

## Repo layout
```
junction-open/
  .github/workflows/lint.yml        # basic CI checks
  LICENSE                           # Apache 2.0
  README.md
  docs/
    runbook_sftp_odata.md           # SAP SFTP & OData integration runbook
    sap_s4hana_mapping_cheatsheet.md
    pilot_loi.md
  policies/
    routing_rules_logistics.yaml    # v0 routing policy (edit per client)
  samples/
    payment_intent_logistics_template.csv
    payment_intent_logistics_example.csv
    payment_intent_logistics_complex_example.csv
    exceptions_queue_template.csv
  schemas/
    payment_intent_v1.schema.json   # column schema for inbound CSV
  tools/
    validate_csv.py                 # quick schema check for inbound CSV
  demo/
    demo_runner.py                  # decision-only CLI
```

## SFTP-first integration (clients)
- SAP exports **open AP items** (IDs only) to SFTP.
- Junction processes and writes back **Recommendations** (ZLSCH) + **Exceptions**.
- SAP mass-updates ZLSCH and runs **F110** as usual.

See **docs/runbook_sftp_odata.md** for filenames, schemas, CPI iFlow, and the OData pattern.

## License
Apache-2.0 (see LICENSE).

## Security
See **SECURITY.md** for how to report vulnerabilities.

## Time-aware cutoffs demo

Run the same invoice **before** and **after** ACH Same-Day cutoff to see ETA and ZLSCH change.

```bash
# Before cutoff (uses calendars/cutoffs.sample.yaml)
python3 -m demo.demo_runner_timeaware samples/demo_cutoff_switch.csv out/recs_before.csv calendars/cutoffs.sample.yaml --tz America/New_York

# After cutoff (forces cutoff passed → next business day)
python3 -m demo.demo_runner_timeaware samples/demo_cutoff_switch.csv out/recs_after.csv calendars/cutoffs_after.yaml --tz America/New_York

# Quick peek (first two lines of each result)
sed -n '1,2p' out/recs_before.csv
sed -n '1,2p' out/recs_after.csv

```
