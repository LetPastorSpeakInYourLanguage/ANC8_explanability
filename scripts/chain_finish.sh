#!/usr/bin/env bash
# Everything that has to wait for the last rung to finish.
#
# chain_ladder.sh runs ANC4+ and then the cross-outcome analysis. This picks up
# from there: the hyperparameter ablations (which the user asked for and which
# nothing else depends on), then the exports that feed the web app, the
# figures, and finally the release package -- rebuilt last so it carries every
# result rather than a snapshot taken halfway through.
#
# Sequential throughout. All of it is CPU-bound and running two at once would
# only make both slower.
cd "$(dirname "$0")/.."
PY=/c/Users/pc/AppData/Local/Programs/Python/Python313/python.exe

echo "[finish] waiting for the ladder chain"
while true; do
  if grep -q "\[chain\] complete" logs/chain_ladder.log 2>/dev/null; then break; fi
  if grep -q "\[chain\] anc4plus failed" logs/chain_ladder.log 2>/dev/null; then
    echo "[finish] anc4plus failed; carrying on with what exists"
    break
  fi
  sleep 60
done

echo "[finish] hyperparameter ablation, all rungs"
for rung in anc1plus anc4plus anc8plus; do
  if [ -f "outputs/enhanced/$rung/best_hyperparameters.json" ]; then
    echo "[finish]   $rung"
    $PY -u scripts/run_hyperparameter_ablation.py --outcome "$rung" \
      > "logs/ablation_$rung.log" 2>&1 || echo "[finish]   $rung ablation failed"
  else
    echo "[finish]   $rung has no tuned parameters; skipped"
  fi
done

echo "[finish] refreshing what the app reads"
$PY scripts/export_insights.py 2>&1 | tail -5
$PY scripts/export_app_data.py 2>&1 | tail -8

echo "[finish] figures"
$PY -u scripts/make_figures.py 2>&1 | grep -v findfont | tail -30

echo "[finish] checks"
$PY -u scripts/run_tests.py 2>&1 | tail -12

echo "[finish] release package"
$PY -u scripts/build_release.py 2>&1 | tail -25

echo "[finish] complete"
