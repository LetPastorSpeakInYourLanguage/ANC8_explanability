"""Refit the four library models as objects, for explanation, levers and serving.

    python scripts/fit_library_models.py                       # from G:/My Drive/ANC8_training
    python scripts/fit_library_models.py --root outputs/library

The library (scripts/train_library.py) keeps each model's predictions and tuned
settings, not the fitted model. Explaining a model, applying a lever to it or
exporting it to the studio needs the model itself, so each of logistic regression,
random forest, XGBoost and explainable boosting is refitted here on the development
women, per predictor set and rung, with the settings the library chose.

Gate: every refitted model must reproduce the library's held-out predictions to
1e-9, so the object explained is exactly the one that was evaluated. A model that
does not is reported and not written.

Writes outputs/library/models/<set>_<rung>.joblib:
    {"models": {name: pipeline}, "numeric": [...], "categorical": [...], "params": {...}}
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import library as lib, tuning  # noqa: E402

OUT = ROOT / "outputs" / "library" / "models"
MODELS = lib.LINEUPS["four"]
TOL = 1e-9


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("G:/My Drive/ANC8_training"))
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    bad = []
    for set_ in lib.SETS:
        for rung in lib.RUNGS:
            d = lib.data(set_, rung)
            fitted, params = {}, {}
            for name in MODELS:
                cell = lib.load_cell(args.root, set_, rung, name)
                p = cell["meta"]["params"]
                pipe = tuning.fit_final(name, p, d.X_dev, d.y_dev, d.w_dev, d.numeric, d.categorical)
                held = pipe.predict_proba(d.X_held)[:, 1]
                gap = float(np.max(np.abs(held - cell["held"])))
                if gap > TOL:
                    bad.append(f"{set_}/{rung}/{name}: {gap:.2e}")
                    log(f"  MISMATCH {set_}/{rung}/{name}: max |diff| {gap:.2e}")
                    continue
                fitted[name], params[name] = pipe, p
            joblib.dump({"models": fitted, "numeric": d.numeric, "categorical": d.categorical,
                         "params": params, "set": set_, "rung": rung},
                        OUT / f"{set_}_{rung}.joblib", compress=3)
            log(f"{set_}/{rung}: {len(fitted)} of {len(MODELS)} models match the library")

    if bad:
        print("\nNot reproduced:\n  " + "\n  ".join(bad))
        sys.exit(1)
    log("every model reproduces its library predictions")


if __name__ == "__main__":
    main()
