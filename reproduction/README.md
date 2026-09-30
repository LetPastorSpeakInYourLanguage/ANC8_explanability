# Reproducing the ANC model library

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
