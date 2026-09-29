#!/usr/bin/env bash
# Refresh everything that is derived from the analysis results, in order.
# Run after any analysis stage finishes; each step reads only files on disk.
cd "$(dirname "$0")/.."
PY=/c/Users/pc/AppData/Local/Programs/Python/Python313/python.exe
set -e
echo "[finish] documentation tables";  $PY scripts/build_docs.py
echo "[finish] figures";               $PY -u scripts/make_figures.py 2>&1 | grep -E "\[ok\]|\[skip\]|FAIL|written"
echo "[finish] app data";              $PY scripts/export_app_data.py | tail -3
echo "[finish] studio data";           $PY scripts/run_regional_eda.py | tail -1 && $PY scripts/run_war_model.py | tail -1 \
                                       && $PY scripts/run_scenarios.py | tail -1 \
                                       && $PY scripts/run_time_series.py | tail -1 \
                                       && $PY scripts/run_clinic_screener.py | tail -1 \
                                       && $PY scripts/build_lab_profiles.py | tail -1                                        && $PY scripts/run_model_cards.py | tail -1 \
                                       && $PY scripts/export_viz_data.py
echo "[finish] checks";                $PY -u scripts/run_tests.py | tail -8
# Built into a separate folder so a running `next dev` (which owns .next) keeps
# working; the build is a check here, and Vercel builds the app itself.
echo "[finish] app build";             (cd app && NEXT_DIST_DIR=.next-build npm run build 2>&1 | tail -6; rm -rf .next-build)
echo "[finish] release package";       $PY -u scripts/build_release.py | tail -12
echo "[finish] release checks";        (cd release && $PY -u tests/run_tests.py | tail -6)
echo "[finish] done"
