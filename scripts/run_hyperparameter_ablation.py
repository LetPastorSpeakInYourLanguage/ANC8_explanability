"""How much does each hyperparameter actually matter?

    python scripts/run_hyperparameter_ablation.py --outcome anc8plus

Tuning consumed most of the compute in this project, and the honest finding
from the held-out evaluation was that it bought very little: every model's
development AP was roughly 0.08 higher than its held-out AP, which is the
signature of selection bias rather than of genuine gains.

This asks the question directly. For each tuned hyperparameter, the value is
moved away from the one Optuna chose -- holding every other parameter at its
tuned setting -- and the out-of-fold AP is re-measured. A parameter whose
perturbation barely moves AP was not worth searching over.

Two reference points frame the results:

  * **library defaults**, the model with no tuning at all;
  * **the Optuna optimum**, which the search paid for.

If the gap between those two is small relative to the noise across folds, the
search bought a number rather than a model -- and that is worth knowing before
anyone spends another CPU-week on it.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import design, outcomes, tuning  # noqa: E402

ENHANCED = ROOT / "outputs" / "enhanced"

# Models worth ablating: the two that led development, plus one linear arm as a
# contrast. Ablating all ten would cost more than the original tuning did.
MODELS = ["XGBoost", "Explainable Boosting", "Logistic regression"]

# How each parameter is perturbed away from its tuned value. Multiplicative for
# scale parameters, additive for depths and counts.
PERTURBATIONS = {
    "learning_rate": [0.5, 2.0],
    "n_estimators": [0.5, 2.0],
    "iterations": [0.5, 2.0],
    "max_iter": [0.5, 2.0],
    "max_depth": [-2, +2],
    "depth": [-2, +2],
    "num_leaves": [0.5, 2.0],
    "max_leaf_nodes": [0.5, 2.0],
    "min_child_weight": [0.25, 4.0],
    "min_child_samples": [0.25, 4.0],
    "min_samples_leaf": [0.25, 4.0],
    "min_samples_split": [0.5, 2.0],
    "subsample": [0.7, 1.0],
    "colsample_bytree": [0.6, 1.0],
    "reg_lambda": [0.1, 10.0],
    "reg_alpha": [0.1, 10.0],
    "gamma": [0.1, 10.0],
    "l2_regularization": [0.1, 10.0],
    "l2_leaf_reg": [0.25, 4.0],
    "C": [0.1, 10.0],
    "l1_ratio": [0.0, 1.0],
    "max_bins": [0.5, 2.0],
    "interactions": [+5, +10],
    "alpha": [0.1, 10.0],
    "learning_rate_init": [0.25, 4.0],
}

INT_PARAMS = {
    "n_estimators", "iterations", "max_iter", "max_depth", "depth",
    "num_leaves", "max_leaf_nodes", "min_child_samples", "min_samples_leaf",
    "min_samples_split", "max_bins", "interactions",
}


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def perturb(name, value, factor):
    """Move one parameter away from its tuned value."""
    if isinstance(value, str) or value is None or isinstance(value, bool):
        return None
    if name in ("max_depth", "depth", "interactions"):
        new = value + factor          # additive for depths / term counts
    elif name in ("subsample", "colsample_bytree", "l1_ratio"):
        new = factor                  # already a fraction; set it directly
    else:
        new = value * factor          # multiplicative for scales and counts

    if name in INT_PARAMS:
        new = int(round(new))
        if new < 1:
            return None
    if name in ("subsample", "colsample_bytree") and not (0 < new <= 1):
        return None
    if name == "l1_ratio" and not (0 <= new <= 1):
        return None
    if isinstance(new, float) and new <= 0:
        return None
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outcome", default="anc8plus", choices=outcomes.LADDER)
    args = ap.parse_args()
    OUTCOME = args.outcome
    OUT_DIR = ENHANCED / OUTCOME

    log(f"outcome: {outcomes.describe(OUTCOME)}")

    df = pd.read_pickle(ENHANCED / "ANC8_analysis_frozen_v2.pkl")
    spec = json.load(open(ENHANCED / "feature_spec_v2.json"))
    numeric, categorical = spec["numeric_predictors"], spec["categorical_predictors"]
    best = json.load(open(OUT_DIR / "best_hyperparameters.json"))

    train_psus, _ = design.make_psu_holdout(df)
    dev = df[df.v021.isin(train_psus)].reset_index(drop=True)
    splits = design.folds_to_splits(design.make_psu_stratum_folds(dev))

    X = dev[numeric + categorical].copy()
    for c in categorical:
        X[c] = X[c].astype(str)
    y = dev[OUTCOME].astype(int).to_numpy()
    w = (dev.v005 / 1e6).to_numpy()

    def evaluate(model, params):
        p = tuning.oof_predict(model, params, X, y, w, splits, numeric, categorical)
        return (average_precision_score(y, p, sample_weight=w),
                roc_auc_score(y, p, sample_weight=w))

    rows = []
    for model in MODELS:
        if model not in best:
            continue
        tuned = dict(best[model])

        log(f"\n{model}")
        tuned_ap, tuned_auc = evaluate(model, tuned)
        log(f"  tuned optimum          AP={tuned_ap:.4f} AUROC={tuned_auc:.4f}")

        # Library defaults: what you would get without tuning at all.
        default_ap, default_auc = evaluate(model, {})
        log(f"  library defaults       AP={default_ap:.4f} AUROC={default_auc:.4f}"
            f"   (tuning bought {tuned_ap - default_ap:+.4f})")

        rows.append({"model": model, "parameter": "(library defaults)",
                     "tuned_value": None, "perturbed_value": None,
                     "AP": default_ap, "AUROC": default_auc,
                     "AP_vs_tuned": default_ap - tuned_ap})

        for pname, pval in tuned.items():
            if pname not in PERTURBATIONS:
                continue
            for factor in PERTURBATIONS[pname]:
                new = perturb(pname, pval, factor)
                if new is None or new == pval:
                    continue
                trial = dict(tuned)
                trial[pname] = new
                try:
                    a, u = evaluate(model, trial)
                except Exception as exc:
                    log(f"    {pname}={new}: {type(exc).__name__}")
                    continue
                rows.append({"model": model, "parameter": pname,
                             "tuned_value": pval, "perturbed_value": new,
                             "AP": a, "AUROC": u, "AP_vs_tuned": a - tuned_ap})
                log(f"    {pname:22s} {str(pval)[:10]:>10s} -> {str(new)[:10]:<10s} "
                    f"AP={a:.4f} ({a - tuned_ap:+.4f})")

        rows.append({"model": model, "parameter": "(tuned optimum)",
                     "tuned_value": None, "perturbed_value": None,
                     "AP": tuned_ap, "AUROC": tuned_auc, "AP_vs_tuned": 0.0})

    res = pd.DataFrame(rows)
    res.to_csv(OUT_DIR / "hyperparameter_ablation.csv", index=False)

    # ---- what the ablation says -------------------------------------------
    print()
    print("HYPERPARAMETER SENSITIVITY (development out-of-fold, survey-weighted)")
    print("Largest AP drop caused by moving each parameter off its tuned value.")
    print()
    real = res[~res.parameter.str.startswith("(")]
    if len(real):
        worst = (real.groupby(["model", "parameter"]).AP_vs_tuned.min()
                 .reset_index().sort_values("AP_vs_tuned"))
        for model in worst.model.unique():
            sub = worst[worst.model == model].head(10)
            print(f"  {model}")
            for r in sub.itertuples():
                bar = "#" * min(40, int(abs(r.AP_vs_tuned) * 1000))
                print(f"    {r.parameter:22s} {r.AP_vs_tuned:+.4f}  {bar}")
            print()

    print("TUNING'S TOTAL CONTRIBUTION")
    for model in res.model.unique():
        d = res[(res.model == model) & (res.parameter == "(library defaults)")]
        t = res[(res.model == model) & (res.parameter == "(tuned optimum)")]
        if len(d) and len(t):
            gain = t.AP.iloc[0] - d.AP.iloc[0]
            print(f"  {model:24s} defaults {d.AP.iloc[0]:.4f} -> "
                  f"tuned {t.AP.iloc[0]:.4f}   gain {gain:+.4f}")

    print()
    print("Read these against the held-out reality: every model's development AP")
    print("ran ~0.08 above its held-out AP. A tuning gain smaller than that gap is")
    print("not evidence that the tuned model generalises better.")
    log(f"\nwrote {OUT_DIR / 'hyperparameter_ablation.csv'}")


if __name__ == "__main__":
    main()
