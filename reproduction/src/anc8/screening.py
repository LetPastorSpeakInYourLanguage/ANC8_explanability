"""Systematic candidate screening over the full EDHS Individual Recode.

Notebook 1 selected 21 predictors from a prior mapping register. That register
was inherited from an earlier study with a different outcome, so variables that
matter for ANC contact attainment specifically were never given a chance to be
considered. This module sweeps every column in the IR file instead, and scores
each one's association with ANC8+ under the survey design.

Screening ranks candidates. It does NOT select them: temporality adjudication
(which must be manual, because leakage is a question about *when* a variable
was measured, not about its correlation) happens in Notebook 3.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

# DHS marks variables that were not collected in a given survey by prefixing
# the label with "na - ". They are present as all-missing columns.
NA_LABEL_PREFIX = "na - "

# Recorded at or after delivery, or directly defining the outcome. Any of these
# in a predictor set is leakage, regardless of how well it scores.
# Measured during ANC itself. These are NOT background predictors: they are
# admissible only in the declared ANC-entry arm, which conditions on having
# already initiated ANC. Notebook 2 handled m13 correctly this way; the screen
# must flag it rather than let a 0.78-AUC variable slip into the primary model.
ANC_PROCESS_PREFIXES = ("m13", "m13a")

LEAKY_PREFIXES = (
    "m14",   # number of ANC visits -- the outcome itself
    "m15",   # place of delivery
    "m16",   # assistance at delivery
    "m17",   # caesarean
    "m18",   # size at birth
    "m19",   # birth weight
    "m1_",   # tetanus injections during pregnancy (ANC process)
    "m2",    # ANC provider type (ANC process)
    "m3",    # delivery assistance
    "m4",    # breastfeeding
    "m5",    # months of breastfeeding
    "m6", "m7", "m8", "m9",
    "m4",
    "m45", "m46", "m47", "m48", "m49",
    "m55", "m56", "m57", "m58", "m59",
    "m70", "m71", "m72", "m73", "m74", "m75", "m76", "m77", "m78", "m79",
    "s4",    # country-specific maternity-care modules
    "h",     # child health / immunisation, all post-delivery
)

# Survey design and administrative fields: never predictors.
DESIGN_VARS = {
    "caseid", "v000", "v001", "v002", "v003", "v004", "v005", "v006", "v007",
    "v008", "v008a", "v015", "v016", "v017", "v018", "v019", "v020", "v021",
    "v022", "v023", "v027", "v028", "v029", "v030", "v031", "v032", "v034",
    "v042", "v044", "v046", "v047", "v048", "v049",
}


def is_structurally_excluded(name: str, label: str) -> str | None:
    """Return a reason string if the variable can never be a predictor."""
    if label.startswith(NA_LABEL_PREFIX):
        return "not collected in this survey (DHS 'na -' label)"
    if name in DESIGN_VARS:
        return "survey design / administrative variable"
    low = name.lower()
    for pref in ANC_PROCESS_PREFIXES:
        if low.startswith(pref):
            return "ANC-process variable - ANC-entry arm only, not a background predictor"
    for pref in LEAKY_PREFIXES:
        if low.startswith(pref):
            return f"measured at or after delivery (prefix '{pref}') - temporal leakage"
    return None


def weighted_auc(y, x, w) -> float:
    """Univariate AUC treating the raw variable as a score.

    Reported as max(auc, 1-auc) because direction is irrelevant for screening.
    This assumes monotonicity, so it UNDERSTATES non-monotone and nominal
    variables -- `prevalence_spread` is the companion measure for those.
    """
    ok = np.isfinite(x)
    if ok.sum() < 50 or len(np.unique(x[ok])) < 2 or len(np.unique(y[ok])) < 2:
        return np.nan
    a = roc_auc_score(y[ok], x[ok], sample_weight=w[ok])
    return float(max(a, 1 - a))


def prevalence_spread(y, x, w, min_cell=30) -> float:
    """Weighted outcome-prevalence range across categories.

    Catches nominal variables (region is the obvious one) whose signal a
    monotone AUC cannot see.
    """
    s = pd.Series(x)
    if s.nunique(dropna=True) > 25:
        return np.nan
    df = pd.DataFrame({"y": y, "x": s, "w": w}).dropna()
    if df.empty:
        return np.nan

    vals = []
    for _, t in df.groupby("x", sort=False):
        if len(t) >= min_cell:
            vals.append(np.average(t["y"], weights=t["w"]))

    return float(max(vals) - min(vals)) if len(vals) > 1 else np.nan


def screen(
    cohort: pd.DataFrame,
    labels: dict,
    y: np.ndarray,
    w: np.ndarray,
    min_coverage: float = 0.5,
) -> pd.DataFrame:
    """Score every column of the cohort against the outcome.

    `min_coverage` guards the ranking. Most of the IR file is birth-history
    slots (b*_11, p*_10, ...) that are populated for a handful of women; an AUC
    estimated on 0.9% of the cohort is noise and would otherwise dominate the
    top of the table. Such variables are retained with status
    'low_coverage' so the decision is visible, not silently dropped.

    Returns one row per variable with the information needed to adjudicate it.
    """
    rows = []
    for name in cohort.columns:
        label = labels.get(name, "")
        excluded = is_structurally_excluded(name, label)

        col = cohort[name]
        miss = float(col.isna().mean())

        if excluded or miss > 0.999:
            rows.append(
                {
                    "variable": name, "label": label, "missing": miss,
                    "n_unique": int(col.nunique(dropna=True)),
                    "weighted_auc": np.nan, "prevalence_spread": np.nan,
                    "screen_status": "excluded",
                    "exclusion_reason": excluded or "entirely missing in cohort",
                }
            )
            continue

        low_cov = (1 - miss) < min_coverage

        x = pd.to_numeric(col, errors="coerce").to_numpy(dtype=float)
        rows.append(
            {
                "variable": name, "label": label, "missing": miss,
                "n_unique": int(col.nunique(dropna=True)),
                "weighted_auc": weighted_auc(y, x, w),
                "prevalence_spread": prevalence_spread(y, x, w),
                "screen_status": "low_coverage" if low_cov else "candidate",
                "exclusion_reason": (
                    f"observed for only {(1 - miss):.1%} of the cohort"
                    if low_cov else ""
                ),
            }
        )

    out = pd.DataFrame(rows)
    rankable = out["screen_status"] == "candidate"
    out["screen_rank"] = np.nan
    out.loc[rankable, "screen_rank"] = (
        out.loc[rankable, "weighted_auc"].rank(ascending=False, method="min")
    )
    return out.sort_values(
        ["screen_status", "weighted_auc"],
        ascending=[True, False],
        na_position="last",
    )
