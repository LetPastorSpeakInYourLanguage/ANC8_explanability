"""Build reproduction_full/: the whole model library, rebuilt from the survey file.

    python scripts/build_reproduction_full.py        # writes reproduction_full/

The study's models (reproduction/) are three models on the 21 predictors. On the
way there the study built a much larger model library; this folder's notebooks
rebuild all of it from ETIR8AFL.DTA: the cohort and the 21, the candidate pool
(every survey column screened), the split, the near-duplicate analysis and the
clean pool of 86, the four predictor sets (the pool, the 21, the short set, the
parsimonious set), eleven model families tuned on every set at every rung, their
isotonic and Platt recalibrations, the stacked and cumulative-link ensembles, the
two neural networks and CatBoost (on a GPU), and the study's own grid-tuned models.
Every result is checked against the study's own (reference/).

What all of it found is recorded in research_record/ (scripts/build_research_record.py).

Nothing is hand-written twice: the package is synced from src/anc8, the stage
scripts from scripts/, the cell code of the first notebook is the study's own, and
the study's results are written to reference/ for every notebook to check itself
against.
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
OUT = ROOT / "reproduction_full"

SCRIPTS = ["run_notebooks.py", "run_feature_value.py", "run_redundancy_analysis.py", "train_library.py"]

REQUIREMENTS = """\
# The analysis environment the study ran in. Newer versions will very likely work,
# but the check cells compare against the study's numbers, and the boosted trees and
# networks can differ in the last digits across versions.
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
# on the GPU machine only (notebook 08): CatBoost and the two networks
# catboost==1.2.8
# torch==2.9.0
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

These notebooks rebuild the study's **whole model library** from the EDHS 2024-25 Individual
Recode. The study's own models, three models on the 21 predictors, are rebuilt far more quickly
by `reproduction/`; this folder rebuilds everything the study tried on the way:

- the cohort, the outcome ladder and the 21 predictors (notebook 01, the same as `reproduction/`);
- the **candidate pool**: every one of the survey's 6,648 columns screened, 95 admitted (02);
- the held-out women and the development folds (03);
- the **four predictor sets**: the clean pool of 86 (after the near-duplicate analysis), the 21,
  the short set and the parsimonious set (04-06);
- **eleven model families** tuned on every set at every rung, each with an **isotonic** and a
  **Platt** recalibration, and **stacked** and **cumulative-link** ensembles (07);
- **CatBoost** and two **neural networks** on a GPU (08);
- the ensembles of the three- and four-model lineups, and the study's own grid-tuned models (09);
- every result checked against the study's (10).

Run them in order; each reads only what the earlier ones wrote and ends by checking its results
against the study's (in `reference/`). What all of it found is written up in `research_record/`.

## Before you start

1. **The data.** Obtain `ETIR8AFL.DTA` (Ethiopia DHS 2024-25, Individual Recode, Stata) from
   The DHS Program and put it in `data/`. It is licensed to you and must not be shared;
   nothing in this folder contains survey rows, and everything the notebooks write stays in
   `outputs/`, `results/`, `study/` and `quick/`, which are never committed.
2. **The environment.** Python 3.12 or 3.13, then `pip install -r requirements.txt`; on the GPU
   machine also `catboost` and `torch` (see the file).
3. **The time.** This is days of computing, not hours. The study ran it on this PC's 8 cores and
   a Colab T4 GPU over several days. Every model is saved as it finishes, and a notebook that is
   run again skips what is done, so it can be stopped and resumed at any point.

| Notebook | Does | Time |
|---|---|---|
| 01 | the cohort, the outcome ladder and the 21 predictors | 2 min |
| 02 | the candidate pool: every survey column screened, 95 admitted | 3 min |
| 03 | the held-out split and the development folds | under 1 min |
| 04 | a helper model for the selection steps (LightGBM on the 95) | 15 min per rung |
| 05 | near-duplicate predictors, and the clean pool of 86 | 5 min |
| 06 | the four predictor sets | 6 to 8 h |
| 07 | eleven families x four sets x three rungs, recalibrated, ensembled (CPU) | 3 to 5 days |
| 08 | CatBoost and the two networks (GPU) | about a day on a T4 |
| 09 | the lineup ensembles, and the study's grid-tuned models | 2 h |
| 10 | every result against the study's | 5 min |

To run them without opening Jupyter, from this folder:

```
python scripts/run_notebooks.py --only 01 02 03 04 05 06 07   # this machine
python scripts/run_notebooks.py --only 08                     # on the GPU machine
python scripts/run_notebooks.py --only 09 10
python scripts/run_notebooks.py --quick                       # a smoke run: 3 search trials per model
```

## Two switches, at the top of every notebook

- `QUICK = True` runs everything with three search trials per model. The numbers will not
  match the study's; use it to check that everything runs.
- `FOLLOW_STUDY = True` (the default): where a re-derived choice (a selection step, a helper
  model's settings) differs from the study's, the notebook says so and carries the study's
  choice forward, so that the later notebooks reproduce the study's numbers exactly.

## Folders

```
data/            put ETIR8AFL.DTA here
notebooks/       00-10
src/anc8/        the analysis package every notebook uses
scripts/         the stage scripts the notebooks run (train_library.py builds the library)
reference/       the study's results, for the checks
outputs/         what the notebooks write (analysis frames, tables)
results/         the library: one file per model, set and rung
study/           the study's own grid-tuned models
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

One lever of notebook 12, an earlier first visit, needs to know when care began. The survey
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
for s in lib.ALL_SETS:
    for r in lib.RUNGS:
        num, cat = lib.predictors(s, r)
        rows.append({"set": lib.SET_LABEL[s], "rung": r, "predictors": len(num) + len(cat),
                     "which": ", ".join(list(num) + list(cat)) if len(num) + len(cat) <= 10 else "…"})
        repro.check(f"{s}/{r}: the predictors are the study's",
                    sorted(list(num) + list(cat)) == sorted(study["sets"][s][r]))
print(pd.DataFrame(rows).to_string(index=False))
repro.report()
''')]


def nb07():
    return [md('''
# 07 · The library on this machine: eleven families, four sets, three rungs

Every model family below is tuned on every predictor set at every rung, by the same procedure:

- **Optuna's TPE sampler**, seed 2026, a fixed budget of trials per family (printed below);
- each trial is scored by **survey-weighted average precision, out of fold**, over the five
  development folds of notebook 03, with survey weights rescaled to average one in each fold;
- the best settings are refitted on all 5,518 development women and the held-out women are
  scored once.

Then, for every tuned model:

- two **recalibrated** versions, **isotonic** (a flexible step map) and **Platt** (a logistic map,
  which keeps the ranking), each fitted inside the development folds so it is never scored on the
  women it was fitted to;
- a **stacked ensemble** (a logistic regression over the five best models' out-of-fold
  predictions) and a **cumulative-link ensemble** (the best model refitted at contact thresholds
  1 to 10, forced to fall as the threshold rises, pooled and mapped back to a chance).

The runner (`scripts/train_library.py`) works through the jobs in order of what each needs,
saves every model as it finishes, and skips what is done. **This takes days**; stop and re-run
the cell at will. CatBoost and the networks need a GPU and are left to notebook 08.
'''), code(SETUP + '''
WORKERS = 4   # models trained at once; each uses up to 5 cores for its folds
'''), code('''
print(pd.DataFrame([{"family": f, "trials": tuning.TRIALS[f]} for f in lib.FAMILIES]).to_string(index=False))
print(f"\\n{len(lib.ALL_SETS)} predictor sets x {len(lib.RUNGS)} rungs")
repro.run_script("train_library.py", "--root", P.results, "--status")
'''), code('''
repro.run_script("train_library.py", "--root", P.results, "--device", "cpu", "--workers", WORKERS)
'''), code('''
repro.run_script("train_library.py", "--root", P.results, "--status")
''')]


def nb08():
    return [md('''
# 08 · CatBoost and the two networks, on a GPU

Three parts of the library need a CUDA GPU to finish in reasonable time:

- **CatBoost**, a boosted tree with its own handling of categories (most of the 21 are
  categories), tuned like the other families (20 trials) and recalibrated the same way;
- the **ladder transformer**, which predicts all three rungs at once from one representation of
  the woman, so the three predictions cannot contradict each other;
- the **contact-sequence encoder-decoder**, which predicts the number of contacts step by step.

The study ran these on a Colab T4. To do the same: copy this whole folder (with `data/`) to
Google Drive, open this notebook in Colab with a GPU runtime, install `catboost` and `torch`, and
run it. The runner writes to the same `results/` folder, and skips what is done, so a Colab
session that ends can be resumed.
'''), code(SETUP), code('''
repro.run_script("train_library.py", "--root", P.results, "--device", "gpu", "--workers", 1)
repro.run_script("train_library.py", "--root", P.results, "--status")
''')]


def nb09():
    return [md('''
# 09 · The lineup ensembles, and the study's own models

**Lineup ensembles.** The stacked and cumulative-link ensembles over the study's model lineups:
logistic regression, random forest and XGBoost, and the same with explainable boosting as a
fourth. They need those models' tuned versions from notebook 07.

**The study's own models.** Logistic regression, random forest and XGBoost on the 21 predictors
at each rung, each tuned over the small grid notebook 2 prespecified instead of a search. These
are the models the study's planning studio uses; `reproduction/` builds them on their own. They
are written to `study/`, apart from the library.
'''), code(SETUP), code('''
repro.run_script("train_library.py", "--root", P.results, "--lineup", "three", "four")
repro.run_script("train_library.py", "--root", P.project / "study", "--study")
''')]


def nb10():
    return [md('''
# 10 · Every result against the study's

Each model's development and held-out average precision, set against the study's own
(`reference/expected_results.csv` and `expected_study.csv`). A full run on the study's software
versions reproduces them exactly; a model the study did not finish (most of CatBoost) is listed
as such. The study's reading of all these numbers, with intervals and paired comparisons, is in
`research_record/`.
'''), code(SETUP), code('''
ref = repro.reference("expected_results.csv")
rows = []
for r in ref.itertuples():
    p = lib.cell_path(P.results, r.set, r.rung, r.model)
    if not p.exists():
        rows.append({"set": r.set, "rung": r.rung, "model": r.model, "status": "not run"}); continue
    m = lib.load_cell(P.results, r.set, r.rung, r.model)["meta"]
    rows.append({"set": r.set, "rung": r.rung, "model": r.model, "status": "done",
                 "held_AP": m["held_metrics"]["AP"], "study_held_AP": r.held_AP,
                 "difference": m["held_metrics"]["AP"] - r.held_AP})
res = pd.DataFrame(rows)
print(res.status.value_counts().to_string())
ok = res[res.status == "done"]
repro.check(f"{len(ok)} library models match the study's held-out AP (1e-6)",
            len(ok) == len(res) and ok.difference.abs().max() <= 1e-6, f"largest difference {ok.difference.abs().max():.1e}")
'''), code('''
repro.compare_cells(P.project / "study", ["Logistic regression", "Random Forest", "XGBoost"], sets=("s21",),
                    ref_name="expected_study.csv")
'''), code('''
# the leaderboard at each rung: the best tuned models on any set
best = ok.merge(ref[["set", "rung", "model", "n_predictors"]], on=["set", "rung", "model"])
for rung in lib.RUNGS:
    print(rung)
    print(best[best.rung == rung].sort_values("held_AP", ascending=False).head(10)[["set", "model", "n_predictors", "held_AP"]]
          .round(3).to_string(index=False), "\\n")
repro.report()
''')]


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
def write_reference(out: Path):
    """The study's results, as the notebooks' checks read them."""
    from anc8 import cohorts, library as lib
    from anc8.repro import fingerprint as fp

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

    red = json.load(open(ROOT / "outputs" / "enhanced" / "redundancy" / "redundancy_summary.json"))
    sets = {s: {r: sorted(sum((list(x) for x in lib.predictors(s, r)), [])) for r in lib.RUNGS} for s in lib.ALL_SETS}
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
    summ[["set", "rung", "model", "kind", "n_predictors", "dev_AP", "held_AP", "held_AUROC"]] \
        .to_csv(ref / "expected_results.csv", index=False)
    rows = []
    for job in lib.grid_jobs():
        meta = lib.load_cell(ROOT / "outputs" / "core", job.set, job.rung, job.model)["meta"]
        rows.append({"set": job.set, "rung": job.rung, "model": job.model, "n_predictors": meta["n_predictors"],
                     "dev_AP": meta["dev_metrics"]["AP"], "held_AP": meta["held_metrics"]["AP"]})
    pd.DataFrame(rows).to_csv(ref / "expected_study.csv", index=False)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "src" / "anc8", OUT / "src" / "anc8", ignore=shutil.ignore_patterns("__pycache__"))
    (OUT / "scripts").mkdir()
    for s in SCRIPTS:
        shutil.copy2(ROOT / "scripts" / s, OUT / "scripts" / s)
    (OUT / "data").mkdir()
    (OUT / "data" / "README.md").write_text(DATA_README, encoding="utf-8")
    (OUT / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")
    (OUT / ".gitignore").write_text(GITIGNORE.replace("quick/\n", "quick/\nstudy/\nlogs/\n"), encoding="utf-8")
    (OUT / "README.md").write_text(README, encoding="utf-8")
    write_reference(OUT)

    nbs = {
        "00_start_here": nb00(), "01_cohort_outcomes_and_the_21": nb01(), "02_candidate_pool": nb02(),
        "03_split_and_folds": nb03(), "04_selection_helper": nb04(), "05_duplicates_and_clean_pool": nb05(),
        "06_predictor_sets": nb06(), "07_the_library_on_cpu": nb07(), "08_catboost_and_networks_on_gpu": nb08(),
        "09_lineup_ensembles_and_study_models": nb09(), "10_results_against_the_study": nb10(),
    }
    for name, cells in nbs.items():
        write_nb(OUT / "notebooks" / f"{name}.ipynb", cells)
    print(f"wrote {OUT}: {len(nbs)} notebooks")


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

README = """# Rebuilding the whole model library

Notebooks that rebuild, from the Ethiopia DHS 2024-25 Individual Recode, everything the study
built on the way to its models: the candidate pool of every survey column, the near-duplicate
analysis, four predictor sets, eleven model families tuned on every set at every rung, their
isotonic and Platt recalibrations, stacked and cumulative-link ensembles, CatBoost and two
neural networks. It takes days of computing; every model is saved as it finishes and runs
resume where they stopped.

The study's own models, three models on the 21 predictors, are rebuilt in half an hour by
`reproduction/`. What the whole library found is written up, with intervals, in
`research_record/`.

**Start with `notebooks/00_start_here.ipynb`.** It lists what to install, where the survey file
goes, the run order, the times, and which notebook needs a GPU.

## How the notebooks check themselves

Each notebook ends with checks against the study's own results in `reference/`: the content
fingerprints of the analysis frames, the digests of the split, the predictor sets, the helper
model's settings, and every library model's held-out average precision.

## Layout

```
notebooks/        00-10
src/anc8/         the analysis package (every step is a documented function)
scripts/          the stage scripts; train_library.py builds the library
reference/        the study's results, for the checks
data/             put ETIR8AFL.DTA here (not included; see data/README.md)
requirements.txt  the software versions the study used
```
"""


if __name__ == "__main__":
    main()
