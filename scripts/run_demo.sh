#!/usr/bin/env bash
set -euo pipefail
clear
echo "▶️  Junction demo (time-aware decisions)…"
echo
python3 -m demo.demo_runner_timeaware \
  samples/payment_intent_logistics_example.csv \
  out/recommendations_demo.csv \
  calendars/cutoffs.sample.yaml \
  --now "2025-07-15T14:30:00-04:00"
echo
echo "First rows:"
head -n 6 out/recommendations_demo.csv | sed -n '1,6p' | sed $'s/,/  |  /g'
echo
echo "Now after cutoff (same-day → next-day if cutoff missed)…"
python3 -m demo.demo_runner_timeaware \
  samples/payment_intent_logistics_example.csv \
  out/recommendations_after.csv \
  calendars/cutoffs.sample.yaml \
  --now "2025-07-15T17:00:00-04:00"
echo
echo "Done."
