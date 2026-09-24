"""Does the preprocessing actually matter? An ablation.

The original study used one preprocessing recipe throughout: median imputation
for numerics, most-frequent imputation plus one-hot encoding for categoricals,
and standardisation for the linear arm only. Reasonable defaults, but never
tested against alternatives.

Each variant below changes ONE thing, holding the predictors, the algorithm,
the folds and the weighting fixed, so the difference is attributable to the
preprocessing choice alone.

    python scripts/run_preprocessing_ablation.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder

import lightgbm as lgb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import design  # noqa: E402

OUT = ROOT / "outputs" / "enhanced"
PARAMS = dict(n_estimators=300, learning_rate=0.05, num_leaves=15,
              reg_lambda=1.0, colsample_bytree=0.8, verbose=-1,
              random_state=2026, n_jobs=-1)


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def evaluate(pre, X, y, w, splits):
    oof = np.zeros(len(X))
    for fit_idx, val_idx in splits:
        wf = w[fit_idx] / w[fit_idx].mean()
        pipe = Pipeline([("pre", pre), ("model", lgb.LGBMClassifier(**PARAMS))])
        pipe.fit(X.iloc[fit_idx], y[fit_idx], model__sample_weight=wf)
        oof[val_idx] = pipe.predict_proba(X.iloc[val_idx])[:, 1]
    return (average_precision_score(y, oof, sample_weight=w),
            roc_auc_score(y, oof, sample_weight=w))


def main():
    df = pd.read_pickle(OUT / "ANC8_analysis_frozen_v2.pkl")
    spec = json.load(open(OUT / "feature_spec_v2.json"))
    numeric, categorical = spec["numeric_predictors"], spec["categorical_predictors"]

    train_psus, _ = design.make_psu_holdout(df)
    dev = df[df.v021.isin(train_psus)].reset_index(drop=True)
    splits = design.folds_to_splits(design.make_psu_stratum_folds(dev))

    X = dev[numeric + categorical].copy()
    for c in categorical:
        X[c] = X[c].astype(str)
    y = dev.anc8plus.astype(int).to_numpy()
    w = (dev.v005 / 1e6).to_numpy()

    num_median = Pipeline([("i", SimpleImputer(strategy="median"))])
    cat_mode_ordinal = Pipeline([
        ("i", SimpleImputer(strategy="most_frequent")),
        ("e", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
    ])
    cat_mode_onehot = Pipeline([
        ("i", SimpleImputer(strategy="most_frequent")),
        ("e", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    variants = {}

    # 1. The original recipe: one-hot everything, median-impute numerics.
    variants["one-hot categoricals (original recipe)"] = ColumnTransformer(
        [("numeric", num_median, numeric), ("categorical", cat_mode_onehot, categorical)]
    )

    # 2. Ordinal codes, letting the booster treat categories natively. One-hot
    #    fragments a 14-level variable into 14 near-empty binary splits; native
    #    handling lets the tree partition the levels directly.
    variants["native categorical codes"] = ColumnTransformer(
        [("numeric", num_median, numeric), ("categorical", cat_mode_ordinal, categorical)]
    )

    # 3. Leave numeric missingness to the booster rather than imputing it.
    #    LightGBM routes NaN down a learned default branch, which carries the
    #    information that the value was absent; median imputation erases it.
    variants["no numeric imputation (NaN to the model)"] = ColumnTransformer(
        [("numeric", "passthrough", numeric), ("categorical", cat_mode_ordinal, categorical)]
    )

    # 4. Median imputation plus explicit missingness indicators: keeps the
    #    imputed value but does not hide the fact that it was imputed.
    variants["median impute + missingness indicators"] = ColumnTransformer(
        [("numeric", Pipeline([("i", SimpleImputer(strategy="median", add_indicator=True))]),
          numeric),
         ("categorical", cat_mode_ordinal, categorical)]
    )

    rows = []
    for label, pre in variants.items():
        ap, auc = evaluate(pre, X, y, w, splits)
        rows.append({"variant": label, "AP": ap, "AUROC": auc})
        log(f"{label:46s} AP={ap:.4f} AUROC={auc:.4f}")

    res = pd.DataFrame(rows).sort_values("AP", ascending=False)
    base = res[res.variant.str.contains("original recipe")].AP.iloc[0]
    res["AP_vs_original"] = (res.AP - base).round(4)
    res.to_csv(OUT / "preprocessing_ablation.csv", index=False)

    print()
    print("PREPROCESSING ABLATION (development OOF, survey-weighted)")
    print(res.to_string(index=False))


if __name__ == "__main__":
    main()
