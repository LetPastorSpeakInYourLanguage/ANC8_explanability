# Reproducing the study's models

Notebooks that rebuild, from the Ethiopia DHS 2024-25 Individual Recode, the models the
study's planning studio runs on: the cohort and the ANC1+, ANC4+ and ANC8+ outcomes, the 21
predictors, the split, logistic regression, random forest and XGBoost at each rung (tuned over
the grid the study fixed in advance), their evaluation, their explanations and the planner's
levers. About half an hour in all.

**Start with `notebooks/00_start_here.ipynb`.** It lists what to install, where the survey
file goes and the run order. To run everything from the command line:
`python scripts/run_notebooks.py` (executed copies go to `executed/`).

## How the notebooks check themselves

Each notebook ends with checks against the study's own results in `reference/`: the content
fingerprints of the analysis frames, the digests of the split, and every model's setting and
development and held-out average precision, its explanations and the levers' effects. A run on
the study's software versions reproduces them exactly.

## Everything else the study tried

`reproduction_full/` rebuilds the whole model library (other predictor sets, eleven model
families, recalibration, ensembles, networks), and `research_record/` records what all of it
found. Neither is needed for these models.

## Layout

```
notebooks/        00-09
src/anc8/         the analysis package (every step is a documented function)
scripts/          the stage scripts some notebooks run, and run_notebooks.py
reference/        the study's results, for the checks
executed/         the notebooks as run from the survey file on the study's machine (every check passed)
data/             put ETIR8AFL.DTA here (not included; see data/README.md)
requirements.txt  the software versions the study used
```
