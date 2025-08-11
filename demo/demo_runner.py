#!/usr/bin/env python3
"""demo_runner.py

Usage:
    python3 demo_runner.py <input_csv> <output_csv>

Reads a Payment Intent CSV (logistics format), applies simple routing rules,
and writes a Recommendations CSV with recommended rail, payment method code,
reason, and estimated fee. Also prints a quick ROI summary.

Note: Decision-only demo. Replace fees/thresholds with client values.
"""
import sys, csv, collections

fees = {
    "ach_next_day_fixed": 0.25,
    "ach_same_day_fixed": 1.25,
    "rtp_fixed": 0.50,
    "wire_fixed": 15.00,
    "card_mdr_bps": 250  # 2.50%
}
inst_amount_max = 5000
ach_sameday_amount_max = 100000
high_value_threshold = 50000

method_map = {"ach":"N","ach_same_day":"S","rtp":"T","wire":"W","card":"C"}
settlement_time = {"ach":"T+1-T+2","ach_same_day":"Same day","rtp":"Instant","wire":"Same day","card":"T+1-T+2"}

def estimate_fee(rail, amount):
    if rail == "ach": return fees["ach_next_day_fixed"]
    if rail == "ach_same_day": return fees["ach_same_day_fixed"]
    if rail == "rtp": return fees["rtp_fixed"]
    if rail == "wire": return fees["wire_fixed"]
    if rail == "card": return (amount * fees["card_mdr_bps"]) / 10000.0
    return 0.0

def route(row):
    try:
        amount = float(row.get("amount", 0) or 0)
    except ValueError:
        amount = 0.0
    priority = str(row.get("priority","normal")).lower()
    refundability = str(row.get("refundability_required","no")).lower()
    vendor_country = str(row.get("vendor_country","US"))
    rtp_avail = str(row.get("rtp_available","True")).lower() in ["true","1","yes","y"]
    if vendor_country != "US":
        return "wire", "CROSS_BORDER"
    if amount >= high_value_threshold:
        return "wire", "HIGH_VALUE"
    if priority in ["urgent","high"] and amount <= inst_amount_max and rtp_avail:
        return "rtp", "URGENT_SMALL"
    if refundability == "yes":
        return "card", "REFUNDABILITY"
    if priority == "high" and amount <= ach_sameday_amount_max:
        return "ach_same_day", "HIGH_PRIORITY"
    return "ach", "DEFAULT_DOMESTIC"

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    inp, outp = sys.argv[1], sys.argv[2]
    with open(inp, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    out_fields = list(reader.fieldnames) + ["recommended_rail","recommended_payment_method","decision_reason","estimated_fee","expected_settlement_time"]
    rail_counts = collections.Counter()
    total_amount = 0.0
    baseline_total_fees = 0.0
    orchestrated_total_fees = 0.0

    with open(outp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()
        for r in rows:
            rail, reason = route(r)
            try:
                amt = float(r.get("amount",0) or 0)
            except ValueError:
                amt = 0.0
            fee = round(estimate_fee(rail, amt), 2)
            r["recommended_rail"] = rail
            r["recommended_payment_method"] = method_map[rail]
            r["decision_reason"] = reason
            r["estimated_fee"] = fee
            r["expected_settlement_time"] = settlement_time[rail]
            w.writerow(r)
            # metrics
            rail_counts[rail] += 1
            total_amount += amt
            baseline_total_fees += fees["ach_next_day_fixed"]
            orchestrated_total_fees += fee

    blended_base = (baseline_total_fees / total_amount * 1000) if total_amount else 0.0
    blended_orch = (orchestrated_total_fees / total_amount * 1000) if total_amount else 0.0
    # $/1k to bps (1 bps = $0.10 per $1k)
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
