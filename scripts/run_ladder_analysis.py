"""Cross-outcome predictor importance across the ANC contact ladder.

    python scripts/run_ladder_analysis.py

Requires every rung to have completed run_pipeline.py.

This is the analysis the whole three-rung rebuild exists to support: does what
predicts reaching antenatal care AT ALL differ from what predicts completing
the full eight-contact schedule?

Importance is computed three independent ways per rung -- exact EBM additive
contributions, SHAP on the best booster, and drop-one AP loss -- and a pattern
is only reported as a finding when at least two of them agree. Anything one
method says on its own is treated as a property of that method.
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import design, ladder, outcomes, tuning  # noqa: E402

ENHANCED = ROOT / "outputs" / "enhanced"
OUT = ROOT / "outputs" / "ladder"

# Drop-one over 95 predictors costs 95 out-of-fold passes per rung, so it uses
# a deliberately cheap configuration. It is a corroborating signal, not the
# primary one.
DROPONE_PARAMS = {"n_estimators": 200, "learning_rate": 0.05, "num_leaves": 15,
                  "reg_lambda": 1.0}


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def duplicate_map():
    """dropped copy -> the twin that is kept (outputs/enhanced/redundancy/).

    Ten predictors are the same variable under two names (e.g. `v024` and
    `region`). Importance has to be counted once per variable: drop-one on a
    set containing both copies reports ~0 for each, because the twin carries
    the same information, and per-column EBM/SHAP splits the weight in half.
    """
    red = ENHANCED / "redundancy"
    if not (red / "duplicate_pairs.csv").exists():
        return {}
    dropped = set(json.load(open(red / "redundancy_summary.json"))["dropped"])
    pairs = pd.read_csv(red / "duplicate_pairs.csv")
    out = {}
    for r in pairs.itertuples():
        if r.a in dropped and r.b not in dropped:
            out[r.a] = r.b
        elif r.b in dropped and r.a not in dropped:
            out[r.b] = r.a
    return out


def fold_duplicates(s: pd.Series, dup: dict) -> pd.Series:
    """Add each dropped copy's importance to its kept twin."""
    s = s.copy()
    for copy, twin in dup.items():
        if copy in s.index:
            if twin in s.index:
                s[twin] += s[copy]
            s = s.drop(copy)
    return s


def load_common():
    df = pd.read_pickle(ENHANCED / "ANC8_analysis_frozen_v2.pkl")
    spec = json.load(open(ENHANCED / "feature_spec_v2.json"))
    numeric, categorical = spec["numeric_predictors"], spec["categorical_predictors"]

    train_psus, test_psus = design.make_psu_holdout(df)
    dev = df[df.v021.isin(train_psus)].reset_index(drop=True)
    held = df[df.v021.isin(test_psus)].reset_index(drop=True)
    splits = design.folds_to_splits(design.make_psu_stratum_folds(dev))

    def prep(frame, cols=None):
        cols = cols or (numeric + categorical)
        X = frame[cols].copy()
        for c in cols:
            if c in categorical:
                X[c] = X[c].astype(str)
        return X

    return df, dev, held, splits, numeric, categorical, prep


def ebm_importance(rung, dev, prep, numeric, categorical):
    """Exact additive contributions from the Explainable Boosting model.

    For a GAM the prediction IS the intercept plus these terms, so this is not
    an approximation of importance -- it is the model's own arithmetic.
    """
    import joblib

    blob = joblib.load(ENHANCED / rung / "enhanced_models.joblib")
    pipe = blob["models"].get("Explainable Boosting")
    if pipe is None:
        return None

    est = pipe.named_steps["model"]
    Xt = pipe.named_steps["pre"].transform(prep(dev))
    Xt = np.asarray(Xt.todense()) if hasattr(Xt, "todense") else np.asarray(Xt)

    names = numeric + categorical
    scores = {}
    for ti, feats in enumerate(est.term_features_):
        if len(feats) != 1:
            continue
        f = feats[0]
        raw = est.bins_[f]
        binspec = raw[0] if isinstance(raw, list) else raw
        term = np.asarray(est.term_scores_[ti])

        col = Xt[:, f]
        if isinstance(binspec, dict):
            idx = np.array([binspec.get(v, 0) for v in col], dtype=int)
        else:
            idx = np.searchsorted(np.asarray(binspec, dtype=float), col,
                                  side="right") + 1
        idx = np.clip(idx, 0, len(term) - 1)
        # Mean |contribution| across women: how much this predictor actually
        # moves predictions in this population, not how steep its curve is.
        scores[names[f]] = float(np.abs(term[idx]).mean())

    return pd.Series(scores)


def shap_importance(rung, dev, prep, numeric, categorical, dev_perf):
    """SHAP on the best tree model whose preprocessor keeps one column per
    predictor, so values map back to constructs without re-aggregation."""
    import joblib
    import shap

    blob = joblib.load(ENHANCED / rung / "enhanced_models.joblib")
    names = numeric + categorical

    for candidate in dev_perf.sort_values("AP", ascending=False).model:
        pipe = blob["models"].get(candidate)
        if pipe is None or not hasattr(pipe, "named_steps"):
            continue
        est = getattr(pipe.named_steps["model"], "estimator",
                      pipe.named_steps["model"])
        # XGBoost and LightGBM only. HistGradientBoosting was the best ANC4+
        # model, but its native categorical splits are not handled correctly by
        # SHAP's tree explainer: the first run gave the wealth score 0.009 and
        # mobile-phone ownership 0.113 at ANC4+, disagreeing with EBM entirely.
        if type(est).__module__.split(".")[0] not in ("xgboost", "lightgbm"):
            continue
        try:
            Xt = pipe.named_steps["pre"].transform(prep(dev))
            Xt = np.asarray(Xt.todense()) if hasattr(Xt, "todense") else np.asarray(Xt)
            if Xt.shape[1] != len(names):
                continue
            sv = shap.TreeExplainer(est).shap_values(Xt)
            if isinstance(sv, list):
                sv = sv[1]
            if getattr(sv, "ndim", 2) == 3:
                sv = sv[:, :, 1]
            log(f"    SHAP via {candidate}")
            return pd.Series(np.abs(sv).mean(axis=0), index=names), candidate
        except Exception as exc:
            log(f"    {candidate} unusable for SHAP: {type(exc).__name__}")
    return None, None


def dropone_importance(rung, dev, splits, prep, numeric, categorical):
    """AP lost when each predictor is removed, over the shared folds.

    Run on the distinct variables only (duplicate copies removed first), so
    that removing a variable actually removes its information.
    """
    from sklearn.metrics import average_precision_score

    y = dev[rung].astype(int).to_numpy()
    w = (dev.v005 / 1e6).to_numpy()
    all_cols = numeric + categorical

    full = average_precision_score(
        y, tuning.oof_predict("LightGBM", DROPONE_PARAMS, prep(dev, all_cols), y, w,
                              splits, numeric, categorical, n_jobs=5), sample_weight=w)

    losses = {}
    for i, v in enumerate(all_cols, 1):
        cols = [c for c in all_cols if c != v]
        n_ = [c for c in cols if c in numeric]
        c_ = [c for c in cols if c in categorical]
        ap = average_precision_score(
            y, tuning.oof_predict("LightGBM", DROPONE_PARAMS, prep(dev, cols),
                                  y, w, splits, n_, c_, n_jobs=5), sample_weight=w)
        losses[v] = max(full - ap, 0.0)
        if i % 20 == 0:
            log(f"    drop-one {i}/{len(all_cols)}")
    return pd.Series(losses)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df, dev, held, splits, numeric, categorical, prep = load_common()

    available = [r for r in outcomes.LADDER
                 if (ENHANCED / r / "enhanced_models.joblib").exists()]
    log(f"rungs available: {available}")
    if len(available) < 2:
        log("need at least two rungs; run scripts/run_pipeline.py first")
        sys.exit(1)

    # ---- headline performance, on comparable metrics only -----------------
    perf_rows = []
    for rung in available:
        hp = pd.read_csv(ENHANCED / rung / "heldout_performance.csv")
        v2 = hp[hp.generation == "V2 (enhanced)"].set_index("model")
        # The development champion. Picking the best held-out score would let
        # the test women choose the model and flatter every rung.
        dev = pd.read_csv(ENHANCED / rung / "development_oof_performance.csv")
        champ = next(m for m in dev.dropna(subset=["AP"])
                     .sort_values("AP", ascending=False).model if m in v2.index)
        top = v2.loc[champ].copy()
        top["model"] = champ
        perf_rows.append({
            "rung": outcomes.OUTCOMES[rung]["label"],
            "outcome": rung,
            "weighted_prevalence": outcomes.OUTCOMES[rung]["weighted_prevalence"],
            "best_model": top.model,
            "AUROC": top.AUROC,
            "AP": top.AP,
            "AP_lift_over_prevalence": outcomes.ap_lift(top.AP, rung),
            "Brier": top.Brier,
            "calibration_slope": top.Calibration_slope,
        })
    perf = pd.DataFrame(perf_rows)
    perf.to_csv(OUT / "ladder_performance.csv", index=False)

    print()
    print("HELD-OUT PERFORMANCE ACROSS THE LADDER")
    print("(AP is NOT comparable between rungs -- its floor is the prevalence.")
    print(" Use AUROC, or AP lift over prevalence.)")
    print(perf[["rung", "weighted_prevalence", "best_model", "AUROC", "AP",
                "AP_lift_over_prevalence"]].round(4).to_string(index=False))

    # ---- importance, three ways -------------------------------------------
    methods = {}
    dup = duplicate_map()
    log(f"duplicate copies folded into their twins: {sorted(dup)}")

    log("\nEBM additive contributions")
    ebm = {}
    for rung in available:
        s = ebm_importance(rung, dev, prep, numeric, categorical)
        if s is not None:
            ebm[rung] = fold_duplicates(s, dup)
            log(f"  {rung}: {len(s)} terms")
    if len(ebm) >= 2:
        methods["EBM"] = ladder.assemble(ebm, "EBM")

    log("\nSHAP on the best booster")
    sh = {}
    for rung in available:
        dev_perf = pd.read_csv(ENHANCED / rung / "development_oof_performance.csv")
        dev_perf = dev_perf[dev_perf.AP.notna()]
        s, used = shap_importance(rung, dev, prep, numeric, categorical, dev_perf)
        if s is not None:
            sh[rung] = fold_duplicates(s, dup)
    if len(sh) >= 2:
        methods["SHAP"] = ladder.assemble(sh, "SHAP")

    log("\ndrop-one AP loss")
    do = {}
    for rung in available:
        log(f"  {rung}")
        do[rung] = dropone_importance(
            rung, dev, splits, prep,
            [c for c in numeric if c not in dup], [c for c in categorical if c not in dup])
    if len(do) >= 2:
        methods["drop-one"] = ladder.assemble(do, "drop-one")

    for name, frame in methods.items():
        frame.to_csv(OUT / f"importance_{name.replace(' ', '_')}.csv")

    # ---- do the methods agree? --------------------------------------------
    agree = ladder.agreement(methods)
    agree.to_csv(OUT / "method_agreement.csv", index=False)
    print("\nMETHOD AGREEMENT (Spearman, within rung)")
    print(agree.round(3).to_string(index=False))
    print("")
    print("  Domain-level agreement is the one to weigh: predictor-level")
    print("  understates it when predictors are correlated, as wealth is here.")

    # ---- corroborated ladder patterns -------------------------------------
    corr = ladder.corroborated(methods)
    corr.to_csv(OUT / "ladder_patterns.csv", index=False)

    print("\nPREDICTORS WHOSE ROLE SHIFTS ALONG THE LADDER")
    print("(agreed by at least two independent importance methods)")
    for label, heading in [
        ("access-limited",
         "MATTER MORE FOR REACHING CARE AT ALL than for completing the schedule"),
        ("engagement-limited",
         "MATTER MORE FOR COMPLETING THE SCHEDULE than for reaching care at all"),
    ]:
        sub = corr[corr.pattern == label].head(12)
        print(f"\n  {heading}")
        if len(sub) == 0:
            print("    (none corroborated)")
        for r in sub.itertuples():
            print(f"    {r.predictor:34s} {r.domain:26s} "
                  f"shift {r.mean_share_shift:+.4f}  "
                  f"({r.methods_agreeing}/{r.methods_total} methods)")

    # ---- domain roll-up ----------------------------------------------------
    rolls = {}
    for name, frame in methods.items():
        roll = ladder.domain_rollup(frame)
        roll["method"] = name
        rolls[name] = roll
    allroll = pd.concat(rolls.values())
    allroll.to_csv(OUT / "domain_rollup.csv")

    print("\nDOMAIN SHARE OF TOTAL IMPORTANCE, BY RUNG (mean across methods)")
    rungs = [r for r in available]
    mean_roll = allroll.groupby(level=0)[rungs].mean()
    mean_roll["shift"] = mean_roll[rungs[-1]] - mean_roll[rungs[0]]
    mean_roll = mean_roll.sort_values(rungs[-1], ascending=False)
    hdr = "".join(f"{outcomes.OUTCOMES[r]['label']:>10s}" for r in rungs)
    print(f"{'domain':28s}{hdr}{'shift':>10s}")
    for d, row in mean_roll.iterrows():
        vals = "".join(f"{row[r]:>10.3f}" for r in rungs)
        print(f"{d:28s}{vals}{row['shift']:>+10.3f}")

    json.dump({
        "rungs": available,
        "methods": list(methods),
        "n_corroborated_patterns": int(len(corr)),
        "domain_rollup": mean_roll.to_dict(),
    }, open(OUT / "ladder_summary.json", "w"), indent=2, default=float)

    log(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
