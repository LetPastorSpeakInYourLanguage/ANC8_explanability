"""Survey-design machinery for the EDHS ANC8 analysis.

Every function here is a faithful port of the corresponding cell in
`2_ML_readiness_and_audit.ipynb`, so that Notebooks 3 and 4 reproduce the
original development/held-out partition and cross-validation folds exactly.

Provenance
----------
make_psu_holdout          <- notebook 2, section 2.4 (cell 10)
make_psu_stratum_folds    <- notebook 2, section 2.8 (cell 22)
survey_weights            <- notebook 2, section 2.9 (cell 24)
stratified_psu_bootstrap  <- notebook 2, section 2.25.2 (cell 68)

The seeds below are the ones the original analysis locked. They must not be
changed: altering them would silently produce a different held-out set and
invalidate every comparison against the published results.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SPLIT_SEED = 2026
CV_SEED = 2026
N_FOLDS = 5
TARGET_TEST_PROPORTION = 0.20

PSU = "v021"
STRATUM = "v022"
WEIGHT = "v005"


def survey_weights(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Return (evaluation weight, mean-1 fitting weight).

    DHS stores v005 with an implied factor of 1,000,000; dividing restores the
    conventional relative weight scale used for population-weighted metrics.
    The fitting weight rescales to mean 1 so that absolute weight magnitude
    does not interact with estimator regularisation.
    """
    w = df[WEIGHT].astype(float) / 1_000_000
    return w, w / w.mean()


def make_psu_holdout(
    df: pd.DataFrame,
    seed: int = SPLIT_SEED,
    test_proportion: float = TARGET_TEST_PROPORTION,
) -> tuple[set, set]:
    """Sample ~20% of PSUs *within each survey stratum*.

    The PSU is the indivisible unit, so no woman's cluster spans the two
    partitions. The outcome is never referenced, so the split cannot be
    tuned to it.
    """
    rng = np.random.default_rng(seed)

    psu_frame = (
        df[[PSU, STRATUM]]
        .drop_duplicates()
        .sort_values([STRATUM, PSU])
        .reset_index(drop=True)
    )
    assert psu_frame[PSU].is_unique, "a PSU maps to more than one stratum"

    test_psus: list = []
    for _, stratum_psus in psu_frame.groupby(STRATUM, sort=True):
        psus = stratum_psus[PSU].to_numpy()
        n_test = max(1, int(np.round(len(psus) * test_proportion)))
        test_psus.extend(rng.choice(psus, size=n_test, replace=False).tolist())

    test = set(test_psus)
    return set(psu_frame[PSU]) - test, test


def make_psu_stratum_folds(
    df: pd.DataFrame,
    n_folds: int = N_FOLDS,
    seed: int = CV_SEED,
) -> pd.Series:
    """Assign each development woman a CV fold via her PSU.

    PSUs are shuffled within stratum and dealt to folds; any remainder PSUs go
    to randomly chosen folds rather than always to folds 0,1,2..., so no fold
    systematically absorbs the leftovers across strata.

    Returns a fold label indexed like `df`.
    """
    rng = np.random.default_rng(seed)

    psu_frame = (
        df[[PSU, STRATUM]]
        .drop_duplicates()
        .sort_values([STRATUM, PSU])
        .reset_index(drop=True)
    )

    rows = []
    for stratum, stratum_psus in psu_frame.groupby(STRATUM, sort=True):
        psus = stratum_psus[PSU].to_numpy().copy()
        rng.shuffle(psus)

        base, remainder = divmod(len(psus), n_folds)
        labels = np.repeat(np.arange(n_folds), base)
        if remainder:
            labels = np.concatenate(
                [labels, rng.choice(np.arange(n_folds), size=remainder, replace=False)]
            )
        rng.shuffle(labels)
        assert len(labels) == len(psus)

        rows.extend(
            {PSU: p, STRATUM: stratum, "cv_fold": int(f)} for p, f in zip(psus, labels)
        )

    assignment = pd.DataFrame(rows).set_index(PSU)["cv_fold"]
    folds = df[PSU].map(assignment)
    assert folds.notna().all(), "some development PSU received no fold"
    return folds.astype(int)


def folds_to_splits(folds: pd.Series, n_folds: int = N_FOLDS) -> list[tuple]:
    """Convert fold labels into the (fit_idx, val_idx) list sklearn expects."""
    f = np.asarray(folds)
    splits = [(np.flatnonzero(f != k), np.flatnonzero(f == k)) for k in range(n_folds)]

    seen = np.zeros(len(f), dtype=int)
    for _, val in splits:
        seen[val] += 1
    assert (seen == 1).all(), "each woman must validate exactly once"
    return splits


def stratified_psu_bootstrap(
    strata: np.ndarray,
    psus: np.ndarray,
    n_resamples: int = 2000,
    seed: int = 2026,
):
    """Yield row indices for a stratified bootstrap that resamples whole PSUs.

    Resampling PSUs with replacement *within* stratum is the design-consistent
    way to propagate clustering into the uncertainty around held-out
    performance; resampling women independently would understate it.
    """
    rng = np.random.default_rng(seed)
    strata = np.asarray(strata)
    psus = np.asarray(psus)

    # Precompute, per stratum, its PSU list and the rows belonging to each PSU.
    by_stratum = {}
    for s in np.unique(strata):
        mask = strata == s
        s_psus = np.unique(psus[mask])
        by_stratum[s] = (s_psus, {p: np.flatnonzero(mask & (psus == p)) for p in s_psus})

    for _ in range(n_resamples):
        take = []
        for s, (s_psus, rows) in by_stratum.items():
            for p in rng.choice(s_psus, size=len(s_psus), replace=True):
                take.append(rows[p])
        yield np.concatenate(take)
