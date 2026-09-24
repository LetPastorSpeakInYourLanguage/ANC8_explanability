#!/usr/bin/env bash
# Run ANC4 once ANC1 finishes, then the cross-outcome analysis and the
# insight export. Sequential because both pipelines are CPU-bound and would
# only contend if run together.
cd "$(dirname "$0")/.."
PY=/c/Users/pc/AppData/Local/Programs/Python/Python313/python.exe

echo "[chain] waiting for anc1plus to finish"
while pgrep -f "run_pipeline.py --outcome anc1plus" > /dev/null 2>&1 || \
      tasklist //FI "IMAGENAME eq python.exe" 2>/dev/null | grep -qi python; do
  if grep -q "anc1plus complete in" logs/ladder_anc1plus.log 2>/dev/null; then break; fi
  if grep -q "STAGE FAILED" logs/ladder_anc1plus.log 2>/dev/null; then
    echo "[chain] anc1plus failed; stopping"; exit 1
  fi
  sleep 30
done

echo "[chain] anc1plus done -> starting anc4plus"
$PY -u scripts/run_pipeline.py --outcome anc4plus 2>&1 | tee logs/ladder_anc4plus.log
if grep -q "STAGE FAILED" logs/ladder_anc4plus.log; then
  echo "[chain] anc4plus failed; stopping"; exit 1
fi

echo "[chain] both rungs done -> cross-outcome analysis"
$PY -u scripts/run_ladder_analysis.py 2>&1 | tee logs/ladder_analysis.log

echo "[chain] refreshing insight artifacts for the app"
$PY scripts/export_insights.py 2>&1 | tail -20

echo "[chain] complete"
