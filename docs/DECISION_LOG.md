# Decision log

Every significant choice in the analysis, why it was made, and what it
changed. Several were made because a first attempt gave a misleading answer;
those say so, because a reader deciding how far to trust a result needs to
know what was checked, not only what came out.

---

## Data and design

| Decision | Why | Consequence |
|---|---|---|
| One development / held-out split, drawn once by survey cluster within stratum (seed 2026), for every outcome, horizon and window | Every comparison should be scored on the same women | 5,518 / 1,375 women; the ANC-entry and 24-month cohorts use the same split restricted to their women, asserted woman for woman |
| Survey weights in every metric, cluster-grouped folds, cluster bootstrap for intervals | The DHS is a clustered, stratified sample; ignoring that makes every interval too narrow | The test suite checks no cluster spans two folds |
| Pregnancy timing from the pregnancy history (`p19`, `p3`), not the live-birth history (`b19`) | The live-birth history has no row for a stillbirth; using it silently dropped the women whose last pregnancy ended in one | 61 stillbirth-outcome women timed correctly (55 in the 24-month window) |
| The DHS-8 24-month window as a sensitivity analysis | 28% of the cohort gave birth 24-35 months before interview; the official indicator uses 24 months | The 24-month cohort reproduces the EDHS report's ANC4+ table (national 53.0% vs 53.0%); main results are checked against it |
| Two prediction horizons: before ANC, and at ANC entry | What can be known depends on when the prediction is made; first-contact timing exists only once a woman has started | The whole predictor-value study is repeated at ANC entry (5,001 women), for ANC4+ and ANC8+ |

## Predictors

| Decision | Why | Consequence |
|---|---|---|
| Screen all 6,648 survey columns, on development data only | A pre-specified set can only be judged against what else the survey offers | 577 rankable candidates; 61 admitted after review; a 95-column pool (see PREDICTOR_VALUE.md §1) |
| Exclude everything recorded during or after the care being predicted (facility visits in the last 12 months, HIV testing, first-visit timing, delivery, contraception at interview) | These predict ANC8 superbly and would make a model worthless in practice | Listed with reasons in `src/anc8/features.py`; first-visit timing admitted only at ANC entry |
| Audit the screening for leakage | Screening sees data too | All 61 admitted variables survive development-only screening; largest AUC shift 0.013 |
| Identify duplicates with Theil's U in both directions, not Cramér's V | Cramér's V scored union status and partner education 1.0 because "not applicable" occurs for exactly the unmarried women: structural missingness, not duplication | 10 of the 95 columns are copies; 85 distinct variables; importance reported with copies merged |
| Use age at the birth instead of current age in the predictor-value study | Current age is up to 3 years from the pregnancy for older births; the EDHS report uses age at birth | The one change to the 21-predictor set's constructs |
| Exclude number of living children | It falls if the baby died, which leaks what happened after the birth | Excluded from the candidate pool |
| Flag, do not drop, variables measured at interview (work, insurance, occupation, ideal family size) | They may partly reflect life after the pregnancy, but dropping them blind would be its own assumption | Marked ⚑ wherever selected |

## Predictor-value study

| Decision | Why | Consequence |
|---|---|---|
| Fixed model (logistic regression) for every predictor comparison | Compare variables, not models; a model with almost nothing to tune cannot favour one set through its settings | LightGBM re-scores the chosen sets as a check |
| Regularisation chosen per set from a common grid, not fixed | A single light setting let the 88 overfit (0.478); a heavy one handicapped small sets. Either would have tilted the answer to how many predictors are needed | Each set scored at its own best setting; the 88 score 0.508 |
| The bar: +0.005 AP on average **and** on 4 of 5 splits, fixed before any selection result | Require consistency, not just an average | Applied to adding, dropping and forward selection alike |
| Run the drop study within the 21 on the same fixed model for every rung | A drop study on a different tuned model for one outcome only could not be compared across rungs | Drop-one, the full greedy path and the group drop within the 21, per rung and horizon |
| Compare rungs on a share of each rung's ceiling (full-pool AP minus prevalence), not raw AP | AP's floor is the prevalence (0.78 vs 0.19); a +0.005 bar is far harsher for ANC1+ | The predictor × rung matrix |
| Judge every searched set on held-out women, once | Sets chosen on the development folds are optimistic there | Held-out tables for the tiers, the reduced 21 and the full pool, with paired intervals |
| Bootstrap re-selection | Forward selection is sensitive to the sample | Wealth 100%, pregnancy intention 90%, region 80%; most of tier 2 rotates |
| Report the collective gain of the full pool separately from the per-variable bar | A per-variable bar cannot see value spread thinly across many variables | For ANC1+ and ANC4+ no single addition passes the bar, yet the full pool beats the 21 on held-out women |

## Across the ladder

| Decision | Why | Consequence |
|---|---|---|
| Three importance methods per rung (EBM, SHAP, drop-one); a pattern counts only if two agree | One method's quirks should not become a finding | Drop-one agrees weakly, because correlated predictors compensate; it is the weakest of the three |
| SHAP on XGBoost at every rung | The tree explainer mishandles HistGradientBoosting's native categorical splits (rank agreement with EBM was −0.10 on it) | EBM–SHAP agreement 0.58 to 0.76 |
| Drop-one on the 85 distinct variables, with duplicates folded into their twins | Removing `region` cost nothing while `v024` remained | Importance per variable, not per column |
| Rung performance from each rung's development champion | Choosing by held-out score makes that score optimistic | AUROC 0.83 → 0.79 → 0.76 up the ladder |

## Wartime analysis

| Decision | Why | Consequence |
|---|---|---|
| Exposure by the calendar window of each pregnancy, with cited conflict dates | Birth age does not line up with the conflicts | `docs/conflict_windows.csv` |
| Difference-in-differences against regions without major conflict | Separates the war from the national trend and the recall error of older births | 13 points more women with no ANC during the war |
| Comparison change averaged within regions, not pooled | The pooled comparison mean falls 5 points while every region in it holds steady or rises (Simpson's paradox), because the regional mix differs between periods | Within-region change near zero |
| Report every region over the same two periods | The difference-in-differences summarises the comparison; the levels show it | `region_by_war_period.csv`, fig38 |
| Compare wartime with post-war only | The survey records ANC only for births from about mid-2021, so no pre-war pregnancy is observed | Stated as a scope limit |

## Modelling and evidence

| Decision | Why | Consequence |
|---|---|---|
| Ten model families tuned with Optuna on the same folds and objective | Establish whether the algorithm is the constraint | Development AP spread across all ten is about 0.02: it is not |
| Champion chosen on development folds | Selecting on held-out scores makes them optimistic | Applied in evaluation, export, the ladder, figures and the app |
| Hyperparameter ablation against library defaults | Development scores ran ~0.08 AP above held-out for every model | Tuning bought +0.02 to +0.04 AP in development, less than that gap |
| Cumulative-link (ordinal) arm | ANC8+ is a thresholded count; ordering is information | Helped in development, not held-out (0.402 vs 0.427); reported, not used |
| Platt calibration, fitted on inner folds | Raw slopes were too extreme | Slope 0.62 → 0.99 at −0.005 AP |
| Report held-out intervals even when they span zero | Quoting only agreeing evidence is how analyses mislead | Every held-out comparison carries its paired interval |
| Rest set-comparison claims on repeated splits | One small held-out set cannot resolve differences this size | 20 of 20 splits favour the full pool over the 21, +0.031 AP |

## Deployment and interpretation

| Decision | Why | Consequence |
|---|---|---|
| Export models to plain arrays and score with numpy only | Loading the fitted pipelines needs 341 MB against Vercel's 250 MB limit | A fidelity gate refuses any bundle that does not reproduce the fitted pipeline on every held-out woman |
| Reproduce XGBoost's sparse-zero behaviour | The 21-predictor pipeline treats unstored zeros as missing; scoring densely gave 0.577 where the fitted model gives 0.159 | Documented in METHODS (appendix) |
| Global importance from every term, shape functions with every bin, no "higher increases" label for categories | A truncated list, a dropped top bin and alphabetical category codes each misrepresented the model | Wealth score in the top 15; each region shown as its own bar |
| XGBoost reproducibility stated to about 0.01 AP | Its results vary with CPU thread count (0.506-0.518 development AP) | Logistic regression and LightGBM verified thread-invariant |
