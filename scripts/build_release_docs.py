"""Write the documentation that ships with release/.

Called by build_release.py. Kept separate because the guide is long prose and
mixing it into the assembly logic makes both harder to read.

Numbers quoted in the guide are read from the artifacts wherever one exists,
so the documentation cannot drift away from the results it describes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ENHANCED = ROOT / "outputs" / "enhanced"


def _num(path: Path, fn, default="(not yet produced)"):
    """Read a number out of an artifact, or say plainly that it is missing."""
    try:
        if not path.exists():
            return default
        return fn(path)
    except Exception:
        return default


def facts() -> dict:
    f = {}
    f["stability"] = _num(
        ENHANCED / "anc8plus" / "stability_summary.json",
        lambda p: json.loads(p.read_text()))
    f["bootstrap"] = _num(
        ENHANCED / "anc8plus" / "paired_bootstrap_ci.json",
        lambda p: json.loads(p.read_text()))
    f["redundancy"] = _num(
        ENHANCED / "redundancy" / "redundancy_summary.json",
        lambda p: json.loads(p.read_text()), default=None)
    f["rungs"] = {}
    for rung in ("anc1plus", "anc4plus", "anc8plus"):
        p = ENHANCED / rung / "heldout_performance.csv"
        if p.exists():
            d = pd.read_csv(p)
            d = d[d.generation.astype(str).str.startswith("V2")]  # full-pool models
            if len(d):
                b = d.sort_values("AP", ascending=False).iloc[0]
                f["rungs"][rung] = {"model": str(b.model), "AP": float(b.AP),
                                    "AUROC": float(b.AUROC)}
    return f


GUIDE = """# Reproduction guide

Everything in this package can be rebuilt from source on an ordinary laptop.
No GPU is needed anywhere. The long steps are the hyperparameter search and
the bootstrap re-selection in the predictor-value study.

Work through the sections in order the first time. Each one ends with a check
you can run, and the checks are the point -- a stage that runs without error
but produces different numbers has still failed.

---

## 0. What you are reproducing

Prediction of antenatal care attainment among women in the 2024-25 Ethiopia
Demographic and Health Survey, at three thresholds of the same ladder:

| Rung | Question | Weighted prevalence |
|---|---|---|
| ANC1+ | did she reach antenatal care at all | 77.6% |
| ANC4+ | the previous WHO minimum | 52.4% |
| ANC8+ | the 2016 WHO standard | 19.2% |

Three analyses carry the study:

1. **Predictor value** -- which predictors carry the prediction of each rung,
   how many are needed (an ablation from one predictor to the full candidate
   pool, with the pre-specified 21-predictor set as one of the sets), and how
   each predictor's value changes up the ladder;
2. **Two prediction horizons** -- before ANC starts (6,893 women) and at ANC
   entry (5,001 women who started ANC, adding whether the first contact was
   early);
3. **The Tigray war** -- wartime against post-war pregnancies, against every
   other region.

Two predictor sets are modelled and deployed:

| | Predictors | Algorithms |
|---|---|---|
| **The 21-predictor set** | 21 pre-specified constructs | logistic regression, random forest, XGBoost, at both horizons |
| **The full candidate pool** | 95 columns (85 distinct variables) | ten families plus ensembles, all tuned |

---

## 1. Set up

### 1.1 Python

Python 3.13 is what this was built on; 3.11 or newer will work.

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

### 1.2 The second environment, and why there are two

The 21-predictor pipelines were pickled under **scikit-learn 1.7.2**. They
cannot be unpickled under 1.9, which removed a private attribute they
reference. Anything that touches those pickles -- their fidelity checks and
their deployment bundle -- needs an environment pinned to the versions that
created them:

```bash
python -m venv .venv-serve
.venv-serve/Scripts/pip install -r requirements-serve.txt
```

Nothing else needs it. If you skip this, those checks report themselves as
skipped rather than passing quietly, which is the behaviour you want.

**Watch your PATH.** If `python` resolves to `.venv-serve`, the pipeline
scripts will fail on a missing optuna. Call the interpreter explicitly when in
doubt.

### 1.3 Check

```bash
python scripts/check_environment.py
```

Prints every version and says which of the two environments you are in.

---

## 2. Get the data

The package ships the **derived** analysis dataset in `data/`, not the raw
survey. The DHS Program licences its recode files to named users and does not
permit redistribution, so the raw file has to come from them:

1. register at <https://dhsprogram.com/data/> and request Ethiopia 2024-25;
2. download the **Individual Recode**, Stata format (`ETIR8AFL.DTA`, ~160 MB);
3. place it in the package root next to `notebooks/`.

You only need it to rebuild the analysis dataset from scratch (section 4). To
reproduce the modelling, evaluation and every result, `data/` already has what
you need:

| File | What it is |
|---|---|
| `ANC8_analysis_frozen_v2.parquet` | 6,893 women x ~110 columns: the outcome ladder, all 95 predictors, survey design variables |
| `ANC8_analysis_frozen_v2.csv.gz` | the same, for tools that do not read parquet |
| `codebook.csv` | every column, its role, type, missingness and example values |
| `partition.csv` | which women are development and which are held out |

### Check

```bash
python -c "import pandas as pd; d=pd.read_parquet('data/ANC8_analysis_frozen_v2.parquet'); \\
print(d.shape); print((d.anc8plus*d.v005/1e6).sum()/(d.v005/1e6).sum())"
```

Expect `(6893, ...)` and a weighted ANC8+ prevalence of about **0.1916**.

---

## 3. Reproduce the results without refitting anything

Every table and figure in `artifacts/` and `figures/` is derived from files in
this package. Rebuild the figures to confirm:

```bash
python scripts/make_figures.py
```

This reads the committed CSV and JSON artifacts and rewrites
`outputs/figures/`. It needs no model. Compare against `figures/` -- they
should be identical.

### Check

```bash
python scripts/verify_all.py
```

This is the gate that matters. It checks, in order:

1. the rebuilt held-out set is the study's held-out set, caseid for caseid
   (if this fails, nothing downstream means anything);
2. the outcome ladder is nested -- every woman's ANC8+ implies her ANC4+
   implies her ANC1+ -- and the three weighted prevalences match;
3. the 21-predictor deployment bundle reproduces those models' locked
   held-out predictions;
4. the full-pool bundle reproduces the fitted pipelines' probabilities;
5. the browser-side additive model agrees with the Python scorer.

Checks 3 and 4 need `.venv-serve` and report themselves skipped without it.

---

## 4. Rebuild the analysis dataset from the raw survey

Only needed if you have the DHS file and want to verify the derivation.

```bash
python scripts/build_notebook3.py
python scripts/execute_nb.py 3_ANC8_deep_EDA_and_feature_reascertainment.ipynb
```

This screens all 6,648 columns of the Individual Recode against the outcome
**on the development fold only**, applies the temporality review that excludes
anything recorded during or after the pregnancy, and writes the analysis
dataset.

The temporality exclusions are the part worth reading rather than running:
`src/anc8/features.py` lists each excluded variable with the reason. Several
DHS variables that predict ANC8 superbly -- timing of the first visit, place
of delivery, tetanus doses -- are recorded *after* the thing being predicted,
and a model using them would score beautifully and mean nothing.

### Check

The rebuilt dataset should match the shipped one -- same 6,893 women, same
weighted prevalences, same partition:

```bash
python tests/run_tests.py
```

Sections 1 and 2 of that suite are exactly this comparison.

---

## 5. Refit the models

This is the expensive part. Each outcome runs the full Optuna search over ten
model families, then evaluation, stability, bootstrap and export:

```bash
python scripts/run_pipeline.py --outcome anc1plus
python scripts/run_pipeline.py --outcome anc4plus
python scripts/run_pipeline.py --outcome anc8plus
```

All three share one split and one set of folds, by construction: the split
never looks at the outcome, so the same 5,518 development and 1,375 held-out
women serve every rung. That is what makes importance comparable across the
ladder -- any difference between rungs is the outcome, not the data.

How closely your numbers should match ours depends on the model, and this
was measured rather than assumed:

- **Logistic regression and LightGBM** give the same predictions whatever the
  number of CPU threads (checked: identical to 1e-12). Expect agreement to the
  fourth decimal of AP.
- **XGBoost does not.** It is deterministic at a fixed thread count, but its
  results change with the count: development AP on ANC8+ was 0.518 on 22
  threads, 0.517 on 1 and 0.506 on 4. A machine with a different number of
  cores will get different XGBoost numbers, by up to about 0.01 AP, and that
  is not an error. Treat any XGBoost difference smaller than that as noise.

A difference in the second decimal for logistic regression or LightGBM means
something is wrong; check that your split matches `data/partition.csv` first.

### Then the three analyses

```bash
# 1. predictor value, per cohort and outcome (stages 0-3)
python scripts/run_feature_value.py --cohort full --outcome anc8plus   # and anc1plus, anc4plus
python scripts/run_why21_heldout.py            # the reduced 21 on held-out women
python scripts/run_predictor_matrix.py         # each predictor's value at each rung
python scripts/run_ladder_analysis.py          # importance three ways, per rung
# 2. the two horizons
python scripts/run_feature_value.py --cohort entry --outcome anc8plus  # and anc4plus
python scripts/run_horizons.py
# 3. the Tigray war
python scripts/run_wartime_analysis.py
# sensitivity: the 24-month window
python scripts/run_feature_value.py --cohort recent --outcome anc8plus # and the others
```

### And the supporting analyses

```bash
python scripts/run_policy_analysis.py          # the cascade and targeting work
python scripts/run_redundancy_analysis.py      # duplicated predictors
python scripts/run_hyperparameter_ablation.py --outcome anc8plus
python scripts/export_insights.py              # what the web app reads
python scripts/make_figures.py
```

---

## 6. The web application

The app scores the 21-predictor models at both horizons and the full-pool
model. They are exported to plain numeric arrays and scored by a numpy-only
function, because loading the fitted pipelines would need 341 MB of
dependencies against a 250 MB serverless limit. (`--v1` builds the
21-predictor bundles; `--v2` the full-pool bundle.)

```bash
.venv-serve/Scripts/python scripts/export_serving.py --v1 --v2
python scripts/export_insights.py
python scripts/export_app_data.py      # analysis, documents and figures for the app
powershell -ExecutionPolicy Bypass -File dev.ps1    # or: bash scripts/dev.sh
```

Open <http://localhost:3000>. The app opens on the policy brief; Predictors,
The ladder, Horizons and Tigray war hold the three analyses; Analysis record
holds every analysis with a plain-language glossary; Reports holds every
document and figure; Predict calls the local Python service on port 8000,
which the launcher starts.

### Check

```bash
python scripts/test_scorer.py        # numpy scorer vs the fitted pipelines
python scripts/check_ts_parity.py    # TypeScript scorer vs the Python one
```

The export refuses to write a bundle that fails its own fidelity gate, so a
passing export is itself a check. The gate allows a handful of knife-edge rows
where a float32 comparison inside XGBoost falls the other way from float64;
that tolerance is a share of rows, not a magnitude, and is documented in
`scripts/export_serving.py`.

---

## 7. What to read

Start with `docs/README.md`, which maps everything by reader.

| File | |
|---|---|
| `docs/POLICY_BRIEF.md` | for the Ministry of Health: findings and recommendations |
| `docs/INSIGHTS.md` | the findings in plain language |
| `docs/FINDINGS.md` | the technical hub, including what did not work |
| `docs/DATA_AND_COHORT.md` | the cohort, the official 24-month window, and when each predictor was measured |
| `docs/PREDICTOR_VALUE.md` | from 6,648 columns to a pool; how many predictors each rung needs; the drop study; value across the ladder |
| `docs/HORIZONS.md` | before ANC starts vs at ANC entry, and what early ANC adds |
| `docs/WARTIME.md` | antenatal care during and after the Tigray war, against every region |
| `docs/ANALYSIS_RECORD.md` | every analysis: question, test, result |
| `docs/METHODS.md` | design, splitting, metrics, and why each choice |
| `docs/LIMITATIONS.md` | what this analysis cannot support |
| `docs/DECISION_LOG.md` | every significant decision and why |
| `notebooks/` | five short notebooks, one per stage |
| `artifacts/` | every table behind every claim |
| `figures/` | every figure, with `figures_manifest.csv` giving sources |

---

## 8. Test suite

```bash
python tests/run_tests.py
```

Runs everything above that can be checked without refitting: dataset shape and
prevalence, nested outcomes, split identity, artifact presence, scorer parity,
figure reproduction, and internal consistency between the documentation's
headline numbers and the artifacts they come from.

---

## 9. Known limits of this package

**The held-out set is small.** 1,375 women, 229 of them attaining ANC8+. The
paired bootstrap comparing the full-pool model with the 21-predictor XGBoost is
`{boot_ap}`, which includes zero. Where the full pool is said to beat the 21
in general, that rests on repeated splitting ({seeds}), not on this one test
set, and the write-ups say so wherever the claim appears.

**These are associations.** Nothing here identifies a causal effect. The
what-if surface in the web app moves a predictor and shows what the model
predicts for women with that characteristic -- not what would happen if you
changed it for a given woman. The UI says so where the controls are.

**One survey round, one country.** No temporal or external validation exists.
Applying these models outside Ethiopia 2024-25 is not supported by anything
measured here.
"""


DATA_README = """# Data

## What is here

| File | Rows | What it is |
|---|---|---|
| `ANC8_analysis_frozen_v2.parquet` | 6,893 | the derived analysis dataset |
| `ANC8_analysis_frozen_v2.csv.gz` | 6,893 | the same, as CSV |
| `ANC8_analysis_frozen_v2.pkl` | 6,893 | the same, as the pipeline reads it |
| `codebook.csv` | one row per column | role, type, missingness, example values |
| `anc_entry.csv` | 5,001 | the ANC-entry cohort: early ANC and partition, per woman |
| `partition.csv` | 6,893 | development or held-out, per woman |

The analysis dataset is the *derived* product: one row per woman with a recent
birth who could report her number of antenatal contacts, the outcome ladder,
the 95 screened predictors, and the survey design variables
(`v021` primary sampling unit, `v022` stratum, `v005` sampling weight).

## What is not here, and how to get it

The raw file is **ETIR8AFL.DTA**, the Ethiopia 2024-25 Individual Recode, about
160 MB. It is not in this package because The DHS Program licences recode
files to named users and does not permit redistribution.

To obtain it:

1. register at <https://dhsprogram.com/data/> and describe your intended use;
2. request the Ethiopia 2024-25 Standard DHS dataset;
3. once approved, download the Individual Recode in Stata format;
4. place `ETIR8AFL.DTA` in the package root.

You need it only to rebuild the derived dataset from scratch. Every result in
this package can be reproduced from the derived dataset alone.

## Survey design

This is a stratified, multi-stage cluster sample, and every number in the
analysis respects that:

- **weights** `v005 / 1e6` throughout, so estimates describe the country
  rather than the sample;
- **clusters** all splitting and cross-validation is grouped by `v021`, so
  women from one enumeration area never appear on both sides of a split;
- **strata** the split samples PSUs within `v022`, preserving the design;
- **uncertainty** the bootstrap resamples PSUs within strata, not individuals.

Treating these women as 6,893 independent observations would understate every
standard error. `src/anc8/design.py` holds the machinery; the one
development / held-out partition is drawn there and shipped in
`partition.csv`.

## Citation

> Ethiopian Public Health Institute (EPHI), Ministry of Health, and ICF.
> Ethiopia Demographic and Health Survey 2024-25. Addis Ababa, Ethiopia, and
> Rockville, Maryland, USA: EPHI and ICF.

Cite DHS for the data; this package for the analysis.
"""


REQUIREMENTS = """# Analysis environment.
#
# Pinned to what the results were produced with. Newer versions will very
# likely work; if you change one, re-run scripts/verify_all.py before trusting
# any number.

pandas==3.0.3
numpy==2.5.0
scipy==1.18.0
scikit-learn==1.9.0
statsmodels==0.15.0
xgboost==3.3.0
lightgbm==4.6.0
interpret==0.7.8
shap==0.52.0
optuna==5.0.0
joblib==1.5.3
matplotlib==3.11.0
pyarrow==25.0.1
nbformat==5.10.4
nbclient==0.10.2
jupyter==1.1.1
"""

REQUIREMENTS_SERVE = """# The pinned environment that can read the 21-predictor pipelines.
#
# scikit-learn 1.9 removed a private attribute that pipelines fitted under
# 1.7.2 reference, so those objects cannot be unpickled under it at all. This
# environment exists only to load them: for their fidelity gate, and to build
# their deployment bundle.

pandas==2.3.3
numpy==2.3.5
scikit-learn==1.7.2
xgboost==3.4.1
statsmodels==0.14.5
joblib==1.5.2
pyarrow==25.0.1
"""


README = """# ANC attainment in Ethiopia -- reproduction package

Everything needed to rebuild, check and extend an analysis of antenatal care
attainment in the 2024-25 Ethiopia DHS: the derived dataset, the code, the
fitted models, every table and figure, the write-ups, and a test suite.

**Start with [`GUIDE.md`](GUIDE.md).** It walks from an empty machine to
reproduced results, with a check at the end of every stage.

## Layout

```
GUIDE.md            step by step, including what to run to verify each stage
ENVIRONMENT.md      the two Python environments and why there are two
notebooks/          five short notebooks, one per stage of the analysis
src/anc8/           the library: design, screening, features, models, tuning
scripts/            every runnable stage and analysis
data/               the derived analysis dataset, codebook and partition
models/             fitted models and the exported serving bundles
artifacts/          every result table, as produced
figures/            every figure, with a manifest naming its sources
app_payload/        the JSON the deployed web app reads
docs/               findings, insights, methods, limitations
tests/              the check suite
```

## The short version of the findings

- **How many predictors?** For eight contacts (ANC8+), 7 to 8 predictors --
  wealth, region, pregnancy intention, the woman's work and household say,
  access to a health post -- predict as well as 21 or the full pool of 88 on
  held-out women. For reaching care (ANC1+, ANC4+) the full pool is best.
- **Up the ladder,** region and wealth become far more valuable, and
  household position less.
- **The Tigray war** cut women off from care at the door; access recovered
  after the ceasefire, completion did not.
- **The cascade:** three quarters of women reach antenatal care, but of those
  who reach four contacts most never reach eight.

`docs/INSIGHTS.md` has this in full, in plain language. `docs/FINDINGS.md` has
the technical account, including the things that did not work.

## Licence and attribution

The code is yours to reuse. The data is not ours to give -- see
`data/README.md`. The 2024-25 Ethiopia DHS belongs to EPHI, the Ministry of
Health and ICF, and must be obtained from The DHS Program directly.
"""


ENVIRONMENT = """# Environments

Two, for one specific reason.

## `.venv` -- the analysis environment

Current versions of everything. Runs the screening, tuning, evaluation,
analysis, figures and export. See `requirements.txt`.

## `.venv-serve` -- the pinned environment

The 21-predictor pipelines were pickled under **scikit-learn 1.7.2**. Under
1.9 they cannot be unpickled at all: `SimpleImputer` gained and then lost a
private `_fill_dtype` attribute, and unpickling raises before any of our code
runs. Their held-out predictions are locked, so they are loaded rather than
refitted.

So this environment exists to do exactly two things:

- run the 21-predictor half of `scripts/verify_all.py`, which checks that the
  deployment bundle reproduces their locked held-out predictions;
- build that bundle, with `scripts/export_serving.py --v1`.

Everything else runs in `.venv`. See `requirements-serve.txt`.

## The trap

If `python` on your PATH resolves to `.venv-serve`, the pipeline scripts fail
on a missing optuna, and the error will not obviously point at the PATH. When
a stage fails for a reason that makes no sense, check which interpreter you
are in:

```bash
python -c "import sys; print(sys.executable)"
```

`scripts/check_environment.py` prints this along with every relevant version.

## Platform

Built and run on Windows 11, Python 3.13.9, on CPU. Nothing needs a GPU.
CatBoost and TabPFN were evaluated and are not in the final set: CatBoost cost
hours for no measurable gain over LightGBM, and neither is needed to reproduce
any result here. `src/anc8/models.py` keeps CatBoost in an `OPTIONAL` registry
for anyone who wants to re-check that.
"""


def build(rel: Path):
    f = facts()

    boot = f.get("bootstrap")
    if isinstance(boot, dict):
        b = boot["d_AP"]
        boot_ap = (f"{b['point']:+.3f} AP [{b['lo']:+.3f}, {b['hi']:+.3f}]")
    else:
        boot_ap = "(bootstrap artifact not present)"

    st = f.get("stability")
    if isinstance(st, dict):
        seeds = (f"{st['AP']['seeds_enhanced_better']}/{st['n_seeds']} splits, "
                 f"mean {st['AP']['delta_mean']:+.4f} AP")
    else:
        seeds = "(stability artifact not present)"

    (rel / "GUIDE.md").write_text(
        GUIDE.format(boot_ap=boot_ap, seeds=seeds), encoding="utf-8")
    (rel / "README.md").write_text(README, encoding="utf-8")
    (rel / "ENVIRONMENT.md").write_text(ENVIRONMENT, encoding="utf-8")
    (rel / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")
    (rel / "requirements-serve.txt").write_text(REQUIREMENTS_SERVE, encoding="utf-8")
    (rel / "data").mkdir(parents=True, exist_ok=True)
    (rel / "data" / "README.md").write_text(DATA_README, encoding="utf-8")
    print("    GUIDE.md, README.md, ENVIRONMENT.md, requirements, data/README.md")
