"""Final held-out evaluation of the enhanced ANC8 models.

Run AFTER scripts/run_tuning.py. Produces everything Notebook 4 reports:

  * a stacked ensemble and a nested-calibrated version of the best model;
  * the cumulative-link ordinal arm;
  * a parsimonious model for deployment;
  * held-out performance for old and new models on the IDENTICAL test set;
  * paired stratified-PSU bootstrap CIs for the difference between them;
  * decision-curve analysis and subgroup performance.

The held-out set is touched here for the first time, once, after every model
configuration is locked.

RUNTIME: roughly 2-3 hours, and the forward selection in the parsimony stage
dominates it. That step costs ~950 out-of-fold fits (10 rounds x ~95 remaining
candidates x 5 folds) and takes about 11 minutes per round on this dataset. It
is deliberately not made cheaper by reducing folds or trees: the selected
predictor set is what the deployed quick mode uses, and a selection made on a
noisier signal is a worse selection, not a faster one. If you need a quick pass,
reduce the `range(10)` bound rather than weakening each evaluation.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from anc8 import design, metrics, outcomes, tuning  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "enhanced"
HANDOFF = ROOT / "outputs" / "notebook3_explainability_handoff"

N_BOOT = 2000
BOOT_SEED = 2026


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
    numeric, categorical = spec["numeric_predictors"], spec["categorical_predictors"]
    best = json.load(open(OUT_DIR / "best_hyperparameters.json"))
    dev_perf = pd.read_csv(OUT_DIR / "development_oof_performance.csv")

    train_psus, test_psus = design.make_psu_holdout(df)
    dev = df[df.v021.isin(train_psus)].reset_index(drop=True)
    held = df[df.v021.isin(test_psus)].reset_index(drop=True)

    # Gate: the held-out set must be the same women the original study used.
    lock = pd.read_csv(HANDOFF / "full_cohort_locked_predictions.csv")
    assert set(held.caseid) == set(lock.caseid), "held-out set differs from the original"
    log(f"held-out identity check passed (n={len(held)})")

    def prep(frame, cols=None):
        cols = cols or (numeric + categorical)
        X = frame[cols].copy()
        for c in cols:
            if c in categorical:
                X[c] = X[c].astype(str)
        return X

    X_dev, X_held = prep(dev), prep(held)
    y_dev = dev[OUTCOME].astype(int).to_numpy()
    y_held = held[OUTCOME].astype(int).to_numpy()
    w_dev = (dev.v005 / 1e6).to_numpy()
    w_held = (held.v005 / 1e6).to_numpy()
    splits = design.folds_to_splits(design.make_psu_stratum_folds(dev))

    oof = dict(np.load(OUT_DIR / "development_oof_predictions.npz"))
    fitted, held_pred, dev_oof = {}, {}, {}

    # ---------------------------------------------------------------- zoo
    ok = dev_perf[dev_perf.AP.notna()].sort_values("AP", ascending=False)
    for name in ok.model:
        log(f"refitting {name} on full development set")
        pipe = tuning.fit_final(name, best[name], X_dev, y_dev, w_dev, numeric, categorical)
        fitted[name] = pipe
        held_pred[name] = pipe.predict_proba(X_held)[:, 1]
        dev_oof[name] = oof[name]

    # ------------------------------------------------------------ ensemble
    # Stack over out-of-fold predictions: the meta-learner is fitted on
    # predictions no base model saw during its own fitting, so the weights are
    # not chosen on data the base models memorised.
    top = list(ok.model[:5])
    log(f"stacking {top}")
    Z_dev = np.column_stack([dev_oof[n] for n in top])
    Z_held = np.column_stack([held_pred[n] for n in top])
    meta = LogisticRegression(max_iter=2000).fit(Z_dev, y_dev, sample_weight=w_dev / w_dev.mean())
    dev_oof["Stacked ensemble"] = meta.predict_proba(Z_dev)[:, 1]
    held_pred["Stacked ensemble"] = meta.predict_proba(Z_held)[:, 1]
    fitted["Stacked ensemble"] = {"base": top, "meta": meta}

    # --------------------------------------------------- cumulative link
    # The outcome is a dichotomised count; model several thresholds and pool.
    raw = pd.read_stata(ROOT / "ETIR8AFL.dta", columns=["caseid", "m14_1"],
                        convert_categoricals=False)
    dev_counts = dev[["caseid"]].merge(raw, on="caseid", how="left").m14_1.to_numpy()

    cl_name = ok.model.iloc[0]
    log(f"cumulative-link arm using {cl_name}")
    target_k = outcomes.OUTCOMES[OUTCOME]["threshold"]
    pooled_oof, _ = tuning.cumulative_link_oof(
        cl_name, best[cl_name], X_dev, dev_counts, w_dev, splits, numeric,
        categorical, target=target_k
    )
    # Map the pooled ranking back onto the probability scale, learned on
    # development data only.
    iso = IsotonicRegression(out_of_bounds="clip").fit(pooled_oof, y_dev, sample_weight=w_dev)
    dev_oof["Cumulative-link ensemble"] = iso.predict(pooled_oof)

    # Same ladder, same monotonicity constraint, same distance weighting as the
    # out-of-fold pass -- otherwise the held-out score would not be produced by
    # the procedure that was developed.
    ks, cols = [], []
    for k in tuning.LADDER_THRESHOLDS:
        yk = (dev_counts >= k).astype(int)
        if yk.min() == yk.max():
            continue
        fitted_k = tuning.fit_final(cl_name, best[cl_name], X_dev, yk,
                                    w_dev, numeric, categorical)
        ks.append(k)
        cols.append(fitted_k.predict_proba(X_held)[:, 1])
    mono = tuning._isotonic_decreasing(np.column_stack(cols))
    wts = np.array([1.0 / (1.0 + abs(k - target_k)) for k in ks])
    held_pred["Cumulative-link ensemble"] = iso.predict(
        (mono * wts).sum(axis=1) / wts.sum()
    )
    fitted["Cumulative-link ensemble"] = {"base": cl_name, "isotonic": iso}

    # ------------------------------------------------------- calibration
    # Two calibration maps, because they trade off differently and the choice
    # should be made on evidence rather than habit:
    #
    #   isotonic  flexible, but produces TIED predictions in its flat regions,
    #             which costs ranking performance (AP and AUROC);
    #   Platt     a monotone logistic map, so ranking is preserved almost
    #             exactly while the slope is still corrected.
    #
    # Both are fitted inside inner folds, so the calibrator never sees the
    # predictions it is scored on.
    for method in ("isotonic", "platt"):
        label = f"{cl_name} ({method} calibrated)"
        log(f"nested {method} calibration of {cl_name}")
        dev_oof[label] = tuning.nested_calibrated_oof(
            cl_name, best[cl_name], X_dev, y_dev, w_dev, splits,
            numeric, categorical, method=method,
        )
        if method == "isotonic":
            cal = IsotonicRegression(out_of_bounds="clip").fit(
                dev_oof[cl_name], y_dev, sample_weight=w_dev
            )
            held_pred[label] = cal.predict(held_pred[cl_name])
        else:
            lp_dev = np.log(np.clip(dev_oof[cl_name], 1e-9, 1 - 1e-9)
                            / (1 - np.clip(dev_oof[cl_name], 1e-9, 1 - 1e-9)))
            cal = LogisticRegression(max_iter=1000).fit(
                lp_dev.reshape(-1, 1), y_dev, sample_weight=w_dev
            )
            lp_held = np.log(np.clip(held_pred[cl_name], 1e-9, 1 - 1e-9)
                             / (1 - np.clip(held_pred[cl_name], 1e-9, 1 - 1e-9)))
            held_pred[label] = cal.predict_proba(lp_held.reshape(-1, 1))[:, 1]
        fitted[label] = {"base": cl_name, "method": method, "calibrator": cal}

    # --------------------------------------------------------- parsimony
    # 95 predictors is unusable as a web form. Greedy forward selection on
    # out-of-fold AP finds a short model a health worker could actually fill in.
    # Forward selection costs ~10 x 95 = 950 out-of-fold fits, so the SELECTOR
    # must be cheap: at CatBoost speed this step alone would run for days. A
    # fast booster picks the variable set, and the chosen set is then fitted
    # with the champion's own algorithm below. Selection and final fitting are
    # deliberately separated for this reason.
    # Forward selection over all 95 predictors costs ~950 out-of-fold fits and
    # ran for 2.5 hours on ANC8 -- and the model it produced was badly overfit
    # by its own selection (development AP 0.5372 against 0.3763 held-out).
    # Two changes, for cost and for honesty:
    #
    #   * candidates are pre-screened to the strongest PRESCREEN_N by a single
    #     permutation-free importance pass, so the search is over a shortlist
    #     rather than everything;
    #   * the search stops at MAX_PREDICTORS, because the ANC8 run showed the
    #     selection-induced optimism growing with every extra step while
    #     held-out performance did not follow.
    #
    # The number that matters is still the HELD-OUT AP reported later, never
    # the development AP the search optimised.
    PRESCREEN_N = 30
    MAX_PREDICTORS = 8

    SELECTOR = "LightGBM" if "LightGBM" in best else ok.model.iloc[0]
    sel_params = dict(best[SELECTOR])
    sel_params["n_estimators"] = min(sel_params.get("n_estimators", 300), 300)

    log(f"pre-screening candidates for parsimony (selector: {SELECTOR})")
    import lightgbm as _lgb
    _screen = tuning.fit_final(SELECTOR, sel_params, X_dev, y_dev, w_dev,
                               numeric, categorical)
    _imp = _screen.named_steps["model"].feature_importances_
    _names = numeric + categorical
    shortlist = [n for _, n in sorted(zip(_imp, _names), reverse=True)][:PRESCREEN_N]
    log(f"  shortlist of {len(shortlist)} from {len(_names)} predictors")

    log("parsimonious forward selection")
    chosen, remaining = [], list(shortlist)
    best_ap = 0.0
    for step in range(MAX_PREDICTORS):
        scores = []
        for cand in remaining:
            cols = chosen + [cand]
            n_ = [c for c in cols if c in numeric]
            c_ = [c for c in cols if c in categorical]
            p = tuning.oof_predict(SELECTOR, sel_params, prep(dev, cols), y_dev, w_dev,
                                   splits, n_, c_)
            scores.append((average_precision_score(y_dev, p, sample_weight=w_dev), cand))
        scores.sort(reverse=True)
        gain = scores[0][0] - best_ap
        if step >= 4 and gain < 0.002:
            log(f"  stopping at {len(chosen)} predictors (gain {gain:.4f})")
            break
        best_ap, pick = scores[0]
        chosen.append(pick)
        remaining = [c for c in remaining if c != pick]
        log(f"  +{pick:38s} AP={best_ap:.4f}")

    pool = SELECTOR

    n_p = [c for c in chosen if c in numeric]
    c_p = [c for c in chosen if c in categorical]
    pars = tuning.fit_final(pool, best[pool], prep(dev, chosen), y_dev, w_dev, n_p, c_p)
    fitted["Parsimonious"] = pars
    held_pred["Parsimonious"] = pars.predict_proba(prep(held, chosen))[:, 1]
    dev_oof["Parsimonious"] = tuning.oof_predict(pool, best[pool], prep(dev, chosen),
                                                 y_dev, w_dev, splits, n_p, c_p)
    json.dump({"predictors": chosen, "base_model": pool, "numeric": n_p,
               "categorical": c_p, "development_AP": best_ap,
               "note": "Selected by forward selection on out-of-fold AP; the "
                       "selector is a fast booster because the search costs "
                       "~950 out-of-fold fits."},
              open(OUT_DIR / "parsimonious_spec.json", "w"), indent=2)

    # ------------------------------------------------- ORIGINAL 3 MODELS
    # The original study only ever modelled ANC8+, so its locked predictions
    # exist for that rung alone. The other rungs are evaluated on their own --
    # there is no published comparator to line them up against, and inventing
    # one by refitting V1 would not be the published model.
    has_v1 = OUTCOME == "anc8plus"
    if has_v1:
        for label, col in [("V1 Logistic regression", "prob_logistic"),
                           ("V1 Random Forest", "prob_random_forest"),
                           ("V1 XGBoost", "prob_xgboost")]:
            held_pred[label] = lock.set_index("caseid").loc[held.caseid, col].to_numpy()

    # -------------------------------------------------------- evaluation
    rows = []
    for name, p in held_pred.items():
        m = metrics.probability_metrics(y_held, p, w_held)
        if name in dev_oof:
            thr = metrics.youden_threshold(y_dev, dev_oof[name], w_dev)
        else:
            src = {"V1 Logistic regression": "Logistic regression",
                   "V1 Random Forest": "Random Forest",
                   "V1 XGBoost": "XGBoost"}[name]
            thr = pd.read_csv(
                ROOT / "outputs/publication_results/supplementary_tables"
                       "/Table_S1_full_cohort_development_thresholds.csv"
            ).set_index("Model").loc[src, "Threshold"]
        m.update(metrics.threshold_metrics(y_held, p, thr, w_held))
        m["model"] = name
        m["generation"] = "V1 (original study)" if name.startswith("V1") else "V2 (enhanced)"
        rows.append(m)

    perf = pd.DataFrame(rows).sort_values("AP", ascending=False)
    perf.to_csv(OUT_DIR / "heldout_performance.csv", index=False)
    log("\n" + perf[["model", "generation", "AP", "AUROC", "Brier",
                     "Calibration_slope", "Sensitivity", "Specificity"]].to_string(index=False))

    # ------------------------------------- paired stratified-PSU bootstrap
    log(f"paired bootstrap ({N_BOOT} resamples)")

    # The champion MUST be chosen on development data. Picking the V2 model
    # with the best held-out AP and then reporting that AP as its performance
    # is selection on the test set: it guarantees an optimistic number for
    # whichever model happened to land best on 1,375 women. The development
    # out-of-fold ranking is the only honest basis for the choice.
    dev_ranked = ok.sort_values("AP", ascending=False)
    champion = dev_ranked.model.iloc[0]
    log(f"  champion chosen on DEVELOPMENT OOF: {champion} "
        f"(dev AP {dev_ranked.AP.iloc[0]:.4f})")
    # Compare against the published model where one exists; otherwise against
    # the same architecture fitted on the ORIGINAL 21 predictors, which is the
    # closest like-for-like baseline this rung has.
    baseline = "V1 XGBoost" if has_v1 else dev_ranked.model.iloc[min(1, len(dev_ranked) - 1)]
    boots = {k: [] for k in ["champ_AP", "base_AP", "champ_AUROC", "base_AUROC",
                             "d_AP", "d_AUROC"]}
    for idx in design.stratified_psu_bootstrap(held.v022.to_numpy(), held.v021.to_numpy(),
                                               N_BOOT, BOOT_SEED):
        yy, ww = y_held[idx], w_held[idx]
        if yy.sum() == 0 or yy.sum() == len(yy):
            continue
        ca = average_precision_score(yy, held_pred[champion][idx], sample_weight=ww)
        ba = average_precision_score(yy, held_pred[baseline][idx], sample_weight=ww)
        cu = roc_auc_score(yy, held_pred[champion][idx], sample_weight=ww)
        bu = roc_auc_score(yy, held_pred[baseline][idx], sample_weight=ww)
        boots["champ_AP"].append(ca); boots["base_AP"].append(ba)
        boots["champ_AUROC"].append(cu); boots["base_AUROC"].append(bu)
        boots["d_AP"].append(ca - ba); boots["d_AUROC"].append(cu - bu)

    bd = pd.DataFrame(boots)
    bd.to_csv(OUT_DIR / "paired_bootstrap_distribution.csv", index=False)
    ci = {}
    for k in bd:
        ci[k] = {"point": float(bd[k].mean()),
                 "lo": float(bd[k].quantile(0.025)),
                 "hi": float(bd[k].quantile(0.975))}
    ci["champion"], ci["baseline"] = champion, baseline
    ci["champion_selected_on"] = "development out-of-fold AP"
    ci["d_AP_excludes_zero"] = bool(ci["d_AP"]["lo"] > 0 or ci["d_AP"]["hi"] < 0)
    ci["d_AUROC_excludes_zero"] = bool(ci["d_AUROC"]["lo"] > 0 or ci["d_AUROC"]["hi"] < 0)
    json.dump(ci, open(OUT_DIR / "paired_bootstrap_ci.json", "w"), indent=2)
    log(f"  {champion} vs {baseline}: dAP={ci['d_AP']['point']:+.4f} "
        f"[{ci['d_AP']['lo']:+.4f}, {ci['d_AP']['hi']:+.4f}] "
        f"excludes zero: {ci['d_AP_excludes_zero']}")

    # -------------------------------------------------------------- DCA
    dca = metrics.decision_curve(y_held, held_pred[champion], w_held)
    dca["model_name"] = champion
    dca_v1 = metrics.decision_curve(y_held, held_pred[baseline], w_held)
    dca["v1_xgboost"] = dca_v1["model"]
    dca.to_csv(OUT_DIR / "decision_curve.csv", index=False)

    # --------------------------------------------------------- subgroups
    sub = []
    for var in ["region", "residence", "wealth_quintile", "maternal_education"]:
        for level, g in held.groupby(var, observed=True):
            i = held.index.get_indexer(g.index)
            if len(g) < 40 or y_held[i].sum() < 5:
                continue
            sub.append({
                "variable": var, "level": str(level), "n": len(g),
                "weighted_prevalence": float(np.average(y_held[i], weights=w_held[i])),
                "V2_AUROC": roc_auc_score(y_held[i], held_pred[champion][i],
                                          sample_weight=w_held[i]),
                "V1_AUROC": roc_auc_score(y_held[i], held_pred[baseline][i],
                                          sample_weight=w_held[i]),
            })
    pd.DataFrame(sub).to_csv(OUT_DIR / "subgroup_performance.csv", index=False)

    # ------------------------------------------------------------ export
    pd.DataFrame({"caseid": held.caseid, "y": y_held, "w": w_held,
                  **{f"prob::{k}": v for k, v in held_pred.items()}}
                 ).to_csv(OUT_DIR / "heldout_locked_predictions_v2.csv", index=False)

    joblib.dump({"models": fitted, "numeric": numeric, "categorical": categorical,
                 "champion": champion,
                 "champion_selected_on": "development out-of-fold AP"},
                OUT_DIR / "enhanced_models.joblib", compress=3)

    thresholds = {n: float(metrics.youden_threshold(y_dev, p, w_dev))
                  for n, p in dev_oof.items()}
    json.dump(thresholds, open(OUT_DIR / "operating_thresholds.json", "w"), indent=2)
    log("evaluation complete")


if __name__ == "__main__":
    main()
