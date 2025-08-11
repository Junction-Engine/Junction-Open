# Junction ↔ SAP S/4HANA Runbook (SFTP & OData)

**Goal:** Recommend a payment rail + SAP Payment Method (**ZLSCH**) per open AP line item, then run F110 as usual. Start with **SFTP (files)**; add **OData (APIs)** later.

---

## 1) SFTP Pattern (fastest to pilot)

**Directories**: `/inbox` (SAP → Junction); `/outbox` (Junction → SAP); `/archive` (processed); `/rejects` (bad schema)

**Filenames**: Inbound `AP_OPENITEMS_{BUKRS}_{YYYYMMDD}_{SEQ}.csv`; Outbound recs `JUNC_REC_{same_id}.csv`; Outbound exceptions `JUNC_EXC_{same_id}.csv`

**Security**: SSH key (ed25519), IP allowlist, optional PGP, 30–90 day retention.

**Inbound CSV schema (IDs only)**: `company_code, vendor_id, invoice_document, fiscal_year, line_item, invoice_date, due_date, payment_terms, currency, amount, reference, line_item_text, vendor_country, priority, refundability_required`

**Processing SLA**: ≤ 2 minutes for 10k lines; duplicate `batch_id` ignored; run summary posted.

## 2) SAP Tasks — SFTP Mode

**Export**: CDS/ABAP job writes AP open items CSV; schedule in SM36; push via SAP CPI/PO SFTP adapter.

**Import / mass‑update ZLSCH**: LSMW/BDC (FB02) or small Z-program; log old→new; skip cleared items.

**F110**: FBZP maps ZLSCH → house banks/formats; run as usual.

## 3) Acceptance Test (Day‑1)

Round-trip 100 rows in <2 min; verify ZLSCH changes; F110 splits by method and generates correct files; review ROI summary.

## 4) OData Pattern (add later)

`GET` open items (paged, delta) and `PATCH` ZLSCH per line item with `RecommendedRail`, `DecisionReason`, `PolicyId`. OAuth2 via BTP/CPI. Idempotency with `x-junction-id`.

## 5) Policy & Codes

ZLSCH (example): `N=ACH(next‑day)`, `S=ACH(same‑day)`, `T=RTP`, `W=Wire`, `C=Card`. Exceptions: `MISSING_VENDOR_METHOD`, `OVER_LIMIT`, `INVALID_DATE`, `MANUAL_REVIEW`.

## 6) Ops

Owners: Client AP/SAP FI/BASIS; Junction Integration. Support 8×5 ET; P1 2h. Delete raw files after 30–90d; keep decision logs ≥ 1y.
