"""Region-level analysis for the studio's map and region panels.

    python scripts/run_regional_eda.py

Everything here is descriptive and survey-weighted. Uncertainty comes from a
stratified PSU bootstrap run inside each region (whole clusters resampled within
their stratum), so a region's interval reflects how few clusters it rests on.

Writes outputs/regional/:
  cascade_by_region.csv    the ANC ladder per region and cohort, with 95% intervals
  contacts_by_region.csv   the weighted distribution of the contact count (0..12+)
  subgroups_by_region.csv  the ladder within region x (wealth, residence, education,
                           pregnancy intention, pregnancy order, insurance, access)
  profile_by_region.csv    how common each circumstance is in each region
  drivers_by_region.csv    why a region's predicted attainment differs from the
                           national one, split exactly across predictors (EBM)
  drivers_concepts_by_region.csv   the same, summed to planning concepts
  population.json          births per region per year, and the source
  summary.json             run metadata
"""

from __future__ import annotations

import itertools
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from anc8 import cohorts, design, ladder  # noqa: E402
from anc8.concepts import BY_KEY, CONCEPTS, concept_of  # noqa: E402

ENHANCED = ROOT / "outputs" / "enhanced"
OUT = ROOT / "outputs" / "regional"

N_BOOT = 400
MIN_N = 25  # cells with fewer women are reported but flagged, as the house min-N rule
SEED = 2026

# UN World Population Prospects 2024, medium variant: live births in Ethiopia in
# 2025. Combined with each region's survey-weighted share of recent births, this
# turns shares into numbers of women per year.
WPP_BIRTHS_2025 = 4_176_742
WPP_SOURCE = ("UN World Population Prospects 2024, medium variant, births in 2025 "
              "(https://population.un.org/wpp/)")

RUNGS = {"anc1plus": "anc1", "anc4plus": "anc4", "anc8plus": "anc8"}

# What each cascade quantity is, from the three rung flags.
def cascade_frame(df: pd.DataFrame) -> pd.DataFrame:
    a1, a4, a8 = (df[c].astype(float) for c in ("anc1plus", "anc4plus", "anc8plus"))
    return pd.DataFrame({
        "reach1": a1, "reach4": a4, "reach8": a8,
        "never": 1 - a1, "start_lt4": a1 - a4, "four_lt8": a4 - a8,
    })


def weighted_cascade(c: pd.DataFrame, w: np.ndarray) -> dict:
    tot = w.sum()
    m = {k: float((c[k].to_numpy() * w).sum() / tot) for k in c.columns}
    m["continue_1_to_4"] = m["reach4"] / m["reach1"] if m["reach1"] > 0 else np.nan
    m["continue_4_to_8"] = m["reach8"] / m["reach4"] if m["reach4"] > 0 else np.nan
    return m


LOSS_ACTION = {
    "never": ("never starting", "Outreach"),
    "start_lt4": ("stopping before the 4th contact", "Early engagement"),
    "four_lt8": ("stopping between the 4th and 8th", "Retention"),
}


def cascade_with_ci(df: pd.DataFrame, n_boot: int = N_BOOT) -> dict:
    w = (df.v005 / 1e6).to_numpy()
    c = cascade_frame(df)
    point = weighted_cascade(c, w)
    boots = []
    for idx in design.stratified_psu_bootstrap(df.v022.to_numpy(), df.v021.to_numpy(),
                                               n_resamples=n_boot, seed=SEED):
        boots.append(weighted_cascade(c.iloc[idx], w[idx]))
    b = pd.DataFrame(boots)
    out = {"n": int(len(df)), "n_clusters": int(df.v021.nunique())}
    for k, v in point.items():
        out[k] = v
        out[f"{k}_lo"] = float(np.nanpercentile(b[k], 2.5))
        out[f"{k}_hi"] = float(np.nanpercentile(b[k], 97.5))
    loss = max(("never", "start_lt4", "four_lt8"), key=lambda k: point[k])
    out["biggest_loss"], out["action"] = LOSS_ACTION[loss]
    out["biggest_loss_key"] = loss
    return out


def cascades() -> pd.DataFrame:
    rows = []
    for cohort in cohorts.COHORTS:
        df = cohorts.load(cohort)
        rows.append({"cohort": cohort, "region": "Ethiopia", **cascade_with_ci(df, 200)})
        for region, g in df.groupby("region", observed=True):
            rows.append({"cohort": cohort, "region": str(region), **cascade_with_ci(g)})
        print(f"  cascade: {cohort} ({len(df):,} women)", flush=True)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ subgroups
def access_band(df: pd.DataFrame) -> pd.Series:
    """Travel time to the nearest health post, in the bands a planner uses."""
    minutes = np.exp(df.travel_healthpost_log)
    band = pd.cut(minutes, [-1, 30, 60, np.inf], labels=["Under 30 min", "30-60 min", "Over 60 min"])
    band = band.astype(object)
    band[df.travel_healthpost_is_zero == 1] = "Under 30 min"
    band[df.healthpost_time_missing == 1] = "No health post in reach"
    return band.fillna("No health post in reach")


def subgroup_columns(df: pd.DataFrame) -> dict[str, pd.Series]:
    teen = np.where(df.age_at_birth < 20, "Under 20", np.where(df.age_at_birth < 35, "20-34", "35 and over"))
    return {
        "Wealth": df.wealth_quintile.astype(str),
        "Residence": df.residence.astype(str),
        "Education": df.maternal_education.astype(str),
        "Pregnancy wanted": df.pregnancy_intention.astype(str),
        "Pregnancy number": df.pregnancy_order_group.astype(str).str.replace("Pregnancy order ", "Order "),
        "Health insurance": df.health_insurance.astype(str).map({"Yes": "Insured", "No": "Not insured"}),
        "Health post": access_band(df),
        "Age at birth": pd.Series(teen, index=df.index),
    }


LEVEL_ORDER = {
    "Wealth": ["Poorest", "Poorer", "Middle", "Richer", "Richest"],
    "Residence": ["Rural", "Urban"],
    "Education": ["No education", "Primary", "Secondary", "Higher"],
    "Pregnancy wanted": ["Wanted then", "Wanted later", "Wanted no more"],
    "Pregnancy number": ["First pregnancy", "Order 2-3", "Order 4-5", "Order 6+"],
    "Health insurance": ["Not insured", "Insured"],
    "Health post": ["Under 30 min", "30-60 min", "Over 60 min", "No health post in reach"],
    "Age at birth": ["Under 20", "20-34", "35 and over"],
}


CONTACT_CAP = 12  # 12 or more contacts share one bar: fewer than 1% of women are above it


def contacts() -> pd.DataFrame:
    """How many ANC contacts women had, as weighted shares, per cohort and region.

    The ladder thresholds (1, 4, 8) are cuts through this one distribution, so it is
    what the ladder charts draw from; the heaping at 3-4 and 8 is visible here.
    """
    rows = []
    for cohort in cohorts.COHORTS:
        df = cohorts.load(cohort)
        k = df.anc_contacts.clip(upper=CONTACT_CAP).astype(int)
        w = (df.v005 / 1e6).to_numpy()
        groups = [("Ethiopia", np.ones(len(df), bool))] + [
            (str(r), (df.region == r).to_numpy()) for r in df.region.dropna().unique()]
        for name, m in groups:
            tot = w[m].sum()
            for c in range(CONTACT_CAP + 1):
                sel = m & (k == c).to_numpy()
                rows.append({"cohort": cohort, "region": name, "contacts": c,
                             "share": float(w[sel].sum() / tot), "n": int(sel.sum())})
    return pd.DataFrame(rows)


def subgroups() -> pd.DataFrame:
    rows = []
    for cohort in cohorts.COHORTS:
        df = cohorts.load(cohort)
        cols = subgroup_columns(df)
        c = cascade_frame(df)
        w = (df.v005 / 1e6).to_numpy()
        for dim, levels in cols.items():
            for scope, mask in [("Ethiopia", np.ones(len(df), bool))] + [
                    (str(r), (df.region == r).to_numpy()) for r in df.region.unique()]:
                for lvl in LEVEL_ORDER[dim]:
                    m = mask & (levels == lvl).to_numpy()
                    n = int(m.sum())
                    if n == 0:
                        continue
                    wc = weighted_cascade(c[m], w[m])
                    rows.append({"cohort": cohort, "region": scope, "dimension": dim, "level": lvl,
                                 "order": LEVEL_ORDER[dim].index(lvl), "n": n,
                                 "small": n < MIN_N, **{k: wc[k] for k in
                                 ("reach1", "reach4", "reach8", "never", "continue_4_to_8")}})
        print(f"  subgroups: {cohort}", flush=True)
    return pd.DataFrame(rows)


# -------------------------------------------------------------------- profile
PROFILE = [
    # key, label, how it is computed, whether a health system can move it
    ("poorest40", "In the poorest two-fifths", lambda d: d.wealth_quintile.isin(["Poorest", "Poorer"]), False),
    ("no_school", "No schooling", lambda d: d.maternal_education == "No education", False),
    ("rural", "Rural", lambda d: d.residence == "Rural", False),
    ("unintended", "Pregnancy not wanted then", lambda d: d.pregnancy_intention != "Wanted then", True),
    ("teen", "Under 20 at the birth", lambda d: d.age_at_birth < 20, False),
    ("grand_multi", "Sixth pregnancy or later", lambda d: d.pregnancy_order_group == "Pregnancy order 6+", False),
    ("no_post", "No health post in reach", lambda d: d.healthpost_time_missing == 1, True),
    ("far_post", "Over an hour to a health post",
     lambda d: (np.exp(d.travel_healthpost_log) > 60) & (d.healthpost_time_missing == 0), True),
    ("distance_problem", "Distance a big problem", lambda d: d.v467d == 1, True),
    ("money_problem", "Money a big problem", lambda d: d.v467c == 1, True),
    ("uninsured", "No health insurance", lambda d: d.health_insurance == "No", True),
    ("no_say", "No say in her own health care", lambda d: d.healthcare_decision_participation == "Does not participate", True),
    ("no_media", "No radio, TV or paper weekly",
     lambda d: (d.radio_weekly + d.television_weekly + d.newspaper_weekly) == 0, True),
]


def profile() -> pd.DataFrame:
    rows = []
    for cohort in cohorts.COHORTS:
        df = cohorts.load(cohort)
        w = (df.v005 / 1e6).to_numpy()
        for key, label, fn, modifiable in PROFILE:
            flag = np.asarray(fn(df), dtype=float)
            rows.append({"cohort": cohort, "region": "Ethiopia", "key": key, "label": label,
                         "modifiable": modifiable, "value": float((flag * w).sum() / w.sum())})
            for r, g in df.groupby("region", observed=True):
                m = (df.region == r).to_numpy()
                rows.append({"cohort": cohort, "region": str(r), "key": key, "label": label,
                             "modifiable": modifiable,
                             "value": float((flag[m] * w[m]).sum() / w[m].sum())})
    return pd.DataFrame(rows)


# -------------------------------------------------------------------- drivers
DRIVER_MODELS = {"ebm": "Explainable Boosting", "logistic": "Logistic regression"}
LIBRARY_MODELS = ROOT / "outputs" / "library" / "models"


def drivers(models=tuple(DRIVER_MODELS)) -> pd.DataFrame:
    """Why a region's predicted attainment differs from the country's, exactly.

    Explainable boosting and logistic regression both predict log-odds as an
    intercept plus one term per predictor (the library's models on the full
    candidate pool). So the gap between a region's average predicted log-odds and
    the national average is exactly the sum, over predictors, of the gap in that
    predictor's average term. Each piece says how much of the region's difference
    that predictor accounts for, in that model. It describes the model's arithmetic,
    not a cause. Both models are reported, in the `model` column.
    """
    import joblib
    from build_form_schema import LABELS

    from anc8 import explain, library as lib

    df = lib.raw_frame()
    w = (df.v005 / 1e6).to_numpy()
    rows = []
    for (outcome, rung), key in itertools.product(RUNGS.items(), models):
        blob = joblib.load(LIBRARY_MODELS / f"s21_{outcome}.joblib")
        numeric, categorical = blob["numeric"], blob["categorical"]
        pipe = blob["models"][DRIVER_MODELS[key]]
        X = lib.design_matrix(df, numeric, categorical)
        if key == "ebm":
            T, intercept = explain.ebm_terms(pipe, X, len(numeric) + len(categorical))
        else:
            T, intercept = explain.logistic_terms(pipe, X, numeric, categorical)
        names = list(numeric) + list(categorical)
        national = np.average(T, axis=0, weights=w)
        p = 1 / (1 + np.exp(-(T.sum(axis=1) + intercept)))
        p_nat = float(np.average(p, weights=w))
        for r in df.region.dropna().unique():
            m = (df.region == r).to_numpy()
            diff = np.average(T[m], axis=0, weights=w[m]) - national
            p_reg = float(np.average(p[m], weights=w[m]))
            for pred, d in zip(names, diff):
                concept = concept_of(pred)
                rows.append({
                    "model": key, "rung": rung, "region": str(r), "predictor": pred,
                    "label": LABELS.get(pred, (pred,))[0],
                    "concept": concept,
                    "domain": ladder.domain_of(pred),
                    "modifiable": BY_KEY.get(concept, {}).get("modifiable", False),
                    "contribution": float(d),
                    "region_predicted": p_reg, "national_predicted": p_nat,
                })
        print(f"  drivers: {rung} ({key})", flush=True)
    return pd.DataFrame(rows)


def concept_drivers(drv: pd.DataFrame) -> pd.DataFrame:
    """The same decomposition summed to concepts (exact: the terms are additive)."""
    g = (drv.groupby(["model", "rung", "region", "concept"], as_index=False)
         .agg(contribution=("contribution", "sum"),
              region_predicted=("region_predicted", "first"),
              national_predicted=("national_predicted", "first")))
    g["label"] = g.concept.map(lambda k: BY_KEY.get(k, {}).get("label", k))
    g["modifiable"] = g.concept.map(lambda k: BY_KEY.get(k, {}).get("modifiable", False))
    g["lever"] = g.concept.map(lambda k: BY_KEY.get(k, {}).get("lever", ""))
    return g


def population(casc: pd.DataFrame) -> dict:
    df = cohorts.load("recent")
    w = df.v005 / 1e6
    share = (w.groupby(df.region.astype(str)).sum() / w.sum()).to_dict()
    births = {r: WPP_BIRTHS_2025 * s for r, s in share.items()}
    return {"births_per_year": WPP_BIRTHS_2025, "source": WPP_SOURCE,
            "method": "national births x the region's survey-weighted share of births "
                      "in the 24 months before interview",
            "regions": {r: {"share": share[r], "births": births[r]} for r in sorted(share)}}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", choices=list(DRIVER_MODELS), default=list(DRIVER_MODELS),
                    help="the additive models the regional drivers are split by")
    args = ap.parse_args()
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    print("regional analysis", flush=True)
    casc = cascades()
    casc.to_csv(OUT / "cascade_by_region.csv", index=False)
    contacts().to_csv(OUT / "contacts_by_region.csv", index=False)
    sub = subgroups()
    sub.to_csv(OUT / "subgroups_by_region.csv", index=False)
    prof = profile()
    prof.to_csv(OUT / "profile_by_region.csv", index=False)
    drv = drivers(tuple(args.models))
    drv.to_csv(OUT / "drivers_by_region.csv", index=False)
    concept_drivers(drv).to_csv(OUT / "drivers_concepts_by_region.csv", index=False)
    pop = population(casc)
    (OUT / "population.json").write_text(json.dumps(pop, indent=1), encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps({
        "bootstrap_resamples": N_BOOT, "min_n": MIN_N, "seed": SEED,
        "minutes": round((time.time() - t0) / 60, 1)}, indent=1), encoding="utf-8")
    print(f"done in {(time.time() - t0) / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
