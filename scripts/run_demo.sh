#!/usr/bin/env bash
set -euo pipefail
clear

# Prefer venv if present; else python3 (or override via $PYTHON)
if [[ -x ".venv/bin/python" ]]; then
  PY=".venv/bin/python"
else
  PY="${PYTHON:-$(command -v python3)}"
fi

echo "▶️  Junction demo (time-aware decisions)…"
echo "Using Python: $("$PY" -c 'import sys; print(sys.executable)')"
echo

# ---- dependency check (real imports, verbose if missing) ----
check_deps() {
  "$PY" - <<'PY'
import importlib, sys
mods = ("yaml","holidays","dateutil")
missing = []
for m in mods:
    try:
        importlib.import_module(m)
    except Exception as e:
        missing.append(f"{m} ({e})")
if missing:
    print("MISSING:", ", ".join(missing))
    sys.exit(1)
print("deps OK")
PY
}

# Ensure required modules are present (install INTO venv if present)
if check_deps; then
  :
else
  echo "Installing missing deps…"
  if [[ "$PY" == *"/.venv/"* ]]; then
    "$PY" -m pip install -q PyYAML holidays python-dateutil
  else
    "$PY" -m pip install -q --user PyYAML holidays python-dateutil
  fi
  check_deps || { echo "❌ Still missing deps after install"; exit 1; }
fi
echo

# ---- Run demo BEFORE cutoff
"$PY" -m demo.demo_runner_timeaware \
  samples/payment_intent_logistics_example.csv \
  out/recommendations_demo.csv \
  calendars/cutoffs.sample.yaml \
  --now "2025-07-15T14:30:00-04:00"

echo
echo "First rows:"
head -n 6 out/recommendations_demo.csv | sed -n '1,6p' | sed $'s/,/  |  /g'
echo

# ---- Run demo AFTER cutoff (shows same-day → next-day flip)
echo "Now after cutoff (same-day → next-day if cutoff missed)…"
"$PY" -m demo.demo_runner_timeaware \
  samples/payment_intent_logistics_example.csv \
  out/recommendations_after.csv \
  calendars/cutoffs.sample.yaml \
  --now "2025-07-15T17:00:00-04:00"

echo
echo "Done."
