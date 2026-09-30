# The research record: everything the model library found

The study's models are three, logistic regression, random forest and XGBoost on the 21
predictors at each rung (`reproduction/` rebuilds them). To get there the study built a much
larger model library and ran the studies that decided what to keep. This folder records all
of it as aggregate results, so the work can be cited, checked and taken up again.
`reproduction_full/` rebuilds every number here from the survey file.

No woman's record or prediction is in this folder: only metrics, intervals, paired
differences, predictor lists and step tables. Intervals come from 500 resamples of whole
survey clusters within strata of the 1,375 held-out women; differences are paired (the same
resamples for both models).

## What was built

- **458 of 501 planned models** finished: 11 model families
  (CatBoost, Elastic net logistic, Explainable Boosting, Extra Trees, HistGradientBoosting, LightGBM, Logistic regression, MLP, Random Forest, Spline logistic, XGBoost), each tuned by an Optuna search on four predictor sets (the full pool
  of 86 duplicate-free candidates, the 21, the short set and the parsimonious set) at ANC1+,
  ANC4+ and ANC8+; each recalibrated two ways (isotonic and Platt); stacked and
  cumulative-link ensembles over every family and over the three- and four-model lineups; and
  two neural networks (a ladder transformer and a contact-sequence encoder-decoder).
- **The study's own nine models** (three models on the 21, notebook 2's grids): held-out AP
  anc1plus Logistic regression 0.914, anc1plus Random Forest 0.911, anc1plus XGBoost 0.908, anc4plus Logistic regression 0.782, anc4plus Random Forest 0.793, anc4plus XGBoost 0.805, anc8plus Logistic regression 0.428, anc8plus Random Forest 0.406, anc8plus XGBoost 0.437.

Everything is in `tables/library_cells.csv`, one row per planned model, with its status.

## What it found

**The models are close.** At ANC8+ the five best tuned models on any set:

| Set | Model | Held-out AP (95% interval) |
|---|---|---|
| 21-predictor set | MLP | 0.437 (0.344-0.543) |
| Full pool | XGBoost | 0.436 (0.351-0.524) |
| Full pool | Logistic regression | 0.434 (0.347-0.542) |
| 21-predictor set | CatBoost | 0.434 (0.347-0.535) |
| Full pool | Explainable Boosting | 0.434 (0.349-0.530) |

Their intervals overlap widely. Against logistic regression on the same set and rung
(`tables/versus_logistic.csv`, paired), 3 of 114 tuned models were reliably better
(interval above zero) and 9 reliably worse.

**More predictors buy little.** Median difference from the same model on the 21, held-out AP
(`tables/predictor_sets.csv`, with each model's paired interval):

| set_label        |   anc1plus |   anc4plus |   anc8plus |
|:-----------------|-----------:|-----------:|-----------:|
| Full pool        |      0.017 |      0.018 |     -0.001 |
| Parsimonious set |     -0.001 |     -0.004 |     -0.021 |
| Short set        |     -0     |     -0.018 |     -0     |

The full pool adds about 0.01-0.02 at ANC1+ and ANC4+ and close to nothing at ANC8+; the
short and parsimonious sets hold most of the 21's accuracy with far fewer questions.

**Recalibration.** Platt scaling cannot change the ranking, so its AP difference is zero; it
corrects over- or under-confidence (calibration slope, `tables/calibration.csv`). Isotonic
scaling changed AP by -0.049 to -0.004, and was reliably worse (interval below zero)
in 118 of 120 models: its steps tie women the model had ranked apart, and with
5,518 development women the steps are fitted on too few. Platt is the one worth keeping where
a model is overconfident (XGBoost at ANC8+ on the full pool: slope 0.62 before, 0.88 after).

**Ensembles.** The stacked ensemble changed AP by -0.007 to +0.031 against the single
model a user would have picked (the best on development); its gain was reliably above zero in
1 of 30 cases. The cumulative-link ensemble (the best model refitted at several
contact thresholds and pooled) changed AP by -0.049 to +0.003, reliably worse in 23 of
29: pooling thresholds, and the isotonic map back to a chance, cost more than
neighbouring thresholds lent (`tables/ensembles.csv`).

**Networks.** Against the best tuned model on the same set and rung, the networks changed AP
by -0.063 to -0.001, never above it (`tables/networks.csv`): competitive at best, at far
higher cost.

**Tuning.** Notebook 2's prespecified grids (4, 48 and 64 settings) matched the longer Optuna
searches on held-out women (`tables/tuning/grid_vs_search.csv`); the searches' higher
development scores were the search fitting its own folds.

**How the sets were chosen.** `tables/predictor_value/` holds the predictor-value study per
rung (forward selection over repeated splits, the tiers, what each of the 21 adds and costs,
the held-out check); `tables/duplicates/` the near-duplicate analysis that took the pool from
95 to 86; `tables/parsimonious/` the parsimonious searches' lists.

## Left to do: possible advantages for later work

- **CatBoost.** 6 of 36 planned CatBoost models finished (the tuned models
  on the full pool and the 21, run on a Colab GPU); its recalibrations and the short and
  parsimonious sets did not. On the cells that finished it sits with the other boosted trees
  (`tables/catboost.csv`). Its native handling of categories, most of the 21, is the reason to
  finish it: it may use them better than one-hot or integer codes do.
- **Platt recalibration for the tree models** where the slope is far from 1 (XGBoost at ANC8+),
  if the models are used to give chances, not only to rank.
- **The networks with more data.** They predict all three rungs together, or contact by
  contact; pooled survey rounds could give them the size they need.
- **A second survey round** to check that the accuracy travels, for every model here.

## Files

```
tables/library_cells.csv    every planned model: status, metrics with intervals, settings
tables/calibration.csv      each model against its isotonic and Platt recalibrations
tables/ensembles.csv        each ensemble against the best single model
tables/predictor_sets.csv   each model on the four sets, against the 21
tables/networks.csv         the networks against the best tuned model
tables/versus_logistic.csv  every tuned model against logistic regression, paired
tables/catboost.csv         the CatBoost runs
tables/tuning/              grid against search; one-step setting checks
tables/predictor_value/     the predictor-value study, per rung
tables/duplicates/          the near-duplicate analysis
tables/parsimonious/        the parsimonious searches
record.ipynb                the figures, from these tables alone
```
