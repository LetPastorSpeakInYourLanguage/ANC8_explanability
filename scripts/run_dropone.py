"""Which of the original 21 predictors actually earned their place?

Notebook 3 asks what the original study left out. This asks the other half of
the question: what did it include that contributes nothing?

For each of the 21, the model is refitted without it over the same
PSU-grouped folds, and the change in survey-weighted out-of-fold Average
Precision is recorded. A predictor whose removal does not hurt -- or helps --
is carrying no independent signal in the presence of the others.

Two cautions on reading the result:

  * this is a DROP-ONE measure, so a predictor duplicated by another will look
    worthless even when the pair jointly matters. Region and residence, or the
    several education measures, are the obvious cases;
  * a predictor with no predictive contribution may still belong in a model
    for reasons this measure cannot see (equity monitoring, comparability with
    prior work). "Contributes nothing to prediction" is not "should be deleted".

    python scripts/run_dropone.py
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

from anc8 import design, tuning  # noqa: E402

OUT = ROOT / "outputs" / "enhanced"
HANDOFF = ROOT / "outputs" / "notebook3_explainability_handoff"

MODEL = "LightGBM"
PARAMS = {"n_estimators": 300, "learning_rate": 0.05, "num_leaves": 15,
          "reg_lambda": 1.0, "colsample_bytree": 0.8}


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    frozen = pd.read_pickle(ROOT / "outputs" / "ANC8_analysis_frozen.pkl")
    df = frozen[frozen.anc8plus.notna()].reset_index(drop=True)

    arch = json.load(open(HANDOFF / "predictor_architecture.json"))
    preds = arch["full_cohort_predictors"]
    num_all = arch["numeric_predictors"]

    train_psus, _ = design.make_psu_holdout(df)
    dev = df[df.v021.isin(train_psus)].reset_index(drop=True)
    splits = design.folds_to_splits(design.make_psu_stratum_folds(dev))

    y = dev.anc8plus.astype(int).to_numpy()
    w = (dev.v005 / 1e6).to_numpy()

    def run(cols):
        n = [c for c in cols if c in num_all]
        c_ = [c for c in cols if c not in num_all]
        X = dev[cols].copy()
        for c in c_:
            X[c] = X[c].astype(str)
        p = tuning.oof_predict(MODEL, PARAMS, X, y, w, splits, n, c_)
        return (average_precision_score(y, p, sample_weight=w),
                roc_auc_score(y, p, sample_weight=w))

    full_ap, full_auc = run(preds)
    log(f"full 21-predictor model: AP={full_ap:.4f} AUROC={full_auc:.4f}")

    rows = []
    for v in preds:
        ap, auc = run([c for c in preds if c != v])
        rows.append({
            "predictor": v,
            "AP_without": ap,
            "AUROC_without": auc,
            "AP_loss": full_ap - ap,
            "AUROC_loss": full_auc - auc,
        })
        log(f"  without {v:38s} AP={ap:.4f}  loss={full_ap - ap:+.4f}")

    res = pd.DataFrame(rows).sort_values("AP_loss", ascending=False)
    res["full_AP"] = full_ap
    res.to_csv(OUT / "original21_drop_one.csv", index=False)

    print()
    print("CONTRIBUTION OF EACH ORIGINAL PREDICTOR (drop-one, development OOF)")
    print(res[["predictor", "AP_without", "AP_loss", "AUROC_loss"]].to_string(index=False))

    dead = res[res.AP_loss <= 0]
    print(f"\n{len(dead)} of {len(preds)} predictors cost nothing when removed:")
    for r in dead.itertuples():
        print(f"    {r.predictor:38s} AP change {-r.AP_loss:+.4f}")

    # How much of the 21-predictor model can a handful of its own members
    # reproduce? Greedy forward selection rather than "top k by drop-one":
    # drop-one ranks a predictor by what it adds LAST, given all the others,
    # which is not the same as what it adds FIRST. Taking the top k of a
    # drop-one ranking quietly assumes those two orders agree.
    log("greedy forward selection over the original 21")
    chosen, remaining, ladder_rows = [], list(preds), []

    for _ in range(4):
        scored = []
        for cand in remaining:
            ap, auc = run(chosen + [cand])
            scored.append((ap, auc, cand))
        scored.sort(key=lambda t: (-t[0], t[2]))
        ap, auc, pick = scored[0]
        chosen.append(pick)
        remaining.remove(pick)
        ladder_rows.append({"specification": " + ".join(chosen),
                            "n_predictors": len(chosen), "AP": ap, "AUROC": auc})
        log(f"  +{pick:38s} n={len(chosen)}  AP={ap:.4f}")

    trimmed = [c for c in preds if c not in set(dead.predictor)]
    t_ap, t_auc = run(trimmed)
    log(f"  original minus {len(dead)} non-contributing: AP={t_ap:.4f}")

    ladder = pd.DataFrame(
        [{"specification": "Original 21, as published",
          "n_predictors": len(preds), "AP": full_ap, "AUROC": full_auc},
         {"specification": f"Original minus {len(dead)} non-contributing",
          "n_predictors": len(trimmed), "AP": t_ap, "AUROC": t_auc}]
        + ladder_rows
    )
    ladder["pct_of_full_AP"] = (100 * ladder.AP / full_ap).round(1)
    ladder.to_csv(OUT / "original21_parsimony_ladder.csv", index=False)

    print()
    print("HOW FAR A HANDFUL OF THE ORIGINAL PREDICTORS GETS YOU")
    print(ladder.to_string(index=False))

    best_small = ladder[ladder.n_predictors <= 4].AP.max()
    print(f"\nBest 4-predictor subset: AP {best_small:.4f} against {full_ap:.4f} "
          f"for all 21 ({best_small / full_ap * 100:.0f}% of the full model).")


if __name__ == "__main__":
    main()
