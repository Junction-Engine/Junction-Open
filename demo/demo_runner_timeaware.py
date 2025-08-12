
#!/usr/bin/env python3
import sys, csv, os, collections, datetime as dt
import argparse
from datetime import datetime as _dt
try:
    from dateutil import parser as _dtparse  # add to deps
except Exception:
    _dtparse = None

def _cli():
    p = argparse.ArgumentParser(
        prog="junction-demo",
        description="Time-aware AP rail recommendation (Junction Open)"
    )
    p.add_argument("input_csv")
    p.add_argument("output_csv")
    p.add_argument("cutoffs_yaml", nargs="?")
    p.add_argument("--fee-catalog", dest="fee", default=None)
    p.add_argument("--bank", dest="bank", default=None)
    p.add_argument("--tz", default=None)
    p.add_argument("--now", default=None,
                  help='ISO timestamp, e.g. "2025-07-15T15:00:00-04:00"')
    return p.parse_args()

# --- simple fee defaults (overridden by fee catalog if present) ---
fees = {
    "ach_next_day_fixed": 0.25,
    "ach_same_day_fixed": 1.25,
    "rtp_fixed": 0.50,
    "wire_fixed": 15.00,
    "card_mdr_bps": 250,
    "check_fixed": 1.50,
}
inst_amount_max = 5000
ach_sameday_amount_max = 100000
high_value_threshold = 50000

method_map = {"ach":"N","ach_same_day":"S","rtp":"T","wire":"W","card":"C","check":"H"}

def estimate_fee(rail, amount):
    if rail == "ach": return fees["ach_next_day_fixed"]
    if rail == "ach_same_day": return fees["ach_same_day_fixed"]
    if rail == "rtp": return fees["rtp_fixed"]
    if rail == "wire": return fees["wire_fixed"]
    if rail == "card": return (amount * fees["card_mdr_bps"]) / 10000.0
    if rail == "check": return fees["check_fixed"]
    return 0.0

def parse_args(argv):
    """
    argv: script in out [maybe fee_catalog.yaml bank] [maybe cutoffs.yaml] [--tz ZONE]
    Return: dict with keys: fee_catalog, bank, cutoffs, tz
    """
    out = {"fee_catalog": None, "bank": None, "cutoffs": None, "tz": None}
    i = 3
    while i < len(argv):
        a = argv[i]
        if a == "--tz":
            if i+1 < len(argv): out["tz"] = argv[i+1]
            i += 2
            continue
        if a.endswith((".yml", ".yaml")):
            # treat as fee catalog only if followed by a non-yaml, non-flag token (bank name)
            if out["fee_catalog"] is None and i+1 < len(argv) and (not argv[i+1].startswith("--")) and (not argv[i+1].endswith((".yml",".yaml"))):
                out["fee_catalog"], out["bank"] = a, argv[i+1]
                i += 2
                continue
            # otherwise it's the cutoffs file
            if out["cutoffs"] is None:
                out["cutoffs"] = a
                i += 1
                continue
        i += 1
    return out

def maybe_load_fee_catalog(path, bank):
    global fees, inst_amount_max, ach_sameday_amount_max, high_value_threshold
    if not path or not bank:
        return
    try:
        from demo.fee_catalog_loader import load_fee_catalog
        f, th = load_fee_catalog(path, bank)
        fees.update(f)
        inst_amount_max        = th.get('inst_amount_max',        inst_amount_max)
        ach_sameday_amount_max = th.get('ach_sameday_amount_max', ach_sameday_amount_max)
        high_value_threshold   = th.get('high_value_threshold',   high_value_threshold)
        print(f"Loaded fees for bank '{bank}' from {path}")
    except Exception as e:
        print(f"Warning: fee catalog load failed: {e}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 -m demo.demo_runner_timeaware <input_csv> <output_csv> [fee_catalog.yaml bank] [cutoffs.yaml] [--tz America/New_York]")
        sys.exit(1)
    inp, outp = sys.argv[1], sys.argv[2]
    opts = parse_args(sys.argv)

    # optional fees + cutoffs
    maybe_load_fee_catalog(opts["fee_catalog"], opts["bank"])

    cut = None
    now = None
    if opts["cutoffs"]:
        from calendars.biztime import Cutoffs
        cut = Cutoffs.from_yaml(opts["cutoffs"])
        if opts["tz"]:
            cut.tz = opts["tz"]
        now = dt.datetime.now(cut.tzinfo())
        print(f"Loaded cutoffs from {opts['cutoffs']} (tz={cut.tz}, holidays={cut.holiday_region})")

    # ensure output dir
    parent = os.path.dirname(outp)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(inp, newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    out_fields = list(reader.fieldnames) + ["recommended_rail","recommended_payment_method","decision_reason","estimated_fee","expected_settlement_time"]
    rail_counts = collections.Counter()
    total_amount = 0.0
    baseline_total_fees = 0.0
    orchestrated_total_fees = 0.0

    def before_cutoff(rail: str) -> bool:
        return True if not cut else cut.can_same_day(now, rail)

    with open(outp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()
        for r in rows:
            try:
                amt = float(r.get("amount", 0) or 0)
            except ValueError:
                amt = 0.0
            priority = str(r.get("priority","normal")).lower()
            refundability = str(r.get("refundability_required","no")).lower()
            vendor_country = (r.get("vendor_country") or "US")
            rtp_avail = str(r.get("rtp_available","true")).lower() in ["true","1","yes","y"]
            pref = str(r.get("preferred_rail","auto")).lower()
            allow_fallback = str(r.get("allow_fallback","yes")).lower() not in ["no","0","false","n"]

            # vendor-forced rail (e.g., check)
            if pref == "check" and not allow_fallback:
                rail, reason = "check", "VENDOR_REQUIRES_CHECK"
            else:
                # policy + time-aware gates
                if vendor_country != "US":
                    rail, reason = "wire", "CROSS_BORDER"
                elif amt >= high_value_threshold:
                    rail, reason = "wire", "HIGH_VALUE"
                elif priority in ["urgent","high"] and amt <= inst_amount_max and rtp_avail:
                    rail, reason = "rtp", "URGENT_SMALL"
                elif refundability == "yes":
                    rail, reason = "card", "REFUNDABILITY"
                elif priority == "high" and amt <= ach_sameday_amount_max and before_cutoff("ach_same_day"):
                    rail, reason = "ach_same_day", "HIGH_PRIORITY_SAME_DAY"
                else:
                    rail, reason = "ach", "DEFAULT_DOMESTIC"

            fee = round(estimate_fee(rail, amt), 2)
            # ETA label
            eta = {"ach":"T+1-T+2 (business)","ach_same_day":"Same day","rtp":"Instant","wire":"Same day","card":"T+1-T+2","check":"T+3-T+7 (mail)"}[rail]
            if cut:
                eta = cut.eta_label(now, rail)

            r.update({
                "recommended_rail": rail,
                "recommended_payment_method": method_map[rail],
                "decision_reason": reason,
                "estimated_fee": fee,
                "expected_settlement_time": eta
            })
            w.writerow(r)

            rail_counts[rail] += 1
            total_amount += amt
            baseline_total_fees += fees["ach_next_day_fixed"]
            orchestrated_total_fees += fee

    # tiny summary
    blended_base = (baseline_total_fees / total_amount * 1000) if total_amount else 0.0
    blended_orch = (orchestrated_total_fees / total_amount * 1000) if total_amount else 0.0
    approx_bps_savings = (blended_base - blended_orch) * 0.1
    print(f"Wrote recommendations to {outp}")
    print("---- Summary ----")
    print("Rail mix:", dict(rail_counts))
    print(f"Total amount: ${total_amount:,.2f}")
    print(f"Baseline total fees (all ACH next-day): ${baseline_total_fees:,.2f}")
    print(f"Orchestrated total fees: ${orchestrated_total_fees:,.2f}")
    print(f"Blended cost per $1k (baseline): ${blended_base:.4f}")
    print(f"Blended cost per $1k (orchestrated): ${blended_orch:.4f}")
    print(f"Approx bps savings: {approx_bps_savings:.2f} bps")

if __name__ == "__main__":
    main()
