"""Original 21 vs deduplicated 85 vs enhanced 95, on identical folds.

    python scripts/run_set_comparison.py --outcome anc8plus [--seeds 10]

run_stability.py already compares 21 against 95, but with one model whose
hyperparameters were tuned on the 95 -- which tilts the comparison toward the
set the tuning saw. This widens it in the two ways needed to decide between
the sets:

  * a third arm, the 85 distinct variables left once the ten duplicated
    columns are removed (outputs/enhanced/redundancy/);
  * a second model, logistic regression, which has almost nothing to tune and
    so cannot favour one set through its hyperparameters.

Every arm sees the same folds within a seed, so differences are paired and the
seed-to-seed noise cancels. Written to outputs/enhanced/set_comparison/.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import design, outcomes, tuning  # noqa: E402

OUT = ROOT / "outputs" / "enhanced"
HANDOFF = ROOT / "outputs" / "notebook3_explainability_handoff"
DEST = OUT / "set_comparison"
MODELS = ["Logistic regression", "LightGBM"]


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outcome", default="anc8plus", choices=outcomes.LADDER)
    ap.add_argument("--seeds", type=int, default=10)
    args = ap.parse_args()
    rung = args.outcome
    DEST.mkdir(parents=True, exist_ok=True)

    df = pd.read_pickle(OUT / "ANC8_analysis_frozen_v2.pkl")
    spec = json.load(open(OUT / "feature_spec_v2.json"))
    best = json.load(open(OUT / rung / "best_hyperparameters.json"))
    dropped = set(json.load(open(OUT / "redundancy" / "redundancy_summary.json"))["dropped"])

    # The original 21 need three constructs that live only in the V1 dataset;
    # rebuilt exactly as run_stability.py does, so the original arm is complete.
    orig = json.load(open(HANDOFF / "predictor_architecture.json"))
    v1 = pd.read_pickle(ROOT / "outputs" / "ANC8_analysis_frozen.pkl")
    df = df.merge(v1[["caseid", "traditional_media_weekly_count", "household_size",
                      "travel_time_min"]], on="caseid", how="left",
                  validate="one_to_one")

    e_num, e_cat = spec["numeric_predictors"], spec["categorical_predictors"]
    o_all = orig["full_cohort_predictors"]
    sets = {
        "original 21": ([c for c in o_all if c in orig["numeric_predictors"]],
                        [c for c in o_all if c not in orig["numeric_predictors"]]),
        "deduplicated 85": ([c for c in e_num if c not in dropped],
                            [c for c in e_cat if c not in dropped]),
        "enhanced 95": (e_num, e_cat),
    }
    for name, (n, c) in sets.items():
        log(f"{name}: {len(n) + len(c)} predictors")

    y = df[rung].astype(int).to_numpy()
    w = (df.v005 / 1e6).to_numpy()
    frames = {}
    for name, (n, c) in sets.items():
        X = df[n + c].copy()
        for col in c:
            X[col] = X[col].astype(str)
        frames[name] = X

    params = {m: dict(best.get(m, {})) for m in MODELS}
    if "n_estimators" in params["LightGBM"]:
        params["LightGBM"]["n_estimators"] = min(params["LightGBM"]["n_estimators"], 400)

    rows = []
    t0 = time.time()
    for s in range(args.seeds):
        seed = 2026 + s
        splits = design.folds_to_splits(design.make_psu_stratum_folds(df, seed=seed))
        for model in MODELS:
            for name, (n, c) in sets.items():
                t = time.time()
                p = tuning.oof_predict(model, params[model], frames[name], y, w,
                                       splits, n, c)
                rows.append({
                    "outcome": rung, "seed": seed, "model": model, "set": name,
                    "n_predictors": len(n) + len(c),
                    "AP": average_precision_score(y, p, sample_weight=w),
                    "AUROC": roc_auc_score(y, p, sample_weight=w),
                    "seconds": time.time() - t,
                })
        last = [r for r in rows if r["seed"] == seed]
        log(f"seed {seed}: " + "  ".join(
            f"{r['model'][:3]}/{r['set'].split()[1]} {r['AP']:.4f}" for r in last))

    res = pd.DataFrame(rows)
    res.to_csv(DEST / f"{rung}_repeated.csv", index=False)

    # Paired differences against the original 21, per model.
    summary = {"outcome": rung, "n_seeds": args.seeds,
               "prevalence": outcomes.OUTCOMES[rung]["weighted_prevalence"],
               "minutes": (time.time() - t0) / 60, "models": {}}
    for model in MODELS:
        sub = res[res.model == model].pivot_table(index="seed", columns="set",
                                                  values=["AP", "AUROC"])
        block = {}
        for name in sets:
            entry = {"n_predictors": len(sets[name][0]) + len(sets[name][1])}
            for m in ("AP", "AUROC"):
                entry[f"{m}_mean"] = float(sub[m][name].mean())
                if name != "original 21":
                    d = sub[m][name] - sub[m]["original 21"]
                    entry[f"{m}_gain_vs_21"] = float(d.mean())
                    entry[f"{m}_gain_lo"] = float(d.quantile(0.025))
                    entry[f"{m}_gain_hi"] = float(d.quantile(0.975))
                    entry[f"{m}_seeds_better"] = int((d > 0).sum())
            block[name] = entry
        d85 = sub["AP"]["enhanced 95"] - sub["AP"]["deduplicated 85"]
        block["95_minus_85_AP"] = float(d85.mean())
        block["95_minus_85_seeds_better"] = int((d85 > 0).sum())
        summary["models"][model] = block
    json.dump(summary, open(DEST / f"{rung}_summary.json", "w"), indent=2)

    print()
    print(f"{outcomes.OUTCOMES[rung]['label']}  (prevalence "
          f"{summary['prevalence']:.3f}, {args.seeds} paired splits)")
    for model, block in summary["models"].items():
        print(f"\n  {model}")
        for name in sets:
            e = block[name]
            extra = ""
            if "AP_gain_vs_21" in e:
                extra = (f"   gain vs 21: AP {e['AP_gain_vs_21']:+.4f} "
                         f"({e['AP_seeds_better']}/{args.seeds} splits)  "
                         f"AUROC {e['AUROC_gain_vs_21']:+.4f}")
            print(f"    {name:17s} AP {e['AP_mean']:.4f}  AUROC {e['AUROC_mean']:.4f}{extra}")
        print(f"    95 minus 85: AP {block['95_minus_85_AP']:+.4f} "
              f"({block['95_minus_85_seeds_better']}/{args.seeds} splits favour 95)")


if __name__ == "__main__":
    main()
