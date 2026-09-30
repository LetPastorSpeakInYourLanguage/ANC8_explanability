"""Build the reproduction folder: notebooks that rebuild the model library from the survey.

    python scripts/build_reproduction.py            # writes reproduction/
    python scripts/build_reproduction.py --no-ebm   # the three-model build: no explainable boosting track

reproduction/ is the study's hand-over for other researchers who hold the EDHS
2024-25 Individual Recode. Its notebooks, run in order, rebuild every result of
the model library from ETIR8AFL.DTA: the cohort and outcomes, the 21 predictors,
the candidate pool, the split, the duplicates, the four predictor sets, the tuned
logistic regression, random forest and XGBoost on every set and rung, their
calibrated versions and ensembles, the evaluation, the explanations and the
planner's levers. A parallel track does the same for explainable boosting.

Nothing in it is hand-written twice: the package is synced from src/anc8, the
stage scripts from scripts/, the cell code of the first notebook is the study's
own (notebook 1 at the repository root, with its paths made configurable), and
the study's results are written to reference/ for every notebook to check itself
against. The notebooks are written without outputs; execute them with
`python scripts/run_notebooks.py` (all of them, in order) or one at a time in Jupyter.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import nbformat as nbf
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "reproduction"

SCRIPTS = ["run_notebooks.py", "run_feature_value.py", "run_redundancy_analysis.py", "fit_library_models.py",
           "run_model_cards.py", "run_explainability.py", "run_scenarios.py", "run_regional_eda.py",
           "run_hyperparameter_ablation.py", "build_form_schema.py", "train_library.py"]

REQUIREMENTS = """\
# The analysis environment the study ran in. Newer versions will very likely work,
# but the check cells compare against the study's numbers, and XGBoost, LightGBM and
# explainable boosting can differ in the last digits across versions.
numpy==2.5.0
pandas==3.0.3
scipy==1.18.0
scikit-learn==1.9.0
statsmodels==0.15.0
xgboost==3.3.0
lightgbm==4.6.0
interpret==0.7.8
shap==0.52.0
optuna==5.0.0
joblib==1.5.3
threadpoolctl==3.6.0
matplotlib==3.11.0
pyarrow==25.0.1
python-docx==1.1.2
nbformat==5.10.4
nbclient==0.10.2
jupyter==1.1.1
"""


def md(text):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text):
    return nbf.v4.new_code_cell(text.strip("\n"))


SETUP = '''
# Settings for this notebook
QUICK = False        # True: a smoke run with 3 search trials per model; numbers will not match the study
FOLLOW_STUDY = True  # when a re-derived choice differs from the study's, carry the study's forward

import sys, json, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
here = Path.cwd()
sys.path.insert(0, str(here.parent / "src" if here.name.startswith("notebooks") else here / "src"))
from anc8 import repro
P = repro.setup(quick=QUICK)
QUICK = P.quick

import numpy as np
import pandas as pd
from anc8 import library as lib, tuning
'''


def write_nb(path: Path, cells):
    nb = nbf.v4.new_notebook()
    nb.cells = cells
    for i, c in enumerate(nb.cells):
        c.id = f"cell-{i:03d}"  # stable ids, so a rebuild changes only what changed
    nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                   "language_info": {"name": "python"}}
    path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, str(path))


# ======================================================================== notebooks
def nb00():
    return [md('''
# 00 · Start here

These notebooks rebuild the study's **model library** from the EDHS 2024-25 Individual
Recode: who is in the cohort, how the three outcomes and every predictor were made, how the
data were split, which predictors were kept, how each model was tuned and checked, and what
each model leans on. Run them in order; each one reads only what the earlier ones wrote, and
ends by checking its results against the study's (in `reference/`).

The study predicts whether a woman reaches **one or more** (ANC1+), **four or more** (ANC4+)
and **eight or more** (ANC8+) antenatal care contacts, from what is known before her care
starts. Three models are the core of the library, **logistic regression, random forest and
XGBoost**, each fitted on **four predictor sets** at **three rungs**. The `notebooks_ebm/`
track adds **explainable boosting** as a fourth model.

## Before you start

1. **The data.** Obtain `ETIR8AFL.DTA` (Ethiopia DHS 2024-25, Individual Recode, Stata) from
   The DHS Program and put it in `data/`. It is licensed to you and must not be shared;
   nothing in this folder contains survey rows, and everything the notebooks write stays in
   `outputs/`, `results/` and `quick/`, which are never committed.
2. **The environment.** Python 3.12 or 3.13, then `pip install -r requirements.txt`.
3. **The order.** The table below. The first run of a notebook is the only slow one: every
   model the library trains is saved, and a notebook that is run again skips what is done.

| Notebook | Does | Time (8 cores) |
|---|---|---|
| 01 | the cohort, the outcome ladder and the 21 predictors, from the survey file | 2 min |
| 02 | the candidate pool: every survey column screened, 95 admitted | 3 min |
| 03 | the held-out split and the development folds | under 1 min |
| 04 | a helper model for the selection steps (LightGBM on the 95) | 15 min per rung |
| 05 | near-duplicate predictors, and the clean pool of 86 | 5 min |
| 06 | the four predictor sets: full pool, the 21, the short set, the parsimonious set | 6 to 8 h |
| 07 | logistic regression, tuned on every set and rung | 20 min |
| 08 | random forest, tuned on every set and rung | 2 h |
| 09 | XGBoost, tuned on every set and rung | 1 h |
| 10 | calibrated versions and the two ensembles | 1 h |
| 11 | evaluation on the held-out women | 30 min |
| 12 | explanations: what each model leans on | 10 min |
| 13 | the planner's levers and the regions' drivers | 10 min |
| E1-E3 | explainable boosting: tuning, explanations, levers (optional) | 2 h |

Times are rough. Notebook 06 is the long one; it can take the study's predictor sets instead
of re-deriving them (see its first cell).

To run them all without opening Jupyter, from this folder:

```
python scripts/run_notebooks.py            # the core track
python scripts/run_notebooks.py --ebm      # and the explainable boosting track
python scripts/run_notebooks.py --from 07  # resume after a stop
python scripts/run_notebooks.py --quick    # a smoke run
```

Executed copies, with every table, figure and check, land in `executed/`.

## Two switches, at the top of every notebook

- `QUICK = True` runs the whole chain in about an hour with three search trials per model.
  The numbers will not match the study's; use it to check that everything runs.
- `FOLLOW_STUDY = True` (the default): where a re-derived choice (a selection step, a helper
  model's settings) differs from the study's, the notebook says so and carries the study's
  choice forward, so that the later notebooks reproduce the study's numbers exactly. Set it
  to `False` to carry your own results through instead.

## Folders

```
data/            put ETIR8AFL.DTA here
notebooks/       00-13, the core track
notebooks_ebm/   E1-E3, explainable boosting
src/anc8/        the analysis package every notebook uses
scripts/         the stage scripts some notebooks run
reference/       the study's results, for the checks
outputs/         what the notebooks write (analysis frames, tables, figures)
results/         the model library: one file per model, set and rung
```
'''), code('''
# Is the environment the one the study used, and is the survey file in place?
import importlib, sys
from pathlib import Path

here = Path.cwd()
project = here.parent if here.name.startswith("notebooks") else here
want = {}
for line in (project / "requirements.txt").read_text().splitlines():
    if "==" in line and not line.startswith("#"):
        name, v = line.split("==")
        want[name.strip()] = v.strip()

MODULE = {"scikit-learn": "sklearn", "python-docx": "docx"}
print(f"python {sys.version.split()[0]}")
for name, v in want.items():
    try:
        m = importlib.import_module(MODULE.get(name, name))
        got = getattr(m, "__version__", "?")
        print(f"  {name:14s} {got:10s} {'' if got == v else f'(the study used {v})'}")
    except ImportError:
        print(f"  {name:14s} MISSING    (pip install -r requirements.txt)")

dta = [p for p in (project / "data").glob("*") if p.name.lower() == "etir8afl.dta"]
print("\\nsurvey file:", dta[0] if dta else "NOT FOUND: put ETIR8AFL.DTA in data/")
''')]


# The study's notebook 1 ran on pandas 2. These are the edits it needs on pandas 3, each
# marked in the cell it changes; none changes a value.
PANDAS3 = [
    # relabelling a category: pandas 3 no longer adds the new label as a category itself
    ('anc8_working["partner_occupation_group"]\n    .replace({',
     'anc8_working["partner_occupation_group"]\n    .astype(object)  # pandas 3: relabel as text\n    .replace({'),
]

# Executed copies are shared, so no output may name a woman: the one audit that printed
# case ids numbers the women instead.
PRIVATE = [
    ("for _, row in audit_12.iterrows():", "for k, (_, row) in enumerate(audit_12.iterrows()):"),
    ("f\"\\ncaseid: {row['caseid']}\"", "f\"\\nwoman {k + 1} of {len(audit_12)}\""),
]


def nb01():
    """The study's notebook 1, cell for cell, with its paths made configurable."""
    src = json.loads((ROOT / "1_ANC8_outcome_and_predictor_ascertainment.ipynb").read_text(encoding="utf-8"))
    cells = [md('''
# 01 · The cohort, the outcome ladder and the 21 predictors

This notebook turns the survey file into the study's first analysis frame: one row per woman
whose most recent birth has a recorded number of antenatal care contacts, the outcome
ladder, the survey design, and the 21 predictors the study built by hand from the survey's
variables. Each predictor has its own section: the raw variable is audited, and the decision
on how to code it (which categories to merge, what missing means, what "not applicable"
means) is written down before it is made.

The code below is the study's own, cell for cell; only the file paths are set once, here.
It writes `outputs/ANC8_analysis_frozen.pkl` (the analysis frame), the predictor and outcome
registers, and a descriptive Table 1. The last cell checks the frame against the study's.

**Reads:** `data/ETIR8AFL.DTA` · **Writes:** `outputs/`
'''), code(SETUP + '''
from anc8 import cohorts
PROJECT = P.project
print("survey file:", cohorts.IR_FILE)
''')]
    study_path = re.compile(r'Path\(\s*r"D:\\MOH\\2026\\Data science\\Capstone\\ANC8"\s*\)')
    for c in src["cells"]:
        text = "".join(c["source"])
        if c["cell_type"] == "code" and "CHECK WHETHER THE LATER ANC8 CHECKPOINT" in text:
            # The study's copy of this notebook reads `anc8_final` here without creating
            # it: the checkpoint lived in the kernel from an earlier run. It is the working
            # frame as the cells above leave it; the fingerprint check at the end confirms it.
            cells.append(md('''
**Two last steps, and the analysis checkpoint.** The study's copy of this notebook does not
hold the cells for two steps it relies on below; they are restored here, and the fingerprint
check at the end of the notebook confirms that they reproduce the study's frame exactly:

- the occupation labels are written without spaces around the slash ("Sales/services");
- **`traditional_media_weekly_count`**, one of the 21, is the number of the three traditional
  media (newspaper, radio, television) the woman uses **at least once a week**, from 0 to 3.
  The audit just above shows the three cleaned exposure variables it counts.

The aligned working frame is then kept as `anc8_final`, the checkpoint the audit and the
export below start from.
'''))
            cells.append(code('''
for var in ["maternal_occupation_group", "partner_occupation_group"]:
    anc8_working[var] = anc8_working[var].astype(object).str.replace(" / ", "/", regex=False)

media_source_vars = ["newspaper_exposure", "radio_exposure", "television_exposure"]
anc8_working["traditional_media_weekly_count"] = sum(
    anc8_working[v].eq("At least once a week").astype(int) for v in media_source_vars
)
print(anc8_working["traditional_media_weekly_count"].value_counts().sort_index().to_string())

anc8_final = anc8_working.copy()
'''))
        if c["cell_type"] == "code":
            text = study_path.sub("PROJECT", text)
            for a, b in PANDAS3 + PRIVATE:
                text = text.replace(a, b)
            assert "row['caseid']" not in text
            text = text.replace('IR_FILE = PROJECT_ROOT / "ETIR8AFL.dta"', 'IR_FILE = cohorts.IR_FILE')
            assert "D:\\MOH" not in text, text[:200]
            text = _plain_comments(text)
            cells.append(code(text))
        else:
            cells.append(md(_plain(text)))
    cells += [md('''
## Handing on to the next notebooks

The 21 predictors and how each is typed, in the form the later notebooks read. The
typing (four numbers, three yes/no, fourteen categories) is the study's; the list
must be the one this notebook just built.
'''), code('''
arch = repro.reference("predictor_architecture.json")
repro.check("the 21 predictors are the study's, in the study's order",
            list(anc8_primary_predictors) == arch["full_cohort_predictors"])
handoff = PROJECT / "outputs" / "notebook3_explainability_handoff"
handoff.mkdir(parents=True, exist_ok=True)
(handoff / "predictor_architecture.json").write_text(json.dumps(arch, indent=2))
print(len(arch["full_cohort_predictors"]), "predictors written to", handoff / "predictor_architecture.json")
'''), md('''
## Checks against the study
'''), code('''
ref = repro.reference("fingerprints.json")
frame = pd.read_pickle(PROJECT / "outputs" / "ANC8_analysis_frozen.pkl")
repro.check("6,916 maternal-health records, 23 of them without a resolved count", len(frame) == 6916)
repro.check("the analysis frame is identical to the study's (content fingerprint)",
            repro.fingerprint(frame) == ref["analysis_frame_21"], repro.fingerprint(frame))
repro.report()
''')]
    return cells


def nb02():
    return [md('''
# 02 · The candidate pool

The 21 predictors of notebook 01 were chosen by reasoning about antenatal care. This notebook
asks the survey instead: every one of its 6,648 columns is screened against ANC8+ under the
survey design, and the admissible ones are added to the 21 to form the **candidate pool**.

Screening ranks, it does not select. A column is admitted on three grounds, in this order:

1. **Timing.** It must be known before antenatal care begins. Anything recorded at or after
   the delivery, and anything the antenatal care itself changes, is refused, however well it
   predicts. The refused variables and the reason for each are listed below; `v394` (visited a
   health facility in the last 12 months) is the clearest case, because an antenatal contact
   *is* a facility visit.
2. **Coverage.** Observed for at least half the women. Most of the file is birth-history
   slots filled for a handful of women.
3. **Meaning.** Whole blocks (wealth, education, partner, household, media, access,
   empowerment, barriers to care) are admitted together, with a few derived measures such as
   spousal gaps, counts and the log of travel time.

**Reads:** `data/ETIR8AFL.DTA`, `outputs/ANC8_analysis_frozen.pkl`
**Writes:** `outputs/enhanced/ANC8_analysis_frozen_v2.pkl` (the pool frame),
`feature_spec_v2.json`, `candidate_screening.csv`, `predictor_register_v2.csv`, `birth_timing.parquet`
'''), code(SETUP + '''
from anc8 import cohorts, features, screening
OUT = P.outputs / "enhanced"
OUT.mkdir(parents=True, exist_ok=True)
'''), md('''
## The cohort, rebuilt from the survey file

Women on the maternal-health roster with a resolved contact count (`m14_1` from 0 to 97;
98, "don't know", is unresolved). The rebuilt cohort must be the same women as notebook 01's.
'''), code('''
reader = pd.read_stata(cohorts.IR_FILE, iterator=True)
VARIABLE_LABELS = reader.variable_labels()
ir = pd.read_stata(cohorts.IR_FILE, convert_categoricals=False)
print("survey file:", ir.shape[0], "women x", ir.shape[1], "columns")

cohort = ir[ir.m14_1.notna() & ir.m14_1.between(0, 97)].copy()
y = (cohort.m14_1 >= 8).astype(int).to_numpy()
w = (cohort.v005 / 1e6).to_numpy()
first = pd.read_pickle(P.outputs / "ANC8_analysis_frozen.pkl")
first = first[first.anc8plus.notna()].copy()
repro.check("the cohort is notebook 01's, woman for woman", set(cohort.caseid) == set(first.caseid), f"{len(cohort):,} women")
print(f"weighted ANC8+ prevalence: {np.average(y, weights=w):.1%}")
'''), md('''
## Screening every column

For each column: the survey-weighted AUC of the raw variable as a score (which assumes the
variable is ordered), the spread of ANC8+ prevalence across its categories (which catches
unordered variables such as region), and how often it is missing.
'''), code('''
screen = screening.screen(cohort, VARIABLE_LABELS, y, w)
screen.to_csv(OUT / "candidate_screening.csv", index=False)
print(screen.screen_status.value_counts().to_string())
print("\\nThe 20 strongest columns observed for at least half the women:")
print(screen[screen.screen_status == "candidate"].head(20)[["variable", "label", "missing", "weighted_auc", "prevalence_spread"]].to_string(index=False))
'''), md('''
## Refused on timing

Variables that predict well because they partly record the antenatal care itself.
'''), code('''
for var, reason in features.TEMPORAL_EXCLUSIONS.items():
    auc = screen.loc[screen.variable == var, "weighted_auc"]
    print(f"{var:8s} AUC {auc.iloc[0] if len(auc) and pd.notna(auc.iloc[0]) else float('nan'):.3f}  {VARIABLE_LABELS.get(var, '')}")
    print(f"         {reason}")
'''), md('''
## Assembling the pool

The 21 predictors of notebook 01 are carried over unchanged (their careful handling of
"not applicable" stays), the admitted survey variables are added, and a few measures are
derived: spousal education and age gaps, counts of decisions, of attitudes and of barriers,
an asset index, and travel time treated as a log with flags for zero, top-coding and missing.
Travel time to a health post is missing for about a quarter of women by design (no post in
range), so it carries a `healthpost_time_missing` flag instead of an invented value.
'''), code('''
pool_frame, numeric, categorical = features.assemble(first, ir)
print(f"pool frame: {pool_frame.shape[0]:,} women x {pool_frame.shape[1]} columns")
print(f"{len(numeric)} numeric and {len(categorical)} categorical predictors: {len(numeric) + len(categorical)} in all")

# the leakage audit: nothing from the delivery or after, nothing refused, no outcome or design variable
FORBIDDEN = ("m13", "m14", "m15", "m16", "m17", "m18", "m19")
predictors = set(numeric) | set(categorical)
repro.check("no delivery-era variable among the predictors", not [c for c in predictors if c.lower().startswith(FORBIDDEN)])
repro.check("no variable refused on timing", not (set(features.TEMPORAL_EXCLUSIONS) & predictors))
repro.check("no outcome or survey-design variable", not ({"anc1plus", "anc4plus", "anc8plus", "v005", "v021", "v022"} & predictors))
'''), code('''
pool_frame.to_pickle(OUT / "ANC8_analysis_frozen_v2.pkl")
arch = json.load(open(P.outputs / "notebook3_explainability_handoff" / "predictor_architecture.json"))
spec = {"numeric_predictors": numeric, "categorical_predictors": categorical,
        "n_predictors": len(numeric) + len(categorical), "n_original_predictors": len(arch["full_cohort_predictors"]),
        "outcome": "anc8plus", "survey_design": {"weight": "v005", "PSU": "v021", "stratum": "v022"},
        "temporal_exclusions": features.TEMPORAL_EXCLUSIONS}
json.dump(spec, open(OUT / "feature_spec_v2.json", "w"), indent=2)

# the timing of each woman's most recent birth (for age at the birth and the 24-month cohort)
timing = cohorts.birth_timing()
print("birth timing for", len(timing), "women")
'''), md('''
## The women who started antenatal care, and when

One lever of notebook 13, an earlier first visit, needs to know when care began. The survey
records the timing of the first contact in weeks (`m13a_1` from 100) or months (from 200). A
first contact at 12 weeks or earlier, or in the first three months, is **early**; later is
not; "don't know" (998) and women with no contact stay unresolved and are left out. These
5,001 women are the ANC-entry cohort, on the same split as everyone else.
'''), code('''
t = ir[["caseid", "m13a_1"]].copy()
t["caseid"] = t.caseid.astype(str)
weeks, months = t.m13a_1.between(100, 199), t.m13a_1.between(200, 299)
t["early_anc"] = np.nan
t.loc[weeks, "early_anc"] = (t.m13a_1[weeks] - 100 <= 12).astype(float)
t.loc[months, "early_anc"] = (t.m13a_1[months] - 200 <= 3).astype(float)
full = cohorts.load("full")[["caseid", "partition"]]
entry = full.merge(t[t.early_anc.notna()], on="caseid", how="inner")
entry = entry.rename(columns={"partition": "entry_partition"})[["caseid", "early_anc", "entry_partition"]]
entry.to_csv(OUT / "anc_entry.csv", index=False)
print(f"{len(entry):,} women started care with a known timing; {entry.early_anc.mean():.0%} of them early (unweighted)")
'''), md('''
## Checks against the study
'''), code('''
ref = repro.reference("fingerprints.json")
repro.check("95 predictors", spec["n_predictors"] == 95)
e = cohorts.entry_table().sort_values("caseid").reset_index(drop=True)
repro.check("the ANC-entry cohort is the study's (content fingerprint)", repro.fingerprint(e) == ref["anc_entry"], f"{len(e):,} women")
repro.check("the pool frame is identical to the study's (content fingerprint)",
            repro.fingerprint(pool_frame) == ref["analysis_frame_pool"], repro.fingerprint(pool_frame))
repro.report()
''')]


def nb03():
    return [md('''
# 03 · The held-out women and the development folds

Every number the study reports for a model comes from women the model never saw. A fifth of
the survey's **clusters** (the villages and neighbourhoods the survey visited) are set aside
before anything is fitted: 1,375 women. The rest, 5,518 women, are the **development** set,
split again into five folds for tuning.

Why clusters and not women: women in one cluster share a health post, a road and a season of
fieldwork. Splitting them between development and held-out would let a model learn the
cluster and look better than it is. The folds keep clusters whole for the same reason, and
keep each survey stratum (region by urban/rural) spread across the folds.

The split is drawn once, from a fixed seed, and every later notebook, every model, set and
rung, uses exactly these women and these folds. That is what makes the comparisons fair.
'''), code(SETUP + '''
from anc8 import cohorts, design
dev, held = lib.partitions(base=True)   # also checks the split and folds against the study's digests
folds = design.make_psu_stratum_folds(dev)
print(f"development: {len(dev):,} women in {dev.v021.nunique()} clusters")
print(f"held-out:    {len(held):,} women in {held.v021.nunique()} clusters")
repro.check("no cluster is on both sides", not (set(dev.v021) & set(held.v021)))
'''), code('''
w = dev.v005 / 1e6
table = pd.DataFrame({
    "women": folds.value_counts().sort_index(),
    "clusters": dev.groupby(folds.to_numpy()).v021.nunique(),
    **{f"{r} (weighted)": dev.assign(f=folds.to_numpy(), w=w).groupby("f").apply(lambda g, r=r: np.average(g[r], weights=g.w))
       for r in lib.RUNGS},
})
table.index.name = "fold"
print(table.round(3).to_string())
print("\\nEach fold has a similar share reaching each rung, so no fold is easier than another.")
repro.check("the split and folds are the study's (digests)", True, "checked when the partition was loaded")
repro.report()
''')]


def nb04():
    return [md('''
# 04 · A helper model for the selection steps

Two later steps search over predictors: notebook 05 weighs near-duplicate predictors, and
notebook 06 grows the parsimonious set one predictor at a time. Both need a model that is
fast enough to refit thousands of times, so the study uses **LightGBM** as a helper, tuned
once per rung on all 95 predictors of the pool. It is a tool for the searches, not one of the
library's models.

Tuning, here and everywhere in the study, is the same procedure:

- **Optuna's TPE sampler** with a fixed seed (2026), a fixed number of trials (60 for LightGBM);
- each trial is scored by **survey-weighted average precision, out of fold**, over the five
  development folds of notebook 03;
- inside each fold the survey weights are rescaled to average one, so their size does not
  interact with the model's regularisation;
- the held-out women are not touched.

**Writes:** `outputs/enhanced/<rung>/best_hyperparameters.json`
'''), code(SETUP + '''
RETUNE = True   # False: skip the search and use the study's settings (about 45 minutes saved)
study = repro.reference("selector_lightgbm.json")
'''), code('''
for rung in lib.RUNGS:
    d = lib.data("pool95", rung)
    if RETUNE:
        params, best = tuning.tune("LightGBM", d.X_dev, d.y_dev, d.w_dev, d.splits, d.numeric, d.categorical,
                                   n_trials=tuning.TRIALS["LightGBM"])
        same = params == study[rung]
        repro.check(f"{rung}: the search finds the study's settings", same, "" if same else f"found {params}")
        use = study[rung] if (FOLLOW_STUDY and not same) else params
    else:
        use = study[rung]
    out = P.outputs / "enhanced" / rung
    out.mkdir(parents=True, exist_ok=True)
    json.dump({"LightGBM": use}, open(out / "best_hyperparameters.json", "w"), indent=2)
    print(rung, use)
repro.report()
''')]


def nb05():
    return [md('''
# 05 · Near-duplicate predictors, and the clean pool

Several of the 95 predictors carry the same information twice: wealth as a quintile and as the
continuous score's quintile, education in four levels and in single years, region as a code
and as a label, travel time in minutes and as its log. For explanation this matters: a model
that splits wealth between two copies shows each copy as half as important as wealth is.

Every pair of predictors is scored on the development women (Spearman correlation for numbers,
Theil's U for categories). A pair above 0.95 is a **near-duplicate**, and one of the two is
dropped: 10 of the 95. Two more pairs are exact one-to-one recodings between the 21's own
constructs and pool columns (household size, travel time to a hospital); the pool keeps the
21's member of each. The result is the **clean pool of 86 predictors**, the largest of the four
predictor sets.

**Writes:** `outputs/enhanced/redundancy/`
'''), code(SETUP), code('''
repro.run_script("run_redundancy_analysis.py")
'''), code('''
study = repro.reference("predictor_sets.json")
summary = json.load(open(P.outputs / "enhanced" / "redundancy" / "redundancy_summary.json"))
repro.check("the same 10 near-duplicates are dropped", sorted(summary["dropped"]) == sorted(study["duplicates_dropped"]),
            ", ".join(summary["dropped"]))

# the two exact recodings the 21's constructs make of pool columns
frame = lib.raw_frame()
for a, b in lib.CONSTRUCT_TWINS.items():
    s = frame[[a, b]]
    one_to_one = s.groupby(a, dropna=False)[b].nunique(dropna=False).max() == 1 and s.groupby(b, dropna=False)[a].nunique(dropna=False).max() == 1
    repro.check(f"{a} is an exact recoding of {b}", one_to_one)

num, cat = lib.clean_pool()
repro.check("the clean pool has 86 predictors", len(num) + len(cat) == 86, f"{len(num)} numeric, {len(cat)} categorical")
repro.report()
''')]


def nb06():
    return [md('''
# 06 · The four predictor sets

The study's first question is how many predictors a model needs. Every model is fitted on four
sets, from the largest to the smallest, and compared on the same held-out women:

| Set | What it is |
|---|---|
| **Full pool** | the clean pool of 86 (notebook 05) |
| **21-predictor set** | the 21 predictors built in notebook 01 |
| **Short set** | the predictors that clear a strict bar in repeated forward selection |
| **Parsimonious set** | a short list chosen for a web form, by forward selection with the helper model |

**The short set.** Starting from nothing, the predictor that most raises the out-of-fold AP of a
lightly regularised logistic regression is added, over five different fold seeds. A step is
kept only if it adds at least 0.005 AP on average **and** helps on at least four of the five
seeds. Tier 1 is the steps until 90% of the full pool's gain over chance is reached; Tier 2 the
remaining kept steps. The short set is Tier 1 plus Tier 2. Holding the model fixed and simple
is deliberate: the question is which variables are worth collecting, not which model is best.

**The parsimonious set.** Greedy forward selection with the helper LightGBM of notebook 04 (at
most 300 trees), on out-of-fold AP. The ANC8+ search was the study's first: all 95 candidates
at every step, up to ten steps. It showed how much such a search overfits (its own development
AP ran far above what the list scored on held-out women), so the searches for ANC1+ and ANC4+
first pre-screen to the 30 strongest candidates and stop at eight predictors. Both versions are
reproduced exactly as they ran. A predictor the search chose that notebook 05 found to be a
duplicate is replaced by the copy the clean pool keeps.

**Time.** The short set takes about 30 minutes per rung. The parsimonious search takes about
four hours for ANC8+ (every candidate at every step) and one to two hours each for ANC1+ and
ANC4+. Set `RESELECT = False` to take the study's sets and skip both searches.

**Writes:** `outputs/feature_value/full/<rung>/summary.json`, `outputs/enhanced/<rung>/parsimonious_spec.json`
'''), code(SETUP + '''
from anc8 import parsimony
RESELECT = not QUICK   # False: take the study's sets and skip both searches
study = repro.reference("predictor_sets.json")
'''), md('''
## The short set, per rung
'''), code('''
for rung in lib.RUNGS:
    out = P.outputs / "feature_value" / "full" / rung
    if RESELECT:
        repro.run_script("run_feature_value.py", "--cohort", "full", "--outcome", rung, "--stages", "2", "--bootstrap", "0")
        s = json.load(open(out / "summary.json"))
        got = {"tier1": s["tier1"], "tier2": s["tier2"]}
        same = got == study["short_tiers"][rung]
        repro.check(f"{rung}: the short set is the study's", same, "" if same else str(got))
        if FOLLOW_STUDY and not same:
            s.update(study["short_tiers"][rung]); json.dump(s, open(out / "summary.json", "w"), indent=2)
    else:
        out.mkdir(parents=True, exist_ok=True)
        json.dump(study["short_tiers"][rung], open(out / "summary.json", "w"), indent=2)
    s = json.load(open(out / "summary.json"))
    print(f"{rung}: tier 1 {s['tier1']}, tier 2 {s['tier2']}")
'''), md('''
## The parsimonious set, per rung
'''), code('''
for rung in lib.RUNGS:
    out = P.outputs / "enhanced" / rung
    if RESELECT:
        d = lib.data("pool95", rung)
        best = json.load(open(out / "best_hyperparameters.json"))["LightGBM"]
        prescreen, steps = parsimony.SETTINGS[rung]
        chosen, path = parsimony.forward(d.X_dev, d.y_dev, d.w_dev, d.splits, d.numeric, d.categorical,
                                         parsimony.selector_params(best), prescreen=prescreen, max_steps=steps)
        same = chosen == study["pars_raw"][rung]
        repro.check(f"{rung}: the parsimonious search picks the study's list", same, "" if same else str(chosen))
        if FOLLOW_STUDY and not same:
            chosen = study["pars_raw"][rung]
    else:
        chosen = study["pars_raw"][rung]
    json.dump({"predictors": chosen, "base_model": "LightGBM"}, open(out / "parsimonious_spec.json", "w"), indent=2)
'''), md('''
## The four sets
'''), code('''
lib.predictors.cache_clear()
rows = []
for s in lib.SETS:
    for r in lib.RUNGS:
        num, cat = lib.predictors(s, r)
        rows.append({"set": lib.SET_LABEL[s], "rung": r, "predictors": len(num) + len(cat),
                     "which": ", ".join(list(num) + list(cat)) if len(num) + len(cat) <= 10 else "…"})
        repro.check(f"{s}/{r}: the predictors are the study's",
                    sorted(list(num) + list(cat)) == sorted(study["sets"][s][r]))
print(pd.DataFrame(rows).to_string(index=False))
repro.report()
''')]


def tuning_nb(num: str, model: str, blurb: str, pre: str) -> list:
    return [md(f'''
# {num} · {model}

{blurb}

**Preparation.** {pre}

**Tuning** is the study's single procedure (notebook 04): Optuna's TPE sampler, seed 2026, a fixed
number of trials, each scored by survey-weighted average precision out of fold over the five
development folds, with survey weights rescaled to average one inside each fold. The search
space and the budget are printed below. After the search, the best settings are refitted on all
5,518 development women, and the held-out women are scored **once**. The operating threshold
(for sensitivity and specificity) is chosen on the development predictions only.

The model is tuned separately on every predictor set at every rung: 12 fits, each saved to
`results/<set>/<rung>/{model}.npz` with its out-of-fold and held-out predictions and its
settings. A cell that is already saved is skipped, so the notebook can be stopped and resumed.
'''), code(SETUP + f'''
MODEL = "{model}"
FOLD_JOBS = 5   # folds fitted in parallel; lower it on a machine with few cores
'''), code('''
# The search space: each setting, its range, and whether it is searched on a log scale.
from anc8 import models as zoo
class Space:
    def __init__(self): self.rows = []
    def suggest_float(self, n, lo, hi, log=False, step=None): self.rows.append((n, lo, hi, "log" if log else "")); return lo
    def suggest_int(self, n, lo, hi, step=1, log=False): self.rows.append((n, lo, hi, f"step {step}")); return lo
    def suggest_categorical(self, n, ch): self.rows.append((n, ch, "", "one of")); return ch[0]
sp = Space(); zoo.suggest(sp, MODEL)
print(pd.DataFrame(sp.rows, columns=["setting", "from", "to", ""]).to_string(index=False))
print(f"\\n{tuning.TRIALS[MODEL]} trials per predictor set and rung")
'''), code('''
for s in lib.SETS:
    for r in lib.RUNGS:
        job = lib.Job("tune", s, r, MODEL, MODEL)
        if lib.is_done(P.results, job):
            print(f"{job.id}: already done")
            continue
        lib.run(job, P.results, fold_jobs=FOLD_JOBS)
'''), md('''
## Results, and the check against the study
'''), code('''
res = repro.compare_cells(P.results, [MODEL])
print(res.pivot_table(index="set", columns="rung", values="held_AP").round(3).to_string())
repro.report()
''')]


def nb10(lineup="three"):
    models = '["Logistic regression", "Random Forest", "XGBoost"]'
    return [md('''
# 10 · Calibrated versions and the two ensembles

**Calibration.** A model's scores rank women well but may be too confident or too cautious as
chances. Each model gets two recalibrated versions: **isotonic** (a flexible step map) and
**Platt** (a logistic map, which keeps the ranking). To avoid scoring a calibrator on the data it
was fitted to, calibration is **nested**: inside each development fold, the model is fitted on
part of the fold's training women and the calibrator on the rest; the held-out women get the
calibrator fitted on the model's out-of-fold predictions.

**Stacked ensemble.** A logistic regression that blends the models' out-of-fold predictions.

**Cumulative-link ensemble.** The outcome is a threshold on a count of contacts. The best model
(by development AP) is refitted at several contact thresholds (1, 2, 3, 4, 5, 6, 8, 10), the
curves are forced to fall as the threshold rises, and they are pooled with more weight near
the target, then mapped back to a chance with an isotonic fit on the development women.

The ensembles here are built from the three core models. The explainable boosting track builds
the same two from all four.
'''), code(SETUP + f'''
MODELS = {models}
'''), code('''
for s in lib.SETS:
    for r in lib.RUNGS:
        for m in MODELS:
            for method in lib.CALIBRATIONS:
                job = lib.Job("calib", s, r, lib.calibrated_name(m, method), m)
                if not lib.is_done(P.results, job):
                    lib.run(job, P.results)
for job in lib.lineup_jobs("three"):
    if not lib.is_done(P.results, job):
        lib.run(job, P.results)
'''), code('''
cal = [lib.calibrated_name(m, c) for m in MODELS for c in lib.CALIBRATIONS]
repro.compare_cells(P.results, cal)
res = repro.compare_cells(P.results, [lib.ensemble_name("stack", "three"), lib.ensemble_name("cumlink", "three")])
print(res[["set", "rung", "model", "held_AP"]].round(3).to_string(index=False))
repro.report()
''')]


def nb11():
    return [md('''
# 11 · Evaluation on the held-out women

Everything here is measured on the 1,375 held-out women, with their survey weights, and every
interval comes from resampling **whole clusters within their strata** (500 times), so it
reflects the survey's design.

For each model, predictor set and rung: average precision against chance (the share reaching
the rung), AUROC, the Brier score, calibration (slope and intercept), the share of the women one
is looking for who sit in the top fifth of the ranking, sensitivity and specificity at the
threshold chosen on the development women, AUROC within regions, wealth, education and
residence groups, the difference from the best model and from logistic regression with its
paired interval, and the net benefit across risk thresholds (decision curve).

Two further checks: every model is refitted from its saved settings and must reproduce its
saved predictions exactly, and the tuning is examined: what the search gained over the model's
default settings, and which settings mattered.
'''), code(SETUP + '''
MODELS = ["Logistic regression", "Random Forest", "XGBoost"]
'''), code('''
repro.run_script("fit_library_models.py", "--root", P.results, "--lineup", "three")
repro.run_script("run_hyperparameter_ablation.py", "--root", P.results, "--models", *MODELS)
repro.run_script("run_explainability.py")   # the cards show what each model leans on (notebook 12)
repro.run_script("run_model_cards.py", "--library", P.results, "--lineup", "three", *(["--quick"] if QUICK else []))
'''), md('''
## How many predictors: the four sets against each other

Held-out average precision of each model on each set. The study's finding: for ANC1+ and ANC4+
the full pool is best; for ANC8+ the short set does as well as the pool and the 21.
'''), code('''
cards = json.load(open(P.outputs / "model_cards" / "model_cards.json"))
rows = []
for key, by in cards["cards"].items():
    fam = cards["families"][key]
    for rung, c in by.items():
        rows.append({"set": lib.SET_LABEL[fam["set"]], "model": fam["name"], "rung": rung, "AP": c["ap"],
                     "AP 95%": f"{c['ap_ci'][0]:.3f}–{c['ap_ci'][1]:.3f}", "AUROC": c["auroc"], "slope": c["slope"]})
cardtab = pd.DataFrame(rows)
base = cardtab[cardtab.model.isin(MODELS)]
print(base.pivot_table(index=["rung", "model"], columns="set", values="AP").round(3).to_string())
'''), code('''
import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 3, figsize=(13, 3.6), sharey=False)
for ax, rung in zip(axes, ["anc1", "anc4", "anc8"]):
    t = base[base.rung == rung].pivot_table(index="set", columns="model", values="AP")
    t.plot.bar(ax=ax, rot=0, width=0.75, legend=(rung == "anc8"))
    ax.set_title(rung.upper().replace("ANC", "ANC") + "+"); ax.set_xlabel(""); ax.set_ylim(t.min().min() - 0.02, t.max().max() + 0.01)
axes[0].set_ylabel("held-out average precision")
plt.tight_layout(); plt.show()
'''), md('''
## Every model on the full pool, with intervals
'''), code('''
print(cardtab[cardtab.set == "Full pool"].sort_values(["rung", "AP"], ascending=[True, False])
      [["rung", "model", "AP", "AP 95%", "AUROC", "slope"]].round(3).to_string(index=False))
'''), md('''
## What tuning bought
'''), code('''
for rung in lib.RUNGS:
    a = pd.read_csv(P.outputs / "library" / "tuning" / f"ablation_pool_{rung}.csv")
    g = a[a.parameter.isin(["(library defaults)", "(tuned optimum)"])].pivot_table(index="model", columns="parameter", values="AP")
    g["gain"] = g["(tuned optimum)"] - g["(library defaults)"]
    print(rung); print(g.round(4).to_string(), "\\n")
repro.compare_cells(P.results, MODELS)
repro.report()
''')]


def nb12():
    return [md('''
# 12 · What each model leans on

Each fitted model is explained on the held-out women, with their survey weights:

- **Logistic regression** is additive: its log-odds is a sum over predictors, so a woman's
  contribution from a predictor is its coefficients times her values, measured from the
  weighted average woman. The split is exact.
- **Random forest and XGBoost** are explained by **TreeSHAP**, the exact Shapley attribution for
  a tree ensemble (probability units for the forest, log-odds for XGBoost).

A predictor's importance is its weighted mean absolute contribution; its **share** is that over
the model's total, which makes the models comparable even though their units differ. The
agreement table lists, per set and rung, each predictor's share under every model and how many
models put it in their top five; the concordance table is the rank correlation between models.

**Writes:** `outputs/explain/importance.csv`, `effects.json`, `agreement.csv`, `concordance.csv`
'''), code(SETUP), code('''
# notebook 11 already computed them for the model cards
if not (P.outputs / "explain" / "importance.csv").exists():
    repro.run_script("run_explainability.py")
'''), code('''
agree = pd.read_csv(P.outputs / "explain" / "agreement.csv")
models = [m for m in ["Logistic regression", "Random Forest", "XGBoost", "Explainable Boosting"] if m in agree]
for rung in lib.RUNGS:
    print(rung, "· full pool: the ten predictors the models agree on most")
    print(agree[(agree.set == "pool") & (agree.rung == rung)].head(10)[["predictor", *models, "mean_rank", "top5_models"]].round(3).to_string(index=False), "\\n")
print(pd.read_csv(P.outputs / "explain" / "concordance.csv").query("set == 'pool'").round(2).to_string(index=False))
'''), code('''
# The direction: each model's average contribution from the wealth quintile, by quintile, at ANC8+
# (log-odds for logistic regression and XGBoost, probability for the random forest)
eff = json.load(open(P.outputs / "explain" / "effects.json"))
order = ["Poorest", "Poorer", "Middle", "Richer", "Richest"]
table = pd.DataFrame({m: {r["level"]: r["effect"] for r in eff["pool"]["anc8plus"][m]["wealth_quintile"]} for m in models})
print(table.reindex(order).round(3).to_string())
repro.compare_table(pd.read_csv(P.outputs / "explain" / "importance.csv"), "explain_importance.csv",
                    keys=["set", "rung", "model", "predictor"], value="share", label="every predictor's share, per model")
repro.report()
''')]


def nb13():
    return [md('''
# 13 · The planner's levers, and why regions differ

**Levers.** A lever is something a health system can change, written as an edit to each
woman's record: a health post within 30 minutes, a hospital within an hour, distance and cost
no longer a big problem, health insurance, weekly radio health messages, every pregnancy
wanted, women sharing household decisions. Every woman is re-scored by logistic regression on
the full pool with the lever applied, and the average change in her predicted chance, by
region, is the lever's weight (g-computation). Women already in the better state are unchanged.
All 128 combinations of the seven levers are scored, so any mix of coverages combines exactly.
An eighth lever, an earlier first visit, uses a model fitted on the women who started care.
Intervals resample whole clusters with the model held fixed. These are associations: what the
model expects if circumstances changed, not what a programme would cause.

**Why a region differs.** Logistic regression is additive, so the gap between a region's
average predicted log-odds and the country's splits exactly across predictors, then sums to
planning concepts (access, insurance, wealth, education, and so on).
'''), code(SETUP), code('''
repro.run_script("run_scenarios.py", "--models", "logistic", *(["--quick"] if QUICK else []))
repro.run_script("run_regional_eda.py", "--models", "logistic")
'''), code('''
s = json.load(open(P.outputs / "scenarios" / "scenarios.json"))
keys = [l["key"] for l in s["levers"]] + ["all seven"]
nat = {r: s["by_model"]["logistic"]["rungs"][r]["gain"][-1] for r in ("anc1", "anc4", "anc8")}
print("Change in the share reaching each rung if every eligible woman is reached (points, Ethiopia):")
print(pd.DataFrame({r: [v * 100 for v in g] for r, g in nat.items()}, index=keys).round(2).to_string())
drv = pd.read_csv(P.outputs / "regional" / "drivers_concepts_by_region.csv")
print("\\nWhy Somali's ANC8+ differs from Ethiopia's (log-odds, by concept):")
print(drv[(drv.model == "logistic") & (drv.rung == "anc8") & (drv.region == "Somali")].sort_values("contribution")[["label", "contribution"]].round(3).to_string(index=False))
ref = repro.reference("levers_national.json")["logistic"]
gap = max(abs(a - b) for r in ref for a, b in zip(ref[r], nat[r]))
repro.check("the national lever effects are the study's", gap < 1e-9, f"largest difference {gap:.1e}")
repro.report()
''')]


# ------------------------------------------------------------------ explainable boosting track
def ebm_nbs():
    e1 = [md('''
# E1 · Explainable boosting: tuning, calibration and the four-model ensembles

**Explainable boosting** (EBM) is gradient boosting kept additive: it learns one curve per
predictor, and, when the tuning allows, a few curves for pairs of predictors. Its prediction is
the sum of those curves, so every prediction splits exactly across predictors, as logistic
regression's does, but the curves can bend (a distance that matters up to an hour and then
stops mattering, say). This track adds it as the library's fourth model.

Everything is done exactly as for the three core models: the same folds, weights, objective and
held-out women; the same nested calibration; and the two ensembles, now built from all four.
Run the core track (00-10) first.
'''), code(SETUP + '''
MODEL = "Explainable Boosting"
FOLD_JOBS = 5
'''), code('''
from anc8 import models as zoo
class Space:
    def __init__(self): self.rows = []
    def suggest_float(self, n, lo, hi, log=False, step=None): self.rows.append((n, lo, hi, "log" if log else "")); return lo
    def suggest_int(self, n, lo, hi, step=1, log=False): self.rows.append((n, lo, hi, f"step {step}")); return lo
    def suggest_categorical(self, n, ch): self.rows.append((n, ch, "", "one of")); return ch[0]
sp = Space(); zoo.suggest(sp, MODEL)
print(pd.DataFrame(sp.rows, columns=["setting", "from", "to", ""]).to_string(index=False))
print(f"\\n{tuning.TRIALS[MODEL]} trials per predictor set and rung")
'''), code('''
for s in lib.SETS:
    for r in lib.RUNGS:
        job = lib.Job("tune", s, r, MODEL, MODEL)
        if not lib.is_done(P.results, job):
            lib.run(job, P.results, fold_jobs=FOLD_JOBS)
        for method in lib.CALIBRATIONS:
            cj = lib.Job("calib", s, r, lib.calibrated_name(MODEL, method), MODEL)
            if not lib.is_done(P.results, cj):
                lib.run(cj, P.results)
for job in lib.lineup_jobs("four"):
    if not lib.is_done(P.results, job):
        lib.run(job, P.results)
repro.run_script("fit_library_models.py", "--root", P.results, "--lineup", "four")
'''), code('''
repro.compare_cells(P.results, [MODEL] + [lib.calibrated_name(MODEL, c) for c in lib.CALIBRATIONS])
res = repro.compare_cells(P.results, [lib.ensemble_name("stack", "four"), lib.ensemble_name("cumlink", "four")])
print(repro.compare_cells(P.results, [MODEL]).pivot_table(index="set", columns="rung", values="held_AP").round(3).to_string())
repro.report()
''')]
    e2 = [md('''
# E2 · What explainable boosting leans on

The explanations of notebook 12, now with explainable boosting beside the three core models.
Its shares come from its own curves, exactly; a pair term's contribution is split equally
between its two predictors. The **shape functions** below are the curves themselves: what the
model adds to a woman's log-odds at each value of a predictor, which is what makes the model
readable.
'''), code(SETUP), code('''
repro.run_script("run_explainability.py")
# the model cards again, now with all four models, their calibrated versions and the four-model ensembles
repro.run_script("run_model_cards.py", "--library", P.results, "--lineup", "four", *(["--quick"] if QUICK else []))
'''), code('''
agree = pd.read_csv(P.outputs / "explain" / "agreement.csv")
models = ["Logistic regression", "Random Forest", "XGBoost", "Explainable Boosting"]
print(agree[(agree.set == "pool") & (agree.rung == "anc8plus")].head(12)[["predictor", *models, "mean_rank"]].round(3).to_string(index=False))
print(pd.read_csv(P.outputs / "explain" / "concordance.csv").query("set == 'pool' and (a == 'Explainable Boosting' or b == 'Explainable Boosting')").round(2).to_string(index=False))
'''), code('''
import joblib, matplotlib.pyplot as plt
b = joblib.load(P.outputs / "library" / "models" / "pool_anc8plus.joblib")
ebm = b["models"]["Explainable Boosting"].named_steps["model"]
names = list(b["numeric"]) + list(b["categorical"])
fig, axes = plt.subplots(1, 3, figsize=(13, 3.4))
for ax, pred in zip(axes, ["v191", "travel_healthpost_log", "age_at_birth"]):
    f = names.index(pred)
    t = next(i for i, feats in enumerate(ebm.term_features_) if tuple(feats) == (f,))
    cuts = np.asarray(ebm.bins_[f][0], dtype=float)
    scores = np.asarray(ebm.term_scores_[t])[1:len(cuts) + 2]
    x = np.r_[cuts[0] - (cuts[1] - cuts[0]), cuts]
    ax.step(x, scores[:len(x)], where="post"); ax.axhline(0, color="grey", lw=0.6)
    ax.set_title(pred); ax.set_ylabel("adds to log-odds" if pred == "v191" else "")
plt.tight_layout(); plt.show()
repro.compare_table(pd.read_csv(P.outputs / "explain" / "importance.csv"), "explain_importance.csv",
                    keys=["set", "rung", "model", "predictor"], value="share", label="every predictor's share, per model")
repro.report()
''')]
    e3 = [md('''
# E3 · Levers and drivers with explainable boosting, beside logistic regression

The planner's levers and the regional drivers of notebook 13, computed with explainable
boosting as well as logistic regression. Both are additive, so both split a region's gap
exactly; the difference is that explainable boosting's curves can bend. The table at the end
shows each lever's weight under both models and the gap: where they agree, the answer does not
depend on the shape of the model; where they part, it does, and the lever should be read with
care.
'''), code(SETUP), code('''
repro.run_script("run_scenarios.py", "--models", "ebm", "logistic", *(["--quick"] if QUICK else []))
repro.run_script("run_regional_eda.py", "--models", "ebm", "logistic")
'''), code('''
s = json.load(open(P.outputs / "scenarios" / "scenarios.json"))
keys = [l["key"] for l in s["levers"]] + ["all seven"]
rows = []
for r in ("anc1", "anc4", "anc8"):
    e = s["by_model"]["ebm"]["rungs"][r]["gain"][-1]
    l = s["by_model"]["logistic"]["rungs"][r]["gain"][-1]
    for k, a, b in zip(keys, e, l):
        rows.append({"rung": r, "lever": k, "EBM": a * 100, "logistic": b * 100, "gap": (a - b) * 100,
                     "same direction": (a > 0) == (b > 0)})
t = pd.DataFrame(rows)
print(t.round(2).to_string(index=False))
print(f"\\nThe models agree on direction for {t['same direction'].mean():.0%} of lever-rung pairs.")
ref = repro.reference("levers_national.json")
for m in ("ebm", "logistic"):
    got = {r: s["by_model"][m]["rungs"][r]["gain"][-1] for r in ref[m]}
    gap = max(abs(a - b) for r in ref[m] for a, b in zip(ref[m][r], got[r]))
    repro.check(f"the national lever effects ({m}) are the study's", gap < 1e-9, f"largest difference {gap:.1e}")
repro.report()
''')]
    return e1, e2, e3


# ------------------------------------------------------------------ helpers
def _plain(text: str) -> str:
    """The study's single-study wording, in the notebook's prose."""
    reps = [(r"\bNotebook 2\b", "the later notebooks"), (r"\bNotebook 3\b", "notebook 02"),
            (r"\bNotebook 4\b", "the modelling notebooks"), (r"\bNotebook 1\b", "this notebook"),
            (r"(?<![/_\w])frozen\b(?![_/])", "fixed"), (r"\bpublished\b", "reported"),
            (r"original study", "earlier analysis")]
    for a, b in reps:
        text = re.sub(a, b, text, flags=re.I if "Notebook" in a else 0)
    return text


def _plain_comments(code_text: str) -> str:
    return "\n".join(_plain(line) if line.lstrip().startswith("#") else line for line in code_text.splitlines())


# ------------------------------------------------------------------ reference files
def write_reference(out: Path, lineup: str):
    """The study's results, as the notebooks' checks read them."""
    from anc8 import cohorts, library as lib
    from anc8.repro import fingerprint as fp

    lineup_models = lib.LINEUPS[lineup]
    ref = out / "reference"
    ref.mkdir(parents=True, exist_ok=True)

    entry = cohorts.entry_table().sort_values("caseid")
    json.dump({
        "analysis_frame_21": fp(pd.read_pickle(ROOT / "outputs" / "ANC8_analysis_frozen.pkl")),
        "analysis_frame_pool": fp(pd.read_pickle(ROOT / "outputs" / "enhanced" / "ANC8_analysis_frozen_v2.pkl")),
        "anc_entry": fp(entry.reset_index(drop=True)),
        "partition": {"development": lib.DEV_DIGEST, "held_out": lib.HELD_DIGEST, "folds": lib.FOLD_DIGEST},
    }, open(ref / "fingerprints.json", "w"), indent=2)
    shutil.copy2(ROOT / "outputs" / "notebook3_explainability_handoff" / "predictor_architecture.json",
                 ref / "predictor_architecture.json")

    # what the explanations and the levers came to (aggregates only: no woman's record)
    imp = pd.read_csv(ROOT / "outputs" / "explain" / "importance.csv")
    imp[imp.model.isin(lineup_models)].to_csv(ref / "explain_importance.csv", index=False)
    s = json.load(open(ROOT / "outputs" / "scenarios" / "scenarios.json"))
    json.dump({m: {r: b["gain"][-1] for r, b in blk["rungs"].items()} for m, blk in s["by_model"].items()
               if m == "logistic" or "Explainable Boosting" in lineup_models},
              open(ref / "levers_national.json", "w"), indent=2)

    red = json.load(open(ROOT / "outputs" / "enhanced" / "redundancy" / "redundancy_summary.json"))
    sets = {s: {r: sorted(sum((list(x) for x in lib.predictors(s, r)), [])) for r in lib.RUNGS} for s in lib.SETS}
    tiers = {}
    for r in lib.RUNGS:
        s = json.load(open(ROOT / "outputs" / "feature_value" / "full" / r / "summary.json"))
        tiers[r] = {"tier1": s["tier1"], "tier2": s["tier2"]}
    pars = {r: json.load(open(ROOT / "outputs" / "enhanced" / r / "parsimonious_spec.json"))["predictors"] for r in lib.RUNGS}
    json.dump({"duplicates_dropped": red["dropped"], "construct_twins": lib.CONSTRUCT_TWINS,
               "short_tiers": tiers, "pars_raw": pars, "sets": sets}, open(ref / "predictor_sets.json", "w"), indent=2)

    sel = {r: json.load(open(ROOT / "outputs" / "enhanced" / r / "best_hyperparameters.json"))["LightGBM"] for r in lib.RUNGS}
    json.dump(sel, open(ref / "selector_lightgbm.json", "w"), indent=2)

    summ = pd.read_csv(ROOT / "outputs" / "library" / "summary.csv")
    keep = set(lineup_models) | {lib.calibrated_name(m, c) for m in lineup_models for c in lib.CALIBRATIONS}
    keep |= {lib.ensemble_name(k, ln) for k in ("stack", "cumlink") for ln in lib.LINEUPS
             if set(lib.LINEUPS[ln]) <= set(lineup_models)}
    summ[summ.model.isin(keep)][["set", "rung", "model", "n_predictors", "dev_AP", "held_AP", "held_AUROC"]] \
        .to_csv(ref / "expected_results.csv", index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-ebm", action="store_true", help="leave out the explainable boosting track")
    args = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "src" / "anc8", OUT / "src" / "anc8", ignore=shutil.ignore_patterns("__pycache__"),
                    dirs_exist_ok=True)
    (OUT / "scripts").mkdir(exist_ok=True)
    for s in SCRIPTS:
        shutil.copy2(ROOT / "scripts" / s, OUT / "scripts" / s)
    (OUT / "data").mkdir(exist_ok=True)
    (OUT / "data" / "README.md").write_text(DATA_README, encoding="utf-8")
    (OUT / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")
    (OUT / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (OUT / "README.md").write_text(README if not args.no_ebm else README_NO_EBM, encoding="utf-8")
    write_reference(OUT, "three" if args.no_ebm else "four")

    nbs = {
        "00_start_here": nb00(), "01_cohort_outcomes_and_the_21": nb01(), "02_candidate_pool": nb02(),
        "03_split_and_folds": nb03(), "04_selection_helper": nb04(), "05_duplicates_and_clean_pool": nb05(),
        "06_predictor_sets": nb06(),
        "07_logistic_regression": tuning_nb("07", "Logistic regression",
            "A weighted sum of the predictors, turned into a chance: the plain baseline every other model must beat. "
            "It is regularised (L2), and the one setting searched is how strongly.",
            "Numbers: median fill for missing values, then scaled to mean 0 and standard deviation 1. "
            "Categories: the most frequent level fills a missing value, then one column per level (one-hot)."),
        "08_random_forest": tuning_nb("08", "Random Forest",
            "Hundreds of decision trees, each grown on a bootstrap sample of women and a random share of the "
            "predictors at every split, averaged. It needs no scaling and finds interactions by itself.",
            "Numbers: median fill. Categories: the most frequent level fills a missing value, then each level becomes "
            "an integer code the trees split on."),
        "09_xgboost": tuning_nb("09", "XGBoost",
            "Gradient boosting: small trees added one at a time, each correcting the last. It is fitted on one "
            "thread everywhere, because its row and column sampling depends on the thread count, and a result that "
            "followed the machine could not be reproduced.",
            "Numbers: median fill. Categories: the most frequent level fills a missing value, then integer codes."),
        "10_calibration_and_ensembles": nb10(), "11_evaluation": nb11(), "12_explainability": nb12(),
        "13_levers_and_drivers": nb13(),
    }
    for name, cells in nbs.items():
        if args.no_ebm:
            for c in cells:
                for a, b in THREE_ONLY:
                    c.source = c.source.replace(a, b)
        write_nb(OUT / "notebooks" / f"{name}.ipynb", cells)
    if args.no_ebm:
        shutil.rmtree(OUT / "notebooks_ebm", ignore_errors=True)
    else:
        e1, e2, e3 = ebm_nbs()
        for name, cells in (("E1_explainable_boosting", e1), ("E2_ebm_explainability", e2),
                            ("E3_ebm_levers_and_drivers", e3)):
            write_nb(OUT / "notebooks_ebm" / f"{name}.ipynb", cells)
    n = len(list((OUT / "notebooks").glob("*.ipynb"))) + len(list((OUT / "notebooks_ebm").glob("*.ipynb")))
    print(f"wrote {OUT}: {n} notebooks")


DATA_README = """# data

Put the Ethiopia DHS 2024-25 Individual Recode here, as Stata: **`ETIR8AFL.DTA`**.

Obtain it from The DHS Program (https://dhsprogram.com), under your own registration. The
file is licensed to you and must not be redistributed. Nothing the notebooks write contains
it: every per-woman file they make stays in `outputs/`, `results/` and `quick/`, which the
folder's `.gitignore` keeps out of version control. Do not share those folders either.
"""

GITIGNORE = """# the survey and everything made from it, row by row
data/*.DTA
data/*.dta
outputs/
results/
quick/
__pycache__/
.ipynb_checkpoints/
"""

README = """# Reproducing the ANC model library

Notebooks that rebuild the study's model library from the Ethiopia DHS 2024-25 Individual
Recode, for any researcher who holds the survey file: the cohort and the ANC1+, ANC4+ and ANC8+
outcomes, the 21 predictors and the candidate pool, the split, the four predictor sets, the
tuned models, their evaluation, their explanations and the planner's levers.

**Start with `notebooks/00_start_here.ipynb`.** It lists what to install, where the survey
file goes, the run order and how long each step takes. To run everything in order from the
command line: `python scripts/run_notebooks.py --ebm` (executed copies go to `executed/`).

## The two tracks

- `notebooks/` (00-13): the core library, **logistic regression, random forest and XGBoost**,
  each on four predictor sets (the full pool of 86, the 21, the short set, the parsimonious set)
  at three rungs, with calibrated versions and two ensembles.
- `notebooks_ebm/` (E1-E3): **explainable boosting** as a fourth model, with its exact
  explanations and its version of the planner's levers, set side by side with logistic
  regression's.

## How the notebooks check themselves

Each notebook ends with checks against the study's own results in `reference/`: the content
fingerprints of the analysis frames, the digests of the split, the predictor sets, and every
model's development and held-out average precision. A full run on the study's software versions
reproduces them exactly. `QUICK = True` at the top of a notebook runs a fast version whose
numbers are not expected to match.

## Layout

```
notebooks/        the core track
notebooks_ebm/    explainable boosting
src/anc8/         the analysis package (every step is a documented function)
scripts/          the stage scripts some notebooks run, and run_notebooks.py
reference/        the study's results, for the checks
executed/         executed copies of the notebooks (after a run)
data/             put ETIR8AFL.DTA here (not included; see data/README.md)
requirements.txt  the software versions the study used
```
"""

README_NO_EBM = README.replace("""- `notebooks_ebm/` (E1-E3): **explainable boosting** as a fourth model, with its exact
  explanations and its version of the planner's levers, set side by side with logistic
  regression's.
""", "").replace("notebooks_ebm/    explainable boosting\n", "").replace(
    "`python scripts/run_notebooks.py --ebm`", "`python scripts/run_notebooks.py`")

# The three-model build has no explainable boosting track: its notebooks do not point to one.
THREE_ONLY = [
    (" The `notebooks_ebm/`\ntrack adds **explainable boosting** as a fourth model.", ""),
    ("| E1-E3 | explainable boosting: tuning, explanations, levers (optional) | 2 h |\n", ""),
    ("python scripts/run_notebooks.py --ebm      # and the explainable boosting track\n", ""),
    ("notebooks_ebm/   E1-E3, explainable boosting\n", ""),
    (" The explainable boosting track builds\nthe same two from all four.", ""),
    (', "XGBoost", "Explainable Boosting"] if m in agree]', ', "XGBoost"] if m in agree]'),
]


if __name__ == "__main__":
    main()
