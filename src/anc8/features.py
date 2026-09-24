"""Adjudicated predictor set for the enhanced ANC8 model.

Screening ranks variables by association; this module decides which of them may
actually be used, on grounds of *temporality* rather than strength. A variable
is admissible only if it describes something knowable before or early in the
index pregnancy. Several of the strongest-scoring candidates fail that test and
are excluded here despite their performance.

Design decisions that differ from the original 21-predictor register, with the
reason each one was made:

  v191 replaces (and joins) v190
      The continuous wealth factor score carries a univariate weighted AUC of
      0.755 on its own -- essentially the whole performance of the original
      model. Collapsing it to quintiles threw that away. Both are kept: trees
      split the continuous score finely, while the quintile stays interpretable.

  v157 / v158 / v159 replace traditional_media_weekly_count
      The original collapsed newspaper, radio and television into a 0-3 count.
      Television alone scores 0.677; radio scores 0.505 and newspaper 0.527, so
      the count (0.644) is *worse than its best component*. The collapse
      destroyed signal rather than summarising it.

  v133 joins v106
      Education in single years outscores the four-level version (0.674 vs
      0.657) because the levels are wide and unevenly spaced.

  s1101b joins s1101
      Ethiopian ANC is largely delivered at health posts, yet only travel time
      to the nearest hospital/health *centre* was used. Health-post travel time
      is a distinct access dimension.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# EXCLUSIONS ON TEMPORALITY GROUNDS
#
# Each of these scored well enough to be tempting. Each is excluded because it
# is measured at interview and plausibly reflects the ANC episode itself, so
# including it would let the outcome leak backwards into the predictors.
# ---------------------------------------------------------------------------

TEMPORAL_EXCLUSIONS = {
    "v394": (
        "Visited health facility last 12 months -- ANC contacts ARE facility "
        "visits. Empirically: for births within the last 12 months, "
        "P(v394=1 | ANC>=1)=0.67 vs 0.28 for ANC=0, and the gap narrows to "
        "0.56 vs 0.31 once the birth is 24-60 months back, i.e. once the ANC "
        "visits fall outside the 12-month recall window. That is the outcome "
        "being re-reported as a predictor."
    ),
    "v395": "Told about family planning at facility -- conditional on the same visit as v394.",
    "v393": "Visited by fieldworker last 12 months -- same recall-window contamination.",
    "v393a": "Conditional on v393.",
    "v781": (
        "Ever tested for HIV -- provider-initiated HIV testing is a routine "
        "component of Ethiopian ANC, so for this cohort the variable is partly "
        "a record of having attended ANC."
    ),
    "v312": "Current contraceptive method, measured at interview; postpartum FP is delivered at ANC/PNC contacts.",
    "v313": "As v312.",
    "v361": "Contraceptive use pattern, as v312.",
    "v364": "Contraceptive use and intention, as v312.",
    "v326": "Source of current contraceptive method -- conditional on post-pregnancy service contact.",
    "v327": "As v326.",
    "v247b": "Menstrual hygiene -- measured post-pregnancy, 36% missing, subsample only.",
    "v719": "Works for family/other/self -- asked only of working women, 65% missing in cohort.",
    "m13_1": "Timing of first ANC -- ANC-process variable, admissible only in the ANC-entry arm.",
    "m13a_1": "As m13_1.",
}

# ---------------------------------------------------------------------------
# ADMITTED RAW VARIABLES, BY DOMAIN
# ---------------------------------------------------------------------------

# Continuous / count. Kept numeric so trees can split them finely and the
# spline arm can model curvature.
NUMERIC_RAW = {
    "v012": "Maternal age at interview (years)",
    "v191": "Wealth index factor score (continuous)",
    "v191a": "Wealth index factor score, urban/rural specific",
    "v133": "Maternal education, single years",
    "v715": "Partner education, total years",
    "v730": "Partner age (years)",
    "v136": "Household size",
    "v137": "Children aged 5 and under in household",
    "v138": "Eligible women in household",
    "v152": "Age of household head",
    "v115": "Time to water source (minutes)",
    "v201": "Total children ever born",
    "v212": "Age at first birth",
    "v218": "Number of living children",
    "v511": "Age at first cohabitation",
    "v613": "Ideal number of children",
    "s1101": "Travel time to nearest hospital/health centre (minutes)",
    "s1101b": "Travel time to nearest health post (minutes)",
}

# Ordered categorical, left as integer codes: the ordering is meaningful.
ORDINAL_RAW = {
    "v106": "Maternal education level",
    "v190": "Wealth quintile",
    "v190a": "Wealth quintile, urban/rural specific",
    "v155": "Literacy",
    "v157": "Newspaper reading frequency",
    "v158": "Radio listening frequency",
    "v159": "Television watching frequency",
    "v171a": "Internet use recency",
    "v149": "Educational attainment (detailed)",
    "v729": "Partner educational attainment",
}

# Nominal categorical.
NOMINAL_RAW = {
    "v024": "Region",
    "v025": "Place of residence",
    "v130": "Religion",
    "v045c": "Native language of respondent",
    "v113": "Source of drinking water",
    "v116": "Type of toilet facility",
    "v127": "Main floor material",
    "v151": "Sex of household head",
    "v716": "Maternal occupation (detailed)",
    "s1101a": "Transport mode to hospital/health centre",
    "s1102": "Transport mode to health post",
}

# Binary yes/no assets, autonomy and barrier items.
BINARY_RAW = {
    "v119": "Household has electricity",
    "v120": "Household has radio",
    "v121": "Household has television",
    "v123": "Household has bicycle",
    "v169a": "Owns a mobile telephone",
    "v170": "Has a bank/financial account",
    "v481": "Covered by health insurance",
    "v731": "Worked in last 12 months",
    "v745a": "Owns a house",
    "v745b": "Owns land",
    "v467b": "Barrier to care: getting permission",
    "v467c": "Barrier to care: getting money",
    "v467d": "Barrier to care: distance to facility",
    "v467f": "Barrier to care: not wanting to go alone",
    "v744a": "IPV attitude: goes out without telling",
    "v744b": "IPV attitude: neglects children",
    "v744c": "IPV attitude: argues",
    "v744d": "IPV attitude: refuses sex",
    "v744e": "IPV attitude: burns food",
    "v743b": "Decides: large household purchases",
    "v743d": "Decides: visits to family",
    "v743f": "Decides: use of partner earnings",
}

# Constructs Notebook 1 built carefully (structural non-applicability preserved
# as explicit categories rather than imputed). Reused verbatim from the frozen
# dataset rather than rebuilt, so that they mean exactly what they meant before.
INHERITED_CONSTRUCTS = [
    "maternal_education",
    "maternal_current_union_status",
    "maternal_occupation_group",
    "partner_education",
    "partner_occupation_group",
    "healthcare_decision_participation",
    "wealth_quintile",
    "residence",
    "region",
    "religion_group",
    "internet_exposure",
    "health_insurance",
    "pregnancy_order_group",
    "preceding_pregnancy_interval_group",
    "pregnancy_intention",
    "previous_pregnancy_history",
    "transport_mode_group",
]


def build_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Construct composite predictors from admitted raw variables.

    Each composite is an index over items that individually carry little signal
    but jointly describe a coherent construct, which trees pick up more readily
    than the scattered items.
    """
    out = pd.DataFrame(index=df.index)

    # Spousal gaps: large asymmetries in education or age are associated with
    # lower decision-making latitude for the woman.
    out["spousal_education_gap"] = df["v715"] - df["v133"]
    out["spousal_age_gap"] = df["v730"] - df["v012"]

    # Decision-making participation: count of domains in which the woman has a
    # say. v743* codes 1 (respondent) and 2 (jointly with partner) count as
    # participation; 3+ (partner/other alone) do not.
    dm = [c for c in ("v743a", "v743b", "v743d", "v743f") if c in df]
    out["decision_participation_count"] = (
        sum(df[c].isin([1, 2]).astype(float) for c in dm) if dm else np.nan
    )

    # Attitude to intimate-partner violence: number of scenarios endorsed.
    # A standard DHS proxy for gender norms.
    ipv = [c for c in ("v744a", "v744b", "v744c", "v744d", "v744e") if c in df]
    out["ipv_justification_count"] = (
        sum(df[c].eq(1).astype(float) for c in ipv) if ipv else np.nan
    )

    # Barriers to accessing care: number reported as a big problem (code 1).
    bar = [c for c in ("v467b", "v467c", "v467d", "v467f") if c in df]
    out["access_barrier_count"] = (
        sum(df[c].eq(1).astype(float) for c in bar) if bar else np.nan
    )

    # Household asset/infrastructure index.
    assets = [c for c in ("v119", "v120", "v121", "v123", "v169a", "v170") if c in df]
    out["asset_index"] = (
        sum(df[c].eq(1).astype(float) for c in assets) if assets else np.nan
    )

    # Media exposure kept as separate weekly-exposure flags, NOT summed --
    # see the module docstring for why the original count was harmful.
    for src, name in (("v157", "newspaper"), ("v158", "radio"), ("v159", "television")):
        if src in df:
            out[f"{name}_weekly"] = df[src].ge(2).astype(float)

    # Travel time: the raw minutes are heavily right-skewed and top-coded at
    # 600. log1p gives the linear arm a usable scale; the zero flag separates
    # "lives at the facility" from "very close to it", which are different.
    for src, name in (("s1101", "hospital"), ("s1101b", "healthpost")):
        if src in df:
            out[f"travel_{name}_log"] = np.log1p(df[src])
            out[f"travel_{name}_is_zero"] = df[src].eq(0).astype(float)
            out[f"travel_{name}_topcoded"] = df[src].ge(600).astype(float)

    # s1101b is ~23% missing by design (not all clusters have a health post in
    # range). An explicit flag is more honest than silent median imputation,
    # which would assert a travel time nobody reported.
    if "s1101b" in df:
        out["healthpost_time_missing"] = df["s1101b"].isna().astype(float)

    # Parity pressure: children already at home relative to the ideal family
    # size the woman states. Captures whether this pregnancy is "extra".
    if {"v218", "v613"} <= set(df):
        ideal = df["v613"].where(df["v613"] < 90)  # 90+ are non-numeric codes
        out["children_over_ideal"] = df["v218"] - ideal

    return out


def assemble(frozen: pd.DataFrame, ir: pd.DataFrame):
    """Join the inherited constructs to the newly admitted raw variables.

    Returns (frame, numeric_columns, categorical_columns).
    """
    raw_cols = (
        list(NUMERIC_RAW)
        + list(ORDINAL_RAW)
        + list(NOMINAL_RAW)
        + list(BINARY_RAW)
        + ["v743a"]  # construct input for the decision index
    )
    raw_cols = [c for c in dict.fromkeys(raw_cols) if c in ir.columns]

    keep_frozen = ["caseid", "anc8plus", "anc4plus", "v005", "v021", "v022"] + [
        c for c in INHERITED_CONSTRUCTS if c in frozen.columns
    ]
    base = frozen[keep_frozen].copy()

    # Add every rung of the contact ladder, derived from the same source count.
    # Notebook 1 froze only ANC4+ and ANC8+; ANC1+ ("reached antenatal care at
    # all") is the rung that separates an access failure from an engagement
    # failure, and the cross-outcome analysis needs all three on identical rows.
    from . import outcomes as _outcomes

    counts = base[["caseid"]].merge(
        ir[["caseid", _outcomes.SOURCE_VARIABLE]], on="caseid", how="left"
    )[_outcomes.SOURCE_VARIABLE]
    counts.index = base.index

    ladder = _outcomes.derive(counts)
    for name in _outcomes.LADDER:
        base[name] = ladder[name].to_numpy()
    base["anc_contacts"] = counts.to_numpy()
    _outcomes.check_nested(base[_outcomes.LADDER])

    merged = base.merge(
        ir[["caseid"] + raw_cols], on="caseid", how="left", validate="one_to_one"
    )
    derived = build_derived(merged)
    merged = pd.concat([merged, derived], axis=1)

    numeric = [c for c in NUMERIC_RAW if c in merged] + list(derived.columns)
    categorical = (
        [c for c in ORDINAL_RAW if c in merged]
        + [c for c in NOMINAL_RAW if c in merged]
        + [c for c in BINARY_RAW if c in merged]
        + [c for c in INHERITED_CONSTRUCTS if c in merged]
    )
    # v743a is a construct input, not itself a predictor (the inherited
    # healthcare_decision_participation already encodes it with its structural
    # "Not applicable" category intact).
    categorical = [c for c in categorical if c != "v743a"]

    return merged, numeric, categorical
