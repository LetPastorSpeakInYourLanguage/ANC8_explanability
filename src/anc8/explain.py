"""Per-predictor contributions from the library's fitted models.

Every function takes a fitted pipeline (the "pre" preprocessor and the "model"
estimator, as models.build makes them) and the women to explain, and returns a
matrix with one row per woman and one column per predictor, in the pipeline's
predictor order (numeric first, then categorical).

  logistic_terms      exact log-odds: coefficient x value, summed over each
                      predictor's columns (one-hot levels, or a spline basis).
  ebm_terms           exact log-odds: explainable boosting's own term scores; a
                      pair term is split equally between its two predictors.
  tree_shap           TreeSHAP for random forest (probability units) and XGBoost
                      (log-odds): the exact Shapley attribution for a tree ensemble.

The first two are additive, so a model's prediction is its intercept plus the row
sum: a difference between two groups of women splits exactly across predictors.
"""

from __future__ import annotations

import numpy as np


def _column_groups(pre, numeric, categorical, total):
    """Which predictor each transformed column belongs to."""
    groups = []
    onehot = pre.named_transformers_["categorical"].named_steps["onehot"] if categorical else None
    n_num_out = total - (sum(len(c) for c in onehot.categories_) if onehot is not None else 0)
    if numeric:
        per = n_num_out // len(numeric)  # a spline basis gives several columns per predictor
        for j in range(len(numeric)):
            groups += [j] * per
    if onehot is not None:
        for j, cats in enumerate(onehot.categories_):
            groups += [len(numeric) + j] * len(cats)
    return np.array(groups)


def logistic_terms(pipe, X, numeric, categorical):
    """(n, predictors) log-odds contributions and the intercept (uncentred)."""
    pre, est = pipe.named_steps["pre"], pipe.named_steps["model"]
    Z = np.asarray(pre.transform(X), dtype=float)
    raw = Z * est.coef_.ravel()
    groups = _column_groups(pre, numeric, categorical, Z.shape[1])
    out = np.zeros((len(X), len(numeric) + len(categorical)))
    for g in range(out.shape[1]):
        out[:, g] = raw[:, groups == g].sum(axis=1)
    return out, float(est.intercept_.ravel()[0])


def ebm_terms(pipe, X, n_predictors):
    """(n, predictors) log-odds contributions and the intercept (uncentred)."""
    pre, est = pipe.named_steps["pre"], pipe.named_steps["model"]
    Z = np.asarray(pre.transform(X), dtype=float)
    terms = est.eval_terms(Z)
    out = np.zeros((len(X), n_predictors))
    for t, feats in enumerate(est.term_features_):
        for f in feats:
            out[:, f] += terms[:, t] / len(feats)
    return out, float(np.ravel(est.intercept_)[0])


def tree_shap(pipe, X):
    """(n, predictors) SHAP values for the positive class."""
    import shap

    pre, est = pipe.named_steps["pre"], pipe.named_steps["model"]
    Z = np.asarray(pre.transform(X), dtype=float)
    sv = shap.TreeExplainer(est).shap_values(Z, check_additivity=False)
    if isinstance(sv, list):
        sv = sv[1]
    sv = np.asarray(sv)
    return sv[:, :, 1] if sv.ndim == 3 else sv


def contributions(name, pipe, X, numeric, categorical, w=None):
    """A model's per-woman, per-predictor contributions, centred on the weighted
    average woman for the additive models (so each is 'relative to typical')."""
    if name == "Logistic regression":
        c, _ = logistic_terms(pipe, X, numeric, categorical)
    elif name == "Explainable Boosting":
        c, _ = ebm_terms(pipe, X, len(numeric) + len(categorical))
    else:
        return tree_shap(pipe, X)
    return c - np.average(c, axis=0, weights=w)
