# SAP S/4HANA Mapping Cheat Sheet (Decision-Only)

**Goal:** Use Junction’s recommendations to set/override SAP **Payment Method (ZLSCH)** per line item before payment run.

## Key SAP Fields
- `BUKRS` Company Code
- `LIFNR` Vendor
- `BELNR` Invoice Doc No.
- `GJAHR` Fiscal Year
- `BUZEI` Line Item
- `WAERS` Currency
- `WRBTR` Amount
- `XBLNR` Reference (PO)
- `FAEDT` Due Date
- `ZTERM` Payment Terms
- `SGTXT` Line Item Text
- `ZLSCH` Payment Method (per item)

## Payment Method Codes (example)
- `N` ACH (next-day)
- `S` ACH (same-day)
- `T` RTP
- `W` Wire
- `C` Card

## Minimal Process (Pilot)
1) Export open AP items to CSV.  
2) Junction returns Recommendation File with `ZLSCH`, reason, est. fee.  
3) Mass-update ZLSCH; run F110 as usual.
