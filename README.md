# Predicting antenatal care attainment in Ethiopia (EDHS 2024-25)

What best predicts whether a woman completes **eight or more antenatal care
contacts (ANC8+)**, and the earlier rungs **ANC1+** and **ANC4+**, in the
2024-25 Ethiopia Demographic and Health Survey (Individual Recode, 6,893
women).

Three analyses carry the study:

| | Question | Where |
|---|---|---|
| **1. Predictor value** | Which predictors carry the prediction of each rung, and how many are needed? How does each predictor's value change from ANC1+ to ANC8+? | `docs/PREDICTOR_VALUE.md` |
| **2. Two prediction horizons** | Does the answer change once a woman has started ANC, and what does knowing her first contact was early add? | `docs/HORIZONS.md` |
| **3. The Tigray war** | What did the war do to antenatal care, against every other region? | `docs/WARTIME.md` |

`FINDINGS.md` is the technical hub; `docs/README.md` maps every document by
reader; `docs/POLICY_BRIEF.md` is the brief for the Ministry of Health.

---

## Headline results

**How many predictors.** Every predictor set was compared on the same
held-out women, with the model held fixed, from 1 predictor up to the full
candidate pool of 88. The 21-predictor set specified in advance is one of
those sets.

- **ANC8+: 7 to 8 predictors are enough.** Wealth, region, pregnancy
  intention, the woman's work and say in household decisions, and access to a
  health post predict as well as all 21 or all 88. Of the 21, 14 add nothing
  to ANC8+ once the rest are in.
- **ANC1+ and ANC4+: the full pool is best.** It beats the 21 on held-out
  women (+0.014 and +0.023 AP, intervals excluding zero). No single extra
  variable matters much alone, but together they do.
- **The same few lead everywhere.** The continuous wealth score is chosen
  first in every run, and region in every run. Pregnancy intention matters
  for staying in care, not for reaching it.

**Up the ladder.** Completing care is harder to predict than reaching it
(AUROC 0.83 → 0.79 → 0.76). Region and wealth become far more valuable at
ANC8+. Household position matters most for reaching care at all.

**The two horizons.** Once a woman has started ANC, whether her first contact
was early is the strongest predictor after wealth. For ANC4+, wealth plus
early initiation (2 predictors) beats all 21 on held-out women. A model
fitted before ANC serves the entry women as well as one fitted on them alone.

**The Tigray war.** About one wartime pregnancy in five in Tigray received
no antenatal care, against one in thirteen after the ceasefire: 13 points
beyond the change in other regions. Access recovered; eight-contact
completion did not.

---

## Layout

```
1_ANC8_outcome_and_predictor_ascertainment.ipynb   cohort, outcome and the 21 constructs
2_ML_readiness_and_audit.ipynb                     21-predictor models at both horizons
3_ANC8_deep_EDA_and_feature_reascertainment.ipynb  screening the survey; the candidate pool
4_ANC8_expanded_modelling.ipynb                    model families on the candidate pool

src/anc8/        design, cohorts, screening, features, selection, models, tuning, metrics
scripts/         every runnable stage and analysis
outputs/         results, per analysis (see docs/README.md)
docs/            the write-ups
app/             Next.js frontend + Python serverless API
release/         the reproduction package (built by scripts/build_release.py)
```

---

## Reproducing

```bash
# The candidate pool (screens all 6,648 columns)
python scripts/build_notebook3.py
python scripts/execute_nb.py 3_ANC8_deep_EDA_and_feature_reascertainment.ipynb

# Model families on the pool, per outcome
python scripts/run_pipeline.py --outcome anc8plus        # and anc1plus, anc4plus

# 1. Predictor value
python scripts/run_feature_value.py --cohort full --outcome anc8plus   # and the other rungs
python scripts/run_why21_heldout.py
python scripts/run_21_models_heldout.py      # the 21 under logistic, random forest, XGBoost
python scripts/run_predictor_matrix.py
python scripts/run_ladder_analysis.py

# 2. The two horizons
python scripts/run_feature_value.py --cohort entry --outcome anc8plus  # and anc4plus
python scripts/run_horizons.py

# 3. The Tigray war
python scripts/run_wartime_analysis.py

# Documents, figures, app data, checks
bash scripts/finish_all.sh
python scripts/run_tests.py
```

Use the analysis environment for all of these. `.venv-serve` is a pinned
environment that exists only to load the 21-predictor pipelines for their
deployment bundle (`scripts/export_serving.py --v1`); if `python` resolves to
it, the analysis scripts fail. `release/GUIDE.md` walks through everything
step by step.

The web app, locally:

```bash
powershell -ExecutionPolicy Bypass -File dev.ps1     # Windows
bash scripts/dev.sh                                  # macOS / Linux
```

Then open <http://localhost:3000>.

---

## Caveats

Research and educational software. Not clinical advice, not validated for
decisions about individual women, and based on one survey round in one
country. A predicted probability describes a rate among women with similar
recorded characteristics; nothing here estimates a causal effect. What the
analysis cannot support is set out in `docs/LIMITATIONS.md`.
