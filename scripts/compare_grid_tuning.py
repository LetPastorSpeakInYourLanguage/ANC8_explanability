"""What does the library's longer tuning buy over notebook 2's prespecified grids?

    python scripts/compare_grid_tuning.py

For logistic regression, random forest and XGBoost on the 21 predictors at every
rung: the grid notebook 2 prespecified (4, 48 and 64 settings), searched exactly
as the library searches (the same development folds, weights and objective:
survey-weighted out-of-fold average precision), the best setting refitted on the
development women and scored once on the held-out women. Set against the
library's Optuna search (40, 50 and 60 trials over wider ranges) for the same
model, predictor set and rung.

Writes outputs/library/tuning/grid_vs_search.csv.
"""

from __future__ import annotations

import sys
import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import library as lib, tuning  # noqa: E402

LIBRARY = ROOT / "outputs" / "library"
OUT = LIBRARY / "tuning" / "grid_vs_search.csv"

# notebook 2, section 2.12
GRIDS = {
    "Logistic regression": {"C": [0.01, 0.1, 1.0, 10.0]},
    "Random Forest": {"n_estimators": [300, 600], "max_depth": [None, 6, 12], "min_samples_split": [2, 10],
                      "min_samples_leaf": [1, 5], "max_features": ["sqrt", 0.5]},
    "XGBoost": {"n_estimators": [200, 400], "learning_rate": [0.03, 0.1], "max_depth": [3, 6],
                "min_child_weight": [1, 5], "subsample": [0.8, 1.0], "colsample_bytree": [0.8, 1.0]},
}


def settings(grid):
    keys = list(grid)
    return [dict(zip(keys, v)) for v in product(*grid.values())]


def main():
    rows = []
    t0 = time.time()
    for rung in lib.RUNGS:
        d = lib.data("s21", rung)
        for model, grid in GRIDS.items():
            best, best_ap = None, -1.0
            for p in settings(grid):
                oof = tuning.oof_predict(model, p, d.X_dev, d.y_dev, d.w_dev, d.splits, d.numeric, d.categorical, n_jobs=5)
                ap = average_precision_score(d.y_dev, oof, sample_weight=d.w_dev)
                if ap > best_ap:
                    best, best_ap = p, ap
            pipe = tuning.fit_final(model, best, d.X_dev, d.y_dev, d.w_dev, d.numeric, d.categorical)
            held = pipe.predict_proba(d.X_held)[:, 1]
            cell = lib.load_cell(LIBRARY, "s21", rung, model)
            rows.append({
                "rung": rung, "model": model, "grid_settings": len(settings(grid)),
                "grid_dev_AP": best_ap,
                "grid_held_AP": average_precision_score(d.y_held, held, sample_weight=d.w_held),
                "grid_held_AUROC": roc_auc_score(d.y_held, held, sample_weight=d.w_held),
                "search_trials": cell["meta"].get("n_trials"),
                "search_dev_AP": cell["meta"]["dev_metrics"]["AP"],
                "search_held_AP": cell["meta"]["held_metrics"]["AP"],
                "search_held_AUROC": cell["meta"]["held_metrics"]["AUROC"],
                "grid_best": str(best),
            })
            r = rows[-1]
            print(f"[{(time.time() - t0) / 60:5.1f} min] {rung} {model:20s} held AP grid {r['grid_held_AP']:.4f} "
                  f"vs search {r['search_held_AP']:.4f} ({r['grid_held_AP'] - r['search_held_AP']:+.4f})", flush=True)
    out = pd.DataFrame(rows)
    out["held_AP_difference"] = out.grid_held_AP - out.search_held_AP
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(out[["rung", "model", "grid_held_AP", "search_held_AP", "held_AP_difference"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
