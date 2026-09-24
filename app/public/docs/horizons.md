# Two prediction horizons: before ANC, and at ANC entry

**Question.** A prediction made before a woman starts antenatal care can use
only who she is, her household and where she lives. Once she has started, it
can also use when her first contact happened. Does the answer to "which
predictors, and how many" change at that second horizon? What does knowing
that the first contact was early add?

**Short answer.**

- **Once a woman has started ANC, whether her first contact was early is the
  strongest single predictor after household wealth.** Added alone to the 21
  it raises development AP by +0.032 for ANC4+ and +0.077 for ANC8+, several
  times more than any other candidate, and forward selection picks it second
  (after the wealth score) at both rungs. For ANC8+ it was chosen in all 10
  bootstrap resamples.
- **ANC4+ at entry: 2 to 3 predictors beat all 21.** The wealth score and
  early ANC together score held-out AP 0.880 and AUROC 0.779, against 0.848 and
  0.727 for the 21 (both intervals exclude zero); adding literacy gives 0.881
  and 0.786. The full pool is higher still (0.900, 0.808). On held-out women,
  early ANC adds +0.043 AP and +0.070 AUROC to the 21, interval excluding zero.
- **ANC8+ at entry: about 7 predictors, and the evidence is weaker.** The
  selected set is wealth score, early ANC, occupation, region, say in large
  purchases, pregnancy intention and living at a health post (held-out AP
  0.472 against 0.447 for the 21 and 0.482 for the full pool). Only the full
  pool's AUROC gain over the 21 excludes zero (+0.061); early ANC's own gain
  (+0.027 AP, +0.041 AUROC over the 21) cannot be confirmed on 984 women.
- **A separate model for the entry horizon is not needed.** The same
  predictors fitted on all women score the ANC-entry women as well as models
  fitted on those women alone (every AUROC difference +0.004 to +0.014,
  intervals including zero). What changes at entry is the extra information,
  not the population.
- **The 21 carry less dead weight at entry:** 7 of 21 add nothing for ANC4+
  and 12 for ANC8+, against 10 and 14 before ANC.

---

## 1. The two horizons

| | Before ANC starts | At ANC entry |
|---|---|---|
| Women | 6,893 (all births) | 5,001 who started ANC and know when their first contact was |
| Development / held-out | 5,518 / 1,375 | 4,017 / 984 (the same split, restricted) |
| Outcomes | ANC1+, ANC4+, ANC8+ | ANC4+, ANC8+ (every woman here has ANC1+) |
| Candidate pool | 88 | 89: the 88 plus **early ANC** |

**Early ANC** is 1 when the first contact came by 12 weeks or 3 months, and 0
when it came later: 2,130 of the 5,001 women. It is admissible only at this
horizon: before a woman starts care it is not yet known, and in the full
cohort it would be leakage.

The ANC-entry partition is the full-cohort split restricted to these women,
asserted woman for woman in `src/anc8/cohorts.py`, so every held-out woman at
this horizon is also a held-out woman before ANC.

The whole predictor-value study (PREDICTOR_VALUE.md) is repeated at ANC
entry: the same fixed model, the same bar (+0.005 AP on 4 of 5 splits), the
same stages.

---

## 2. Which predictors carry the prediction at each horizon

<!-- AUTO:horizon_tiers -->
| Outcome | Horizon | Tier 1 | Tier 2 | Prevalence | 21-predictor set | Full pool |
|---|---|---|---|---|---|---|
| ANC4+ | before ANC | Household wealth score, Pregnancy number | Region, Was this pregnancy wanted? | 0.526 | 0.783 | 0.785 |
| ANC4+ | ANC entry | Household wealth score, First ANC contact by 3 months | Literacy | 0.675 | 0.844 | 0.872 |
| ANC8+ | before ANC | Household wealth score, Region | Decides on large purchases, Was this pregnancy wanted?, Mother's occupation, Children ever born, Lives at a health post, Travel time to health post (log) | 0.199 | 0.469 | 0.509 |
| ANC8+ | ANC entry | Household wealth score, First ANC contact by 3 months | Mother's occupation, Region, Decides on large purchases, Was this pregnancy wanted?, Lives at a health post | 0.255 | 0.494 | 0.584 |

Forward selection at each horizon, in order. Development AP; the ANC-entry pool adds the timing of the first contact.
<!-- /AUTO:horizon_tiers -->

<!-- AUTO:tiers_entry -->
**ANC4+**

| Tier | Variable | Code | AP after adding | Gain | Splits | Re-selected | In the 21 |
|---|---|---|---|---|---|---|---|
| tier 1 | Household wealth score | `v191` | 0.824 | +0.1492 | 5/5 | — |  |
| tier 1 | First ANC contact by 3 months | `early_anc` | 0.870 | +0.0454 | 5/5 | — |  |
| tier 2 | Literacy | `v155` | 0.876 | +0.0057 | 5/5 | — |  |
| not selected | Region | `region` | 0.880 | +0.0040 | 5/5 | — | yes |

**ANC8+**

| Tier | Variable | Code | AP after adding | Gain | Splits | Re-selected | In the 21 |
|---|---|---|---|---|---|---|---|
| tier 1 | Household wealth score | `v191` | 0.495 | +0.2391 | 5/5 | 100% |  |
| tier 1 | First ANC contact by 3 months | `early_anc` | 0.580 | +0.0852 | 5/5 | 100% |  |
| tier 2 | Mother's occupation ⚑ | `maternal_occupation_group` | 0.596 | +0.0159 | 5/5 | 50% | yes |
| tier 2 | Region | `region` | 0.605 | +0.0090 | 5/5 | 60% | yes |
| tier 2 | Decides on large purchases | `v743b` | 0.617 | +0.0121 | 5/5 | 30% |  |
| tier 2 | Was this pregnancy wanted? | `pregnancy_intention` | 0.624 | +0.0068 | 5/5 | 50% | yes |
| tier 2 | Lives at a health post | `travel_healthpost_is_zero` | 0.630 | +0.0064 | 5/5 | 20% |  |
| not selected | Partner's education | `partner_education` | 0.634 | +0.0044 | 5/5 | 30% | yes |

⚑ measured at interview rather than during the pregnancy (see DATA_AND_COHORT.md). "Re-selected" is the share of 10 bootstrap resamples in which the same variable was chosen again (ANC8+ only); the last row of each table is the first step that failed the threshold.
<!-- /AUTO:tiers_entry -->

---

## 3. What early ANC adds

Early ANC added to the 21-predictor set, to the set selected at ANC entry
(without early ANC) and to the full pool, on development folds and then once
on the 984 held-out ANC-entry women.

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

---

## 4. Every set at ANC entry, on the held-out women

<!-- AUTO:sets_heldout_entry -->
| Outcome | Model | Tier 1 | Tier 1+2 | 21-predictor set | 21 + early ANC | Full pool |
|---|---|---|---|---|---|---|
| ANC4+ | logistic | 0.880 (+0.033 [+0.003, +0.068]) | 0.881 (+0.034 [+0.001, +0.071]) | 0.848 | 0.891 (+0.043 [+0.019, +0.072]) | 0.900 (+0.051 [+0.026, +0.084]) |
| ANC4+ | LightGBM | 0.874 (+0.012 [-0.020, +0.052]) | 0.869 (+0.007 [-0.027, +0.049]) | 0.862 | 0.893 (+0.031 [+0.006, +0.063]) | 0.896 (+0.033 [+0.007, +0.068]) |
| ANC8+ | logistic | 0.442 (-0.005 [-0.106, +0.088]) | 0.472 (+0.024 [-0.054, +0.093]) | 0.447 | 0.474 (+0.027 [-0.034, +0.082]) | 0.482 (+0.035 [-0.032, +0.096]) |
| ANC8+ | LightGBM | 0.392 (-0.050 [-0.156, +0.052]) | 0.467 (+0.024 [-0.068, +0.107]) | 0.442 | 0.487 (+0.046 [-0.020, +0.108]) | 0.499 (+0.057 [-0.019, +0.134]) |

Held-out AP, each set fitted on development women and scored once on women it never saw. In brackets: the difference from the 21-predictor set and its 95% paired stratified-PSU bootstrap interval. An interval containing 0 means the held-out set cannot tell the two apart.
<!-- /AUTO:sets_heldout_entry -->

**The 21 under three model families, at ANC entry.** Logistic regression, random forest and XGBoost on the same 21 predictors (without early ANC), on the 984 held-out women:

<!-- AUTO:models_21_entry -->
| Outcome | Model | AP | AUROC | AP vs logistic (95% interval) | Calibration slope | Best of three |
|---|---|---|---|---|---|---|
| ANC4+ | Logistic regression | 0.848 | 0.727 | reference | 1.09 |  |
| ANC4+ | Random Forest | 0.855 | 0.734 | +0.008 [-0.006, +0.024] | 1.10 |  |
| ANC4+ | XGBoost | 0.864 | 0.740 | +0.017 [+0.001, +0.034] | 0.79 | best |
| ANC8+ | Logistic regression | 0.447 | 0.721 | reference | 0.73 | best |
| ANC8+ | Random Forest | 0.423 | 0.718 | -0.021 [-0.052, +0.009] | 0.96 |  |
| ANC8+ | XGBoost | 0.440 | 0.728 | -0.006 [-0.044, +0.030] | 0.92 |  |

The 21-predictor set under three model families, each fitted on the development women (random forest and XGBoost tuned on development folds, 20 trials) and scored once on the held-out women. "Best of three" is the highest held-out AP; the interval says whether the held-out women can tell it from logistic regression.
<!-- /AUTO:models_21_entry -->

<!-- AUTO:entry_heldout -->
| Outcome | Set | + early ANC | Predictors | AP | AUROC | Calibration slope |
|---|---|---|---|---|---|---|
| ANC4+ | 21 |  | 21 | 0.848 | 0.727 | 1.091 |
| ANC4+ | 21 | yes | 22 | 0.891 | 0.798 | 1.292 |
| ANC4+ | tier set |  | 2 | 0.836 | 0.710 | 1.166 |
| ANC4+ | tier set | yes | 3 | 0.881 | 0.786 | 1.315 |
| ANC4+ | full pool |  | 88 | 0.863 | 0.750 | 1.168 |
| ANC4+ | full pool | yes | 89 | 0.900 | 0.808 | 1.136 |
| ANC8+ | 21 |  | 21 | 0.447 | 0.721 | 0.730 |
| ANC8+ | 21 | yes | 22 | 0.474 | 0.761 | 0.742 |
| ANC8+ | tier set |  | 6 | 0.435 | 0.705 | 0.741 |
| ANC8+ | tier set | yes | 7 | 0.472 | 0.757 | 0.746 |
| ANC8+ | full pool |  | 88 | 0.463 | 0.734 | 0.811 |
| ANC8+ | full pool | yes | 89 | 0.482 | 0.782 | 0.887 |
<!-- /AUTO:entry_heldout -->

---

## 5. Is a separate model for the entry horizon worth building?

The 21-predictor set and the full pool fitted on all development women
(before ANC), against the same sets fitted on the ANC-entry development
women, both scored on the same 984 held-out women who started ANC. Neither
uses early ANC, so this isolates the effect of fitting on the entry
population.

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

## 6. The 21-predictor models at this horizon

The 21-predictor set was also fitted at ANC entry with logistic regression,
random forest and XGBoost, with and without early ANC (notebook 2). On the
held-out ANC-entry women, adding early ANC raised ANC8+ AP by 0.022 to 0.034 and
AUROC by 0.036 to 0.041 across the three algorithms, with every interval
including zero. Those are the models the web app serves at this horizon.

---

**Reproduce:**

```bash
python scripts/run_feature_value.py --cohort entry --outcome anc8plus
python scripts/run_feature_value.py --cohort entry --outcome anc4plus
python scripts/run_horizons.py
```

Results: `outputs/feature_value/entry/`, `outputs/horizons/`. Figures:
`fig36_horizons`, `fig37_early_anc`.
