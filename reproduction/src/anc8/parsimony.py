"""The parsimonious predictor set: greedy forward selection with a fast booster.

A web form with 95 questions is unusable, so the study searched for a short list a
health worker could actually fill in. Forward selection adds, one at a time, the
predictor that most raises the out-of-fold survey-weighted average precision of a
fast booster (LightGBM, with the settings its own tuning chose on the 95 and at
most 300 trees). The chosen list is then fitted by every library model in turn.

Two versions of the search were run, and both are reproduced here:

  ANC8+   the first run: every one of the 95 candidates at every step, up to ten
          steps. It took two and a half hours, and its own development AP (0.54)
          ran far above what the list later scored on held-out women (0.38): the
          search had fitted noise.
  ANC1+,  the revised run: candidates are first pre-screened to the 30 the
  ANC4+   selector ranks highest in one fit, and the search stops at eight
          predictors, or once four are chosen and a step adds under 0.002 AP.

The number that matters is never the AP the search optimised, only the held-out
AP of the models fitted on the list afterwards.
"""

from __future__ import annotations

from sklearn.metrics import average_precision_score

from . import tuning

# (pre-screen to this many, most steps); None: every candidate
SETTINGS = {"anc8plus": (None, 10), "anc1plus": (30, 8), "anc4plus": (30, 8)}
MIN_STEPS, MIN_GAIN = 4, 0.002


def selector_params(best_lightgbm: dict) -> dict:
    p = dict(best_lightgbm)
    p["n_estimators"] = min(p.get("n_estimators", 300), 300)
    return p


def forward(X, y, w, splits, numeric, categorical, params, prescreen=None, max_steps=8, log=print):
    """Greedy forward selection. X holds every candidate; returns (chosen, path)."""
    names = list(numeric) + list(categorical)
    candidates = names
    if prescreen:
        pipe = tuning.fit_final("LightGBM", params, X[names], y, w, numeric, categorical)
        imp = pipe.named_steps["model"].feature_importances_
        candidates = [n for _, n in sorted(zip(imp, names), reverse=True)][:prescreen]
        log(f"  pre-screened to {len(candidates)} of {len(names)} candidates")

    chosen, path, best_ap = [], [], 0.0
    remaining = list(candidates)
    for step in range(max_steps):
        scores = []
        for cand in remaining:
            cols = chosen + [cand]
            n_ = [c for c in cols if c in numeric]
            c_ = [c for c in cols if c in categorical]
            p = tuning.oof_predict("LightGBM", params, X[n_ + c_], y, w, splits, n_, c_)
            scores.append((average_precision_score(y, p, sample_weight=w), cand))
        scores.sort(reverse=True)
        gain = scores[0][0] - best_ap
        if step >= MIN_STEPS and gain < MIN_GAIN:
            log(f"  stopping at {len(chosen)} predictors (gain {gain:.4f})")
            break
        best_ap, pick = scores[0]
        chosen.append(pick)
        remaining = [c for c in remaining if c != pick]
        path.append({"step": step + 1, "added": pick, "AP": best_ap})
        log(f"  +{pick:38s} AP={best_ap:.4f}")
    return chosen, path
