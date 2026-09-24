"""Dependency-light scoring for the deployed ANC8 models.

WHY THIS EXISTS
---------------
The fitted pipelines are ordinary scikit-learn / XGBoost objects, and the
obvious way to serve them is to load the pickles. That does not fit: the
dependency set needed to unpickle them measures 341 MB unzipped
(scipy 118 + xgboost 88 + numpy 58 + pandas 43 + scikit-learn 33 + joblib 1)
against Vercel's 250 MB serverless limit, and dropping xgboost alone still
leaves 253 MB -- over the limit before a single model file is added.

So the models are exported to plain arrays at build time and evaluated here
with numpy alone (58 MB), leaving ample room for the model files themselves.

The obvious risk in re-implementing a model's arithmetic is that it stops
agreeing with the fitted model. That risk is retired empirically rather than
argued away: `scripts/export_serving.py` checks this scorer against the
fitted pipelines across the entire 1,375-woman held-out set and refuses to
write the bundle unless they agree to within 1e-9. The locked held-out
predictions of the 21-predictor models are reproduced exactly.
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# PREPROCESSING
# ---------------------------------------------------------------------------

def apply_preprocessor(spec: dict, row: dict) -> np.ndarray:
    """Turn a dict of raw answers into the model's feature vector.

    Mirrors the fitted ColumnTransformer block for block, in the order it
    emits them:

      numeric      median-imputed, then standardised (linear models only)
      binary       mapped to 0/1 through a fixed category order, NOT scaled
      categorical  most-frequent-imputed, then one-hot or ordinal encoded
      extra        any trailing block, such as the ANC-entry models' separate
                   `early_anc` transformer, passed through as a number

    Keeping the binary block out of the scaling is what makes this match: the
    21-predictor pipeline used an OrdinalEncoder there purely as a text -> 0/1
    converter, sitting outside the numeric pipeline that carries the scaler.
    """
    blocks = []

    # --- numeric -----------------------------------------------------------
    vals = []
    for col in spec["numeric"]:
        v = row.get(col, None)
        try:
            v = float(v) if v is not None and v != "" else None
        except (TypeError, ValueError):
            v = None
        if v is None or not np.isfinite(v):
            v = spec["numeric_impute"][col]
        vals.append(float(v))
    numeric_block = np.asarray(vals, dtype=float)

    if spec.get("numeric_scale"):
        mean = np.asarray(spec["numeric_scale"]["mean"], dtype=float)
        scale = np.asarray(spec["numeric_scale"]["scale"], dtype=float)
        numeric_block = (numeric_block - mean) / scale
    blocks.append(numeric_block)

    # --- binary ------------------------------------------------------------
    if spec.get("binary"):
        codes = []
        for col in spec["binary"]:
            cats = spec["categories"][col]
            v = row.get(col, None)
            v = spec["binary_impute"][col] if v is None or v == "" else str(v)
            codes.append(float(cats.index(v)) if v in cats else 0.0)
        blocks.append(np.asarray(codes, dtype=float))

    # --- categorical -------------------------------------------------------
    if spec["encoding"] == "onehot":
        for col in spec["categorical"]:
            cats = spec["categories"][col]
            v = row.get(col, None)
            v = spec["categorical_impute"][col] if v is None or v == "" else str(v)
            vec = np.zeros(len(cats), dtype=float)
            if v in cats:
                vec[cats.index(v)] = 1.0
            # An unseen category yields all zeros, matching
            # OneHotEncoder(handle_unknown="ignore").
            blocks.append(vec)
    else:  # ordinal codes for the tree models
        codes = []
        for col in spec["categorical"]:
            cats = spec["categories"][col]
            v = row.get(col, None)
            v = spec["categorical_impute"][col] if v is None or v == "" else str(v)
            codes.append(float(cats.index(v)) if v in cats else -1.0)
        blocks.append(np.asarray(codes, dtype=float))

    # --- extra trailing block ----------------------------------------------
    if spec.get("extra"):
        vals = []
        for col in spec["extra"]:
            v = row.get(col, None)
            try:
                v = float(v) if v is not None and v != "" else None
            except (TypeError, ValueError):
                v = None
            if v is None or not np.isfinite(v):
                v = spec["extra_impute"].get(col, 0.0)
            vals.append(float(v))
        blocks.append(np.asarray(vals, dtype=float))

    return np.concatenate(blocks)


# ---------------------------------------------------------------------------
# ESTIMATORS
# ---------------------------------------------------------------------------

def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def score_logistic(model: dict, x: np.ndarray) -> float:
    coef = np.asarray(model["coef"], dtype=float)
    return float(_sigmoid(float(np.dot(coef, x)) + model["intercept"]))


def _walk(tree: dict, x: np.ndarray) -> float:
    """Descend one CART tree to its leaf.

    sklearn encodes a leaf as children_left == -1.
    """
    left = tree["children_left"]
    right = tree["children_right"]
    feature = tree["feature"]
    threshold = tree["threshold"]
    value = tree["value"]

    node = 0
    while left[node] != -1:
        node = left[node] if x[feature[node]] <= threshold[node] else right[node]
    return value[node]


def score_forest(model: dict, x: np.ndarray) -> float:
    """Average the per-tree class-1 probabilities, as sklearn forests do."""
    return float(np.mean([_walk(t, x) for t in model["trees"]]))


def _walk_xgb(tree: dict, x: np.ndarray, zero_is_missing: bool = False) -> float:
    """Descend one XGBoost tree.

    Three differences from sklearn that matter:

      * the comparison is strict `<` (sklearn uses `<=`);
      * `default_left` is a 0/1 FLAG saying which way missing values go, not a
        node index;
      * `zero_is_missing` reproduces sparse-matrix semantics. The 21-predictor
        pipeline's ColumnTransformer emits a scipy CSR matrix, and XGBoost treats
        an unstored entry -- i.e. any exact zero -- as MISSING rather than as
        the number zero. Every absent one-hot indicator, and any genuinely
        zero numeric value such as a zero-minute travel time, therefore goes
        down the default branch. Scoring the same rows densely returns 0.577
        where the locked held-out probability is 0.159, so this flag is what
        makes the deployed 21-predictor XGBoost agree with the fitted model.
    """
    node = 0
    while True:
        left = tree["left"][node]
        if left == -1:
            return tree["leaf_value"][node]
        f = tree["split_feature"][node]
        v = x[f]
        missing = (not np.isfinite(v)) or (zero_is_missing and v == 0.0)
        if missing:
            node = left if tree["default_left"][node] else tree["right"][node]
        else:
            node = left if v < tree["split_condition"][node] else tree["right"][node]


def score_xgboost(model: dict, x: np.ndarray) -> float:
    zim = bool(model.get("zero_is_missing", False))
    total = sum(_walk_xgb(t, x, zim) for t in model["trees"])
    return float(_sigmoid(total + model["base_score"]))


def _walk_lgb(tree: dict, x: np.ndarray) -> float:
    """Descend one LightGBM tree.

    LightGBM distinguishes numeric splits (`<=`) from categorical splits
    (membership in a set of category codes), so both are handled.
    """
    node = 0
    while node >= 0:
        f = tree["split_feature"][node]
        v = x[f]
        if tree["decision_type"][node] == "categorical":
            go_left = int(v) in tree["cat_threshold"][node]
        else:
            go_left = (not np.isfinite(v)) if tree["default_left"][node] and not np.isfinite(v) \
                else (np.isfinite(v) and v <= tree["threshold"][node])
        node = tree["left"][node] if go_left else tree["right"][node]
    return tree["leaf_value"][-node - 1]


def score_lightgbm(model: dict, x: np.ndarray) -> float:
    total = sum(_walk_lgb(t, x) for t in model["trees"])
    return float(_sigmoid(total))


def _ebm_term_contribution(term: dict, x: np.ndarray) -> float:
    """The log-odds contribution of one additive term for one woman."""
    v = x[term["feature"]]
    scores = term["scores"]

    if term["kind"] == "nominal":
        # Bin 0 is interpret's missing bin, which is also where an unseen
        # level lands.
        key = str(int(v)) if float(v).is_integer() else str(v)
        idx = term["mapping"].get(key, 0)
    elif not np.isfinite(v):
        idx = 0
    else:
        # n cut points define n+1 intervals, offset by one for the missing bin
        # that sits at index 0.
        idx = int(np.searchsorted(np.asarray(term["cuts"], dtype=float),
                                  v, side="right")) + 1

    return float(scores[min(idx, len(scores) - 1)])


def score_ebm(model: dict, x: np.ndarray) -> float:
    """Evaluate a generalised additive model: intercept plus one term per feature.

    Every term is a one-dimensional step function read out of a lookup table,
    so the contribution of each predictor is directly inspectable -- which is
    the point of shipping this model rather than a booster.
    """
    total = model["intercept"] + sum(
        _ebm_term_contribution(t, x) for t in model["terms"]
    )
    return float(_sigmoid(total))


def explain_ebm(model: dict, x: np.ndarray, names, top: int = 8) -> list:
    """Exact per-predictor attribution for an additive model.

    For a GAM this is not an approximation. The prediction IS the intercept
    plus these contributions, so they sum exactly to the model's log-odds --
    unlike SHAP values for a booster, which estimate an attribution that the
    model never literally computes.

    Returned on the log-odds scale, positive meaning the value pushes towards
    attaining ANC8+.
    """
    rows = []
    for term in model["terms"]:
        f = term["feature"]
        rows.append({
            "predictor": names[f] if f < len(names) else f"feature_{f}",
            "contribution": _ebm_term_contribution(term, x),
        })

    rows.sort(key=lambda r: abs(r["contribution"]), reverse=True)
    return rows[:top]


SCORERS = {
    "logistic": score_logistic,
    "forest": score_forest,
    "xgboost": score_xgboost,
    "lightgbm": score_lightgbm,
    "ebm": score_ebm,
}


def _apply_isotonic(cal: dict, p: float) -> float:
    """Piecewise-linear isotonic calibration, clipped at the fitted range."""
    xs = np.asarray(cal["x"], dtype=float)
    ys = np.asarray(cal["y"], dtype=float)
    return float(np.interp(p, xs, ys, left=ys[0], right=ys[-1]))


def predict(bundle: dict, model_name: str, row: dict) -> dict:
    """Score one woman with one named model.

    Returns the probability, the model's locked operating threshold and the
    resulting classification. The threshold comes from development data only,
    exactly as every model's threshold was selected.
    """
    entry = bundle["models"][model_name]
    spec = bundle["preprocessors"][entry["preprocessor"]]

    x = apply_preprocessor(spec, row)
    p = SCORERS[entry["kind"]](entry, x)

    if entry.get("calibrator"):
        p = _apply_isotonic(entry["calibrator"], p)

    threshold = entry.get("threshold")
    out = {
        "model": model_name,
        "probability": p,
        "threshold": threshold,
        "classification": (
            None if threshold is None
            else ("likely to attain ANC8+" if p >= threshold else "unlikely to attain ANC8+")
        ),
    }

    # Additive models can say exactly why, so they do.
    if entry["kind"] == "ebm":
        names = (
            spec["numeric"] + spec.get("binary", [])
            + spec["categorical"] + spec.get("extra", [])
        )
        out["contributions"] = explain_ebm(entry, x, names)

    return out
