"""Candidate model zoo and preprocessing for the enhanced ANC8 analysis.

The original study compared three algorithms: L2 logistic regression, random
forest and XGBoost. Its own supplementary Table S3 found XGBoost was not
significantly better than logistic regression on any metric, which says the
comparison was not wide enough to find whatever headroom existed.

This module widens it along three axes the original did not explore:

  * gradient boosters with native categorical handling (LightGBM, CatBoost,
    HistGradientBoosting). The expectation was that these would suit 14-level
    region and 7-level partner occupation better than one-hot encoding, which
    fragments them. The ablation in scripts/run_preprocessing_ablation.py does
    NOT bear that out -- ordinal codes scored 0.476 AP against 0.484 for
    one-hot, slightly better on AUROC and slightly worse on AP. These families
    are kept for the diversity they bring to the ensemble, not because the
    encoding argument survived testing;
  * a glass-box additive model (EBM) and a spline logistic regression, both of
    which relax the linearity the original logistic arm assumed without
    giving up interpretability;
  * a stacked ensemble over out-of-fold predictions.
"""

from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OneHotEncoder,
    OrdinalEncoder,
    SplineTransformer,
    StandardScaler,
)

RANDOM_STATE = 2026


class _CatBoostIntCast(ClassifierMixin, BaseEstimator):
    """Cast ordinal-encoded categorical columns to int for CatBoost.

    The shared tree preprocessor emits a float matrix, but CatBoost requires
    categorical features to arrive as int or str -- a float column is rejected
    outright. This adapter casts just the categorical block, keeping the rest
    of the pipeline identical to every other tree model so the comparison stays
    like-for-like.
    """

    def __init__(self, estimator, cat_idx):
        self.estimator = estimator
        self.cat_idx = list(cat_idx)

    def _cast(self, X):
        X = np.asarray(X, dtype=float).copy()
        out = X.astype(object)
        for j in self.cat_idx:
            col = X[:, j]
            col = np.where(np.isfinite(col), col, -1)
            out[:, j] = col.astype(int)
        return out

    def fit(self, X, y, sample_weight=None):
        self.estimator.fit(self._cast(X), y, sample_weight=sample_weight)
        self.classes_ = self.estimator.classes_
        self.is_fitted_ = True
        return self

    def predict_proba(self, X):
        return self.estimator.predict_proba(self._cast(X))

    def predict(self, X):
        return self.estimator.predict(self._cast(X))

    def __sklearn_is_fitted__(self):
        return getattr(self, "is_fitted_", False)


# ---------------------------------------------------------------------------
# PREPROCESSING
# ---------------------------------------------------------------------------

def make_linear_preprocessor(numeric, categorical, splines=False, knots=5):
    """Median-impute + scale numerics, most-frequent-impute + one-hot categoricals.

    With `splines`, continuous predictors additionally get a natural spline
    basis so the linear arm can express curvature. The original logistic arm
    assumed every continuous effect was linear on the logit scale, which for
    maternal age in particular is implausible.
    """
    if splines:
        num = Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("spline", SplineTransformer(n_knots=knots, degree=3, include_bias=False)),
            ("scale", StandardScaler()),
        ])
    else:
        num = Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ])

    cat = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False, dtype=float)),
    ])

    return ColumnTransformer(
        [("numeric", num, numeric), ("categorical", cat, categorical)],
        remainder="drop",
    )


def make_tree_preprocessor(numeric, categorical):
    """Median-impute numerics; ordinal-encode categoricals for native handling.

    Trees do not need scaling, and ordinal codes let LightGBM / CatBoost /
    HistGradientBoosting treat a category as a category rather than as a wall
    of one-hot columns that fragments the split space.

    Worth knowing: on this dataset that theoretical advantage does not show up
    in the numbers (see scripts/run_preprocessing_ablation.py). Ordinal codes
    are used here because the tree families need them, not because they were
    measured to be better.
    """
    num = Pipeline([("impute", SimpleImputer(strategy="median"))])
    cat = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("ordinal", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
    ])
    return ColumnTransformer(
        [("numeric", num, numeric), ("categorical", cat, categorical)],
        remainder="drop",
    )


# ---------------------------------------------------------------------------
# HYPERPARAMETER SEARCH SPACES
#
# Deliberately wider than the original fixed grids, which offered 4 / 48 / 64
# configurations and -- for XGBoost -- no regularisation terms at all.
# ---------------------------------------------------------------------------

def suggest(trial, name: str) -> dict:
    """Optuna search space for each algorithm."""
    if name in ("Logistic regression", "Spline logistic"):
        return {"C": trial.suggest_float("C", 1e-3, 1e2, log=True)}

    if name == "Elastic net logistic":
        return {
            "C": trial.suggest_float("C", 1e-3, 1e2, log=True),
            "l1_ratio": trial.suggest_float("l1_ratio", 0.0, 1.0),
        }

    if name in ("Random Forest", "Extra Trees"):
        return {
            "n_estimators": trial.suggest_int("n_estimators", 200, 900, step=100),
            "max_depth": trial.suggest_categorical("max_depth", [None, 6, 9, 12, 16]),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 30),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 30),
            "max_features": trial.suggest_categorical("max_features", ["sqrt", 0.3, 0.5, 0.7]),
        }

    if name == "XGBoost":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 150, 900, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "max_depth": trial.suggest_int("max_depth", 2, 8),
            "min_child_weight": trial.suggest_float("min_child_weight", 0.5, 20, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0),
            # The original grid had no regularisation terms whatsoever.
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 50, log=True),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 10, log=True),
            "gamma": trial.suggest_float("gamma", 1e-4, 5, log=True),
        }

    if name == "LightGBM":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 150, 900, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 7, 63),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 50, log=True),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 10, log=True),
        }

    if name == "CatBoost":
        return {
            "iterations": trial.suggest_int("iterations", 200, 1000, step=100),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "depth": trial.suggest_int("depth", 3, 8),
            "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 30.0, log=True),
        }

    if name == "HistGradientBoosting":
        return {
            "max_iter": trial.suggest_int("max_iter", 150, 800, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "max_leaf_nodes": trial.suggest_int("max_leaf_nodes", 7, 63),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 5, 100),
            "l2_regularization": trial.suggest_float("l2_regularization", 1e-3, 50, log=True),
        }

    if name == "Explainable Boosting":
        return {
            "max_bins": trial.suggest_categorical("max_bins", [128, 256, 512]),
            "learning_rate": trial.suggest_float("learning_rate", 0.005, 0.1, log=True),
            "interactions": trial.suggest_int("interactions", 0, 10),
        }

    if name == "MLP":
        return {
            "hidden": trial.suggest_categorical("hidden", ["64", "128", "64-32", "128-64"]),
            "alpha": trial.suggest_float("alpha", 1e-5, 1e-1, log=True),
            "learning_rate_init": trial.suggest_float("learning_rate_init", 1e-4, 1e-2, log=True),
        }

    raise ValueError(f"no search space defined for {name!r}")


# Threads each estimator may use. -1 (all cores) suits one large fit; when the
# caller parallelises across folds or candidates instead, it sets this to 1 so
# the workers do not each claim every core and spend their time contending.
THREADS = -1

# "gpu" moves the two boosters that can use one onto CUDA: CatBoost (whose
# categorical CTR computation is what made it the slowest model on CPU) and
# XGBoost. Every other family is CPU-only whatever this says.
DEVICE = "cpu"


def build(name: str, params: dict, numeric, categorical):
    """Instantiate a full preprocessing + estimator pipeline."""
    params = dict(params)

    if name in ("Logistic regression", "Elastic net logistic", "Spline logistic"):
        pre = make_linear_preprocessor(
            numeric, categorical, splines=(name == "Spline logistic")
        )
        if name == "Elastic net logistic":
            est = LogisticRegression(
                penalty="elasticnet", solver="saga", max_iter=5000,
                random_state=RANDOM_STATE, **params,
            )
        else:
            est = LogisticRegression(max_iter=5000, random_state=RANDOM_STATE, **params)
        return Pipeline([("pre", pre), ("model", est)])

    if name == "MLP":
        from sklearn.neural_network import MLPClassifier
        hidden = tuple(int(x) for x in str(params.pop("hidden")).split("-"))
        pre = make_linear_preprocessor(numeric, categorical)
        est = MLPClassifier(
            hidden_layer_sizes=hidden, max_iter=600,
            early_stopping=True, random_state=RANDOM_STATE, **params,
        )
        return Pipeline([("pre", pre), ("model", est)])

    pre = make_tree_preprocessor(numeric, categorical)
    n_num = len(numeric)
    cat_idx = list(range(n_num, n_num + len(categorical)))

    if name == "Random Forest":
        est = RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=THREADS, **params)
    elif name == "Extra Trees":
        est = ExtraTreesClassifier(random_state=RANDOM_STATE, n_jobs=THREADS, **params)
    elif name == "XGBoost":
        import xgboost as xgb
        est = xgb.XGBClassifier(
            eval_metric="logloss", tree_method="hist",
            random_state=RANDOM_STATE, n_jobs=THREADS,
            **({"device": "cuda"} if DEVICE == "gpu" else {}), **params,
        )
    elif name == "LightGBM":
        import lightgbm as lgb
        est = lgb.LGBMClassifier(
            verbose=-1, random_state=RANDOM_STATE, n_jobs=THREADS,
            subsample_freq=1, **params,
        )
    elif name == "CatBoost":
        from catboost import CatBoostClassifier
        est = _CatBoostIntCast(
            CatBoostClassifier(
                verbose=0, random_seed=RANDOM_STATE, cat_features=cat_idx,
                allow_writing_files=False,
                # Each category on its own, no combinations: with 60 categorical
                # predictors the combinations made one fit take minutes even on a GPU.
                max_ctr_complexity=1,
                # CatBoost takes 95% of GPU memory by default; two jobs and a
                # network share one card, so each takes at most 40%.
                **({"task_type": "GPU", "devices": "0", "gpu_ram_part": 0.4} if DEVICE == "gpu"
                   else {"thread_count": THREADS}),
                **params,
            ),
            cat_idx,
        )
    elif name == "HistGradientBoosting":
        cat_mask = [False] * n_num + [True] * len(categorical)
        est = HistGradientBoostingClassifier(
            categorical_features=cat_mask, early_stopping=False,
            random_state=RANDOM_STATE, **params,
        )
    elif name == "Explainable Boosting":
        from interpret.glassbox import ExplainableBoostingClassifier
        est = ExplainableBoostingClassifier(random_state=RANDOM_STATE, n_jobs=THREADS, **params)
    else:
        raise ValueError(f"unknown model {name!r}")

    return Pipeline([("pre", pre), ("model", est)])


# Every model in the zoo accepts per-sample weights through the sklearn
# `model__sample_weight` fit parameter, which is how DHS survey weights enter
# model fitting.
# CatBoost is defined above and still fully supported, but it is NOT in the
# default zoo: on this dataset it cost 4,358 seconds of CPU -- more than every
# other model combined -- for only 12 trials, and finished last on development
# AP (0.5022). Its categorical CTR computation is largely serial, so more CPU
# cores do not help; a GPU does.
#
# Run it separately on a GPU via notebooks/CatBoost_GPU_Colab.ipynb, which
# writes a result file this pipeline can merge back in.
ZOO = [
    "Logistic regression",
    "Elastic net logistic",
    "Spline logistic",
    "Random Forest",
    "Extra Trees",
    "XGBoost",
    "LightGBM",
    "HistGradientBoosting",
    "Explainable Boosting",
    "MLP",
]

# Available to build() and tune() on request, just not run by default.
OPTIONAL = ["CatBoost"]
