"""Why 21? The reduced versions of the 21, on the held-out women.

    python scripts/run_why21_heldout.py [--cohort full]

Stage 0 of run_feature_value.py finds, on development folds, how far the 21
can shrink: the best k of them (the peak of the greedy path within the 21) and
the 21 without every member whose removal costs nothing. Both were chosen on
the same folds they are scored on, so their development scores are optimistic.
This scores them ONCE on the held-out women, next to the 21, the set selected
from the full pool and the full pool itself, with a paired stratified-PSU
bootstrap against the 21.

Logistic regression, each set at the regularisation it earned on development
folds -- the same fixed model as the rest of the predictor-value study.

Output: outputs/feature_value/<cohort>/<outcome>/why21_heldout.csv and
why21_bootstrap.json.
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", default="full")
    args = ap.parse_args()

    df, pool = sel.build_pool(cohorts.load(args.cohort))
    dev, held = cohorts.development(df), cohorts.heldout(df)
    for outcome in cohorts.COHORT_OUTCOMES[args.cohort]:
        d = FV / args.cohort / outcome
        if not (d / "forward_within_21.csv").exists():
            print(f"{outcome}: stage 0 not run, skipped")
            continue
        js = json.loads((d / "summary.json").read_text())
        path = pd.read_csv(d / "forward_within_21.csv")
        drop = pd.read_csv(d / "drop_one_within_21.csv")
        k = int(js["stage0"]["best_k_within_21"])
        sets = {
            "21-predictor set": pool.original21,
            f"best {k} of the 21": list(path.predictor.head(k)),
            "21 minus non-contributors": list(drop[drop.loss > 0].predictor),
            "selected from the pool": js["tier1"] + js["tier2"],
            "full pool": pool.names,
        }
        sets = {name: cols for name, cols in sets.items() if cols}

        scorer = sel.Scorer(dev, outcome, pool)
        try:
            Cs = {}
            for name, cols in sets.items():
                scorer.seeds(cols)
                Cs[name] = scorer.last_C
        finally:
            sel.shutdown(scorer)
            shutil.rmtree(sel.CACHE / scorer.cache_key, ignore_errors=True)

        y_d = dev[outcome].astype(int).to_numpy()
        w_d = (dev.v005 / 1e6).to_numpy()
        y = held[outcome].astype(int).to_numpy()
        w = (held.v005 / 1e6).to_numpy()
        prev = float(np.average(y, weights=w))
        preds, rows = {}, []
        for name, cols in sets.items():
            num, cat = pool.split(cols)
            pipe = zoo.build("Logistic regression", {"C": Cs[name]}, num, cat)
            tuning._fit(pipe, dev[num + cat], y_d, w_d / w_d.mean())
            p = pipe.predict_proba(held[num + cat])[:, 1]
            preds[name] = p
            m = metrics.probability_metrics(y, p, w)
            rows.append({"set": name, "n_predictors": len(cols), "C": Cs[name], **m,
                         "AP_lift": m["AP"] - prev, "prevalence": prev,
                         "predictors": "|".join(cols) if len(cols) <= 21 else ""})
        res = pd.DataFrame(rows)
        res.to_csv(d / "why21_heldout.csv", index=False)

        base = preds["21-predictor set"]
        boot = {}
        for name, p in preds.items():
            if name == "21-predictor set":
                continue
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
            boot[name] = {"d_AP": float(d_ap.mean()),
                          "d_AP_lo": float(np.quantile(d_ap, .025)),
                          "d_AP_hi": float(np.quantile(d_ap, .975)),
                          "d_AUROC": float(d_auc.mean()),
                          "d_AUROC_lo": float(np.quantile(d_auc, .025)),
                          "d_AUROC_hi": float(np.quantile(d_auc, .975))}
        json.dump(boot, open(d / "why21_bootstrap.json", "w"), indent=2)
        print(f"{outcome}  prevalence {prev:.3f}")
        for r in res.itertuples():
            b = boot.get(r.set)
            ci = (f"  vs 21: dAP {b['d_AP']:+.3f} [{b['d_AP_lo']:+.3f}, {b['d_AP_hi']:+.3f}]"
                  f"  dAUROC {b['d_AUROC']:+.3f} [{b['d_AUROC_lo']:+.3f}, {b['d_AUROC_hi']:+.3f}]"
                  if b else "")
            print(f"  {r.set:28s} n={r.n_predictors:2d}  AP {r.AP:.3f}  AUROC {r.AUROC:.3f}{ci}")


if __name__ == "__main__":
    main()
