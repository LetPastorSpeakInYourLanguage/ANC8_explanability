"""The 21-predictor set under three model families, on the held-out women.

    python scripts/run_21_models_heldout.py [--cohort full entry recent] [--trials 20]

Stage 3 of run_feature_value.py scores every predictor set with logistic
regression and LightGBM. This adds the two other families the study fits on
the 21 -- random forest and XGBoost -- so each rung shows the 21 under
logistic regression, random forest and XGBoost side by side, and which of the
three does best.

Same protocol as stage 3: logistic regression at the regularisation the 21
earned on development folds; random forest and XGBoost tuned on development
folds only (Optuna, survey-weighted AP); every model fitted on the development
women and scored once on the held-out women, with a paired stratified-PSU
bootstrap against the 21 under logistic regression.

Output, per cohort and outcome in outputs/feature_value/<cohort>/<outcome>/:
    heldout_21_models.csv             AP, AUROC, calibration per family
    heldout_21_models_bootstrap.json  each family vs logistic regression
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import cohorts, design, metrics, selection as sel, tuning  # noqa: E402
from anc8 import models as zoo  # noqa: E402

FV = ROOT / "outputs" / "feature_value"
FAMILIES = ("Logistic regression", "Random Forest", "XGBoost")


def run(cohort: str, n_trials: int):
    df, pool = sel.build_pool(cohorts.load(cohort))
    dev, held = cohorts.development(df), cohorts.heldout(df)
    cols = pool.original21
    num, cat = pool.split(cols)
    for outcome in cohorts.COHORT_OUTCOMES[cohort]:
        out = FV / cohort / outcome
        out.mkdir(parents=True, exist_ok=True)
        y_d = dev[outcome].astype(int).to_numpy()
        w_d = (dev.v005 / 1e6).to_numpy()
        y = held[outcome].astype(int).to_numpy()
        w = (held.v005 / 1e6).to_numpy()
        prevalence = float(np.average(y, weights=w))

        preds, rows = {}, []
        for family in FAMILIES:
            if family == "Logistic regression":
                scorer = sel.Scorer(dev, outcome, pool)
                try:
                    scorer.seeds(cols)
                    params = {"C": scorer.last_C}
                finally:
                    sel.shutdown(scorer)
                    shutil.rmtree(sel.CACHE / scorer.cache_key, ignore_errors=True)
            else:
                params, _ = tuning.tune(family, dev[num + cat], y_d, w_d,
                                        cohorts.folds(dev), num, cat,
                                        n_trials=n_trials, n_jobs=5)
            pipe = zoo.build(family, params, num, cat)
            tuning._fit(pipe, dev[num + cat], y_d, w_d / w_d.mean())
            p = pipe.predict_proba(held[num + cat])[:, 1]
            preds[family] = p
            m = metrics.probability_metrics(y, p, w)
            rows.append({"model": family, "set": "original 21", "n_predictors": len(cols),
                         **m, "AP_lift": m["AP"] - prevalence, "prevalence": prevalence,
                         "params": json.dumps(params)})
            print(f"  {cohort:6s} {outcome:9s} {family:20s} AP {m['AP']:.3f}  "
                  f"AUROC {m['AUROC']:.3f}", flush=True)

        res = pd.DataFrame(rows)
        res["best_of_three"] = res.AP == res.AP.max()
        res.to_csv(out / "heldout_21_models.csv", index=False)

        base = preds["Logistic regression"]
        boot = {}
        for family in FAMILIES[1:]:
            p = preds[family]
            d_ap, d_auc = [], []
            for idx in design.stratified_psu_bootstrap(held.v022.to_numpy(),
                                                       held.v021.to_numpy(),
                                                       n_resamples=1000, seed=2026):
                yy, ww = y[idx], w[idx]
                if yy.min() == yy.max():
                    continue
                d_ap.append(average_precision_score(yy, p[idx], sample_weight=ww)
                            - average_precision_score(yy, base[idx], sample_weight=ww))
                d_auc.append(roc_auc_score(yy, p[idx], sample_weight=ww)
                             - roc_auc_score(yy, base[idx], sample_weight=ww))
            d_ap, d_auc = np.asarray(d_ap), np.asarray(d_auc)
            boot[f"{family} | original 21 vs original 21"] = {
                "d_AP": float(d_ap.mean()),
                "d_AP_lo": float(np.quantile(d_ap, .025)),
                "d_AP_hi": float(np.quantile(d_ap, .975)),
                "d_AUROC": float(d_auc.mean()),
                "d_AUROC_lo": float(np.quantile(d_auc, .025)),
                "d_AUROC_hi": float(np.quantile(d_auc, .975)),
            }
        json.dump(boot, open(out / "heldout_21_models_bootstrap.json", "w"), indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", nargs="*", default=["full", "entry", "recent"],
                    choices=cohorts.COHORTS)
    ap.add_argument("--trials", type=int, default=20)
    args = ap.parse_args()
    for cohort in args.cohort:
        run(cohort, args.trials)


if __name__ == "__main__":
    main()
