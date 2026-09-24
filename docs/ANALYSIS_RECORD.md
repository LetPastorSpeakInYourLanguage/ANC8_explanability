# Analysis record

Every analysis in this study, in reading order. Each entry says what we
wanted to know, what we did, how we tested it, what came out, and what
followed from it.

Every technical term used below, such as AP, AUROC, held-out, bootstrap or
tier, is explained in plain language in `docs/GLOSSARY.md`, which also
explains how to read each figure.

---

## 1 · Data and cohorts
<!-- phase: p1 | title: Data and cohorts -->
Who the study is about, what is predicted, and how every result is tested
fairly.

### The outcome and the cohort
<!-- kind: step | figures: fig01_cascade, fig02_regional_cascade | terms: anc-rungs, cohort, weight, cascade -->
**Question.** What exactly is predicted, and for whom?

**What we did.**
- Took the 2024-25 Ethiopia DHS women's file and kept the **6,893 women**
  whose most recent pregnancy has a recorded number of antenatal contacts.
- Defined three nested outcomes on that count: ANC1+, ANC4+ and ANC8+.

**How we tested it.** The code asserts, woman by woman, that ANC8+ implies
ANC4+ implies ANC1+. All figures are survey-weighted.

**What we found.** 77.6% of women reach ANC1+, 52.4% ANC4+ and 19.2%
ANC8+. The biggest loss is between the fourth and eighth contacts: only 37%
of women who reach four go on to eight.

**What changed.** ANC8+ is the main outcome; ANC1+ and ANC4+ are studied as
the earlier rungs of the same ladder.

**Source.** `docs/DATA_AND_COHORT.md`

### One held-out set, for everything
<!-- kind: step | figures: | terms: heldout, cluster, stratum, cv -->
**Question.** How do we test a model fairly?

**What we did.** Split the women once, by survey cluster within stratum
(seed 2026):
- **5,518 for development**, to build, compare and tune;
- **1,375 held out**, scored only at the end.

The same split, restricted to their women, serves the ANC-entry cohort
(4,017 / 984) and the 24-month window (4,040 / 997).

**How we tested it.** The test suite checks that no cluster spans two folds,
and that the ANC-entry partition matches the full split woman for woman.

**What we found.** The held-out set contains only 229 women who
reached ANC8+, so comparisons on it carry wide uncertainty.

**What changed.** Every result in the study is scored on these same women,
and every held-out comparison carries a paired bootstrap interval.

**Source.** `src/anc8/design.py`, `src/anc8/cohorts.py`

### Checked against the official report
<!-- kind: step | figures: | terms: window24, dhs -->
**Question.** Is the outcome defined the way the official survey defines it?

**What we did.**
- Read the *Guide to DHS Statistics* (DHS-8) and the 2024-25 EDHS key
  indicators report.
- Recomputed the report's regional ANC4+ table on its own 24-month window,
  with pregnancy timing taken from the pregnancy history so that stillbirths
  are kept.

**How we tested it.** Our figure against the report's, region by region.

**What we found.** National ANC4+ **53.0% against 53.0%**; 13 of 14 regions
within 0.8 points.

**What changed.** This validates the outcome, weights and region coding. The
24-month window (5,037 women) is kept as a sensitivity check on every result.

**Source.** `docs/DATA_AND_COHORT.md`

---

## 2 · From 6,648 columns to a candidate pool
<!-- phase: p2 | title: The candidate pool -->
Before asking which predictors matter, decide which could legitimately be
predictors at all.

### Screening every survey column
<!-- kind: step | figures: fig14_screening | terms: screening, univariate-auc, temporality -->
**Question.** Which of the survey's 6,648 columns could predict antenatal
care?

**What we did.**
- Excluded, automatically, columns not collected in this round (1,719),
  entirely missing (808), measured at or after the delivery (2,296), observed
  for under half the cohort (1,208) or administrative (28).
- Scored the remaining **577** on their own, on development women only, and
  reviewed each for timing and relevance.

**How we tested it.** The screening was rerun on development women alone and
compared with the whole-cohort run.

**What we found.**
- **61 survey variables admitted**; 507 not admitted, with a median
  univariate AUC of 0.518 (almost no signal), mostly from post-birth modules.
- The strongest legitimate predictor is the **continuous wealth score**
  (univariate AUC 0.755).
- All 61 survive development-only screening; the largest AUC shift is 0.013.

**What changed.** A full candidate pool of 95 columns: the 61, the 21-set
constructs and derived measures such as log travel times and separate media
channels.

**Source.** `outputs/enhanced/candidate_screening.csv`, `docs/PREDICTOR_VALUE.md` §1

### Refusing the variables that record the care itself
<!-- kind: step | figures: | terms: leakage -->
**Question.** Which strong candidates must not be used?

**What we did.** Checked the strongest candidates against when they were
measured.

**How we tested it.** For "visited a health facility in the last 12
months", compared attenders and non-attenders by how recent the birth was.

**What we found.** Among women whose birth was within 12 months, 67% of ANC
attenders report a facility visit against 28% of non-attenders, a gap that
narrows once the birth falls outside the recall window: the outcome being
re-reported. HIV testing, contraception at interview and first-contact
timing are refused for the same reason.

**What changed.** Nine strong candidates refused with written reasons;
first-contact timing admitted only at the ANC-entry horizon.

**Source.** `src/anc8/features.py`

### Merging copies of the same variable
<!-- kind: step | figures: fig24_redundancy | terms: duplicate, importance -->
**Question.** Is any variable in the pool twice?

**What we did.** Searched for pairs carrying the same information, using
Theil's U in both directions, which separates true copies from structurally
missing categories (for example "not applicable" for unmarried women).

**How we tested it.** Refitting without the copies, and restating importance
per variable.

**What we found.** **10 of the 95 columns are copies: 85 distinct
variables.** Removing them changes AP by 0.002, but importance had been split
between copies: travel time to hospital rises from rank 10 to rank 2 once its
copy is counted.

**What changed.** The predictor-value study uses 88 candidates: the 85 plus
the three constructs only the 21-predictor set has. Importance is always
reported with copies merged.

**Source.** `outputs/enhanced/redundancy/`

---

## 3 · Predictor value: how many, and which
<!-- phase: p3 | title: Predictor value -->
The central analysis: which predictors carry the prediction of each rung,
and how many are needed.

### A fair way to compare predictor sets
<!-- kind: step | figures: | terms: logistic, bar, repeated -->
**Question.** How do we compare *variables* without the model or its
settings tipping the scales?

**What we did.**
- **Fixed model:** logistic regression, scored on 5 repeated
  cluster-grouped splits of the development women.
- **Per-set regularisation** from a common grid, because a single setting
  favours small or large sets (the 88 score 0.478 at a light setting and 0.508
  at their own best).
- **The bar**, fixed before any selection result: a variable counts only if
  it changes AP by at least 0.005 on average and on 4 of 5 splits.

**How we tested it.** The fast scorer against the full scikit-learn pipeline:
identical AP.

**What we found.** Nothing yet; this entry is about the method.

**What changed.** Every predictor comparison below uses this setup.

**Source.** `src/anc8/selection.py`

### Dropping each of the 21
<!-- kind: step | figures: fig33_drop_within_21 | terms: drop-one, versions -->
**Question.** Does every member of the 21-predictor set earn its place, at
each rung?

**What we did.** Removed each of the 21 in turn and rescored the rest, for
ANC1+, ANC4+ and ANC8+.

**How we tested it.** AP lost on each of 5 splits.

**What we found.**
- Region, pregnancy intention and wealth carry the 21 at every rung.
- Members that add nothing: **8 of 21 for ANC1+, 10 for ANC4+, 14 for
  ANC8+**. Health insurance, household size, religion, the weekly media count,
  internet use and transport mode add nothing to any rung.

**What changed.** Motivated the question of how many of the 21 are needed.

**Source.** `outputs/feature_value/full/<outcome>/drop_one_within_21.csv`

### How many of the 21 are needed
<!-- kind: step | figures: fig34_why21 | terms: forward-selection, lift -->
**Question.** What is the smallest subset of the 21 that does as well as all
21?

**What we did.** Greedy forward selection within the 21, run all the way to
21, and the 21 without all its non-contributors at once.

**How we tested it.** Development AP as a share of the full pool's lift over
prevalence.

**What we found.**
- **ANC8+:** the path peaks at **7 predictors**, reaching the full pool's
  development AP (0.509), and every further member lowers it; all 21 reach
  0.469.
- **ANC1+ and ANC4+:** the path is flat after about 8-11 predictors; the 21
  are about as good as their best subset.

**What changed.** The reduced sets were taken to the held-out test, because
they were chosen on the same folds they were scored on.

**Source.** `outputs/feature_value/full/<outcome>/forward_within_21.csv`

### What the rest of the pool adds
<!-- kind: step | figures: fig26_add_one, fig27_diminishing_returns | terms: add-one, remove-one, bar -->
**Question.** Of the 67 pool candidates outside the 21, how many add value?

**What we did.**
- Added each **alone** to the 21;
- stacked them all in order of gain;
- removed each one from the full pool.

**How we tested it.** Development AP, gain on each of 5 splits, the +0.005
bar.

**What we found.**
- **ANC1+ and ANC4+:** none clears the bar alone.
- **ANC8+:** 8 of 67 do; the wealth score gains most (+0.017).
- Stacking on ANC8+: the best 5 carry 88% of the gain.

**What changed.** Individually, almost none of the 67 matter; the collective
value is judged on held-out women.

**Source.** `outputs/feature_value/full/<outcome>/add_one_to_21.csv`

### Building from nothing: the tiers
<!-- kind: step | figures: fig28_tier_ladders, fig29_selection_frequency | terms: tier, selection-frequency -->
**Question.** Starting from zero, which variables would the data choose?

**What we did.**
- Forward selection over all 88, stopping at the first step that fails the
  bar. Tier 1 runs to 90% of the full pool's lift; tier 2 is the rest that
  pass.
- For ANC8+, the selection repeated on 10 bootstrap resamples.

**How we tested it.** Gain per step on 5 splits, and how often each variable
was chosen again.

**What we found.**
- The **wealth score is chosen first in every run** and **region** in every
  run; **pregnancy intention** enters for ANC4+ and ANC8+ but not ANC1+.
- Sets of **2 (ANC1+), 4 (ANC4+) and 8 (ANC8+)** predictors.
- Stability for ANC8+: wealth 100%, intention 90%, region 80%, health-post
  access 60%; most other places rotate.

**What changed.** The compact candidate sets for the held-out test.

**Source.** `outputs/feature_value/full/<outcome>/forward_steps.csv`

### Every set, on the held-out women
<!-- kind: step | figures: fig30_heldout_sets | terms: heldout, paired, spans-zero, ablation -->
**Question.** Which number of predictors holds up on women who played no
part in choosing it?

**What we did.** Fitted every set on development women and scored it once on
the held-out women: tier 1, tier 1+2, the best k of the 21, the 21 without
its non-contributors, all 21 and the full pool, with paired bootstrap
intervals against the 21. The tiers were also refitted with LightGBM.

**How we tested it.** Held-out AP and AUROC, paired stratified-PSU
bootstrap.

**What we found.**
- **ANC8+:** 7 of the 21 (0.440), the 8 selected from the pool (0.425), all
  21 (0.428) and the full pool (0.435) cannot be separated: every interval
  includes zero. **7 to 8 predictors are enough.**
- **ANC4+ and ANC1+:** the full pool beats the 21 (+0.023 and +0.014 AP,
  intervals excluding zero); compact sets fall slightly short.

**What changed.** The selection result is stated per rung: a short set for
completing care, the full pool for reaching it.

**Source.** `outputs/feature_value/full/<outcome>/why21_heldout.csv`, `docs/PREDICTOR_VALUE.md` §2

---

## 4 · Across the ANC ladder
<!-- phase: p4 | title: Across the ladder -->
The same women, predictors and folds at three rungs: what changes from
reaching care to completing it.

### How predictable each rung is
<!-- kind: step | figures: fig18_ladder_performance | terms: anc-rungs, prevalence, auroc, lift, champion -->
**Question.** Is completing care harder to predict than reaching it?

**What we did.** Built ten model families for ANC1+, ANC4+ and ANC8+ on the
full pool, and scored each rung's development champion on held-out women.

**How we tested it.** Held-out AUROC and lift, because raw AP cannot be
compared across outcomes with different prevalences.

**What we found.** AUROC falls **0.83 → 0.79 → 0.76** from ANC1+ to ANC8+.
Completing care is genuinely harder to predict.

**What changed.** Every cross-rung comparison uses AUROC, lift, or a share of
each rung's ceiling.

**Source.** `outputs/ladder/ladder_performance.csv`

### Each predictor's value at each rung
<!-- kind: step | figures: fig35_predictor_rung_matrix | terms: add-one, drop-one, lift -->
**Question.** Which predictors gain or lose value from ANC1+ to ANC8+?

**What we did.** Put every predictor's marginal value relative to the 21 (AP
lost when dropped, or gained when added) on one scale: a share of each rung's
ceiling above prevalence.

**How we tested it.** The same development splits for all three rungs.

**What we found.**
- **Region** is worth 2.7% of the ANC1+ ceiling and 8.7% of the ANC8+
  ceiling; the **wealth score** 0.3% and 5.4%.
- Say in large purchases, water source and living at a health post matter
  only for completing the schedule.
- Residence, the gap since the previous pregnancy and sex of the household
  head matter only for reaching care.

**What changed.** The ladder finding stated per predictor, not only by
domain.

**Source.** `outputs/predictor_value/full/matrix.csv`

### Importance, three ways
<!-- kind: step | figures: fig19_ladder_importance, fig20_domain_rollup | terms: importance, ebm, shap, drop-one, agreement, domain -->
**Question.** Do independent importance methods show the same shift?

**What we did.** Measured each predictor's importance at each rung with
exact EBM contributions, SHAP on XGBoost and drop-one, normalised to a share
within the rung, with copies merged. A pattern counts only if two methods
agree. SHAP uses XGBoost at every rung because its tree explainer mishandles
HistGradientBoosting's categorical splits.

**How we tested it.** Rank agreement between methods.

**What we found.**
- Agency and household factors carry the most for reaching care (28%) and
  the least for completing it (19%); socioeconomic factors (20% → 26%),
  pregnancy intention and access rise.
- EBM and SHAP agree well (0.58 to 0.76); drop-one agrees weakly.

**What changed.** Household position gets women through the door; money,
distance and wanting the pregnancy keep them coming back.

**Source.** `outputs/ladder/domain_rollup.csv`, `outputs/ladder/ladder_patterns.csv`

---

## 5 · Two prediction horizons
<!-- phase: p5h | title: Two prediction horizons -->
Before ANC starts, and at ANC entry, when the timing of the first contact is
known.

### The ANC-entry cohort
<!-- kind: step | figures: | terms: horizon, early-anc, heldout -->
**Question.** Who can be predicted at ANC entry, and on which split?

**What we did.** Took the 5,001 women who started ANC and know when their
first contact was, with early ANC (first contact by 12 weeks or 3 months;
2,130 women), and restricted the full-cohort split to them.

**How we tested it.** The code asserts that the entry partition matches the
full split woman for woman (4,017 / 984).

**What we found.** Every woman at this horizon has ANC1+, so only ANC4+ and
ANC8+ are predicted.

**What changed.** The whole predictor-value study was repeated at this
horizon, with early ANC as an 89th candidate.

**Source.** `src/anc8/cohorts.py`

### What early initiation adds
<!-- kind: step | figures: fig36_horizons, fig37_early_anc | terms: early-anc, add-one, paired, spans-zero -->
**Question.** How much does knowing that the first contact was early add?

**What we did.** Added early ANC to the 21, to the entry selected set and to
the full pool; ran forward selection and bootstrap re-selection at entry; and
scored every set once on the 984 held-out entry women.

**How we tested it.** Development gain on 5 splits, then paired bootstrap on
held-out women.

**What we found.**
- Early ANC is the strongest single addition at both rungs (+0.032 AP for
  ANC4+, +0.077 for ANC8+) and is selected second, after the wealth score;
  for ANC8+ in 10 of 10 resamples.
- **ANC4+:** wealth score and early ANC (2 predictors) beat all 21 on
  held-out women (AP 0.880 against 0.848, interval excluding zero).
- **ANC8+:** about 7 predictors; early ANC's held-out gain over the 21
  (+0.027 AP) cannot be confirmed on 984 women.

**What changed.** At ANC entry the recommended set is 2-3 predictors for
ANC4+ and about 7 for ANC8+, each led by wealth and early initiation.

**Source.** `outputs/feature_value/entry/`, `outputs/horizons/`

### One model or two
<!-- kind: step | figures: fig36_horizons | terms: horizon, paired -->
**Question.** Is a model fitted on the ANC-entry women better for them than
one fitted on everyone?

**What we did.** Fitted the 21 and the full pool on all development women and
on the entry development women, and scored both on the same held-out entry
women, without early ANC.

**How we tested it.** Paired bootstrap of the AUROC difference.

**What we found.** No measurable difference (+0.004 to +0.014 AUROC, every
interval including zero).

**What changed.** What matters at entry is adding the timing of the first
contact, not refitting on the entry population.

**Source.** `outputs/horizons/cross_horizon.csv`

---

## 6 · The Tigray war
<!-- phase: p6 | title: The Tigray war -->
Pregnancies during and after the war, against every other region. The survey
records ANC only for births from about mid-2021, so no pre-war pregnancy is
observed.

### Wartime against post-war, net of other regions
<!-- kind: step | figures: fig31_tigray_did | terms: did, comparison-regions, simpsons, biases -->
**Question.** What did the war do to antenatal care in Tigray?

**What we did.**
- A pregnancy is "wartime" if at least 3 of its 9 months fell inside the war
  (3 Nov 2020 – 2 Nov 2022, cited in `docs/conflict_windows.csv`), and
  "post-war" if conceived after the ceasefire.
- Difference-in-differences against regions without major conflict, with the
  comparison change averaged **within** each region (pooling produces a
  spurious 5-point fall, a Simpson's paradox).

**How we tested it.** Stratified cluster bootstrap; the war window shifted
±3 months; Oromia and Benishangul-Gumuz added to the comparison group.

**What we found.** Tigray wartime pregnancies (n = 259) against post-war
(n = 323):
- **no ANC at all: 19.5% → 7.7%**, 13 points beyond other regions
  [−20.3, −6.2];
- ANC4+ +13.6 points; ANC8+ no clear change (+2.0).

The ANC4+ result stays between +11 and +14 under every robustness check.

**What changed.** The war's damage was at the door: access recovered,
completion did not.

**Source.** `outputs/wartime/tigray_difference_in_differences.csv`

### Tigray against every region
<!-- kind: step | figures: fig38_tigray_regions_by_period | terms: comparison-regions -->
**Question.** How does Tigray's change compare with every other region over
the same calendar periods?

**What we did.** Computed ANC levels in every region for pregnancies in the
war window and pregnancies conceived after the ceasefire.

**How we tested it.** Survey-weighted levels, region by region.

**What we found.** Tigray's change in reaching care is the largest of any
region (no-ANC −12 points, ANC4+ +14); most regions move a few points. Its
ANC8+ barely moves.

**What changed.** The difference-in-differences is shown against the levels
behind it.

**Source.** `outputs/wartime/region_by_war_period.csv`

### Tigray against its own circumstances
<!-- kind: step | figures: fig21_regional_gap, fig32_regional_gap_cohort | terms: regional-gap, window24 -->
**Question.** Tigray sits about 4 points below expectation on ANC8+. Is that
only the war?

**What we did.** Compared each region's attainment with what its population
profile predicts (region withheld), on all births, on post-war pregnancies
only, and in the 24-month window.

**How we tested it.** The same model in each cohort.

**What we found.** Post-war, Tigray is **above** expectation for reaching
care (ANC1+ +6.3, ANC4+ +7.4 points) and still **below** it for completing
care (ANC8+ −2.8). The regional ranking is stable across windows.

**What changed.** Tigray's completion shortfall is not only a war artefact.

**Source.** `outputs/wartime/regional_gap_by_cohort.csv`

---

## 7 · Supporting analyses
<!-- phase: p7 | title: Supporting analyses -->
Could the results be an artefact of the modelling? Each of these asks one
version of that question.

### Ten model families, tuned on the same folds
<!-- kind: step | figures: fig04_leaderboard_anc8plus | terms: tuning, trees, ebm, mlp, logistic, overfitting, champion -->
**Question.** With the full pool, does the choice of algorithm matter?

**What we did.** Tuned ten families with Optuna on identical folds and the
same objective (weighted AP), choosing the champion on development folds.

**How we tested it.** Development out-of-fold AP, then held-out AP.

**What we found.** Development AP ranged only from 0.501 to 0.518; every
model dropped about **0.08 AP** on held-out women, more than the gap between
models.

**What changed.** The algorithm is not the constraint; the predictors are.

**Source.** `outputs/enhanced/anc8plus/development_oof_performance.csv`

### Calibration, and an additive model
<!-- kind: step | figures: fig05_calibration, fig08_global_importance, fig09_shape_functions | terms: platt, calibration-slope, ebm, shape-function -->
**Question.** Can the predicted probabilities be read as honest rates?

**What we did.** Added Platt or isotonic calibration, fitted on inner folds.

**How we tested it.** Calibration slope and AP cost.

**What we found.**
- Platt moved the slope from 0.62 to **0.99** at a cost of 0.005 AP;
  isotonic cost 0.023.
- The Explainable Boosting Machine, offered ten interactions, **chose none**
  and matched XGBoost on AUROC (0.789 against 0.788): ANC8+ attainment
  behaves additively.

**What changed.** The EBM is the model the app explains, with exact
per-predictor contributions.

**Source.** `docs/METHODS.md` §7

### Modelling the whole count
<!-- kind: step | figures: | terms: ordinal, overfitting -->
**Question.** Does modelling the contact count, not just "8 or more", help?

**What we did.** A cumulative-link model of the count, reading off "at least
8".

**How we tested it.** Development and held-out AP against the plain yes/no
model.

**What we found.** Better in development (0.500 against 0.494), **worse on
held-out women (0.402 against 0.427)**.

**What changed.** Reported, not used.

**Source.** `docs/METHODS.md` §7

### What tuning and preprocessing bought
<!-- kind: step | figures: fig15_preprocessing, fig16_hyperparameters, fig17_tuning_gain | terms: tuning, ablation, overfitting -->
**Question.** How much of the accuracy comes from tuning and data
preparation?

**What we did.** Refitted each tuned model at library defaults, moved each
setting one step with the others fixed, and tried four preprocessing
variants with everything else fixed.

**How we tested it.** Development AP against the tuned optimum.

**What we found.** Tuning bought +0.02 to +0.04 AP, less than the 0.08
optimism gap; preprocessing at most +0.003.

**What changed.** Neither is a lever; the choice of predictors is.

**Source.** `outputs/enhanced/anc8plus/hyperparameter_ablation.csv`, `outputs/enhanced/preprocessing_ablation.csv`

### The full pool against the 21, on repeated splits
<!-- kind: step | figures: fig06_stability, fig07_bootstrap, fig10_decision_curve, fig11_subgroups, fig25_set_comparison | terms: repeated, bootstrap, spans-zero, paired, net-benefit -->
**Question.** Is the difference between the full pool and the 21 real, on
evidence that would convince a sceptic?

**What we did.** 20 fresh random splits of all women, each refit from
scratch with the model fixed and only the predictors changed; and a paired
bootstrap on the held-out women.

**How we tested it.** AP differences with 95% intervals, and splits won.

**What we found.**
- Repeated splits: **+0.031 AP, better in 20 of 20**.
- Held-out: +0.021 AP [−0.036, +0.075]; one set of 1,375 women cannot
  resolve a gain this size.
- Within most regions the models rank women much less well than nationally.

**What changed.** Set comparisons rest on repeated splits, with the held-out
interval always reported next to them.

**Source.** `outputs/enhanced/anc8plus/stability_summary.json`, `outputs/enhanced/set_comparison/`

### The 24-month window
<!-- kind: step | figures: | terms: window24 -->
**Question.** Do the predictor results hold on the official 24-month window?

**What we did.** Repeated the predictor-value study on the 5,037 women with a
birth in the last 24 months.

**How we tested it.** The same stages and held-out test.

**What we found.** The same leaders: the wealth score first in every run,
region in every run, pregnancy intention for ANC4+ and ANC8+; years of
schooling also enters.

**What changed.** The main results do not depend on including older births.

**Source.** `outputs/feature_value/recent/`
