# Rebuilding the whole model library

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
