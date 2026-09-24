#!/usr/bin/env bash
# The predictor-value runs this study needs beyond the existing results:
# stage 0 (the 21 on their own) on the full cohort for every rung, then the
# whole study at the ANC-entry horizon.
set -e
cd "$(dirname "$0")/.."
# The analysis interpreter, not the pinned serving environment (.venv-serve).
PY="${PY:-/c/Users/pc/AppData/Local/Programs/Python/Python313/python}"
for o in anc8plus anc4plus anc1plus; do
  $PY scripts/run_feature_value.py --cohort full --outcome $o --stages 0 > logs/fv0_full_$o.log 2>&1
done
$PY scripts/run_feature_value.py --cohort entry --outcome anc8plus > logs/fv_entry_anc8plus.log 2>&1
$PY scripts/run_feature_value.py --cohort entry --outcome anc4plus > logs/fv_entry_anc4plus.log 2>&1
echo CHAIN_DONE
