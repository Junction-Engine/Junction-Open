#!/usr/bin/env python3
import sys, csv, json, os

def main():
    if len(sys.argv) < 3:
        print("Usage: validate_csv.py <schema.json> <csvfile>")
        sys.exit(1)
    schema_path, csv_path = sys.argv[1], sys.argv[2]
    with open(schema_path) as f:
        schema = json.load(f)
    required = schema.get("required_columns", [])
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        headers = next(reader, [])
    missing = [c for c in required if c not in headers]
    if missing:
        print("ERROR: Missing columns:", ", ".join(missing))
        sys.exit(2)
    extra = [c for c in headers if c not in required + schema.get("optional_columns", [])]
    print("OK: Headers valid. Extra columns:", ", ".join(extra) if extra else "(none)")
if __name__ == "__main__":
    main()
