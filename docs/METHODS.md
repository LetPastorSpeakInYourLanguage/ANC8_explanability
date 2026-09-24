# Methods

Written for someone who has to decide whether to believe the results, or to
extend them. Every choice below is one that could reasonably have gone
another way; the reasoning is given so you can disagree with it specifically
rather than in general.

---

## 1. Data, cohorts and outcomes

**Source.** Ethiopia Demographic and Health Survey 2024-25, Individual Recode
(`ETIR8AFL.DTA`), 6,648 columns.

**Outcome.** The number of antenatal contacts for the most recent pregnancy
(`m14_1`), thresholded three ways:

| Rung | Threshold | Weighted prevalence (all births) |
|---|---|---|
| ANC1+ | ≥ 1 | 77.6% |
| ANC4+ | ≥ 4 | 52.4% |
| ANC8+ | ≥ 8 | 19.2% |

The three are nested by construction and the pipeline asserts it: every woman
with ANC8+ has ANC4+ has ANC1+.

**Cohorts.** Three, all on one development / held-out split:

- **All births, 6,893 women** — every woman whose most recent pregnancy has a
  recorded contact count. The main analysis and the first prediction horizon
  (before ANC starts). Women with a missing count are excluded rather than
  imputed: the outcome cannot be inferred from the predictors without
  circularity.
- **ANC entry, 5,001 women** — those who started ANC and know when their
  first contact was. The second prediction horizon. Every woman in it has
  ANC1+, so only ANC4+ and ANC8+ are defined.
- **Last 24 months, 5,037 women** — the DHS-8 reference period for the ANC
  indicator. A sensitivity check, and the validity check against the official
  report (national ANC4+ 53.0% against 53.0%).

Birth timing comes from the pregnancy history (`p19_01`, `p3_01`), which,
unlike the live-birth history, has a row for a stillbirth.

---

## 2. Survey design, and why it governs everything

The DHS is a stratified, multi-stage cluster sample. Three consequences run
through every stage:

**Weights.** Every estimate uses `v005 / 1e6`, in metrics as well as in
descriptives: AP, AUROC, Brier, calibration-in-the-large and calibration
slope. Every substantive claim here is about Ethiopia, not about the sample.

**Clusters.** Women in one enumeration area (`v021`) resemble each other. If
some are in training and others in test, the model can memorise the area and
the test score is optimistic. So **every split and every cross-validation
fold is grouped by PSU**, and the test suite checks that no PSU spans a fold.

**Strata.** The held-out set is built by sampling PSUs *within* stratum
(`v022`), so the design structure survives the split.

**Uncertainty.** Confidence intervals come from a stratified PSU bootstrap —
resampling clusters within strata, not individuals. Every comparison between
two sets or two models is **paired**: the same resampled women score both.

**One split for everything.** The development / held-out partition (5,518 /
1,375, seed 2026) is drawn once on the full cohort. The ANC-entry and 24-month
cohorts use the same partition restricted to their women (4,017 / 984 and
4,040 / 997); `src/anc8/cohorts.py` asserts that the ANC-entry partition
matches it woman for woman. Every outcome and horizon therefore shares folds
and held-out women, so a difference between them is the outcome or horizon,
not the sample.

---

## 3. The predictors

### The 21-predictor set

21 constructs chosen in advance from the literature and screened for timing,
in four domains:

| Domain | Predictors |
|---|---|
| Maternal and sociodemographic | age, education, union status, occupation, partner's education, partner's occupation, healthcare decision participation |
| Household and socioeconomic | wealth quintile, residence, region, household size, religion, weekly media count, internet use, health insurance |
| Pregnancy and obstetric | pregnancy order, preceding interval, pregnancy intention, previous pregnancy outcomes |
| Health service and access | travel time to hospital or health centre, transport mode |

In the predictor-value study, maternal age enters as **age at the birth**
rather than at interview: for the 28% of women who gave birth 2-3 years
before interview, current age is that far from the pregnancy.

### The full candidate pool

Every one of the 6,648 IR columns was screened against ANC8+ **on the
development fold only**, and each candidate was then checked on three
grounds:

**Timing (temporality).** A variable must describe something known before or
early in the pregnancy. Several DHS variables predict ANC8 superbly and are
unusable because they encode the care itself or come after it: timing of the
first antenatal contact (`m13`), a facility visit in the last 12 months
(`v394`), place of delivery, tetanus doses, HIV testing (`v781`),
contraception measured at interview. `src/anc8/features.py` lists every
exclusion with its reason. First-contact timing is admitted only at the
ANC-entry horizon, as `early_anc`.

**Availability.** A variable a health system cannot observe at prediction
time is not usable, however strong.

**Sparsity.** Variables with too few observations were dropped, with the
threshold set before seeing held-out data.

Screening is itself a decision made on data, so it was audited: all 61
admitted variables survive development-only screening, with a largest AUC
shift of 0.013 (`outputs/enhanced/screening_sensitivity.json`).

The pool has 95 columns, which are **85 distinct variables**: the survey's
raw codes and derived relabelled versions (`region` and `v024`,
`wealth_quintile` and `v190`) both entered. Duplicates are identified with
Theil's U in both directions (`scripts/run_redundancy_analysis.py`);
importance is always reported with each duplicate folded into its twin. The
predictor-value study uses **88 candidates**: the 85 plus the three
constructs that exist only in the 21-predictor set (household size, travel
time, weekly media count). Number of living children is excluded because it
falls when the index child dies, which leaks what happened after the birth.

---

## 4. The predictor-value study

The question is which variables carry the prediction, not which model is
best, so the model is **held fixed**: logistic regression (L2). It has
almost nothing to tune, so it cannot favour one predictor set through
settings searched on another. Its one setting, the regularisation strength
C, is chosen **per set** from a common grid (0.003, 0.01, 0.1, 1): a single
fixed C favours small sets or large ones depending on the value (the 88 score
0.478 at C = 1 and 0.508 at their own best).

**Scoring.** Development women only, 5 repeated PSU-grouped,
stratum-preserving 5-fold splits. Each fold's preprocessor is fitted once on
all candidates and a subset is scored by slicing its columns — exact, not an
approximation, because every preprocessing step is column-wise; verified to
0.0 AP against the full pipeline (`src/anc8/selection.py`).

**The bar.** A variable counts only if it changes AP by at least **0.005 on
average and on at least 4 of the 5 splits**. Fixed before any selection
result was seen.

**The stages** (`scripts/run_feature_value.py`), run per outcome and horizon:

| Stage | What | Output |
|---|---|---|
| 0 | The 21 on their own: drop each from the 21; the full greedy path within the 21 (1…21); the 21 without every member whose removal costs nothing | `drop_one_within_21.csv`, `forward_within_21.csv`, `drop_group_21.csv` |
| 1 | Each other candidate added alone to the 21; all of them stacked in order of gain; each candidate removed from the full pool | `add_one_to_21.csv`, `cumulative_from_21.csv`, `remove_one_from_all.csv` |
| 2 | Forward selection from nothing over the full pool, stopping at the first step that fails the bar. Tier 1 = steps until 90% of the full pool's lift over prevalence; tier 2 = the further steps that pass. For ANC8+, the selection is repeated on 10 PSU-bootstrap resamples | `forward_steps.csv`, `selection_frequency.csv` |
| 3 | Tier 1, tier 1+2, the 21 and the full pool fitted on development women and scored **once** on held-out women, with logistic regression and LightGBM (tuned per set on development folds), paired bootstrap against the 21 | `heldout.csv`, `heldout_bootstrap.json` |

`scripts/run_why21_heldout.py` adds the held-out test of the reduced 21
(best k of the 21, the 21 without its non-contributors) found in stage 0.
`scripts/run_21_models_heldout.py` scores the 21 under three model families
-- logistic regression, random forest and XGBoost, the two tree models tuned
on development folds (20 trials) -- for every cohort and rung, with a paired
bootstrap against logistic regression (`heldout_21_models.csv`).

**Comparing rungs.** AP has a floor at the prevalence, so AP differences are
not comparable across ANC1+, ANC4+ and ANC8+. Every predictor's value is
therefore also expressed as a share of the rung's **ceiling** — the full
pool's development AP minus the prevalence
(`scripts/run_predictor_matrix.py`). For members of the 21 the value is the
AP lost when dropped from the 21; for the rest, the AP gained when added to
it: one quantity, one scale, for all 88.

**Importance, three ways** (`scripts/run_ladder_analysis.py`), as an
independent view of the same question: exact EBM contributions, SHAP on
XGBoost, and drop-one AP loss from the full pool, each normalised to a share
within the rung. A shift across rungs is reported only when at least two
methods agree. SHAP uses XGBoost at every rung: the tree explainer mishandles
HistGradientBoosting's native categorical splits.

---

## 5. The two prediction horizons

`scripts/run_horizons.py`, for ANC4+ and ANC8+:

1. **What early ANC adds.** `early_anc` added to the 21, to the ANC-entry
   selected set and to the full pool: development gain on the 5 splits, and
   held-out gain on the 984 ANC-entry women with a paired bootstrap.
2. **Whether the same predictors carry the prediction.** Tier membership and
   marginal values at both horizons, side by side.
3. **Whether a separate model is worth fitting.** The 21 and the full pool
   fitted on all development women (before ANC) and on the ANC-entry
   development women, both scored on the same 984 held-out ANC-entry women.

---

## 6. The Tigray war

`scripts/run_wartime_analysis.py`. Each pregnancy is dated from the
pregnancy history: the month it ended and the eight before. A pregnancy is
**wartime** if at least 3 of its 9 months fall inside the Tigray war window
(3 Nov 2020 – 2 Nov 2022, cited in `docs/conflict_windows.csv`) and
**post-war** if it was conceived after the ceasefire; those in between are
dropped. The survey records ANC only for births from about mid-2021, so no
pre-war pregnancy is observed.

The estimate is a **difference-in-differences**: Tigray's post-war minus
wartime change, minus the same change in regions without major conflict over
the same calendar periods. The comparison change is **averaged within each
region** and weighted by region, not taken from the pooled mean: the mix of
regions differs between periods, and pooling produces a spurious 5-point fall
(Simpson's paradox). Intervals: stratified PSU bootstrap (1,000 resamples)
over Tigray and the comparison regions together. Robustness: the war window
shifted ±3 months; Oromia and Benishangul-Gumuz (which had their own
conflicts) added to the comparison group. Every region's level in both
periods is reported alongside (`region_by_war_period.csv`).

Whether war exposure changed the effect of wealth or distance on ANC4+ is
tested in the three northern regions with a weighted logistic regression,
region fixed effects and cluster-robust errors.

---

## 7. Supporting analyses

These answer "could the result be an artefact of the modelling?" and are
reported in full in the Evidence view and the files named.

- **Model families.** Ten families tuned with Optuna's TPE sampler on the
  shared folds and the same weighted-AP objective: logistic regression,
  elastic net, spline logistic, random forest, extra trees, XGBoost,
  LightGBM, histogram gradient boosting, a multilayer perceptron and an
  Explainable Boosting Machine; plus a stacked ensemble, a cumulative-link
  ordinal arm and calibrated variants. The **champion is chosen on
  development folds** and then scored once on held-out women.
- **Tuning ablation.** Each tuned model refitted at library defaults, and each
  setting moved one step with the others fixed
  (`hyperparameter_ablation.csv`).
- **Preprocessing ablation.** Imputation and encoding variants with
  everything else fixed (`preprocessing_ablation.csv`).
- **Calibration.** Platt and isotonic maps, fitted on inner folds so the
  calibrator never sees the predictions it is judged on.
- **Repeated splitting.** 20 independent PSU splits of all women, each refit
  from scratch, the 21 against the full pool with the model fixed
  (`stability_summary.json`).

**The Explainable Boosting Machine** is the model the app explains: its
prediction is an intercept plus one learned curve per predictor, so
attribution is exact rather than approximated. Its categorical predictors are
ordinal-encoded, so a regional effect read off a single shape function is
less trustworthy than the model's overall predictions; read regional effects
from the descriptive cascade.

---

## 8. Metrics

**Average precision (AP)** is the headline within a rung, because it focuses
on the rarer outcome. **AUROC** and **AP lift over prevalence** are used
across rungs. **Calibration** is reported as calibration-in-the-large,
calibration slope (statsmodels GLM) and the integrated calibration index.
**Decision-curve analysis** gives net benefit across thresholds. Operating
thresholds are set on development data only.

---

## 9. Reporting

The analysis follows **TRIPOD+AI** for reporting and was self-assessed against
**PROBAST+AI** for risk of bias. Both papers are in the repository. The
places where it would be marked down are stated in `docs/LIMITATIONS.md`.

---

## Appendix: deployment

The web app's Predict tab offers every deployed model. The user chooses the
outcome (ANC1+, ANC4+ or ANC8+), the horizon (before ANC starts, or at the
first visit) and a model, and sees each model's held-out AP and AUROC. The
study's recommended model is marked and chosen by default:

| Outcome | Before ANC starts | At the first ANC visit |
|---|---|---|
| ANC1+ | full pool, XGBoost | (every woman there has ANC1+) |
| ANC4+ | full pool, XGBoost | 3 predictors selected from the pool, logistic regression |
| ANC8+ | best 7 of the 21, logistic regression | 7 predictors selected from the pool, logistic regression |

Deployed: the 21-predictor models of ANC8+ at both horizons, the full-pool
models of all three outcomes, and one logistic model per best small set of
the predictor-value study, fitted on the development women at the
regularisation it earned there (`scripts/export_serving.py --small`). Two
full-pool models are not deployed: the ANC4+ explainable boosting model, which
learned interaction terms the serving scorer does not support, and the ANC4+
Extra Trees, whose 63 MB export is over the per-model serving limit.

**Why the models are exported.** Vercel's serverless functions cap at 250 MB
unzipped; loading the fitted pipelines needs scipy, xgboost, numpy, pandas
and scikit-learn, about 341 MB. So `scripts/export_serving.py` converts every
fitted pipeline to plain arrays (tree structures, coefficient vectors, EBM
lookup tables) and `app/api/_lib/scorer.py` evaluates them with numpy alone.

**The fidelity gate.** The exporter refuses to write a bundle whose
probabilities differ from the fitted pipeline's, on every held-out woman,
beyond a tight tolerance; for the 21-predictor models the comparison is
against their locked held-out predictions. The tolerance is a share of rows
(about 1 in 1,375 falls on a float32/float64 knife edge inside XGBoost), so a
systematic error cannot hide inside it.

**XGBoost and sparse zeros.** The 21-predictor pipeline emits a scipy sparse
matrix, and XGBoost treats an unstored entry — any exact zero — as missing.
Scoring densely moved one held-out prediction from 0.159 to 0.577, so the
scorer reproduces sparse semantics (`zero_is_missing`).

**XGBoost and float32.** XGBoost compares inputs to split points in float32,
and its JSON dump prints each split point in its shortest float32 form, which
read back as float64 is a slightly different number. The scorer rounds both
sides to float32; without that, 4% of held-out women took a different branch
in the ANC1+ model (differences up to 0.03).

**In the browser.** The additive models (explainable boosting, logistic
regression; 16 of the deployed models) are ported to TypeScript
(`app/src/lib/ebm.ts`), so they respond as answers change and show exactly
what each answer adds. `scripts/check_ts_parity.py` checks every one against
the Python scorer on all 1,375 held-out women (agreement within 1e-15).

**Reproducibility.** Logistic regression and LightGBM give identical results
on any thread count. XGBoost is deterministic at a fixed thread count but
varies with it (ANC8+ development AP 0.506 to 0.518), so XGBoost figures
reproduce to about 0.01 AP on another machine.
