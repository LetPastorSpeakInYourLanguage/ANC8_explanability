"""The ANC contact ladder: ANC1+, ANC4+, ANC8+.

All three outcomes are thresholds on the same count, `m14_1`, measured on the
same women. They are nested by construction -- a woman with eight contacts also
has four and one -- so they are three rungs of one ladder rather than three
unrelated questions.

Two things follow, and both matter for the cross-outcome analysis:

**The split is shared.** `design.make_psu_holdout` never looks at an outcome,
so the same development/held-out partition and the same PSU-grouped folds serve
every rung. Any difference in predictor importance between rungs is therefore
attributable to the outcome, not to who happened to land in which fold.

**Average Precision is NOT comparable across rungs.** AP has a floor at the
outcome prevalence, and prevalence here runs from 77.6% to 19.2% -- a random
model would "score" four times higher on ANC1+ than on ANC8+. Cross-rung
comparisons must use AUROC, which is prevalence-free, or AP lift over
prevalence. Comparing raw AP across rungs is the single easiest way to draw a
badly wrong conclusion from this analysis.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SOURCE_VARIABLE = "m14_1"

OUTCOMES = {
    "anc1plus": {
        "threshold": 1,
        "label": "ANC1+",
        "question": "any antenatal contact at all",
        "meaning": (
            "Whether the woman reached antenatal care even once. Failure here "
            "is a question of access and contact with the health system."
        ),
        "weighted_prevalence": 0.7760,
    },
    "anc4plus": {
        "threshold": 4,
        "label": "ANC4+",
        "question": "the previous WHO minimum",
        "meaning": (
            "The focused-ANC standard WHO recommended until 2016. A middle "
            "rung: requires sustained contact but not the full schedule."
        ),
        "weighted_prevalence": 0.5243,
    },
    "anc8plus": {
        "threshold": 8,
        "label": "ANC8+",
        "question": "the 2016 WHO recommended schedule",
        "meaning": (
            "The current WHO standard of eight or more contacts. Failure here "
            "is a question of sustained engagement over a whole pregnancy."
        ),
        "weighted_prevalence": 0.1916,
    },
}

LADDER = ["anc1plus", "anc4plus", "anc8plus"]


def derive(counts) -> pd.DataFrame:
    """Build every ladder outcome from the raw contact count.

    Counts of 98 ("don't know") are unresolved and must already have been
    excluded; anything outside 0-97 yields NaN rather than a silent zero.
    """
    counts = pd.Series(counts, dtype="float64")
    resolved = counts.between(0, 97)

    out = {}
    for name, spec in OUTCOMES.items():
        out[name] = np.where(resolved, (counts >= spec["threshold"]).astype(float), np.nan)
    return pd.DataFrame(out, index=counts.index)


def check_nested(df: pd.DataFrame) -> None:
    """A woman who attained a higher rung must have attained every lower one.

    This is true by construction, so a violation means the outcomes were built
    from different data or a merge went wrong -- worth an assertion rather than
    an assumption, since the whole ladder analysis rests on it.
    """
    a1, a4, a8 = df["anc1plus"], df["anc4plus"], df["anc8plus"]
    ok = df.notna().all(axis=1)
    assert (a8[ok] <= a4[ok]).all(), "ANC8+ attained without ANC4+"
    assert (a4[ok] <= a1[ok]).all(), "ANC4+ attained without ANC1+"


def ap_lift(ap: float, outcome: str) -> float:
    """Average Precision expressed above its prevalence floor.

    A model with no signal scores AP = prevalence, so the lift is what the
    model actually contributes. This is the only AP-based quantity that can be
    compared between rungs.
    """
    return float(ap - OUTCOMES[outcome]["weighted_prevalence"])


def describe(outcome: str) -> str:
    spec = OUTCOMES[outcome]
    return (f"{spec['label']} ({spec['question']}) -- "
            f"{spec['weighted_prevalence'] * 100:.1f}% weighted prevalence")
