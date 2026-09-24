"""Repeated-split stability comparison of the two predictor sets.

The held-out set has 1,375 women and roughly 234 events, which is why the
original study's confidence intervals were as wide as they were (AUROC 0.688
to 0.834). A single split cannot resolve a difference of a few points of AP,
so a difference measured on it -- in either direction -- is weak evidence.

This script instead repeats the whole PSU-grouped, stratum-preserving
cross-validation over many split seeds and compares the ORIGINAL 21 predictors
against the ENHANCED set, holding the algorithm, the folds and the weighting
fixed. Because the two arms see identical folds within each seed, the
comparison is paired and the seed-to-seed noise cancels.

This is the honest evidence for whether the feature work helped.

    python scripts/run_stability.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import design, outcomes, tuning  # noqa: E402

OUT = ROOT / "outputs" / "enhanced"
HANDOFF = ROOT / "outputs" / "notebook3_explainability_handoff"

N_SEEDS = 20
MODEL = "LightGBM"  # fast, and competitive with the champion


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)



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

    df = pd.read_pickle(OUT / "ANC8_analysis_frozen_v2.pkl")
    spec = json.load(open(OUT / "feature_spec_v2.json"))
    best = json.load(open(OUT_DIR / "best_hyperparameters.json"))

    params = dict(best.get(MODEL, {"n_estimators": 400, "learning_rate": 0.03,
                                   "num_leaves": 15}))
    params["n_estimators"] = min(params.get("n_estimators", 400), 400)

    enh_num = spec["numeric_predictors"]
    enh_cat = spec["categorical_predictors"]

    # The original 21, as the study defined them. traditional_media_weekly_count
    # lives only in the V1 frozen dataset, so it is rebuilt here from its three
    # source items exactly as Notebook 1 built it -- otherwise the ORIGINAL arm
    # would be handicapped by a missing predictor and the comparison would be
    # unfair to it.
    orig = json.load(open(HANDOFF / "predictor_architecture.json"))
    frozen_v1 = pd.read_pickle(ROOT / "outputs" / "ANC8_analysis_frozen.pkl")
    df = df.merge(
        frozen_v1[["caseid", "traditional_media_weekly_count", "household_size",
                   "travel_time_min"]],
        on="caseid", how="left", validate="one_to_one",
    )

    orig_all = orig["full_cohort_predictors"]
    orig_num = [c for c in orig_all if c in orig["numeric_predictors"]]
    orig_cat = [c for c in orig_all if c not in orig["numeric_predictors"]]
    missing = [c for c in orig_all if c not in df.columns]
    assert not missing, f"original predictors missing from the frame: {missing}"

    y = df[OUTCOME].astype(int).to_numpy()
    w = (df.v005 / 1e6).to_numpy()

    def prep(cols, cats):
        X = df[cols].copy()
        for c in cats:
            X[c] = X[c].astype(str)
        return X

    X_orig = prep(orig_all, orig_cat)
    X_enh = prep(enh_num + enh_cat, enh_cat)

    rows = []
    for seed in range(N_SEEDS):
        folds = design.make_psu_stratum_folds(df, seed=2026 + seed)
        splits = design.folds_to_splits(folds)

        p_o = tuning.oof_predict(MODEL, params, X_orig, y, w, splits, orig_num, orig_cat)
        p_e = tuning.oof_predict(MODEL, params, X_enh, y, w, splits, enh_num, enh_cat)

        r = {
            "seed": 2026 + seed,
            "original_AP": average_precision_score(y, p_o, sample_weight=w),
            "enhanced_AP": average_precision_score(y, p_e, sample_weight=w),
            "original_AUROC": roc_auc_score(y, p_o, sample_weight=w),
            "enhanced_AUROC": roc_auc_score(y, p_e, sample_weight=w),
        }
        r["delta_AP"] = r["enhanced_AP"] - r["original_AP"]
        r["delta_AUROC"] = r["enhanced_AUROC"] - r["original_AUROC"]
        rows.append(r)
        log(f"seed {r['seed']}: original AP={r['original_AP']:.4f}  "
            f"enhanced AP={r['enhanced_AP']:.4f}  delta={r['delta_AP']:+.4f}")

    res = pd.DataFrame(rows)
    res.to_csv(OUT_DIR / "stability_repeated_splits.csv", index=False)

    summary = {
        "model": MODEL,
        "n_seeds": N_SEEDS,
        "n_original_predictors": len(orig_all),
        "n_enhanced_predictors": len(enh_num) + len(enh_cat),
    }
    for m in ["AP", "AUROC"]:
        d = res[f"delta_{m}"]
        summary[m] = {
            "original_mean": float(res[f"original_{m}"].mean()),
            "enhanced_mean": float(res[f"enhanced_{m}"].mean()),
            "delta_mean": float(d.mean()),
            "delta_sd": float(d.std(ddof=1)),
            # Percentile interval over seeds, and the count of seeds where the
            # enhanced set won. Every seed favouring one arm is far stronger
            # evidence than a single split's point estimate.
            "delta_lo": float(d.quantile(0.025)),
            "delta_hi": float(d.quantile(0.975)),
            "seeds_enhanced_better": int((d > 0).sum()),
        }
    json.dump(summary, open(OUT_DIR / "stability_summary.json", "w"), indent=2)

    print()
    for m in ["AP", "AUROC"]:
        s = summary[m]
        print(f"{m}: original {s['original_mean']:.4f} -> enhanced {s['enhanced_mean']:.4f}  "
              f"delta {s['delta_mean']:+.4f} (sd {s['delta_sd']:.4f}), "
              f"enhanced better in {s['seeds_enhanced_better']}/{N_SEEDS} seeds")


if __name__ == "__main__":
    main()
