"""Run the whole modelling pipeline for one rung of the ANC ladder.

    python scripts/run_pipeline.py --outcome anc1plus
    python scripts/run_pipeline.py --outcome anc4plus --skip tuning

Every rung uses the same predictors, the same development/held-out split and
the same PSU-grouped folds -- only the outcome changes. That is what makes the
cross-outcome importance comparison in run_ladder_analysis.py meaningful.

Stages run in order and the run stops at the first failure, naming it, rather
than letting later stages fail confusingly on missing inputs.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import outcomes  # noqa: E402

# The pipeline needs optuna / interpret / shap, which live in the system
# interpreter. `python` on PATH may resolve to .venv-serve (the pinned
# scikit-learn 1.7.2 environment used only for serving the frozen V1 models),
# so the interpreter is resolved explicitly rather than inherited.
PY = sys.executable

STAGES = [
    ("tuning", ["-u", "scripts/run_tuning.py"]),
    ("evaluation", ["-u", "scripts/run_evaluation.py"]),
    ("stability", ["-u", "scripts/run_stability.py"]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outcome", required=True, choices=outcomes.LADDER)
    ap.add_argument("--skip", nargs="*", default=[],
                    help="stage names to skip, e.g. --skip tuning")
    args = ap.parse_args()

    print(f"\n{'=' * 78}")
    print(f"PIPELINE: {outcomes.describe(args.outcome)}")
    print(f"{'=' * 78}", flush=True)

    started = time.time()
    for name, cmd in STAGES:
        if name in args.skip:
            print(f"\n[{time.strftime('%H:%M:%S')}] skipping {name}", flush=True)
            continue

        print(f"\n{'-' * 78}")
        print(f"[{time.strftime('%H:%M:%S')}] {args.outcome}: {name}")
        print(f"{'-' * 78}", flush=True)

        r = subprocess.run([PY] + cmd + ["--outcome", args.outcome], cwd=ROOT)
        if r.returncode != 0:
            print(f"\nSTAGE FAILED: {name} for {args.outcome} (exit {r.returncode})")
            sys.exit(r.returncode)

    mins = (time.time() - started) / 60
    print(f"\n[{time.strftime('%H:%M:%S')}] {args.outcome} complete in {mins:.0f} min",
          flush=True)


if __name__ == "__main__":
    main()
