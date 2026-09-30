"""Train the study's models: logistic regression, random forest and XGBoost on the
21 predictors at each rung, each tuned over notebook 2's grid (library.GRIDS).

    python scripts/train_core.py                     # into outputs/core
    python scripts/train_core.py --root results_dir

Nine models, about five minutes. Each is one file,
<root>/results/s21/<rung>/<model>.npz, with its development out-of-fold and
held-out predictions and the setting its grid chose; a model already trained is
skipped.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import library as lib  # noqa: E402

CORE = ROOT / "outputs" / "core"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=CORE)
    ap.add_argument("--fold-jobs", type=int, default=5, help="folds fitted in parallel")
    args = ap.parse_args()
    for job in lib.grid_jobs():
        if lib.is_done(args.root, job):
            lib.log(f"{job.id}: already trained")
            continue
        lib.run(job, args.root, fold_jobs=args.fold_jobs)


if __name__ == "__main__":
    main()
