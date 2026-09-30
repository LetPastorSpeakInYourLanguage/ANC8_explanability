"""The analysis cohorts, and the birth timing they are built on.

  full    6,893 women: every woman whose most recent birth has an ANC count.
          The first prediction horizon -- before ANC starts.
  entry   5,001 women: those who started ANC and know when their first contact
          was. The second prediction horizon -- at ANC entry -- which adds
          `early_anc` (first contact by 12 weeks / 3 months). Every woman in it
          has ANC1+, so only ANC4+ and ANC8+ are defined here.
  recent  5,037 women: only births in the 24 months before interview. This is
          the DHS-8 reference period for the ANC indicator (Guide to DHS
          Statistics, table 9.2), and restricting to it reproduces the
          2024-25 EDHS report's regional ANC4+ table within about half a point.
          Used as a sensitivity analysis.

The 28% of the full cohort outside that window gave birth 24-35 months before
interview. That matters for two reasons: recall of a contact count is worse
years later, and in the north those pregnancies overlapped the war.

Every cohort uses the SAME development / held-out partition -- the PSU split
drawn on the full cohort, restricted to the cohort -- so their held-out women
are subsets of the same 1,375 and nothing is re-drawn.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import design

ROOT = Path(__file__).resolve().parents[2]


def _first(*paths: Path) -> Path:
    """The repository keeps derived data under outputs/enhanced/; the release
    package keeps it under data/. Use whichever exists."""
    return next((p for p in paths if p.exists()), paths[0])


FROZEN = _first(ROOT / "outputs" / "enhanced" / "ANC8_analysis_frozen_v2.pkl",
                ROOT / "data" / "ANC8_analysis_frozen_v2.pkl")
IR_FILE = _first(ROOT / "ETIR8AFL.dta", ROOT / "ETIR8AFL.DTA",
                 ROOT / "data" / "ETIR8AFL.DTA", ROOT / "data" / "ETIR8AFL.dta")
TIMING_CACHE = _first(ROOT / "outputs" / "enhanced" / "birth_timing.parquet",
                      ROOT / "data" / "birth_timing.parquet")

HANDOFF = ROOT / "outputs" / "notebook3_explainability_handoff"
ENTRY_FILES = (HANDOFF / "anc_entry_development.pkl", HANDOFF / "anc_entry_heldout.pkl")
# The release package ships the same cohort as one small table instead, and the
# reproduction notebooks rebuild it from the survey file into outputs/enhanced/.
ENTRY_TABLE = _first(ROOT / "outputs" / "enhanced" / "anc_entry.csv", ROOT / "data" / "anc_entry.csv")

RECENT_MONTHS = 24
COHORTS = ("full", "entry", "recent")
# Outcomes each cohort can support: at ANC entry every woman already has ANC1+.
COHORT_OUTCOMES = {"full": ("anc1plus", "anc4plus", "anc8plus"),
                   "entry": ("anc4plus", "anc8plus"),
                   "recent": ("anc1plus", "anc4plus", "anc8plus")}


def birth_timing() -> pd.DataFrame:
    """Months since the index birth and its calendar date, per woman.

    Read from the raw Individual Recode once and cached, because the 160 MB
    file takes a while to parse and only three columns are needed.
    """
    if TIMING_CACHE.exists():
        return pd.read_parquet(TIMING_CACHE)
    # The pregnancy-history variables (p19, p3) refer to the same pregnancy as
    # the maternity section that holds the ANC count, INCLUDING stillbirths.
    # The live-birth history (b19, b3) has no row for a stillbirth, so using
    # it would silently drop the twelve women whose most recent pregnancy
    # ended in one.
    ir = pd.read_stata(IR_FILE, columns=["caseid", "p19_01", "p3_01", "m80_1",
                                         "b19_01", "v008", "b5_01"],
                       convert_categoricals=False)
    out = pd.DataFrame({
        "caseid": ir.caseid.astype(str),
        "months_since_birth": ir.p19_01,
        "birth_cmc": ir.p3_01,
        "interview_cmc": ir.v008,
        "pregnancy_outcome": ir.m80_1.map({1: "live birth", 3: "stillbirth"}),
        "months_since_birth_livebirth_history": ir.b19_01,
        "index_child_alive": ir.b5_01,
    })
    out.to_parquet(TIMING_CACHE, index=False)
    return out


def cmc_to_year(cmc) -> np.ndarray:
    """DHS century-month code to a decimal year (CMC 1 = January 1900)."""
    cmc = np.asarray(cmc, dtype=float)
    return 1900 + (cmc - 1) / 12.0


def load(cohort: str = "full") -> pd.DataFrame:
    """The analysis frame for one cohort, with birth timing attached.

    Adds `months_since_birth`, `birth_cmc`, `age_at_birth` and a `partition`
    column ("development" or "held-out") taken from the original split.
    """
    if cohort not in COHORTS:
        raise ValueError(f"cohort must be one of {COHORTS}")
    df = pd.read_pickle(FROZEN)
    df["caseid"] = df.caseid.astype(str)
    timing = birth_timing()
    timing["caseid"] = timing.caseid.astype(str)
    df = df.merge(timing, on="caseid", how="left", validate="one_to_one")
    if df.months_since_birth.isna().any():
        raise ValueError("birth timing missing for some women")

    # Age at the birth, which is what the DHS report tabulates. Current age
    # adds up to three years of noise for the older births.
    df["age_at_birth"] = df.v012 - df.months_since_birth / 12.0

    # The split is drawn once, on the full cohort, and then restricted. Drawing
    # it again on the recent cohort would change which clusters are held out.
    train_psus, test_psus = design.make_psu_holdout(pd.read_pickle(FROZEN))
    df["partition"] = np.where(df.v021.isin(test_psus), "held-out", "development")

    if cohort == "recent":
        df = df[df.months_since_birth < RECENT_MONTHS]
    elif cohort == "entry":
        df = _restrict_to_entry(df)
    return df.reset_index(drop=True)


def entry_table() -> pd.DataFrame:
    """caseid, early_anc and partition for the 5,001 ANC-entry women."""
    if all(p.exists() for p in ENTRY_FILES):
        parts = []
        for path, label in zip(ENTRY_FILES, ("development", "held-out")):
            e = pd.read_pickle(path)[["caseid", "early_anc"]]
            e["entry_partition"] = label
            parts.append(e)
        entry = pd.concat(parts, ignore_index=True)
    elif ENTRY_TABLE.exists():
        entry = pd.read_csv(ENTRY_TABLE)
    else:
        raise FileNotFoundError("ANC-entry cohort: neither the handoff files nor "
                                "data/anc_entry.csv is present")
    entry["caseid"] = entry.caseid.astype(str)
    return entry


def _restrict_to_entry(df: pd.DataFrame) -> pd.DataFrame:
    """The ANC-entry women, with `early_anc`, on the full cohort's split.

    The cohort is taken from the ANC-entry development and held-out files so
    it is exactly the population the 21-predictor ANC-entry models were built
    on. Their partition must equal the full-cohort PSU split restricted to
    these women -- checked here rather than assumed.
    """
    entry = entry_table()
    out = df.merge(entry, on="caseid", how="inner", validate="one_to_one")
    if len(out) != len(entry):
        raise ValueError("ANC-entry women missing from the full cohort")
    if not (out.partition == out.entry_partition).all():
        raise ValueError("ANC-entry partition differs from the full-cohort split")
    if not out.anc1plus.astype(bool).all():
        raise ValueError("ANC-entry cohort contains women without ANC")
    out["early_anc"] = out.early_anc.astype(int)
    return out.drop(columns="entry_partition")


def development(df: pd.DataFrame) -> pd.DataFrame:
    """Only the rows selection and tuning are allowed to see."""
    dev = df[df.partition == "development"].reset_index(drop=True)
    assert (dev.partition == "development").all()
    return dev


def heldout(df: pd.DataFrame) -> pd.DataFrame:
    return df[df.partition == "held-out"].reset_index(drop=True)


def folds(dev: pd.DataFrame, seed: int = 2026):
    """PSU-grouped, stratum-preserving folds inside a development set."""
    return design.folds_to_splits(design.make_psu_stratum_folds(dev, seed=seed))
