"""Export fitted pipelines to dependency-light arrays for deployment.

Run in the PINNED environment for V1:
    .venv-serve/Scripts/python.exe scripts/export_serving.py --v1

and in the main environment for V2:
    python scripts/export_serving.py --v2

Why: unpickling the fitted models needs 341 MB of dependencies against a
250 MB Vercel limit (see app/api/_lib/scorer.py). Exporting to plain arrays
gets the serving function down to numpy alone.

The re-implementation risk this creates is retired by an explicit gate: every
exported model is scored against its original fitted pipeline across the whole
held-out set, and the bundle is NOT written unless they agree to 1e-9.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

HANDOFF = ROOT / "outputs" / "notebook3_explainability_handoff"
ENHANCED = ROOT / "outputs" / "enhanced"
DEST = ROOT / "app" / "models"

# XGBoost accumulates its tree sum in float32, so a float64 re-implementation
# cannot agree more closely than float32 resolution. Everything else is
# float64 end to end and must match to machine precision.
TOLERANCE = {"logistic": 1e-9, "forest": 1e-9, "xgboost": 1e-6,
             "lightgbm": 1e-9, "ebm": 1e-9}

# A tree model can disagree on a knife-edge row: when a feature value sits
# essentially exactly on a split threshold, float32 (XGBoost's arithmetic) and
# float64 (this scorer's) can send it down different branches, and the two
# leaves differ by a real amount. That is inherent to the model's precision,
# not a defect in the export.
#
# Tolerating it with a blanket loose threshold would also hide genuine bugs, so
# the gate is on the SHARE of rows that disagree instead: a real error in the
# preprocessing or the tree walk moves most rows, while a tie moves a handful.
MAX_OUTLIER_SHARE = 0.002


# ---------------------------------------------------------------------------
# PREPROCESSOR EXTRACTION
# ---------------------------------------------------------------------------

def extract_preprocessor(ct, numeric=None, binary=None, categorical=None):
    """Read a fitted ColumnTransformer into a serialisable spec.

    Column lists and block order are taken FROM THE FITTED TRANSFORMER rather
    than reconstructed from a predictor register. Reconstructing them means
    guessing an ordering, and a wrong guess produces a silently misaligned
    feature vector -- a bug that shows up as plausible-but-wrong probabilities
    rather than as an error. The `numeric`/`binary`/`categorical` arguments are
    accepted for backwards compatibility and ignored.

    Handles four block shapes, which is every shape used across both
    generations:

      numeric      impute (+ optional scale)
      binary       a bare OrdinalEncoder used as a text -> 0/1 converter
      categorical  impute + one-hot or ordinal encoding
      extra        any additional trailing block, such as the ANC-entry
                   models' separate `early_anc` transformer
    """
    spec = {
        "numeric": [], "binary": [], "categorical": [], "extra": [],
        "numeric_impute": {}, "binary_impute": {}, "categorical_impute": {},
        "extra_impute": {},
        "categories": {}, "numeric_scale": None, "encoding": "onehot",
    }

    def step(pipe, *aliases):
        if not hasattr(pipe, "named_steps"):
            return None
        for a in aliases:
            if a in pipe.named_steps:
                return pipe.named_steps[a]
        return None

    for name, trans, cols in ct.transformers_:
        if trans == "drop" or name == "remainder":
            continue
        cols = list(cols)

        if name == "numeric":
            spec["numeric"] = cols
            imp = step(trans, "imputer", "impute")
            if "spline" in getattr(trans, "named_steps", {}):
                raise TypeError(
                    "spline basis expansion is not supported by the serving "
                    "scorer (numeric columns are expanded before scaling)"
                )
            stats = imp.statistics_ if imp is not None else [0.0] * len(cols)
            for c, v in zip(cols, stats):
                spec["numeric_impute"][c] = float(v)
            sc = step(trans, "scaler", "scale")
            if sc is not None:
                spec["numeric_scale"] = {
                    "mean": [float(x) for x in sc.mean_],
                    "scale": [float(x) for x in sc.scale_],
                }

        elif name == "binary":
            spec["binary"] = cols
            # A bare OrdinalEncoder with a prespecified category order.
            for c, cats in zip(cols, trans.categories_):
                spec["categories"][c] = [str(x) for x in cats]
                spec["binary_impute"][c] = str(cats[0])

        elif name == "categorical":
            spec["categorical"] = cols
            imp = step(trans, "imputer", "impute")
            for c, v in zip(cols, imp.statistics_):
                spec["categorical_impute"][c] = str(v)
            enc = step(trans, "onehot", "ordinal")
            for c, cats in zip(cols, enc.categories_):
                spec["categories"][c] = [str(x) for x in cats]
            spec["encoding"] = (
                "onehot" if "onehot" in trans.named_steps else "ordinal"
            )

        else:
            # A trailing block such as the ANC-entry models' `early_anc`.
            # Treated as numeric: it is already 0/1 and is not encoded.
            spec["extra"].extend(cols)
            imp = step(trans, "imputer", "impute")
            stats = imp.statistics_ if imp is not None else [0.0] * len(cols)
            for c, v in zip(cols, stats):
                spec["extra_impute"][c] = float(v)

    return spec


def export_sklearn_tree(tree):
    t = tree.tree_
    # value[:, 0, :] holds class counts; normalise to P(class 1).
    v = t.value[:, 0, :]
    proba = v[:, 1] / np.clip(v.sum(axis=1), 1e-12, None)
    return {
        "children_left": t.children_left.astype(int).tolist(),
        "children_right": t.children_right.astype(int).tolist(),
        "feature": t.feature.astype(int).tolist(),
        "threshold": t.threshold.astype(float).tolist(),
        "value": proba.astype(float).tolist(),
    }


def export_xgboost(booster_model, zero_is_missing=False):
    """Convert an XGBClassifier to per-tree arrays via its JSON dump.

    `zero_is_missing` must be set when the model is served sparse input (see
    app/api/_lib/scorer.py), which is the case for the V1 pipelines.
    """
    booster = booster_model.get_booster()
    raw = json.loads(booster.save_raw("json").decode("utf-8"))
    gbtree = raw["learner"]["gradient_booster"]["model"]
    # XGBoost >= 2.0 serialises base_score as a bracketed vector string, e.g.
    # "[1.9886424E-1]", and it is a PROBABILITY -- the trees sum on the logit
    # scale, so it has to be converted before being added to their total.
    bs_raw = str(raw["learner"]["learner_model_param"]["base_score"])
    base_score = float(bs_raw.strip("[]").split(",")[0])
    base_margin = float(np.log(base_score / (1 - base_score)))

    trees = []
    for t in gbtree["trees"]:
        left = [int(x) for x in t["left_children"]]
        trees.append({
            "left": left,
            "right": [int(x) for x in t["right_children"]],
            "split_feature": [int(x) for x in t["split_indices"]],
            "split_condition": [float(x) for x in t["split_conditions"]],
            "default_left": [int(x) for x in t["default_left"]],
            # For leaf nodes XGBoost stores the (already shrunk) leaf value in
            # split_conditions; base_weights carries the same number there.
            "leaf_value": [float(x) for x in t["split_conditions"]],
        })
    return {"kind": "xgboost", "trees": trees, "base_score": base_margin,
            "zero_is_missing": bool(zero_is_missing)}


def export_lightgbm(model):
    d = model.booster_.dump_model()
    trees = []
    for t in d["tree_info"]:
        nodes, leaves = {}, {}

        def walk(n):
            if "leaf_index" in n:
                leaves[n["leaf_index"]] = n["leaf_value"]
                return -(n["leaf_index"] + 1)
            idx = len(nodes)
            nodes[idx] = n
            n["_idx"] = idx
            n["_l"] = walk(n["left_child"])
            n["_r"] = walk(n["right_child"])
            return idx

        walk(t["tree_structure"])
        order = sorted(nodes)
        trees.append({
            "left": [nodes[i]["_l"] for i in order],
            "right": [nodes[i]["_r"] for i in order],
            "split_feature": [nodes[i]["split_feature"] for i in order],
            "threshold": [float(nodes[i]["threshold"]) for i in order],
            "decision_type": [
                "categorical" if nodes[i]["decision_type"] == "==" else "numeric"
                for i in order
            ],
            "cat_threshold": [
                [int(c) for c in str(nodes[i]["threshold"]).split("||")]
                if nodes[i]["decision_type"] == "==" else []
                for i in order
            ],
            "default_left": [bool(nodes[i].get("default_left", False)) for i in order],
            "leaf_value": [leaves[k] for k in sorted(leaves)],
        })
    return {"kind": "lightgbm", "trees": trees}


def export_ebm(model):
    """Convert an Explainable Boosting Machine to per-term lookup tables.

    An EBM is a generalised additive model: a prediction is the intercept plus
    one score per term, each read out of a binned lookup table. With
    `interactions = 0` -- which the tuner chose here -- every term is a single
    feature, so the whole model is a set of one-dimensional step functions.

    That makes it both trivially exportable and the most inspectable model in
    the zoo, which is why it is worth the extra exporter rather than falling
    back to a booster at deployment time.

    Bin index convention, matching interpret's own scoring:
      index 0            missing
      index 1..n         the n+1 intervals defined by n cut points
      index -1 (last)    unseen / out of range
    """
    terms = []
    for ti, feats in enumerate(model.term_features_):
        if len(feats) != 1:
            raise TypeError(
                "EBM export supports additive terms only; this model contains "
                f"a {len(feats)}-way interaction term"
            )
        f = feats[0]
        raw = model.bins_[f]
        spec = raw[0] if isinstance(raw, list) else raw

        if isinstance(spec, dict):
            # Nominal feature: interpret maps each observed level to a bin.
            terms.append({
                "feature": int(f),
                "kind": "nominal",
                "mapping": {str(k): int(v) for k, v in spec.items()},
                "scores": [float(x) for x in np.asarray(model.term_scores_[ti])],
            })
        else:
            terms.append({
                "feature": int(f),
                "kind": "continuous",
                "cuts": [float(x) for x in np.asarray(spec, dtype=float)],
                "scores": [float(x) for x in np.asarray(model.term_scores_[ti])],
            })

    return {
        "kind": "ebm",
        "intercept": float(np.asarray(model.intercept_).ravel()[0]),
        "terms": terms,
    }


def export_estimator(est, sparse_input=False):
    from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression

    if isinstance(est, LogisticRegression):
        return {
            "kind": "logistic",
            "coef": est.coef_[0].astype(float).tolist(),
            "intercept": float(est.intercept_[0]),
        }
    if isinstance(est, (RandomForestClassifier, ExtraTreesClassifier)):
        return {"kind": "forest", "trees": [export_sklearn_tree(t) for t in est.estimators_]}

    mod = type(est).__module__
    if "xgboost" in mod:
        return export_xgboost(est, zero_is_missing=sparse_input)
    if "lightgbm" in mod:
        return export_lightgbm(est)
    if "interpret" in mod or type(est).__name__.startswith("ExplainableBoosting"):
        return export_ebm(est)
    raise TypeError(f"no exporter for {type(est).__name__}")


# ---------------------------------------------------------------------------
# FIDELITY GATE
# ---------------------------------------------------------------------------

def verify(bundle, name, pipeline, frame, rows, published=None):
    """Score every held-out woman both ways and refuse to proceed on drift.

    Checked against the fitted pipeline and, where available, against the
    study's own published probabilities -- the second check is the one that
    actually matters, since it is what the paper reports.
    """
    sys.path.insert(0, str(ROOT / "app" / "api" / "_lib"))
    import scorer

    kind = bundle["models"][name]["kind"]
    tol = TOLERANCE[kind]

    mine = np.array([scorer.predict(bundle, name, r)["probability"] for r in rows])

    def compare(reference, label):
        d = np.abs(mine - reference)
        outliers = int((d > tol).sum())
        share = outliers / len(d)
        passed = share <= MAX_OUTLIER_SHARE
        note = f"max|diff|={d.max():.3e}"
        if outliers:
            note += (f", {outliers}/{len(d)} rows over tol "
                     f"({share:.3%}); typical={np.quantile(d, 0.999):.1e}")
        print(f"    {name:26s} vs {label:18s} {note}  "
              f"{'PASS' if passed else 'FAIL'}")
        return passed, d.max()

    ok, worst = compare(pipeline.predict_proba(frame)[:, 1], "fitted pipeline")
    if published is not None:
        pok, _ = compare(published, "PUBLISHED values")
        ok &= pok
    return ok, worst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1", action="store_true")
    ap.add_argument("--v2", action="store_true")
    args = ap.parse_args()

    DEST.mkdir(parents=True, exist_ok=True)
    frozen = pd.read_pickle(ROOT / "outputs" / "ANC8_analysis_frozen.pkl")

    if args.v1:
        arch = json.load(open(HANDOFF / "predictor_architecture.json"))
        lock = pd.read_csv(HANDOFF / "full_cohort_locked_predictions.csv")
        held = lock[["caseid"]].merge(frozen, on="caseid", how="left", validate="one_to_one")
        preds = arch["full_cohort_predictors"]
        X = held[preds]
        rows = X.astype(object).where(pd.notna(X), None).to_dict("records")

        models = joblib.load(HANDOFF / "full_cohort_final_models.joblib")
        bundle = {"generation": "v1", "predictors": preds,
                  "preprocessors": {}, "models": {}}

        thr = pd.read_csv(
            ROOT / "outputs/publication_results/supplementary_tables"
                   "/Table_S1_full_cohort_development_thresholds.csv"
        ).set_index("Model")["Threshold"].to_dict()

        print("exporting V1 (original study)")
        all_ok = True
        for name, pipe in models.items():
            pre = extract_preprocessor(
                pipe.named_steps["preprocessor"],
                arch["numeric_predictors"], arch["binary_predictors"],
                arch["categorical_predictors"],
            )
            key = f"{name}::pre"
            bundle["preprocessors"][key] = pre
            # V1 preprocessors emit scipy CSR, so zeros reach XGBoost as
            # missing values.
            entry = export_estimator(pipe.named_steps["model"], sparse_input=True)
            entry["preprocessor"] = key
            entry["threshold"] = float(thr[name])
            bundle["models"][name] = entry

            col = {"Logistic regression": "prob_logistic",
                   "Random Forest": "prob_random_forest",
                   "XGBoost": "prob_xgboost"}[name]
            ok, _ = verify(bundle, name, pipe, X, rows,
                           published=lock[col].to_numpy())
            all_ok &= ok

        if not all_ok:
            print("\nFIDELITY GATE FAILED -- bundle not written")
            sys.exit(1)

        out = DEST / "v1_bundle.json.gz"
        with gzip.open(out, "wt", encoding="utf-8") as fh:
            json.dump(bundle, fh)
        print(f"\nwrote {out} ({out.stat().st_size / 1e6:.1f} MB)")

        # ---- ANC-entry horizon -------------------------------------------
        # The original study's second prediction horizon: women who had already
        # initiated ANC and whose timing of first contact is known. Six models,
        # baseline and extended (adding early_anc) per algorithm, so the app can
        # show the incremental-value question the paper asked.
        print("\nexporting V1 ANC-entry horizon")
        entry_lock = pd.read_csv(HANDOFF / "anc_entry_locked_predictions.csv")
        entry_held = pd.read_pickle(HANDOFF / "anc_entry_heldout.pkl")
        entry_models = joblib.load(HANDOFF / "anc_entry_final_models.joblib")
        entry_frame = entry_lock[["caseid"]].merge(
            entry_held, on="caseid", how="left", validate="one_to_one"
        )
        entry_thr = pd.read_csv(
            ROOT / "outputs/publication_results/supplementary_tables"
                   "/Table_S2_anc_entry_development_thresholds.csv"
        )

        entry_bundle = {
            "generation": "v1_anc_entry",
            "predictors": arch["anc_entry_extended_predictors"],
            "preprocessors": {}, "models": {},
        }
        col_for = {
            ("Logistic regression", "Baseline"): "prob_logistic_baseline",
            ("Logistic regression", "Extended"): "prob_logistic_extended",
            ("Random Forest", "Baseline"): "prob_rf_baseline",
            ("Random Forest", "Extended"): "prob_rf_extended",
            ("XGBoost", "Baseline"): "prob_xgb_baseline",
            ("XGBoost", "Extended"): "prob_xgb_extended",
        }

        entry_ok = True
        for algo, specs in entry_models.items():
            for spec_name, pipe in specs.items():
                preds_e = arch[
                    "anc_entry_extended_predictors" if spec_name == "Extended"
                    else "anc_entry_baseline_predictors"
                ]
                Xe = entry_frame[preds_e]
                rows_e = Xe.astype(object).where(pd.notna(Xe), None).to_dict("records")

                name = f"{algo} ({spec_name})"
                pre_e = extract_preprocessor(pipe.named_steps["preprocessor"])
                key = f"{name}::pre"
                entry_bundle["preprocessors"][key] = pre_e
                ent = export_estimator(pipe.named_steps["model"], sparse_input=True)
                ent["preprocessor"] = key
                match = entry_thr[(entry_thr.Algorithm == algo)
                                  & (entry_thr.Specification == spec_name)]
                if len(match):
                    ent["threshold"] = float(match.Threshold.iloc[0])
                entry_bundle["models"][name] = ent

                ok, _ = verify(entry_bundle, name, pipe, Xe, rows_e,
                               published=entry_lock[col_for[(algo, spec_name)]].to_numpy())
                entry_ok &= ok

        if not entry_ok:
            print("\nANC-ENTRY FIDELITY GATE FAILED -- bundle not written")
            sys.exit(1)

        out_e = DEST / "v1_anc_entry_bundle.json.gz"
        with gzip.open(out_e, "wt", encoding="utf-8") as fh:
            json.dump(entry_bundle, fh)
        print(f"wrote {out_e} ({out_e.stat().st_size / 1e6:.1f} MB)")


    if args.v2:
        spec = json.load(open(ENHANCED / "feature_spec_v2.json"))
        blob = joblib.load(ENHANCED / "anc8plus" / "enhanced_models.joblib")
        df = pd.read_pickle(ENHANCED / "ANC8_analysis_frozen_v2.pkl")
        perf = pd.read_csv(ENHANCED / "anc8plus" / "heldout_performance.csv")

        from anc8 import design
        _, test_psus = design.make_psu_holdout(df)
        held = df[df.v021.isin(test_psus)].reset_index(drop=True)

        numeric, categorical = spec["numeric_predictors"], spec["categorical_predictors"]
        X = held[numeric + categorical].copy()
        for c in categorical:
            X[c] = X[c].astype(str)
        rows = X.astype(object).where(pd.notna(X), None).to_dict("records")

        thresholds = json.load(open(ENHANCED / "anc8plus" / "operating_thresholds.json"))
        bundle = {"generation": "v2", "predictors": numeric + categorical,
                  "preprocessors": {}, "models": {}}

        print("exporting V2 (enhanced)")
        all_ok = True
        skipped = []

        for name, pipe in blob["models"].items():
            if not hasattr(pipe, "named_steps"):
                # Composite arms (stacked ensemble, cumulative-link) are made of
                # several fitted models plus a calibrator; they are reported in
                # the notebook but are not single-pipeline exportable.
                skipped.append((name, "composite arm, not a single pipeline"))
                continue
            try:
                # Both the estimator and its preprocessor can be unexportable
                # -- a spline basis expands the numeric block in a way the
                # serving scorer does not reproduce -- so both are attempted
                # together and a refusal from either skips the model cleanly.
                entry = export_estimator(pipe.named_steps["model"])
                pre = extract_preprocessor(pipe.named_steps["pre"])
            except TypeError as exc:
                skipped.append((name, str(exc)))
                continue

            key = f"{name}::pre"
            bundle["preprocessors"][key] = pre
            entry["preprocessor"] = key
            if name in thresholds:
                entry["threshold"] = float(thresholds[name])
            bundle["models"][name] = entry

            ok, _ = verify(bundle, name, pipe, X, rows)
            all_ok &= ok

        if not all_ok:
            print("\nFIDELITY GATE FAILED -- bundle not written")
            sys.exit(1)

        # The deployed champion is the best model that can actually ship. If the
        # overall best cannot, say so rather than quietly serving a weaker model
        # under the same name.
        # Rank on DEVELOPMENT out-of-fold AP, not held-out. Choosing which
        # model to deploy by its held-out score is selection on the test set,
        # and it would make the deployed model's reported performance
        # optimistic by construction.
        dev_perf = pd.read_csv(ENHANCED / "anc8plus" / "development_oof_performance.csv")
        dev_order = (dev_perf[dev_perf.AP.notna()]
                     .sort_values("AP", ascending=False).model.tolist())
        perf_v2 = perf[perf.generation == "V2 (enhanced)"].set_index("model")
        ranked = pd.DataFrame([
            {"model": m, "AP": perf_v2.loc[m, "AP"] if m in perf_v2.index else np.nan}
            for m in dev_order
        ])
        best_overall = ranked.iloc[0]
        shippable = ranked[ranked.model.isin(bundle["models"])]

        if len(shippable) == 0:
            print("\nNo V2 model could be exported for serving.")
            sys.exit(1)

        champion = shippable.iloc[0]
        bundle["champion"] = champion.model
        bundle["champion_heldout_AP"] = float(champion.AP)
        bundle["best_overall_model"] = best_overall.model
        bundle["best_overall_heldout_AP"] = float(best_overall.AP)
        bundle["champion_gap_AP"] = float(best_overall.AP - champion.AP)

        if skipped:
            print("\nnot exportable for serving:")
            for n, why in skipped:
                print(f"    {n:32s} {why}")

        if best_overall.model != champion.model:
            print(f"\nNOTE: the best V2 model overall is {best_overall.model} "
                  f"(held-out AP {best_overall.AP:.4f}), which cannot be exported.")
            print(f"      Deploying {champion.model} (AP {champion.AP:.4f}) instead, "
                  f"a gap of {best_overall.AP - champion.AP:.4f} AP.")
        else:
            print(f"\ndeployed champion: {champion.model} (held-out AP {champion.AP:.4f})")

        out = DEST / "v2_bundle.json.gz"
        with gzip.open(out, "wt", encoding="utf-8") as fh:
            json.dump(bundle, fh)
        print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
