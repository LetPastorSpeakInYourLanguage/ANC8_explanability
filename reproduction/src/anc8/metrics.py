"""Survey-weighted performance metrics for the ANC8 analysis.

Ported from `2_ML_readiness_and_audit.ipynb` sections 2.21-2.24 so that new
models are scored on exactly the same footing as the published ones.

All metrics take the DHS relative weight (v005 / 1e6). Unweighted metrics
describe the *sample*; weighted metrics describe the Ethiopian population the
sample was designed to represent, which is the estimand this study is after.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)


def _clip(p, eps=1e-15):
    return np.clip(np.asarray(p, dtype=float), eps, 1 - eps)


def calibration_intercept_slope(y, p, w=None) -> tuple[float, float]:
    """Calibration-in-the-large and calibration slope on the logit scale.

    Uses statsmodels GLM with the same parameterisation as notebook 2 section
    2.22: CITL is the intercept when the predicted log-odds enters as a fixed
    OFFSET (slope pinned at 1), while the calibration slope is estimated
    jointly with its own intercept. The joint intercept is *not* CITL, and the
    two must not be conflated.

    Slope < 1 means predictions are too spread out (the usual overfitting
    signature); CITL < 0 means they are systematically too high.
    """
    import statsmodels.api as sm

    y = np.asarray(y, dtype=float)
    lp = np.log(_clip(p) / (1 - _clip(p)))
    w = None if w is None else np.asarray(w, dtype=float)

    citl = (
        sm.GLM(
            y,
            np.ones((len(y), 1)),
            family=sm.families.Binomial(),
            offset=lp,
            freq_weights=w,
        )
        .fit()
        .params[0]
    )

    slope = (
        sm.GLM(
            y,
            sm.add_constant(lp),
            family=sm.families.Binomial(),
            freq_weights=w,
        )
        .fit()
        .params[1]
    )

    return float(citl), float(slope)


def integrated_calibration_index(y, p, w=None) -> float:
    """ICI: mean absolute difference between predicted and smoothed observed risk."""
    from sklearn.isotonic import IsotonicRegression

    p = np.asarray(p, dtype=float)
    obs = IsotonicRegression(out_of_bounds="clip").fit(p, y, sample_weight=w).predict(p)
    d = np.abs(obs - p)
    return float(np.average(d, weights=w))


def probability_metrics(y, p, w=None) -> dict:
    """The three prespecified probability metrics plus calibration."""
    citl, slope = calibration_intercept_slope(y, p, w)
    return {
        "AP": float(average_precision_score(y, p, sample_weight=w)),
        "AUROC": float(roc_auc_score(y, p, sample_weight=w)),
        "Brier": float(brier_score_loss(y, p, sample_weight=w)),
        "CITL": citl,
        "Calibration_slope": slope,
        "ICI": integrated_calibration_index(y, p, w),
    }


def threshold_metrics(y, p, threshold: float, w=None) -> dict:
    """Classification performance at a given operating threshold."""
    y = np.asarray(y, dtype=float)
    pred = (np.asarray(p) >= threshold).astype(float)
    w = np.ones_like(y) if w is None else np.asarray(w, dtype=float)

    tp = np.sum(w * (pred == 1) * (y == 1))
    fp = np.sum(w * (pred == 1) * (y == 0))
    fn = np.sum(w * (pred == 0) * (y == 1))
    tn = np.sum(w * (pred == 0) * (y == 0))

    sens = tp / (tp + fn) if tp + fn else np.nan
    spec = tn / (tn + fp) if tn + fp else np.nan
    ppv = tp / (tp + fp) if tp + fp else np.nan
    npv = tn / (tn + fn) if tn + fn else np.nan
    f1 = 2 * ppv * sens / (ppv + sens) if (ppv + sens) else np.nan

    return {
        "Threshold": float(threshold),
        "Sensitivity": float(sens),
        "Specificity": float(spec),
        "PPV": float(ppv),
        "NPV": float(npv),
        "F1": float(f1),
        "Predicted_positive_rate": float((tp + fp) / w.sum()),
    }


def youden_threshold(y, p, w=None) -> float:
    """Threshold maximising Youden's J, as the original analysis selected."""
    from sklearn.metrics import roc_curve

    fpr, tpr, thr = roc_curve(y, p, sample_weight=w)
    return float(thr[np.argmax(tpr - fpr)])


def net_benefit(y, p, threshold: float, w=None) -> float:
    """Net benefit for decision-curve analysis (Vickers & Elkin).

    Answers the question performance metrics cannot: at a given risk
    threshold, does acting on this model beat treating everybody or nobody?
    """
    y = np.asarray(y, dtype=float)
    pred = (np.asarray(p) >= threshold).astype(float)
    w = np.ones_like(y) if w is None else np.asarray(w, dtype=float)
    n = w.sum()

    tp = np.sum(w * (pred == 1) * (y == 1)) / n
    fp = np.sum(w * (pred == 1) * (y == 0)) / n
    return float(tp - fp * (threshold / (1 - threshold)))


def decision_curve(y, p, w=None, thresholds=None) -> pd.DataFrame:
    """Net benefit of the model, treat-all and treat-none across thresholds."""
    if thresholds is None:
        thresholds = np.arange(0.01, 0.61, 0.01)
    y = np.asarray(y, dtype=float)
    w = np.ones_like(y) if w is None else np.asarray(w, dtype=float)
    prev = np.average(y, weights=w)

    rows = []
    for t in thresholds:
        rows.append(
            {
                "threshold": float(t),
                "model": net_benefit(y, p, t, w),
                "treat_all": float(prev - (1 - prev) * (t / (1 - t))),
                "treat_none": 0.0,
            }
        )
    return pd.DataFrame(rows)
