#!/usr/bin/env bash
# All six cohort x outcome runs of the tiered-selection analysis, one after
# another. Sequential on purpose: each run already uses 8 worker processes,
# and overlapping runs would only contend for cores and memory.
cd "$(dirname "$0")/.."
PY=/c/Users/pc/AppData/Local/Programs/Python/Python313/python.exe
for spec in "full anc8plus" "recent anc8plus" "full anc1plus" "full anc4plus" "recent anc1plus" "recent anc4plus"; do
  set -- $spec
  echo "[chain] $1 $2 starting $(date +%H:%M)"
  $PY -u scripts/run_feature_value.py --cohort "$1" --outcome "$2" > "logs/fv_$1_$2.log" 2>&1 \
    && echo "[chain] $1 $2 done $(date +%H:%M)" \
    || echo "[chain] $1 $2 FAILED -- see logs/fv_$1_$2.log"
done
echo "[chain] complete"
