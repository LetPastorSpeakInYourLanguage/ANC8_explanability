#!/usr/bin/env bash
# Re-run the ANC8 evaluation once the ladder chain is done.
#
# ANC8's evaluation predates two fixes the other rungs will have: the champion
# was selected on held-out data (selection on the test set), and the parsimony
# search used the older, slower, more overfit configuration. Re-running makes
# all three rungs consistent, which the cross-outcome comparison depends on.
cd "$(dirname "$0")/.."
PY=/c/Users/pc/AppData/Local/Programs/Python/Python313/python.exe

echo "[anc8] waiting for the ladder chain to finish"
while ! grep -q "\[chain\] complete" logs/chain_ladder.log 2>/dev/null; do
  if grep -q "\[chain\] .* failed" logs/chain_ladder.log 2>/dev/null; then
    echo "[anc8] ladder chain failed; running anyway so ANC8 is at least consistent"
    break
  fi
  sleep 30
done

echo "[anc8] re-running evaluation with corrected champion selection"
$PY -u scripts/run_evaluation.py --outcome anc8plus 2>&1 | tee logs/anc8_rerun.log

echo "[anc8] refreshing exports"
$PY scripts/export_serving.py --v2 2>&1 | tail -6
$PY scripts/build_performance_json.py 2>&1 | tail -3
$PY -u scripts/run_ladder_analysis.py 2>&1 | tee logs/ladder_analysis_final.log
$PY scripts/export_insights.py 2>&1 | tail -8

echo "[anc8] hyperparameter ablation (was tuning worth it?)"
for RUNG in anc8plus anc1plus anc4plus; do
  if [ -f "outputs/enhanced/$RUNG/best_hyperparameters.json" ]; then
    $PY -u scripts/run_hyperparameter_ablation.py --outcome $RUNG       2>&1 | tee "logs/ablation_$RUNG.log" | tail -30
  fi
done
echo "[anc8] complete"
