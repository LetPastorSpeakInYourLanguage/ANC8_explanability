"""The two prediction horizons: before ANC starts, and at ANC entry.

    python scripts/run_horizons.py

Needs the ANC-entry predictor-value runs (run_feature_value.py --cohort entry)
for its tier sets. For ANC4+ and ANC8+ -- the rungs defined at ANC entry -- it
answers three questions.

1. What does knowing the timing of the first contact add?
   `early_anc` added to the 21, to the entry tier set and to the full pool,
   on development folds (same fixed logistic regression, 5 split seeds) and
   once on the held-out ANC-entry women with a paired stratified-PSU
   bootstrap.

2. Do the same predictors carry the prediction at entry as before ANC?
   Tier membership and each predictor's marginal value at both horizons (read
   from the two runs' outputs; nothing refitted for this part).

3. Is a model for the entry horizon worth building separately?
   The full-cohort 21-predictor and full-pool models, fitted on full-cohort
   development women, scored on the held-out ANC-entry women; against the
   same sets fitted on ANC-entry development women. Same women, same metric.

Output: outputs/horizons/.
"""

from __future__ import annotations

import json
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
OUT = ROOT / "outputs" / "horizons"
RUNGS = ("anc4plus", "anc8plus")
EARLY = "early_anc"


def fit_predict(pool, cols, C, dev, held, outcome):
    num, cat = pool.split(cols)
    y = dev[outcome].astype(int).to_numpy()
    w = (dev.v005 / 1e6).to_numpy()
    pipe = zoo.build("Logistic regression", {"C": C}, num, cat)
    tuning._fit(pipe, dev[num + cat], y, w / w.mean())
    return pipe.predict_proba(held[num + cat])[:, 1]


def paired(held, y, w, a, b, n=1000):
    """Mean and 95% interval of metric(a) - metric(b) over PSU resamples."""
    d_ap, d_auc = [], []
    for idx in design.stratified_psu_bootstrap(held.v022.to_numpy(), held.v021.to_numpy(),
                                               n_resamples=n, seed=2026):
        yy, ww = y[idx], w[idx]
        if yy.min() == yy.max():
            continue
        d_ap.append(average_precision_score(yy, a[idx], sample_weight=ww)
                    - average_precision_score(yy, b[idx], sample_weight=ww))
        d_auc.append(roc_auc_score(yy, a[idx], sample_weight=ww)
                     - roc_auc_score(yy, b[idx], sample_weight=ww))
    d_ap, d_auc = np.asarray(d_ap), np.asarray(d_auc)
    q = lambda x, p: float(np.quantile(x, p))
    return {"d_AP": float(d_ap.mean()), "d_AP_lo": q(d_ap, .025), "d_AP_hi": q(d_ap, .975),
            "d_AUROC": float(d_auc.mean()), "d_AUROC_lo": q(d_auc, .025),
            "d_AUROC_hi": q(d_auc, .975)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df_e, pool_e = sel.build_pool(cohorts.load("entry"))
    df_f, pool_f = sel.build_pool(cohorts.load("full"))
    dev_e, held_e = cohorts.development(df_e), cohorts.heldout(df_e)
    dev_f = cohorts.development(df_f)
    held_f_on_e = df_f.set_index("caseid").loc[held_e.caseid].reset_index()
    assert (held_f_on_e.partition == "held-out").all()

    early_rows, held_rows, cross_rows, boot = [], [], [], {}
    for outcome in RUNGS:
        js_e = json.loads((FV / "entry" / outcome / "summary.json").read_text())
        js_f = json.loads((FV / "full" / outcome / "summary.json").read_text())
        tier_e = js_e["tier1"] + js_e["tier2"]
        base_pool = [c for c in pool_e.names if c != EARLY]
        base_tier = [c for c in tier_e if c != EARLY]
        print(f"{outcome}: entry tiers {tier_e}")

        # 1. early_anc on development folds.
        scorer = sel.Scorer(dev_e, outcome, pool_e)
        try:
            Cs = {}
            for name, base in (("21", pool_e.original21), ("tier set", base_tier),
                               ("full pool", base_pool)):
                if not base:
                    continue
                without = scorer.seeds(base); Cs[(name, False)] = scorer.last_C
                with_ = scorer.seeds(base + [EARLY]); Cs[(name, True)] = scorer.last_C
                g = with_ - without
                early_rows.append({"outcome": outcome, "base": name, "n_base": len(base),
                                   "AP_without": without.mean(), "AP_with": with_.mean(),
                                   "gain": g.mean(), "seeds_positive": int((g > 0).sum()),
                                   "prevalence": scorer.prevalence})
                print(f"  dev  {name:9s} {without.mean():.4f} -> {with_.mean():.4f}"
                      f"  ({g.mean():+.4f}, {int((g > 0).sum())}/5)")
        finally:
            sel.shutdown(scorer)

        # 1b. ... and once on the held-out ANC-entry women.
        y = held_e[outcome].astype(int).to_numpy()
        w = (held_e.v005 / 1e6).to_numpy()
        prev = float(np.average(y, weights=w))
        preds = {}
        for (name, early), C in Cs.items():
            base = {"21": pool_e.original21, "tier set": base_tier,
                    "full pool": base_pool}[name]
            cols = base + ([EARLY] if early else [])
            p = fit_predict(pool_e, cols, C, dev_e, held_e, outcome)
            preds[(name, early)] = p
            m = metrics.probability_metrics(y, p, w)
            held_rows.append({"outcome": outcome, "horizon": "ANC entry",
                              "trained_on": "ANC-entry development", "set": name,
                              "early_anc": early, "n_predictors": len(cols), **m,
                              "prevalence": prev})
        for name in ("21", "tier set", "full pool"):
            if (name, True) in preds:
                boot[f"{outcome} | {name} + early ANC vs {name}"] = paired(
                    held_e, y, w, preds[(name, True)], preds[(name, False)])

        # 3. The full-cohort models on the same held-out ANC-entry women.
        for name, cols, C in (("21", pool_f.original21, js_f["anchors"]["original21_C"]),
                              ("full pool", pool_f.names, js_f["anchors"]["all88_C"])):
            p = fit_predict(pool_f, cols, C, dev_f, held_f_on_e, outcome)
            m = metrics.probability_metrics(y, p, w)
            cross_rows.append({"outcome": outcome, "set": name,
                               "trained_on": "full-cohort development", **m,
                               "prevalence": prev})
            same = preds[(name, False)]
            boot[f"{outcome} | {name}: entry-trained vs full-cohort-trained"] = paired(
                held_e, y, w, same, p)
            mm = metrics.probability_metrics(y, same, w)
            cross_rows.append({"outcome": outcome, "set": name,
                               "trained_on": "ANC-entry development", **mm,
                               "prevalence": prev})

    pd.DataFrame(early_rows).to_csv(OUT / "early_anc_development.csv", index=False)
    pd.DataFrame(held_rows).to_csv(OUT / "heldout_entry.csv", index=False)
    pd.DataFrame(cross_rows).to_csv(OUT / "cross_horizon.csv", index=False)
    json.dump(boot, open(OUT / "heldout_bootstrap.json", "w"), indent=2)

    # 2. The two horizons' selections side by side.
    rows = []
    for outcome in RUNGS:
        for horizon, cohort in (("before ANC", "full"), ("ANC entry", "entry")):
            d = FV / cohort / outcome
            js = json.loads((d / "summary.json").read_text())
            steps = pd.read_csv(d / "forward_steps.csv")
            for r in steps[steps.tier.isin(["tier 1", "tier 2"])].itertuples():
                rows.append({"outcome": outcome, "horizon": horizon, "step": r.step,
                             "predictor": r.predictor, "tier": r.tier, "AP": r.AP,
                             "gain": r.gain, "prevalence": js["anchors"]["prevalence"],
                             "all_pool_AP": js["anchors"]["all88"],
                             "set21_AP": js["anchors"]["original21"]})
    pd.DataFrame(rows).to_csv(OUT / "tiers_by_horizon.csv", index=False)
    for k, v in boot.items():
        print(f"  {k:55s} dAP {v['d_AP']:+.4f} [{v['d_AP_lo']:+.4f}, {v['d_AP_hi']:+.4f}]"
              f"  dAUROC {v['d_AUROC']:+.4f} [{v['d_AUROC_lo']:+.4f}, {v['d_AUROC_hi']:+.4f}]")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
