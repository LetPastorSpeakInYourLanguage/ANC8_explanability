# The model library: what it found, and what is worth pursuing

The study's planning studio runs on three models: logistic regression, random forest and
XGBoost on the 21 predictors, at ANC1+, ANC4+ and ANC8+. Before settling on them, the study
built a much larger model library to test whether more predictors, more model families,
recalibration, ensembles or neural networks would do better. This file sets out what that
library found and which directions are still open, as a starting point for later papers.

Everything below is measured on the 1,375 held-out women that no model saw while it was built,
weighted to stand for all women. Intervals are 95%, from 500 resamples of whole survey clusters
within strata; differences between two models are paired (the same resamples for both).
`tables/` holds every number; `record.ipynb` draws the figures from the tables alone;
`reproduction_full/` rebuilds the whole library from the survey file.

## 1. What was built

- **458 of 501 planned models finished.**
- **Eleven model families**: logistic regression, elastic-net and spline logistic regression,
  random forest, extra trees, XGBoost, LightGBM, histogram gradient boosting, explainable
  boosting (EBM), a small neural network (MLP), and CatBoost.
- **Four predictor sets**: the full candidate pool (86 predictors after removing near-duplicates),
  the 21, a short set and a parsimonious set chosen by forward selection.
- **Three rungs**: ANC1+, ANC4+ and ANC8+.
- **Every tuned model recalibrated two ways**: isotonic and Platt.
- **Ensembles**: stacked and cumulative-link, over every family and over the three- and
  four-model lineups.
- **Two neural networks**: a ladder transformer and a contact-sequence encoder-decoder.

## 2. What it found

### The models are close

At ANC8+ (chance: 16% of held-out women reach eight visits), the best tuned models on any set
all sit between 0.43 and 0.44 average precision, with intervals from about 0.35 to 0.54 that
overlap almost entirely:

| Set | Model | Held-out AP (95% interval) |
|---|---|---|
| The 21 | MLP | 0.437 (0.344-0.543) |
| Full pool | XGBoost | 0.436 (0.351-0.524) |
| Full pool | Logistic regression | 0.434 (0.347-0.542) |
| The 21 | CatBoost | 0.434 (0.347-0.535) |
| Full pool | Explainable boosting | 0.434 (0.349-0.530) |

Against logistic regression on the same set and rung, only 3 of 114 tuned models were reliably
better (paired interval above zero), and 9 were reliably worse (`tables/versus_logistic.csv`).
**At this sample size, no model family reliably beats logistic regression.** This is why the
study keeps the three models of its 21-predictor analysis.

### More predictors buy little (the ablation)

Median difference in held-out AP from the same model on the 21 (`tables/predictor_sets.csv`):

| Set | ANC1+ | ANC4+ | ANC8+ |
|---|---|---|---|
| Full pool (86) | +0.017 | +0.018 | -0.001 |
| Short set | 0.000 | -0.018 | 0.000 |
| Parsimonious set | -0.001 | -0.004 | -0.021 |

- **ANC1+ and ANC4+:** the full pool adds 1 to 2 points.
- **ANC8+:** it adds nothing. The rung the study is built around is predicted as well by the
  21 as by all 86 candidates.
- **The short sets:** they keep most of the accuracy with far fewer questions.

**How the sets were chosen** (`tables/predictor_value/`, `tables/duplicates/`, `tables/parsimonious/`):

- **The candidate pool.** Every one of the survey's 6,648 columns was screened, and 95 were
  admitted as candidates.
- **Near-duplicates.** Ten were near-duplicates of another candidate (for example, wealth as a
  quintile and as a score), and two were exact recodings of the 21's own constructs. Dropping
  those twelve and adding the 21's three constructs left 86.
- **Forward selection.** Selection was repeated over five seeds and admitted a predictor only if
  it added at least 0.005 AP on at least four of the five. It found very few strong predictors:
  - **ANC1+:** the wealth score and region.
  - **ANC4+:** the wealth score and pregnancy order, then region and whether the pregnancy was
    wanted.
  - **ANC8+:** the wealth score and region, then six more (decisions on large purchases,
    pregnancy intention, the mother's occupation, children ever born, and two measures of
    travel time to a health post).

### Recalibration

- **Platt scaling cannot change the ranking**, so its AP is identical. It corrects over- or
  under-confidence. Of 120 models, 22 had a calibration slope below 0.8 (too confident). After
  Platt, 106 of 120 sat within 0.8 to 1.25.
- **Isotonic scaling cost ranking accuracy:** AP changed by -0.049 to -0.004 and was reliably
  worse in 118 of 120 models. Its steps tie together women the model had ranked apart, and with
  5,518 development women the steps are fitted on too few.

### XGBoost's overconfidence

XGBoost was the most overconfident model, and more so with more predictors. Its calibration
slope at ANC8+ (1 is honest; below 1 means its high chances are too high and its low chances
too low):

| Set | ANC1+ | ANC4+ | ANC8+ |
|---|---|---|---|
| Full pool | 0.96 | 0.84 | **0.62** |
| Parsimonious | 0.79 | 0.89 | **0.61** |
| Short | 1.03 | 0.99 | 0.78 |
| The 21 (search-tuned) | 1.20 | 0.94 | 0.99 |
| The 21 (the study's grid) | 1.03 | 0.85 | 0.84 |

Platt scaling brought the full-pool ANC8+ model from 0.62 to 0.88 without changing its ranking.
**If XGBoost is used to give chances rather than only to rank women, it should be
Platt-recalibrated.** The study's own models on the 21 are closer to honest (0.84), which is
one more reason for the 21.

### Ensembles

- **Stacked ensemble** (a logistic regression over the best models' predictions): changed AP by
  -0.007 to +0.031 against the single model a user would have picked (the best on development).
  Its gain was reliably above zero in 1 of 30 cases.
- **Cumulative-link ensemble** (the best model refitted at contact thresholds 1 to 10, forced to
  fall as the threshold rises, pooled and mapped back to a chance): changed AP by -0.049 to
  +0.003, reliably worse in 23 of 29. Pooling the neighbouring thresholds cost more than they
  lent.

### Neural networks and their attention

- **Accuracy:** against the best tuned model on the same set and rung, the networks changed AP
  by -0.063 to -0.001. They never beat it, at far higher cost (`tables/networks.csv`).
- **They never contradict the ladder.** They predict all three rungs together, so no woman
  was ever given a higher chance of eight visits than of four. Three separate XGBoost models did
  that for 0.4% of held-out women.
- **Where they look.** The ladder transformer's attention, summed by planning concept, falls
  most on household wealth (15%), partner and household (14%) and women's say in decisions
  (12%), then information and media (9%) and age and pregnancy history (8%).
- **What changes along the visits.** The contact-sequence network attends to household wealth
  for the first few contacts and shifts to partner and household for the later ones. This
  hints that starting care is about money, and continuing it is about the household. It is a
  hypothesis worth testing, not a finding: attention shows what a network used, not what
  causes anything.

### Tuning

Notebook 2's prespecified grids (4, 48 and 64 settings for the three models) matched the
longer Optuna searches (40 to 60 trials) on held-out women, better in 6 of 9 cells
(`tables/tuning/grid_vs_search.csv`). The searches' higher development scores were the search
fitting its own folds. One-step checks of each setting (`tables/tuning/ablation_*.csv`) show
most settings barely matter.

### CatBoost

Only 6 of 36 planned CatBoost models finished: the tuned models on the full pool and the 21,
run on a Colab GPU. Its recalibrations, and the short and parsimonious sets, did not. Where it
finished, it sits with the other boosted trees and is **well calibrated** (slopes 0.87 to 1.03),
far better than XGBoost at ANC8+ on the same full pool (0.87 against 0.62):

| Set | ANC1+ | ANC4+ | ANC8+ |
|---|---|---|---|
| Full pool | 0.920 (0.891-0.951) | 0.808 (0.743-0.866) | 0.432 (0.347-0.535) |
| The 21 | 0.916 (0.882-0.946) | 0.796 (0.726-0.860) | 0.434 (0.347-0.535) |

## 3. What is worth pursuing

1. **Finish CatBoost.** Most of the 21 are categories, and CatBoost handles categories natively
   rather than through one-hot or integer codes, and it was already better calibrated than
   XGBoost where it finished. The remaining 30 runs need a GPU (`reproduction_full/`, notebook 08).
2. **Platt-recalibrated XGBoost for chances.** A small, safe change wherever the studio or a
   paper reports XGBoost's probabilities rather than its ranking, most of all at ANC8+.
3. **Explainable boosting as a second additive model.** It matched the best models (0.434 at
   ANC8+ on the full pool) and splits every prediction exactly, like logistic regression, but its
   effects can bend: for example, travel time that matters up to an hour and then stops mattering.
   A four-model build of the studio exists (branch `studio-ebm`), with the planner's levers
   computed by both models side by side.
4. **Test the attention hypothesis.** "Starting care is about wealth, continuing is about the
   household" can be tested directly with the continuation steps (1 to 4, 4 to 8) as outcomes.
5. **The networks with more data.** Their one clear advantage, never contradicting the ladder,
   matters for planning. Pooled survey rounds could give them the size to compete on accuracy
   as well.
6. **A short screening set for ANC1+ and ANC4+.** Two to four predictors (the wealth score,
   region, pregnancy order and intention) keep most of the accuracy. A two-minute question
   set for outreach is within reach.
7. **Another survey round.** Every accuracy figure here comes from one round. The first test of
   any of this work elsewhere is whether it holds on the next one.

## Files

```
FUTURE_WORK.md              this file
research_record/README.md   the record's own summary, generated from its tables
research_record/tables/     every model: status, metrics and intervals, calibration,
                            ensembles, networks, predictor sets, CatBoost, tuning,
                            the predictor-value study, duplicates, parsimonious searches
research_record/record.ipynb   the figures, from the tables alone
reproduction_full/          notebooks that rebuild the whole library from ETIR8AFL.DTA
```

No woman's record or prediction is included, only aggregates (the DHS licence).
