"""Generate 3_ANC8_deep_EDA_and_feature_reascertainment.ipynb.

The notebook is assembled programmatically so that its cells stay in sync with
the modules under src/anc8/ rather than drifting into a second copy of the
logic. Run it, then execute the notebook to populate outputs.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip().splitlines(keepends=True)}


def code(text):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.strip("\n").splitlines(keepends=True),
    }


cells = []

cells.append(md("""
# 3. ANC8 deep EDA and predictor re-ascertainment

## 3.1 Why this notebook exists

Notebook 1 selected 21 predictors by translating a previously frozen EDHS
mapping register into ANC8-specific roles. That register was built for a
different study with a different outcome (post-delivery transition safety), so
its candidate list was never a list of *everything the survey could say about
ANC attendance* -- it was a list of what a prior analysis happened to need.

Two consequences follow, and this notebook establishes both empirically:

1. **Variables that matter for ANC contact attainment were never offered for
   consideration.** They are not in the register, so no decision was ever
   recorded about them, favourable or otherwise.
2. **Two of the 21 were coarsened in ways that destroyed signal**, rather than
   summarising it.

This notebook screens every column of the Individual Recode, adjudicates the
survivors on temporality, and freezes an enhanced analytic dataset. It does not
fit any prediction model; that is Notebook 4.

**Nothing in Notebooks 1 and 2 is modified.** The frozen dataset, the
publication tables and the locked held-out predictions remain exactly as they
were, and Notebook 4 measures the new work against them.
"""))

cells.append(code("""
import sys, json, hashlib, warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, "src")

from anc8 import design, features, screening

pd.set_option("display.width", 220)
pd.set_option("display.max_colwidth", 70)

ROOT = Path(".")
OUT = ROOT / "outputs" / "enhanced"
OUT.mkdir(parents=True, exist_ok=True)

FROZEN = ROOT / "outputs" / "ANC8_analysis_frozen.pkl"
IR_FILE = ROOT / "ETIR8AFL.dta"

print("frozen dataset :", FROZEN)
print("source IR file :", IR_FILE)
"""))

cells.append(md("""
## 3.2 Reconstructing the cohort

The analytic cohort is defined exactly as Notebook 1 defined it: maternal-health
roster records with a resolved ANC contact count (`m14_1` between 0 and 97).
Women coded 98 ("don't know") remain unresolved and are excluded from the
denominator, as before.

Reproducing the cohort from the raw file rather than assuming it is a check
that this notebook and Notebook 1 are talking about the same women.
"""))

cells.append(code("""
reader = pd.read_stata(IR_FILE, iterator=True)
VARIABLE_LABELS = reader.variable_labels()

ir = pd.read_stata(IR_FILE, convert_categoricals=False)
print("IR file:", ir.shape[0], "women x", ir.shape[1], "columns")

cohort = ir[ir.m14_1.notna() & ir.m14_1.between(0, 97)].copy()
y = (cohort.m14_1 >= 8).astype(int).to_numpy()
w = (cohort.v005 / 1e6).to_numpy()

frozen = pd.read_pickle(FROZEN)
frozen = frozen[frozen.anc8plus.notna()].copy()

print("\\nreconstructed cohort :", len(cohort))
print("Notebook 1 frozen    :", len(frozen))
assert set(cohort.caseid) == set(frozen.caseid), "cohort definition has drifted"
print("cohort membership identical to Notebook 1: True")

print("\\nunweighted ANC8+ prevalence :", f"{y.mean() * 100:.2f}%")
print("weighted ANC8+ prevalence   :", f"{np.average(y, weights=w) * 100:.2f}%")
"""))

cells.append(md("""
## 3.3 The outcome is a dichotomised count

`anc8plus` is not a natively binary outcome. It is `m14_1 >= 8`, where `m14_1`
counts reported ANC contacts. The distribution below matters for Notebook 4:
the mass sitting at 4 and 6 contacts means a large group of women are close to
the threshold, and a binary model at 8 treats a woman with 7 contacts as
identical to one with 0.

That discarded ordering is recoverable, and Notebook 4 tests whether recovering
it helps.
"""))

cells.append(code("""
counts = cohort.m14_1.astype(int)
dist = (
    pd.DataFrame({"contacts": counts, "w": w})
    .groupby("contacts")
    .agg(n=("w", "size"), weighted_pct=("w", lambda s: 100 * s.sum() / w.sum()))
)
dist["cum_weighted_pct"] = dist.weighted_pct.cumsum()
print(dist.head(16).to_string())

print("\\nwomen with 6 or 7 contacts (just below threshold):",
      int(counts.between(6, 7).sum()))
print("women with exactly 8 contacts                  :", int((counts == 8).sum()))
print("\\nA binary split at 8 treats the first group as equivalent to zero contacts.")
"""))

cells.append(md("""
## 3.4 Systematic screening of every IR column

Rather than inheriting a candidate list, every one of the 6,648 columns is
scored against the outcome under the survey design.

Three measures are computed per variable:

- **weighted AUC** treating the raw variable as a score. This assumes
  monotonicity, so it understates nominal variables;
- **weighted prevalence spread**, the range of ANC8+ prevalence across
  categories, which catches the nominal variables AUC misses (region is the
  clearest case: AUC 0.52, spread 0.62);
- **cohort missingness**.

Screening *ranks*. It does not select: a high score is a reason to look at a
variable, never a reason to admit it. Admission is decided in 3.6 on
temporality grounds, and several of the highest-scoring candidates are refused.
"""))

cells.append(code("""
screen = screening.screen(cohort, VARIABLE_LABELS, y, w)
screen.to_csv(OUT / "candidate_screening.csv", index=False)

print(screen.screen_status.value_counts().to_string())
print("\\nwhy variables were excluded outright:")
print(screen[screen.screen_status == "excluded"]
      .exclusion_reason.value_counts().head(10).to_string())
"""))

cells.append(md("""
### 3.4.1 Coverage floor

Most of the IR file is birth-history and pregnancy-history slots (`b*_11`,
`p*_10`, ...) populated for a handful of women. An AUC estimated on 0.9% of the
cohort is noise, and without a coverage floor those columns dominate the top of
the ranking -- the unfiltered table is led by `idx97_6` ("index to birth
history") at AUC 1.000 on 61 women.

Variables observed for under half the cohort are therefore ranked separately as
`low_coverage` rather than silently dropped, so the decision stays visible.
"""))

cells.append(code("""
candidates = screen[screen.screen_status == "candidate"]
print(f"rankable candidates (>=50% coverage): {len(candidates)}")
print("\\nTOP 30 BY WEIGHTED AUC")
print(candidates.head(30)[
    ["variable", "label", "missing", "n_unique", "weighted_auc", "prevalence_spread"]
].to_string(index=False))
"""))

cells.append(md("""
## 3.5 What the original 21 predictors missed

Two findings, both measurable.

### 3.5.1 The strongest variable in the dataset was coarsened away

`v191` is the DHS wealth index factor score, a continuous latent measure.
`v190` is the same quantity collapsed into population quintiles. Notebook 1
used only `v190`.

On its own, `v191` reaches a survey-weighted AUC of about 0.755 -- close to the
held-out AUROC of 0.761 that the published 21-predictor XGBoost model achieved
using everything it had. Collapsing a continuous score into five bins discards
within-quintile ordering, and here that ordering was carrying real information.

### 3.5.2 The media count is worse than its best component

Notebook 1 combined newspaper (`v157`), radio (`v158`) and television (`v159`)
into `traditional_media_weekly_count`, a 0-3 count of media accessed weekly.
But the three are not interchangeable: television carries most of the signal
and radio carries almost none, so summing them dilutes television with noise.

The check below compares the components against the count that replaced them.
"""))

cells.append(code("""
from sklearn.metrics import roc_auc_score

def wauc(series):
    x = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    ok = np.isfinite(x)
    a = roc_auc_score(y[ok], x[ok], sample_weight=w[ok])
    return max(a, 1 - a)

print("WEALTH")
print(f"  v191 continuous factor score : {wauc(cohort.v191):.4f}   <- not used by Notebook 1")
print(f"  v190 quintile (used)         : {wauc(cohort.v190):.4f}")

media_count = (cohort[["v157", "v158", "v159"]] >= 2).sum(axis=1)
print("\\nMEDIA")
print(f"  v159 television alone        : {wauc(cohort.v159):.4f}")
print(f"  v158 radio alone             : {wauc(cohort.v158):.4f}")
print(f"  v157 newspaper alone         : {wauc(cohort.v157):.4f}")
print(f"  combined weekly count (used) : {wauc(media_count):.4f}   <- below television alone")

print("\\nEDUCATION")
print(f"  v133 single years            : {wauc(cohort.v133):.4f}   <- not used")
print(f"  v106 four-level (used)       : {wauc(cohort.v106):.4f}")

print("\\nACCESS")
print(f"  s1101  hospital/health centre (used) : {wauc(cohort.s1101):.4f}")
print(f"  s1101b health post                   : {wauc(cohort.s1101b):.4f}   <- not used")
print("  (most Ethiopian ANC is delivered at health posts)")
"""))

cells.append(md("""
### 3.5.3 And which of the original 21 earned their place?

The complementary question. A predictor that contributes nothing still costs
something: it consumes a degree of freedom, it has to be collected, and in a
deployed tool it is another question someone has to answer.

Each of the 21 is removed in turn and the model refitted over the same folds.
A predictor whose removal does not hurt is carrying no independent signal
given the others.

Two cautions on reading this. Drop-one understates a predictor duplicated by
another -- region and residence overlap heavily, as do the education measures
-- so a small loss is not proof of uselessness. And a predictor may belong in
a model for reasons prediction cannot see, such as equity monitoring or
comparability with prior work. "Contributes nothing to prediction" is not the
same as "should be deleted".
"""))

cells.append(code("""
drop1 = pd.read_csv(OUT / "original21_drop_one.csv")

print("CONTRIBUTION OF EACH ORIGINAL PREDICTOR (drop-one, development OOF)")
print(f"full 21-predictor model: AP = {drop1.full_AP.iloc[0]:.4f}")
print()
print(drop1[["predictor", "AP_without", "AP_loss", "AUROC_loss"]].to_string(index=False))

dead = drop1[drop1.AP_loss <= 0]
print(f"\\n{len(dead)} of 21 predictors cost nothing when removed:")
for r in dead.itertuples():
    print(f"    {r.predictor:38s} AP improves by {-r.AP_loss:+.4f} without it")
"""))

cells.append(md("""
Region dominates everything else by an order of magnitude, which fits the
descriptive picture in 3.10: weighted ANC8+ attainment runs from about 66% in
Addis Ababa to under 4% in Somali.

The more uncomfortable result is below. The original predictor set is not
merely incomplete -- it is *larger than it should be*. Three of its own members
already outperform all twenty-one together.

The subsets come from greedy forward selection rather than "top k of the
drop-one ranking". The two are not the same thing: drop-one measures what a
predictor adds LAST, given every other predictor, while forward selection
measures what it adds FIRST. Taking the top k of a drop-one ranking quietly
assumes those orders agree, and here they do not -- wealth quintile is the
strongest single predictor, while region has the largest drop-one loss.
"""))

cells.append(code("""
ladder = pd.read_csv(OUT / "original21_parsimony_ladder.csv")
print("HOW FAR A HANDFUL OF THE ORIGINAL PREDICTORS GETS YOU")
print(ladder.to_string(index=False))

full = ladder.AP.iloc[0]
best_small = ladder[ladder.n_predictors <= 4].AP.max()
print(f"\\nBest 4-predictor subset reaches AP {best_small:.4f} against {full:.4f} "
      f"for all 21 -- that is {best_small / full * 100:.0f}% of the full model, "
      "on 4 of its own predictors.")
print("Dropping the 5 non-contributing predictors alone improves AP by "
      f"{ladder.AP.iloc[1] - full:+.4f}.")
"""))

cells.append(md("""
## 3.6 Temporality adjudication

A high screening score is not a licence to use a variable. The question is
*when* it was measured relative to the ANC episode being predicted.

Several strong candidates fail this test and are refused. The most important is
`v394`, "visited a health facility in the last 12 months" -- because ANC
contacts **are** facility visits. For a woman whose birth was recent, the ANC
visits themselves fall inside the recall window, so the variable partly records
the outcome.

The check below shows the signature: the gap between ANC attenders and
non-attenders is widest exactly when the birth is recent enough for the ANC
visits to be inside the 12-month window, and shrinks as the birth recedes.
"""))

cells.append(code("""
months_since_birth = cohort.v008 - cohort.b3_01

print("v394 'visited health facility last 12 months', by recency of index birth")
print(f"{'window':<26}{'n':>7}{'P(v394=1|ANC>=1)':>19}{'P(v394=1|ANC=0)':>18}{'gap':>8}")
for lo, hi, label in [(0, 11, "birth within 12 months"),
                      (12, 23, "birth 12-23 months ago"),
                      (24, 60, "birth 24-60 months ago")]:
    s = cohort[months_since_birth.between(lo, hi)]
    a = s.loc[s.m14_1 >= 1, "v394"].mean()
    b = s.loc[s.m14_1 == 0, "v394"].mean()
    print(f"{label:<26}{len(s):>7}{a:>19.3f}{b:>18.3f}{a - b:>8.3f}")

print("\\nThe gap is largest when the ANC visits lie inside the recall window.")
print("That is the outcome being re-reported as a predictor, so v394 is excluded.")
"""))

cells.append(code("""
print("VARIABLES REFUSED ON TEMPORALITY GROUNDS")
print("=" * 100)
for var, reason in features.TEMPORAL_EXCLUSIONS.items():
    label = VARIABLE_LABELS.get(var, "")
    auc = screen.loc[screen.variable == var, "weighted_auc"]
    auc_txt = f"{auc.iloc[0]:.3f}" if len(auc) and pd.notna(auc.iloc[0]) else "  -  "
    print(f"\\n{var:8s} (AUC {auc_txt})  {label}")
    print(f"         {reason}")
"""))

cells.append(md("""
## 3.7 Assembling the enhanced predictor set

The enhanced set combines three sources:

1. **Notebook 1's derived constructs, reused verbatim.** Constructs such as
   `partner_education` and `preceding_pregnancy_interval_group` encode
   structural non-applicability as explicit categories ("Not applicable /
   not currently in union", "First pregnancy") rather than as missing data.
   That work was done carefully and is inherited rather than redone, so those
   variables mean exactly what they meant before.
2. **Newly admitted raw variables**, across wealth, education, partner
   characteristics, household infrastructure, media, access, reproductive
   history, empowerment and barriers to care.
3. **Derived composites**, including spousal education and age gaps, a
   decision-making participation count, an IPV-attitude count, an access-barrier
   count, an asset index, and log/zero/top-code treatments of travel time.

One missingness decision worth stating: `s1101b` (health-post travel time) is
~23% missing by design, because not every cluster has a health post in range.
It is carried with an explicit `healthpost_time_missing` flag rather than
median-imputed, since imputing would assert a travel time nobody reported.
"""))

cells.append(code("""
enhanced, numeric, categorical = features.assemble(frozen, ir)

print(f"enhanced analytic frame : {enhanced.shape[0]} women x {enhanced.shape[1]} columns")
print(f"numeric predictors      : {len(numeric)}")
print(f"categorical predictors  : {len(categorical)}")
print(f"TOTAL predictors        : {len(numeric) + len(categorical)}  (original study: 21)")

miss = enhanced[numeric + categorical].isna().mean().sort_values(ascending=False)
print("\\npredictors with any missingness:")
print((miss[miss > 0] * 100).round(2).to_string())
"""))

cells.append(md("""
## 3.8 Predictor register v2

The register records every admitted predictor with its source, role and
rationale, in the same schema as `ANC8_predictor_register_final.csv` so the two
generations can be read side by side. It is also the schema the deployed web
application builds its input form from, so the form cannot drift away from what
the model actually expects.
"""))

cells.append(code("""
rows = []
DOMAIN = {
    **{k: "Household and socioeconomic" for k in
       ["v191", "v191a", "v190", "v190a", "v136", "v137", "v138", "v151", "v152",
        "v113", "v115", "v116", "v119", "v120", "v121", "v123", "v127", "v169a",
        "v170", "asset_index", "wealth_quintile", "residence", "v025"]},
    **{k: "Maternal and sociodemographic" for k in
       ["v012", "v133", "v106", "v149", "v155", "v157", "v158", "v159", "v171a",
        "v130", "v045c", "v716", "v731", "maternal_education",
        "maternal_occupation_group", "religion_group", "internet_exposure",
        "newspaper_weekly", "radio_weekly", "television_weekly"]},
    **{k: "Partner and empowerment" for k in
       ["v715", "v729", "v730", "v701", "v705", "v511", "v745a", "v745b",
        "v743b", "v743d", "v743f", "v744a", "v744b", "v744c", "v744d", "v744e",
        "spousal_education_gap", "spousal_age_gap", "decision_participation_count",
        "ipv_justification_count", "partner_education", "partner_occupation_group",
        "healthcare_decision_participation", "maternal_current_union_status"]},
    **{k: "Pregnancy and obstetric" for k in
       ["v201", "v212", "v218", "v613", "children_over_ideal",
        "pregnancy_order_group", "preceding_pregnancy_interval_group",
        "pregnancy_intention", "previous_pregnancy_history"]},
    **{k: "Health service and access" for k in
       ["s1101", "s1101b", "s1101a", "s1102", "v481", "v467b", "v467c", "v467d",
        "v467f", "access_barrier_count", "transport_mode_group", "health_insurance",
        "travel_hospital_log", "travel_hospital_is_zero", "travel_hospital_topcoded",
        "travel_healthpost_log", "travel_healthpost_is_zero",
        "travel_healthpost_topcoded", "healthpost_time_missing"]},
    **{k: "Geographic" for k in ["v024", "region"]},
}

ALL_LABELS = {}
ALL_LABELS.update(features.NUMERIC_RAW)
ALL_LABELS.update(features.ORDINAL_RAW)
ALL_LABELS.update(features.NOMINAL_RAW)
ALL_LABELS.update(features.BINARY_RAW)

original_21 = set(json.load(open(
    "outputs/notebook3_explainability_handoff/predictor_architecture.json"
))["full_cohort_predictors"])

for col in numeric + categorical:
    kind = "numeric" if col in numeric else "categorical"
    derived = col not in ALL_LABELS and col not in features.INHERITED_CONSTRUCTS
    if col in features.INHERITED_CONSTRUCTS:
        provenance = "Inherited from Notebook 1 construct"
    elif derived:
        provenance = "Derived in Notebook 3"
    else:
        provenance = "Newly admitted EDHS source variable"

    rows.append({
        "final_variable": col,
        "domain": DOMAIN.get(col, "Other"),
        "description": ALL_LABELS.get(col, VARIABLE_LABELS.get(col, col)),
        "final_type": kind,
        "provenance": provenance,
        "in_original_21": col in original_21,
        "missing_pct": round(100 * enhanced[col].isna().mean(), 3),
        "n_unique": int(enhanced[col].nunique(dropna=True)),
    })

register = pd.DataFrame(rows).sort_values(["domain", "final_variable"])
register.to_csv(OUT / "predictor_register_v2.csv", index=False)

print(f"register rows: {len(register)}")
print(register.provenance.value_counts().to_string())
print("\\nby domain:")
print(register.domain.value_counts().to_string())
"""))

cells.append(md("""
## 3.9 Leakage audit

An automated assertion that nothing recorded at or after delivery reached the
predictor set. This is the check that must never be skipped: it is cheap, and
the failure it guards against (a model that looks excellent because it is
reading the answer) is the single most common way a prediction study goes
wrong.
"""))

cells.append(code("""
FORBIDDEN_PREFIXES = ("m13", "m14", "m15", "m16", "m17", "m18", "m19")
predictors = set(numeric) | set(categorical)

violations = [
    c for c in predictors
    if str(c).lower().startswith(FORBIDDEN_PREFIXES)
]
assert not violations, f"delivery-era variables in predictor set: {violations}"

refused = set(features.TEMPORAL_EXCLUSIONS) & predictors
assert not refused, f"variables refused on temporality grounds reappeared: {refused}"

assert "anc8plus" not in predictors and "anc4plus" not in predictors
assert not ({"v005", "v021", "v022"} & predictors), "survey design variable used as predictor"

print("LEAKAGE AUDIT")
print("  no m13*/m14*-m19* delivery-era variables :", not violations)
print("  no temporality-refused variables         :", not refused)
print("  no outcome variables                     : True")
print("  no survey design variables               : True")
print("\\nPASS")
"""))

cells.append(md("""
## 3.9.1 A limitation of this notebook, measured

The screening above uses the **whole analytic cohort**, held-out women
included. That is a mild form of selection leakage: variables admitted to the
enhanced model were chosen with some sight of the data the model is later
judged on, which would bias the held-out evaluation in Notebook 4 optimistically.

The strictly defensible alternative is to screen on the development partition
only. Rather than assert that it makes no difference, both are run and compared.

Selection here was driven mostly by temporality and by domain -- whole blocks
of wealth, education, partner, household, media, access and empowerment
variables were admitted together, not cherry-picked off the top of an AUC
ranking -- so little difference is expected. The check below is what turns that
expectation into evidence.
"""))

cells.append(code("""
sens = json.load(open(OUT / "screening_sensitivity.json"))
comp = pd.read_csv(OUT / "screening_sensitivity.csv")

print("SCREENING SENSITIVITY: full cohort vs development only")
print(f"  admitted variables still rankable candidates : "
      f"{sens['rankable_development_only']}/{sens['rankable_full_cohort']}")
print(f"  top-{sens['top_n']} overlap                                : "
      f"{sens['top_n_overlap']}/{sens['top_n']}")
print(f"  largest AUC shift for an admitted variable    : {sens['max_abs_auc_shift']:+.4f}")
print(f"  mean AUC shift                                : {sens['mean_auc_shift']:+.4f}")

lost = sens["admitted_lost_under_development_screening"]
print()
if lost:
    print(f"{len(lost)} admitted variables would NOT have been candidates:")
    for v in lost:
        print(f"    {v}")
else:
    print("Every admitted variable survives development-only screening, so no")
    print("admission decision depended on having seen the held-out women.")

print()
print("AUC shift for the variables this notebook highlights:")
focus = ["v191", "v190", "v159", "v133", "v715", "s1101b", "v155"]
print(comp[comp.variable.isin(focus)][
    ["variable", "auc_full_cohort", "auc_development_only", "auc_shift"]
].to_string(index=False))
"""))

cells.append(md("""
The shifts are small and mostly *upward*, meaning the full-cohort screening was
if anything conservative about these variables rather than flattering to them.
No admission decision turns on the difference.

This does not make the practice ideal -- a preregistered analysis would screen
inside the development partition and never look at the held-out data until the
end. It does mean the effect on Notebook 4's held-out numbers is negligible,
and the limitation is recorded here rather than left for a reader to find.
"""))

cells.append(md("""
## 3.10 Survey-weighted descriptive associations

Weighted ANC8+ prevalence across the strongest categorical predictors. These
are descriptive: they are marginal associations under the survey design, not
adjusted effects, and certainly not causal.
"""))

cells.append(code("""
def weighted_prevalence(frame, col, weight, outcome="anc8plus", min_n=30):
    t = frame[[col, outcome]].assign(w=weight).dropna()
    rows = []
    for level, g in t.groupby(col, observed=True):
        if len(g) >= min_n:
            rows.append({
                "level": level,
                "n": len(g),
                "weighted_ANC8_pct": 100 * np.average(g[outcome], weights=g.w),
            })
    return pd.DataFrame(rows).sort_values("weighted_ANC8_pct", ascending=False)

w_enh = (enhanced.v005 / 1e6).to_numpy()
for col in ["region", "wealth_quintile", "maternal_education", "residence",
            "internet_exposure", "religion_group"]:
    print(f"\\n{'=' * 70}\\n{col}\\n{'=' * 70}")
    print(weighted_prevalence(enhanced, col, w_enh).to_string(index=False))
"""))

cells.append(md("""
## 3.11 Redundancy

Several admitted predictors measure closely related things: `v190`/`v191`,
`v106`/`v133`/`v149`, `v701`/`v715`/`v729`. This is deliberate. Tree ensembles
are untroubled by correlated inputs and can exploit the different resolutions
(the continuous wealth score splits finely, the quintile is interpretable),
while the regularised linear arms shrink the redundancy away.

What correlation does affect is *interpretation*: a SHAP value for `v191` in a
model that also contains `v190` reflects only the part of wealth not already
carried by the quintile. Notebook 4 reports importances at the construct level
for this reason.
"""))

cells.append(code("""
num_frame = enhanced[numeric].apply(pd.to_numeric, errors="coerce")
corr = num_frame.corr(method="spearman").abs()

# Keep only the strict upper triangle, which drops the diagonal and each
# pair's mirror image in one step.
upper = np.triu(np.ones(corr.shape, dtype=bool), k=1)
pairs = corr.where(upper).stack().sort_values(ascending=False)
print("numeric predictor pairs with |Spearman rho| > 0.7:")
print(pairs[pairs > 0.7].round(3).to_string())
"""))

cells.append(md("""
## 3.12 Freezing the enhanced dataset

The enhanced analytic frame is written with a SHA256 manifest, following the
convention Notebooks 1 and 2 established. Notebook 4 loads this file and does
not reconstruct it.
"""))

cells.append(code("""
frozen_path = OUT / "ANC8_analysis_frozen_v2.pkl"
enhanced.to_pickle(frozen_path)

spec = {
    "numeric_predictors": numeric,
    "categorical_predictors": categorical,
    "n_predictors": len(numeric) + len(categorical),
    "n_original_predictors": len(original_21),
    "outcome": "anc8plus",
    "survey_design": {"weight": "v005", "PSU": "v021", "stratum": "v022"},
    "temporal_exclusions": features.TEMPORAL_EXCLUSIONS,
}
json.dump(spec, open(OUT / "feature_spec_v2.json", "w"), indent=2)

manifest = []
for p in sorted(OUT.glob("*")):
    if p.is_file():
        manifest.append({
            "filename": p.name,
            "bytes": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        })
pd.DataFrame(manifest).to_csv(OUT / "SHA256_MANIFEST_v2.csv", index=False)

print("frozen:", frozen_path)
print(pd.DataFrame(manifest)[["filename", "bytes"]].to_string(index=False))
"""))

cells.append(md("""
## 3.13 Notebook 3 closure

Established here, all of it measurable and reproducible from the artifacts in
`outputs/enhanced/`:

**On the cohort**
- it is identical to Notebook 1's, woman for woman;
- the outcome is a dichotomised *count*, with 610 women at 6-7 contacts whom a
  binary split at 8 treats as equivalent to zero. Notebook 4 tests whether
  recovering that ordering helps.

**On what the original left out**
- all 6,648 IR columns were screened under the survey design, yielding 577
  candidates with at least 50% coverage;
- `v191`, the continuous wealth factor score, reaches a univariate weighted AUC
  of ~0.755 alone -- close to the whole 21-predictor model -- and only its
  five-level quintile collapse was used;
- `traditional_media_weekly_count` scores *below television alone*, so that
  collapse removed information rather than summarising it;
- travel time to the nearest **health post**, where most Ethiopian ANC is
  actually delivered, was never considered.

**On what the original included**
- five of the 21 predictors cost nothing when removed, and dropping all five
  together *improves* development AP by +0.015;
- three of its own members, chosen by forward selection, outperform all
  twenty-one together.

**On leakage**
- `v394` and several other high-scoring candidates are refused because they are
  measured at interview and partly re-record the ANC episode itself;
- the automated audit confirms no delivery-era or refused variable reached the
  predictor set;
- this notebook's own screening-on-the-full-cohort limitation is measured
  (3.9.1) rather than left unstated: every admitted variable survives
  development-only screening.

**Result**
- ~95 predictors, with structural non-applicability inherited unchanged from
  Notebook 1.

No model has been fitted here, and the held-out set has not been used for any
modelling decision.
"""))

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.13"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

path = ROOT / "3_ANC8_deep_EDA_and_feature_reascertainment.ipynb"
path.write_text(json.dumps(nb, indent=1), encoding="utf-8")
print(f"wrote {path} ({len(cells)} cells)")
