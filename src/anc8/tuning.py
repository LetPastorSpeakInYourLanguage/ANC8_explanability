"""Out-of-fold tuning and evaluation over the locked survey-design folds.

Every model in the zoo is tuned against the *same* PSU-grouped,
stratum-preserving folds the original study locked, on the same
survey-weighted Average Precision objective, so that the comparison between
the original three models and the new ones is like-for-like.

Two things here that the original analysis did not do:

  * calibration is fitted inside inner folds (`nested_calibrated_oof`), so the
    calibrator never sees the data it is scored on. Fitting a calibrator on the
    out-of-fold predictions and then scoring those same predictions looks like
    a large Brier improvement but is optimistic;
  * the cumulative-link ensemble (`cumulative_link_oof`) uses the fact that
    the outcome is a dichotomised *count*. Modelling several thresholds and
    pooling recovers ordering information that thresholding at 8 throws away.
"""

from __future__ import annotations

import warnings

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score

from . import models as zoo

warnings.filterwarnings("ignore")


def _fit(pipe, X, y, w):
    """Fit a pipeline passing survey weights through to the estimator."""
    return pipe.fit(X, y, model__sample_weight=w)


def _fold(name, params, X, y, w, fit_idx, val_idx, numeric, categorical, threads):
    """Fit one fold and return its validation probabilities.

    Runs in a worker process when folds are parallelised, so it sets the
    estimator thread count and caps BLAS/OpenMP itself: a fresh worker would
    otherwise default to every core, and five of them would contend.
    """
    from threadpoolctl import threadpool_limits

    previous = zoo.THREADS
    zoo.THREADS = threads
    try:
        with threadpool_limits(limits=None if threads == -1 else threads):
            wf = w[fit_idx] / w[fit_idx].mean()
            pipe = zoo.build(name, params, numeric, categorical)
            _fit(pipe, X.iloc[fit_idx], y[fit_idx], wf)
            return pipe.predict_proba(X.iloc[val_idx])[:, 1]
    finally:
        zoo.THREADS = previous


def oof_predict(name, params, X, y, w, splits, numeric, categorical, n_jobs=1):
    """Out-of-fold probabilities over the locked folds.

    Fitting weights are renormalised to mean 1 *within each fitting fold*,
    matching notebook 2 section 2.9: absolute weight magnitude can interact
    with regularisation strength, while the relative weights are what carry
    the design information.

    n_jobs=1 fits the folds one after another, each estimator using every core
    -- the original behaviour. n_jobs>1 fits folds in parallel processes with
    one thread per estimator, which is several times faster on this data: at
    5,500 rows a single fit cannot keep 22 cores busy, but five fits can.
    """
    oof = np.zeros(len(X), dtype=float)
    splits = list(splits)
    if n_jobs == 1:
        for fit_idx, val_idx in splits:
            oof[val_idx] = _fold(name, params, X, y, w, fit_idx, val_idx,
                                 numeric, categorical, zoo.THREADS)
        return oof

    from joblib import Parallel, delayed

    parts = Parallel(n_jobs=min(n_jobs, len(splits)))(
        delayed(_fold)(name, params, X, y, w, f, v, numeric, categorical, 1)
        for f, v in splits
    )
    for (_, val_idx), p in zip(splits, parts):
        oof[val_idx] = p
    return oof


def tune(name, X, y, w, splits, numeric, categorical, n_trials=60, seed=2026,
         n_jobs=1):
    """Optuna search maximising survey-weighted out-of-fold Average Precision.

    AP is the original study's prespecified primary criterion and is the right
    one here: at 19% prevalence, AUROC is dominated by the majority class while
    AP tracks how well the model ranks the women who actually attain ANC8+.
    """
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial):
        params = zoo.suggest(trial, name)
        p = oof_predict(name, params, X, y, w, splits, numeric, categorical,
                        n_jobs=n_jobs)
        return average_precision_score(y, p, sample_weight=w)

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=seed),
    )
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return study.best_params, study.best_value


def nested_calibrated_oof(name, params, X, y, w, splits, numeric, categorical,
                          method="isotonic", inner_folds=4, seed=2026):
    """Out-of-fold probabilities from a model calibrated on inner folds only.

    For each outer fold: split the fitting data again, fit the model on the
    inner-fit part, fit the calibrator on the held-back inner part, then apply
    both to the outer validation fold. The calibrator therefore never sees the
    predictions it is later judged on.
    """
    rng = np.random.default_rng(seed)
    oof = np.zeros(len(X), dtype=float)

    for fit_idx, val_idx in splits:
        inner = rng.integers(0, inner_folds, size=len(fit_idx))
        cal_raw, cal_y, cal_w = [], [], []

        # Build calibration data out-of-sample within the fitting fold.
        for k in range(inner_folds):
            tr = fit_idx[inner != k]
            ho = fit_idx[inner == k]
            if len(ho) == 0:
                continue
            wf = w[tr] / w[tr].mean()
            pipe = zoo.build(name, params, numeric, categorical)
            _fit(pipe, X.iloc[tr], y[tr], wf)
            cal_raw.append(pipe.predict_proba(X.iloc[ho])[:, 1])
            cal_y.append(y[ho])
            cal_w.append(w[ho])

        cal_raw = np.concatenate(cal_raw)
        cal_y = np.concatenate(cal_y)
        cal_w = np.concatenate(cal_w)

        if method == "isotonic":
            cal = IsotonicRegression(out_of_bounds="clip").fit(cal_raw, cal_y, sample_weight=cal_w)
            apply = cal.predict
        else:  # Platt scaling on the logit
            lr = LogisticRegression(max_iter=1000)
            lp = np.log(np.clip(cal_raw, 1e-9, 1 - 1e-9) / (1 - np.clip(cal_raw, 1e-9, 1 - 1e-9)))
            lr.fit(lp.reshape(-1, 1), cal_y, sample_weight=cal_w)
            apply = lambda p: lr.predict_proba(
                np.log(np.clip(p, 1e-9, 1 - 1e-9) / (1 - np.clip(p, 1e-9, 1 - 1e-9))).reshape(-1, 1)
            )[:, 1]

        # Full-fold model, calibrated by the map just learned out-of-sample.
        wf = w[fit_idx] / w[fit_idx].mean()
        pipe = zoo.build(name, params, numeric, categorical)
        _fit(pipe, X.iloc[fit_idx], y[fit_idx], wf)
        oof[val_idx] = apply(pipe.predict_proba(X.iloc[val_idx])[:, 1])

    return oof


# The full ANC contact ladder. Modelling every rung rather than only the three
# reported thresholds gives the pooled score more of the count's ordering to
# work with; 1/4/8 are the WHO-relevant cut points, the rest are shape.
LADDER_THRESHOLDS = (1, 2, 3, 4, 5, 6, 8, 10)


def _isotonic_decreasing(matrix: np.ndarray) -> np.ndarray:
    """Force P(count >= k) to be non-increasing in k, row by row.

    Separately fitted threshold models can cross -- a model can predict a woman
    is likelier to reach 8 contacts than 4, which is impossible, since reaching
    8 entails reaching 4. Pooling incoherent curves would quietly average away
    a contradiction, so the monotone constraint is imposed first by taking a
    running minimum across the ladder.
    """
    return np.minimum.accumulate(matrix, axis=1)


def cumulative_link_oof(name, params, X, counts, w, splits, numeric, categorical,
                        thresholds=LADDER_THRESHOLDS, target=8):
    """Fit the whole contact ladder and read off one rung.

    The outcome is a dichotomised count. A single binary model at the target
    treats a woman with 7 contacts and one with 0 as identical negatives, and
    one with 8 and one with 20 as identical positives. Fitting P(count >= k)
    across the ladder keeps that ordering.

    Returns (pooled score for `target`, per-threshold out-of-fold predictions).

    The pooled score blends the target's own model with its coherent
    neighbours, so it is a RANKING rather than a calibrated probability; the
    caller maps it back onto the probability scale with an isotonic fit on
    development data.
    """
    per_threshold = {}
    for k in thresholds:
        yk = (counts >= k).astype(int)
        if yk.min() == yk.max():
            continue  # a rung with no variation carries no information
        per_threshold[k] = oof_predict(name, params, X, yk, w, splits,
                                       numeric, categorical)

    ks = sorted(per_threshold)
    mono = _isotonic_decreasing(np.column_stack([per_threshold[k] for k in ks]))

    # Weight each rung by how close it sits to the target: adjacent thresholds
    # say the most about it, distant ones mostly add noise.
    weights = np.array([1.0 / (1.0 + abs(k - target)) for k in ks])
    pooled = (mono * weights).sum(axis=1) / weights.sum()

    return pooled, {k: mono[:, i] for i, k in enumerate(ks)}


def fit_final(name, params, X, y, w, numeric, categorical):
    """Refit on the whole development set, as the original study did before
    generating its locked held-out predictions."""
    pipe = zoo.build(name, params, numeric, categorical)
    return _fit(pipe, X, y, w / w.mean())
