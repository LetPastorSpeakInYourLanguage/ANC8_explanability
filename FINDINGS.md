# Predicting antenatal care attainment in Ethiopia: findings

What best predicts whether a woman completes eight or more antenatal care
contacts (ANC8+), and the earlier rungs ANC1+ and ANC4+, in the 2024-25
Ethiopia DHS. This is the technical hub; `docs/README.md` maps the deep
dives, and `docs/POLICY_BRIEF.md` is the brief for the Ministry of Health.

Things that looked like wins in development and did not survive the held-out
women are reported as such.

---

## 1. Question, data and design

- **Outcome.** The number of antenatal contacts for the most recent
  pregnancy, thresholded at 1, 4 and 8: 77.6%, 52.4% and 19.2% of women
  (survey-weighted).
- **Cohort.** 6,893 women whose most recent pregnancy has a recorded contact
  count. The ANC-entry horizon uses the 5,001 of them who started ANC and know
  their first-contact timing; the DHS-8 24-month window (5,037 women) is a
  sensitivity check, and reproduces the official report's national ANC4+
  exactly (53.0% against 53.0%).
- **Design.** One development / held-out split by survey cluster within
  stratum (5,518 / 1,375), shared by every outcome, horizon and window.
  Weights in every metric; cluster-grouped folds; stratified cluster
  bootstrap for every interval; every comparison paired.

<!-- AUTO:cohorts -->
| Cohort | Women | Development | Held out | ANC4+ | ANC8+ | Use |
|---|---|---|---|---|---|---|
| Before ANC | 6893 | 5518 | 1375 | 52.4% | 19.2% | Main analysis; horizon 1 (before ANC) |
| ANC entry | 5001 | 4017 | 984 | 67.6% | 24.7% | Horizon 2 (at ANC entry) |
| Last 24 months | 5037 | 4040 | 997 | 53.0% | 19.5% | Sensitivity (DHS-8 24-month window) |

One development / held-out split, drawn once by survey cluster on the full cohort and restricted to each cohort.
<!-- /AUTO:cohorts -->

---

## 2. Predictor value: how many predictors, and which

Full account in `docs/PREDICTOR_VALUE.md`.

**From 6,648 columns to a pool of 88.** Of the survey's 6,648 columns, 577
are observed for enough women to rank. 61 were admitted after a review for
timing; the rest have almost no signal (median univariate AUC 0.518) or
record the care itself — "visited a health facility in the last 12 months"
is partly the ANC visits. With the constructs of the 21-predictor set and
derived measures, the pool is 95 columns, or 85 distinct variables once
copies are merged; the study selects from 88.

<!-- AUTO:funnel -->
| Step | Columns | Note |
|---|---|---|
| Not collected in this survey round | 1,719 | — |
| Entirely missing in the cohort | 808 | — |
| Measured at or after the delivery (leakage by design) | 2,296 | — |
| Survey design or administrative | 28 | — |
| Observed for under half the cohort | 1,208 | — |
| Other automated exclusions | 12 | — |
| **Rankable candidates** (at least half the cohort observed) | **577** |  |
| Refused on timing: they record the care itself or life after it | 9 | e.g. facility visit in the last 12 months, HIV testing, contraception |
| Not admitted: no plausible link before the pregnancy, or near-zero signal | 507 | median univariate AUC 0.518; breastfeeding, nutrition and child health (after the birth) 94, pregnancy-history index columns 67, contraception (measured at interview) 66, other children's birth history 61, reproductive counts and history 39 |
| **Admitted survey variables** | **61** |  |
| + constructs of the 21-predictor set, and derived measures | 34 | e.g. log travel times, separate media channels, spousal gaps |
| **Full candidate pool (columns)** | **95** |  |
| Distinct variables once copies are merged | 85 | 10 columns were the same variable twice |
| **Predictor-value study pool** | **88** | the 85 plus three constructs only the 21-predictor set had |

From the 6,648 columns of the Individual Recode to the pool the predictor-value study selects from. The automated rows are exclusive, applied top to bottom.
<!-- /AUTO:funnel -->

**The result: every set, on the held-out women.** The model is held fixed
(logistic regression, each set at its own best regularisation) so only the
predictors vary.

<!-- AUTO:ablation -->
**ANC1+** (held-out prevalence 0.762)

| Set | Predictors | Development AP | Share of pool's lift | Held-out AP | Held-out AUROC | ΔAP vs the 21 [95%] | ΔAUROC vs the 21 [95%] |
|---|---|---|---|---|---|---|---|
| Tier 1 (selected from the pool) | 2 | 0.911 | 94% | 0.916 | 0.767 | +0.001 [-0.019, +0.021] | -0.021 [-0.062, +0.014] |
| Best 11 of the 21 | 11 | 0.921 | 101% | 0.907 | 0.768 | -0.007 [-0.013, -0.001] | -0.017 [-0.034, -0.001] |
| The 21 minus its non-contributors | 13 | 0.921 | 101% | 0.911 | 0.779 | -0.003 [-0.008, +0.002] | -0.006 [-0.022, +0.007] |
| **The 21-predictor set** | 21 | 0.916 | 98% | 0.913 | 0.784 | reference |  |
| Full pool | 88 | 0.919 | 100% | 0.928 | 0.804 | +0.014 [+0.003, +0.027] | +0.019 [-0.005, +0.042] |

**ANC4+** (held-out prevalence 0.518)

| Set | Predictors | Development AP | Share of pool's lift | Held-out AP | Held-out AUROC | ΔAP vs the 21 [95%] | ΔAUROC vs the 21 [95%] |
|---|---|---|---|---|---|---|---|
| Tier 1 (selected from the pool) | 2 | 0.771 | 94% | 0.773 | 0.745 | -0.010 [-0.035, +0.016] | -0.024 [-0.055, +0.005] |
| Tier 1+2 (selected from the pool) | 4 | 0.786 | 100% | 0.776 | 0.750 | -0.006 [-0.037, +0.021] | -0.019 [-0.048, +0.007] |
| Best 8 of the 21 | 8 | 0.793 | 103% | 0.769 | 0.756 | -0.013 [-0.032, +0.007] | -0.012 [-0.027, +0.003] |
| The 21 minus its non-contributors | 11 | 0.793 | 103% | 0.766 | 0.761 | -0.015 [-0.044, +0.011] | -0.007 [-0.025, +0.011] |
| **The 21-predictor set** | 21 | 0.783 | 99% | 0.782 | 0.769 | reference |  |
| Full pool | 88 | 0.785 | 100% | 0.806 | 0.793 | +0.023 [+0.011, +0.035] | +0.023 [+0.008, +0.040] |

**ANC8+** (held-out prevalence 0.160)

| Set | Predictors | Development AP | Share of pool's lift | Held-out AP | Held-out AUROC | ΔAP vs the 21 [95%] | ΔAUROC vs the 21 [95%] |
|---|---|---|---|---|---|---|---|
| Tier 1 (selected from the pool) | 2 | 0.491 | 94% | 0.395 | 0.735 | -0.034 [-0.095, +0.028] | -0.029 [-0.061, +0.000] |
| Tier 1+2 (selected from the pool) | 8 | 0.545 | 112% | 0.425 | 0.764 | -0.006 [-0.056, +0.033] | +0.001 [-0.023, +0.024] |
| Best 7 of the 21 | 7 | 0.509 | 100% | 0.440 | 0.754 | +0.010 [-0.026, +0.052] | -0.008 [-0.024, +0.008] |
| The 21 minus its non-contributors | 7 | 0.508 | 100% | 0.439 | 0.759 | +0.011 [-0.028, +0.050] | -0.003 [-0.020, +0.011] |
| **The 21-predictor set** | 21 | 0.469 | 87% | 0.428 | 0.762 | reference |  |
| Full pool | 88 | 0.509 | 100% | 0.435 | 0.776 | +0.002 [-0.061, +0.052] | +0.013 [-0.013, +0.042] |

Logistic regression throughout, each set at the regularisation it earned on development folds. Development scores of the searched sets (the tiers and the reduced 21) are optimistic, because they were chosen on those folds; the held-out columns are the fair comparison. Intervals: paired stratified-PSU bootstrap on the held-out women.
<!-- /AUTO:ablation -->

- **ANC8+: 7 to 8 predictors are enough.** The 8 selected from the pool
  (wealth score, region, pregnancy intention, say in large purchases,
  occupation, children ever born, two measures of health-post access) and
  the best 7 of the 21 do as well as all 21 or the full pool on held-out
  women; every interval includes zero.
- **ANC1+ and ANC4+: more information helps.** The full pool beats the 21 on
  held-out women (+0.014 and +0.023 AP, intervals excluding zero), although
  no single extra variable passes the bar alone. Compact sets fall slightly
  short.

**Why 21 is not the answer for ANC8+.** Dropping each member from the 21 in
turn, 8 add nothing for ANC1+, 10 for ANC4+ and **14 for ANC8+**. The greedy
path within the 21 peaks at 7 predictors for ANC8+ and falls from there. The
21's weak points are measurable: wealth enters as a five-level quintile
although the continuous score is stronger (univariate AUC 0.755 against
0.742); the weekly media count scores below television alone (0.644 against
0.677); health insurance, household size, religion, internet use, transport
mode and the media count add nothing to any rung. Its core — region, wealth,
pregnancy intention — is right.

<!-- AUTO:drop_within_21 -->
| Removed from the 21 | ANC1+ | ANC4+ | ANC8+ |
|---|---|---|---|
| Region | +0.0037 (5/5) | +0.0045 (5/5) | +0.0268 (5/5) |
| Was this pregnancy wanted? | +0.0011 (5/5) | +0.0058 (5/5) | +0.0069 (5/5) |
| Wealth quintile | +0.0035 (5/5) | +0.0040 (5/5) | +0.0056 (5/5) |
| Mother's occupation | +0.0021 (5/5) | -0.0012 · (1/5) | +0.0050 (5/5) |
| Partner's education | +0.0001 (3/5) | +0.0015 (4/5) | +0.0037 (4/5) |
| Travel time to hospital or health centre | +0.0001 (4/5) | +0.0003 (3/5) | +0.0029 (5/5) |
| Pregnancy number | +0.0003 (5/5) | +0.0002 (3/5) | +0.0009 (5/5) |
| Marital status | +0.0000 (5/5) | +0.0000 (3/5) | -0.0001 · (2/5) |
| Has a say in her own healthcare | -0.0000 · (2/5) | +0.0002 (3/5) | -0.0002 · (2/5) |
| Mother's education level | +0.0014 (5/5) | -0.0006 · (1/5) | -0.0009 · (1/5) |
| Previous pregnancy outcomes | +0.0003 (5/5) | -0.0003 · (2/5) | -0.0010 · (1/5) |
| Weekly media count (0-3) | -0.0003 · (0/5) | -0.0022 · (0/5) | -0.0016 · (0/5) |
| Urban or rural | +0.0026 (5/5) | +0.0015 (4/5) | -0.0018 · (0/5) |
| Household size | -0.0003 · (0/5) | -0.0006 · (1/5) | -0.0022 · (0/5) |
| Mother's age at the birth | -0.0002 · (3/5) | +0.0007 (3/5) | -0.0024 · (0/5) |
| Internet use | -0.0011 · (0/5) | -0.0009 · (1/5) | -0.0026 · (0/5) |
| Partner's occupation | +0.0001 (2/5) | +0.0007 (3/5) | -0.0029 · (1/5) |
| Has health insurance | -0.0001 · (2/5) | -0.0003 · (2/5) | -0.0030 · (0/5) |
| Gap since previous pregnancy | +0.0018 (5/5) | -0.0009 · (2/5) | -0.0041 · (0/5) |
| Religion | -0.0001 · (4/5) | -0.0018 · (1/5) | -0.0048 · (0/5) |
| Usual transport to care | -0.0014 · (0/5) | -0.0020 · (0/5) | -0.0053 · (0/5) |
| **non-contributors** | 8 | 10 | 14 |

Development AP lost when the predictor is removed from the 21 (logistic regression, each set at its own best regularisation, 5 split seeds; in brackets the seeds on which removing it hurt). · = removing it costs nothing or helps.
<!-- /AUTO:drop_within_21 -->

**What leads everywhere.** The continuous wealth score is chosen first in
every run and region in every run; pregnancy intention enters for ANC4+ and
ANC8+ but not for reaching care. Bootstrap re-selection for ANC8+ keeps
wealth (100%), pregnancy intention (90%) and region (80%); most other places
rotate between variables that carry overlapping information.

---

## 3. Across the ANC ladder

**Completing care is harder to predict than reaching it.** On the full pool,
each rung's development champion scores:

<!-- AUTO:ladder_performance -->
| Rung | Attain it | Model (development champion) | AUROC | AP | AP lift | Share of possible lift |
|---|---|---|---|---|---|---|
| ANC1+ | 77.6% | XGBoost | 0.826 | 0.933 | +0.157 | 0.70 |
| ANC4+ | 52.4% | HistGradientBoosting | 0.789 | 0.803 | +0.279 | 0.59 |
| ANC8+ | 19.2% | XGBoost | 0.759 | 0.427 | +0.236 | 0.29 |

Held-out women, full candidate pool. The model is the one ranked first on development folds, so the held-out set is not used to choose it. "Share of possible lift" is AP lift divided by its maximum (1 minus prevalence).
<!-- /AUTO:ladder_performance -->

Raw AP cannot be compared across rungs (its floor is the prevalence); AUROC
falls 0.83 → 0.79 → 0.76.

**How each predictor's value changes.** Each predictor's marginal value
relative to the 21, as a share of each rung's ceiling:

<!-- AUTO:predictor_matrix -->
| Predictor | In the 21 | ANC1+ | ANC4+ | ANC8+ | Shift ANC1+ → ANC8+ (pts) |
|---|---|---|---|---|---|
| Region | yes | +2.7% T1 | +1.7% T2 | +8.7% T1 | +6.0 |
| Household wealth score |  | +0.3% T1 | +1.3% T1 | +5.4% T1 | +5.1 |
| Wealth quintile (urban/rural) |  | -0.5% | +0.4% | +4.1% | +4.5 |
| Wealth quintile | yes | +2.5% | +1.5% | +1.8% | -0.7 |
| Decides on large purchases |  | -0.4% | -0.2% | +2.5% T2 | +2.9 |
| Listens to radio weekly |  | +1.0% | +1.8% | +2.2% | +1.2 |
| Was this pregnancy wanted? | yes | +0.8% | +2.2% T2 | +2.2% T2 | +1.5 |
| Listens to radio |  | +0.9% | +1.1% | +2.0% | +1.1 |
| Urban or rural | yes | +1.9% | +0.6% | -0.6% | -2.4 |
| Lives at a health post |  | -0.1% | -0.2% | +1.9% T2 | +2.0 |
| Household wealth score (urban/rural) |  | -0.4% | +0.3% | +1.8% | +2.2 |
| Drinking water source |  | -1.0% | -0.0% | +1.7% | +2.7 |
| Mother's occupation | yes | +1.5% | -0.5% | +1.6% T2 | +0.1 |
| Partner's age |  | -0.2% | +0.2% | +1.5% | +1.7 |
| Sex of household head |  | +1.3% | -0.0% | -0.2% | -1.6 |
| Reads newspapers |  | +1.3% | -0.4% | +0.4% | -0.9 |
| Gap since previous pregnancy | yes | +1.3% | -0.4% | -1.3% | -2.6 |
| Worked in the last year |  | +1.2% | -0.2% | +0.3% | -1.0 |
| Partner's education | yes | +0.0% | +0.6% | +1.2% | +1.2 |
| Watches television weekly |  | -0.1% | +1.2% | +0.1% | +0.1 |

Marginal value relative to the 21-predictor set, as a share of each rung's ceiling (full-pool AP minus prevalence): for members of the 21 the AP lost when dropped from it, for the rest the AP gained when added to it. T1 / T2 = selected in tier 1 / tier 2 at that rung. The top predictors by their largest value on any rung.
<!-- /AUTO:predictor_matrix -->

Region (2.7% → 8.7% of the ceiling) and the wealth score (0.3% → 5.4%)
become far more valuable for completing the schedule; so do say in large
purchases, water source and living at a health post. Residence, the gap since
the previous pregnancy and sex of the household head matter only for reaching
care.

**The same shift, three independent ways** (exact EBM contributions, SHAP on
XGBoost, drop-one; copies merged; a pattern counts only if two agree):

<!-- AUTO:domain_rollup -->
| Domain | ANC1+ | ANC4+ | ANC8+ | Shift |
|---|---|---|---|---|
| Socioeconomic | 20% | 26% | 26% | +5.5 pts |
| Agency and household | 28% | 22% | 19% | -8.5 pts |
| Reproductive history | 13% | 13% | 17% | +4.0 pts |
| Access and distance | 13% | 11% | 15% | +2.7 pts |
| Geography and culture | 11% | 12% | 11% | -0.5 pts |
| Education and information | 10% | 12% | 10% | -0.4 pts |
| Work | 5% | 3% | 3% | -2.7 pts |

Share of total predictor importance within each outcome, averaged over EBM, SHAP and drop-one, with duplicate variables counted once.
<!-- /AUTO:domain_rollup -->

Household position gets women through the door; money, distance and wanting
the pregnancy keep them coming back.

---

## 4. Two prediction horizons

Full account in `docs/HORIZONS.md`. Before ANC starts, a prediction can use
only who the woman is and where she lives; at ANC entry it can also use
whether her first contact was early (by 12 weeks or 3 months).

- **Early initiation is the strongest predictor after wealth.** Added alone to
  the 21 it raises development AP by +0.032 (ANC4+) and +0.077 (ANC8+),
  several times more than any other candidate, and forward selection picks it
  second at both rungs.
- **ANC4+ at entry: 2 to 3 predictors beat all 21 on held-out women.** The
  wealth score and early ANC score AP 0.880 / AUROC 0.779 against 0.848 /
  0.727 for the 21, intervals excluding zero; the full pool reaches 0.900 /
  0.808.
- **ANC8+ at entry: about 7 predictors**, with weaker evidence: only the full
  pool's AUROC gain over the 21 is confirmed on the 984 held-out women.
- **No separate model is needed for the entry horizon.** Models fitted on all
  women score the ANC-entry women as well as models fitted on them alone; the
  gain comes from the extra information, not the population.

<!-- AUTO:horizon_tiers -->
| Outcome | Horizon | Tier 1 | Tier 2 | Prevalence | 21-predictor set | Full pool |
|---|---|---|---|---|---|---|
| ANC4+ | before ANC | Household wealth score, Pregnancy number | Region, Was this pregnancy wanted? | 0.526 | 0.783 | 0.785 |
| ANC4+ | ANC entry | Household wealth score, First ANC contact by 3 months | Literacy | 0.675 | 0.844 | 0.872 |
| ANC8+ | before ANC | Household wealth score, Region | Decides on large purchases, Was this pregnancy wanted?, Mother's occupation, Children ever born, Lives at a health post, Travel time to health post (log) | 0.199 | 0.469 | 0.509 |
| ANC8+ | ANC entry | Household wealth score, First ANC contact by 3 months | Mother's occupation, Region, Decides on large purchases, Was this pregnancy wanted?, Lives at a health post | 0.255 | 0.494 | 0.584 |

Forward selection at each horizon, in order. Development AP; the ANC-entry pool adds the timing of the first contact.
<!-- /AUTO:horizon_tiers -->

<!-- AUTO:early_anc -->
| Outcome | Added to | Development AP | Development gain | Held-out ΔAP [95% CI] | Held-out ΔAUROC [95% CI] |
|---|---|---|---|---|---|
| ANC4+ | 21 | 0.844 → 0.875 | +0.0318 (5/5) | +0.043 [+0.019, +0.072] | +0.070 [+0.032, +0.107] |
| ANC4+ | tier set | 0.835 → 0.876 | +0.0403 (5/5) | +0.044 [+0.020, +0.073] | +0.075 [+0.035, +0.118] |
| ANC4+ | full pool | 0.844 → 0.872 | +0.0276 (5/5) | +0.037 [+0.017, +0.060] | +0.057 [+0.024, +0.092] |
| ANC8+ | 21 | 0.494 → 0.572 | +0.0774 (5/5) | +0.027 [-0.034, +0.082] | +0.041 [-0.017, +0.096] |
| ANC8+ | tier set | 0.556 → 0.630 | +0.0743 (5/5) | +0.039 [-0.022, +0.097] | +0.053 [-0.009, +0.115] |
| ANC8+ | full pool | 0.528 → 0.584 | +0.0554 (5/5) | +0.021 [-0.038, +0.079] | +0.049 [+0.005, +0.089] |

What knowing that the first contact came by 3 months adds, among women who started ANC. Held-out: 984 women, paired stratified-PSU bootstrap.
<!-- /AUTO:early_anc -->

<!-- AUTO:cross_horizon -->
| Outcome | Set | Trained before ANC: AP / AUROC | Trained at ANC entry: AP / AUROC | ΔAP [95% CI] | ΔAUROC [95% CI] |
|---|---|---|---|---|---|
| ANC4+ | 21-predictor set | 0.840 / 0.714 | 0.848 / 0.727 | +0.007 [-0.005, +0.017] | +0.012 [-0.010, +0.031] |
| ANC4+ | Full pool | 0.853 / 0.735 | 0.863 / 0.750 | +0.008 [-0.003, +0.020] | +0.014 [-0.010, +0.036] |
| ANC8+ | 21-predictor set | 0.447 / 0.716 | 0.447 / 0.721 | +0.000 [-0.018, +0.017] | +0.004 [-0.007, +0.016] |
| ANC8+ | Full pool | 0.450 / 0.726 | 0.463 / 0.734 | +0.013 [-0.008, +0.029] | +0.008 [-0.006, +0.022] |

Both scored on the same 984 held-out women who started ANC. Neither uses the timing of the first contact; the question is only whether fitting on the entry population itself changes the model.
<!-- /AUTO:cross_horizon -->

---

## 5. The Tigray war

Full account in `docs/WARTIME.md`. The survey records ANC only for births
from about mid-2021, so the comparison is wartime against post-war
pregnancies, net of every other region over the same calendar periods.

<!-- AUTO:wartime -->
| Tigray | Wartime pregnancy (n=259) | Post-war pregnancy (n=323) | Other regions, same periods (pts) | Difference-in-differences (pts) | 95% interval |
|---|---|---|---|---|---|
| Received no antenatal care | 19.5% | 7.7% | +1.2 | **-13.0** | -20.3 to -6.2 |
| Any ANC (ANC1+) | 80.5% | 92.3% | -1.2 | **+13.0** | +6.2 to +20.3 |
| Four or more (ANC4+) | 45.6% | 59.3% | +0.1 | **+13.6** | +5.0 to +22.8 |
| Reached 4, stopped before 8 | 35.8% | 47.0% | -0.5 | **+11.6** | +3.0 to +20.2 |
| Started, stopped before 4 | 34.9% | 33.0% | -1.3 | **-0.7** | -9.7 to +8.1 |
| Eight or more (ANC8+) | 9.8% | 12.3% | +0.6 | **+2.0** | -5.1 to +8.6 |

Robustness: across window shifts of ±3 months and both comparison groups, the ANC4+ effect ranges from +10.9 to +13.6 points.
<!-- /AUTO:wartime -->

- **The damage was at the door.** About one wartime pregnancy in five in
  Tigray received no antenatal care, against one in thirteen after the
  ceasefire: 13 points beyond the change elsewhere.
- **Recovery restored access, not completion.** ANC4+ rose 13.6 points;
  ANC8+ did not measurably change.
- **Tigray against every region:** its change in reaching care is the
  largest of any region, while most move a few points.
- **Not only a war artefact.** Post-war, Tigray is above what its population
  profile predicts for reaching care (ANC1+ +6.3, ANC4+ +7.4 points) and still
  below it for completing care (ANC8+ −2.8).
- **The drivers did not change.** Wealth and distance to a health post
  mattered as much during the war as after (interaction ORs 0.92 and 0.87,
  intervals including 1).

---

## 6. Supporting analyses

Each asks whether the results could be an artefact of the modelling.

- **The algorithm is not the constraint.** Ten model families, tuned on the
  same folds, span only about 0.02 development AP on ANC8+; every one drops
  about 0.08 on held-out women, more than the gap between them.
- **Tuning and preprocessing are small levers.** Tuning bought +0.02 to +0.04
  development AP over library defaults, less than that 0.08 optimism gap; the
  best preprocessing variant +0.003.
- **The signal is additive.** Offered ten pairwise interactions, the
  Explainable Boosting Machine chose none and matched XGBoost on AUROC (0.789
  against 0.788).
- **Calibration is fixable cheaply.** Platt calibration, fitted on inner
  folds, moved the calibration slope from 0.62 to 0.99 at a cost of 0.005 AP;
  isotonic cost 0.023.
- **Modelling the whole count did not help.** The ordinal model was better in
  development (0.500 against 0.494 AP) and worse on held-out women (0.402
  against 0.427).
- **The full pool against the 21, on repeated splits:** +0.031 AP, better in
  20 of 20 splits. On the single held-out set the full-pool model against the
  21-predictor XGBoost is +0.021 AP [−0.036, +0.075]: too few women to
  resolve it.
- **Community context is redundant.** Adding cluster-mean wealth and literacy
  moves development AP from 0.4940 to 0.4909; individual wealth, schooling and
  water source already carry it.

---

## 7. Sensitivity: births in the last 24 months

The predictor-value study repeated on the official window gives the same
leaders: wealth score first in every run, region in every run, pregnancy
intention for ANC4+ and ANC8+, plus years of schooling.

<!-- AUTO:sets_heldout_recent -->
| Outcome | Model | Tier 1 | Tier 1+2 | 21-predictor set | Full pool |
|---|---|---|---|---|---|
| ANC1+ | logistic | 0.920 (-0.003 [-0.021, +0.018]) | 0.920 (-0.003 [-0.021, +0.018]) | 0.921 | 0.930 (+0.008 [-0.004, +0.019]) |
| ANC1+ | LightGBM | 0.916 (+0.008 [-0.021, +0.038]) | 0.916 (+0.008 [-0.021, +0.038]) | 0.907 | 0.940 (+0.032 [+0.012, +0.054]) |
| ANC4+ | logistic | 0.800 (-0.016 [-0.033, +0.001]) | 0.801 (-0.014 [-0.036, +0.008]) | 0.815 | 0.830 (+0.015 [+0.004, +0.027]) |
| ANC4+ | LightGBM | 0.787 (-0.032 [-0.058, -0.003]) | 0.796 (-0.023 [-0.048, +0.003]) | 0.820 | 0.845 (+0.025 [+0.006, +0.049]) |
| ANC8+ | logistic | 0.370 (-0.048 [-0.129, +0.026]) | 0.446 (+0.027 [-0.043, +0.097]) | 0.415 | 0.474 (+0.055 [-0.009, +0.123]) |
| ANC8+ | LightGBM | 0.333 (-0.137 [-0.229, -0.049]) | 0.433 (-0.043 [-0.110, +0.019]) | 0.474 | 0.456 (-0.018 [-0.084, +0.055]) |

Held-out AP, each set fitted on development women and scored once on women it never saw. In brackets: the difference from the 21-predictor set and its 95% paired stratified-PSU bootstrap interval. An interval containing 0 means the held-out set cannot tell the two apart.
<!-- /AUTO:sets_heldout_recent -->

---

## 8. Limitations

Full list in `docs/LIMITATIONS.md`.

- **Associations, not causes.** Nothing here estimates what would happen if a
  woman's circumstances changed.
- **A small held-out set.** 1,375 women, 229 of them attaining ANC8+; most ANC8+
  set comparisons cannot be resolved on it.
- **Screening saw the held-out women** in the first pass. Screening on
  development women alone keeps all 61 admitted variables, with a largest AUC
  shift of 0.013.
- **A sensitive predictor.** The woman's first language is strongly
  predictive and about three-quarters concentrated by region; dropping it
  costs 0.003 AP. Scoring a woman lower because of her language needs an
  explicit justification.
- **One survey round, one country;** a recalled outcome; no facility data;
  no pre-war pregnancies for the war analysis.
