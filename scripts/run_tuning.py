"""Tune the full model zoo against the locked survey-design folds.

Run:  python scripts/run_tuning.py

Writes every artifact Notebook 4 needs into outputs/enhanced/, so the notebook
reads results rather than re-running a multi-hour search.

Trial budgets are scaled to per-fit cost, not set uniformly: the boosters cost
two orders of magnitude more per out-of-fold pass than logistic regression, so
a flat budget would spend almost all the time on one model. Every model still
sees the same folds, the same weights and the same objective.

CatBoost is excluded from the default zoo (see src/anc8/models.py) because it
cost more CPU than every other model combined and finished last. It runs on a
GPU instead, via notebooks/CatBoost_GPU_Colab.ipynb.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from anc8 import design, features, metrics, outcomes, tuning  # noqa: E402
from anc8 import models as zoo  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "enhanced"
OUT.mkdir(parents=True, exist_ok=True)

# Budgets chosen so the whole run lands in ~2h rather than ~8h.
TRIALS = {
    "Logistic regression": 40,
    "Elastic net logistic": 20,
    "Spline logistic": 40,
    "Random Forest": 50,
    "Extra Trees": 50,
    "XGBoost": 60,
    "LightGBM": 60,
    "HistGradientBoosting": 40,
    "Explainable Boosting": 20,
    "MLP": 30,
}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)



def parse_outcome():
    """Every stage takes --outcome so the whole ladder runs through one pipeline.

    The development/held-out split is deliberately NOT parameterised: it is
    built without reference to any outcome, so all three rungs share it. That
    is what makes their predictor importances comparable.
    """
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--outcome", default="anc8plus", choices=outcomes.LADDER)
    args, _ = ap.parse_known_args()
    return args.outcome

def main():
    OUTCOME = parse_outcome()
    OUT_DIR = OUT / OUTCOME
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log(f"outcome: {outcomes.describe(OUTCOME)}")

    # Read the canonical frozen dataset Notebook 3 wrote, so tuning and
    # evaluation cannot drift apart: run_evaluation.py reads the same file, and
    # the stacked ensemble aligns their out-of-fold predictions row by row.
    df = pd.read_pickle(OUT / "ANC8_analysis_frozen_v2.pkl")

    numeric = [c for c in features.NUMERIC_RAW if c in df] + list(
        features.build_derived(df).columns
    )
    categorical = (
        [c for c in features.ORDINAL_RAW if c in df]
        + [c for c in features.NOMINAL_RAW if c in df]
        + [c for c in features.BINARY_RAW if c in df]
        + [c for c in features.INHERITED_CONSTRUCTS if c in df]
    )

    # Only the development partition is materialised here. Tuning must not see
    # the held-out set at all, so it is counted and discarded rather than kept
    # in a variable something could later reach for.
    train_psus, test_psus = design.make_psu_holdout(df)
    dev = df[df.v021.isin(train_psus)].reset_index(drop=True)
    n_held = int(df.v021.isin(test_psus).sum())
    log(f"development n={len(dev)}  held-out n={n_held} (not loaded)")

    splits = design.folds_to_splits(design.make_psu_stratum_folds(dev))

    def prep(frame):
        X = frame[numeric + categorical].copy()
        for c in categorical:
            X[c] = X[c].astype(str)
        return X

    X_dev = prep(dev)
    y_dev = dev[OUTCOME].astype(int).to_numpy()
    w_dev = (dev.v005 / 1e6).to_numpy()

    results, best_params, oof_store = [], {}, {}

    for name in zoo.ZOO:
        n_trials = TRIALS[name]
        log(f"tuning {name} ({n_trials} trials)")
        t0 = time.time()
        try:
            params, best_ap = tuning.tune(
                name, X_dev, y_dev, w_dev, splits, numeric, categorical,
                n_trials=n_trials,
            )
            oof = tuning.oof_predict(
                name, params, X_dev, y_dev, w_dev, splits, numeric, categorical
            )
            m = metrics.probability_metrics(y_dev, oof, w_dev)
            m.update(model=name, n_trials=n_trials, seconds=round(time.time() - t0, 1))
            results.append(m)
            best_params[name] = params
            oof_store[name] = oof
            log(f"  {name}: AP={m['AP']:.4f} AUROC={m['AUROC']:.4f} ({m['seconds']}s)")
        except Exception as exc:  # keep going; report honestly at the end
            log(f"  {name} FAILED: {type(exc).__name__}: {exc}")
            results.append({"model": name, "error": f"{type(exc).__name__}: {exc}"})

    res = pd.DataFrame(results)
    res.to_csv(OUT_DIR / "development_oof_performance.csv", index=False)
    json.dump(best_params, open(OUT_DIR / "best_hyperparameters.json", "w"), indent=2, default=str)
    np.savez_compressed(OUT_DIR / "development_oof_predictions.npz", **oof_store)

    pd.DataFrame(
        {"caseid": dev.caseid, "y": y_dev, "w": w_dev, "fold": design.make_psu_stratum_folds(dev).values}
    ).to_csv(OUT_DIR / "development_index.csv", index=False)

    log("saved development results")
    ok = res[res.get("AP").notna()] if "AP" in res else res
    if len(ok):
        log("\n" + ok.sort_values("AP", ascending=False)[
            ["model", "AP", "AUROC", "Brier", "Calibration_slope"]
        ].to_string(index=False))


if __name__ == "__main__":
    main()
