# Predictor value: how many predictors, and which

**Question.** Which predictors carry the prediction of ANC8+, and of the two
earlier rungs ANC1+ and ANC4+? How many are needed? Where does the
21-predictor set stand among the alternatives?

Every predictor set this study tried is in one ablation (§2), from a single
variable up to the full candidate pool. The result is stated as a number of
predictors per rung, not as a verdict on any one set.

**Short answer.**

- **ANC8+: 7 to 8 predictors are enough.** Forward selection from the full
  pool keeps 8 (wealth score, region, pregnancy intention, say in large
  purchases, occupation, children ever born, and two measures of access to a
  health post). Within the 21-predictor set, the best 7 do as well. On women
  the models never saw, both match all 21 and the full pool of 88 (held-out
  AP 0.425–0.440 against 0.428 and 0.435; every interval includes zero). Seven
  of the 21 carry the 21's whole value, and the other 14 add nothing or make
  it slightly worse.
- **ANC1+ and ANC4+: more information helps.** No single extra variable
  passes the bar, yet the full pool beats the 21 on held-out women for both
  (AP +0.014 and +0.023, intervals excluding zero). Compact sets of 2 to 13
  predictors fall slightly short of the 21. Reaching care depends on many
  small factors.
- **The same few variables lead everywhere.** The continuous wealth score is
  chosen first in every run, and region in every run. Pregnancy intention
  enters for ANC4+ and ANC8+ but not for reaching care at all.

---

## 1. From 6,648 columns to a candidate pool

The survey's women's file has 6,648 columns. Almost all of them cannot be
predictors of antenatal care: they were not asked in this round, describe
things after the birth, or are observed for too few women. The rest were
screened on development women only and reviewed for timing.

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

**Why the 507 rankable candidates were not admitted.** They have almost no
association with the outcome (median univariate AUC 0.518, where 0.5 is none),
and most come from modules that describe life after the index birth:
breastfeeding and child nutrition, contraception at interview, the birth
histories of other children, sibling mortality and HIV/AIDS knowledge. None
has a plausible path to antenatal care that is known before or early in the
pregnancy.

**Why 9 strong candidates were refused.** They record the care itself.
"Visited a health facility in the last 12 months" (`v394`) is the clearest:
ANC contacts *are* facility visits. Among women whose birth was within the
last 12 months, 67% of those with any ANC report a facility visit against
28% of those with none, a gap that narrows once the birth falls outside the
recall window. HIV testing (routine at Ethiopian ANC), contraception at
interview and first-contact timing are refused for the same reason
(first-contact timing is admitted only at the ANC-entry horizon; see
HORIZONS.md).

**The 21-predictor set** was specified in advance: 21 literature-based
constructs in four domains (maternal, household, pregnancy, access), each
screened for timing. It is one of the sets compared below. One change is made
to it in this study: maternal age enters as **age at the birth**, because for
the 28% of women whose birth was 2-3 years before interview, current age is
that far from the pregnancy.

---

## 2. The result: every set, on the same women

How every comparison is run: the model is held fixed (logistic regression) so
that only the predictors vary. Each set gets its own best regularisation from
a common grid. Sets are built on the development women; the held-out women
score each set once.

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

**Reading the table.** Development AP of a *searched* set (the tiers, the
best k of the 21, the 21 minus its non-contributors) is optimistic, because
the search chose it on those same folds. That is why the selected ANC8+ set
shows 112% of the pool's lift in development and falls back on held-out
women. Only the held-out columns compare sets fairly.

**What it says, rung by rung.**

- **ANC8+.** Four very different sets land within 0.015 held-out AP of each
  other: 7 of the 21, the 8 selected from the pool, all 21 and all 88. The
  held-out women, fewer than 300 of whom attain ANC8+, cannot separate them. The number
  of predictors needed is therefore about **7 to 8**, and more buys nothing
  measurable in AP. The full pool keeps a small AUROC edge (0.776 against
  0.754–0.764), so if ranking every woman matters more than finding the
  attainers, the full pool is the safer choice.
- **ANC4+.** The full pool is clearly best (+0.023 AP, +0.023 AUROC over the
  21, both intervals excluding zero). Every smaller set, including the 4
  selected from the pool and the best 8 of the 21, falls 0.006 to 0.015 AP
  short of the 21.
- **ANC1+.** The same pattern: the full pool beats the 21 (+0.014 AP), and
  cutting the 21 down to its best 11 loses a small but measurable amount
  (−0.007 AP, interval excluding zero).

**So how many predictors?** It depends on the rung. For completing the
schedule, which is the question this study is built around, a set of 7 to 8
does the job. For reaching care, information spread thinly across many
variables adds up, and the full pool is best.

---

## 3. The 21 on their own

### 3.1 Dropping each member

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

Region, pregnancy intention and wealth carry the 21 at every rung. The number
of members that add nothing grows up the ladder: 8 of 21 for ANC1+, 10 for
ANC4+, **14 for ANC8+**. Health insurance, household size, religion, the
weekly media count, internet use and transport mode add nothing to any rung.
Several of those collapse or coarsen information that the full pool carries
better: the media count sums newspaper, radio and television, although
television alone predicts better than the sum (univariate AUC 0.677 against
0.644); the wealth quintile is a five-level cut of the continuous wealth
score (0.742 against 0.755).

### 3.2 How many of the 21 are needed

Greedy forward selection within the 21, all the way to 21 (fig34):

<!-- AUTO:path_within_21 -->
**ANC1+**

| Step | Added | AP | Gain | Splits | Share of full-pool lift |
|---|---|---|---|---|---|
| 1 | Wealth quintile | 0.885 | +0.1061 | 5/5 | 76% |
| 2 | Region | 0.904 | +0.0187 | 5/5 | 89% |
| 3 | Partner's education | 0.911 | +0.0069 | 5/5 | 94% |
| 4 | Urban or rural | 0.914 | +0.0028 | 5/5 | 96% |
| 5 | Gap since previous pregnancy | 0.916 | +0.0024 | 5/5 | 98% |
| 6 | Was this pregnancy wanted? | 0.917 | +0.0009 | 5/5 | 99% |
| 7 | Mother's occupation | 0.918 | +0.0010 | 5/5 | 99% |
| 8 | Partner's occupation | 0.919 | +0.0007 | 3/5 | 100% |

**ANC4+**

| Step | Added | AP | Gain | Splits | Share of full-pool lift |
|---|---|---|---|---|---|
| 1 | Wealth quintile | 0.718 | +0.1917 | 5/5 | 74% |
| 2 | Pregnancy number | 0.755 | +0.0375 | 5/5 | 88% |
| 3 | Region | 0.772 | +0.0172 | 5/5 | 95% |
| 4 | Partner's education | 0.782 | +0.0100 | 5/5 | 99% |
| 5 | Was this pregnancy wanted? | 0.789 | +0.0067 | 5/5 | 101% |
| 6 | Urban or rural | 0.791 | +0.0023 | 5/5 | 102% |
| 7 | Mother's age at the birth | 0.793 | +0.0014 | 5/5 | 103% |
| 8 | Travel time to hospital or health centre | 0.793 | +0.0002 | 4/5 | 103% |

**ANC8+**

| Step | Added | AP | Gain | Splits | Share of full-pool lift |
|---|---|---|---|---|---|
| 1 | Wealth quintile | 0.364 | +0.1646 | 5/5 | 53% |
| 2 | Region | 0.439 | +0.0754 | 5/5 | 78% |
| 3 | Partner's education | 0.475 | +0.0365 | 5/5 | 89% |
| 4 | Was this pregnancy wanted? | 0.494 | +0.0186 | 5/5 | 95% |
| 5 | Mother's occupation | 0.501 | +0.0072 | 5/5 | 98% |
| 6 | Previous pregnancy outcomes | 0.505 | +0.0042 | 4/5 | 99% |
| 7 | Travel time to hospital or health centre | 0.509 | +0.0032 | 5/5 | 100% |
| 8 | Has a say in her own healthcare | 0.508 | -0.0002 | 2/5 | 100% |

The first eight steps of the greedy path within the 21; the rest add nothing or lose AP.
<!-- /AUTO:path_within_21 -->

<!-- AUTO:why21 -->
| Outcome | Prevalence | Selected from the pool | Best 3 of the 21 | Best k of the 21 | 21 minus non-contributors | All 21 | Full pool |
|---|---|---|---|---|---|---|---|
| ANC1+ | 0.779 | 2 → 0.911 (94%) | 3 → 0.911 (94%) | 11 → 0.921 (101%) | 13 → 0.921 (101%) | 21 → 0.916 (98%) | 88 → 0.919 (100%) |
| ANC4+ | 0.526 | 4 → 0.786 (100%) | 3 → 0.772 (95%) | 8 → 0.793 (103%) | 11 → 0.793 (103%) | 21 → 0.783 (99%) | 88 → 0.785 (100%) |
| ANC8+ | 0.199 | 8 → 0.545 (112%) | 3 → 0.475 (89%) | 7 → 0.509 (100%) | 7 → 0.508 (100%) | 21 → 0.469 (87%) | 88 → 0.509 (100%) |

Development AP, n → AP (share of the full pool's lift over prevalence). "Best 3 / best k of the 21" follow the greedy path within the 21; the selected sets and the path are chosen on these folds and so are optimistic -- the held-out table is the fair comparison.
<!-- /AUTO:why21 -->

For ANC8+ the path peaks at 7 predictors with the full pool's development
AP, and every further member lowers it: all 21 reach only 87% of the pool's
lift. For ANC1+ and ANC4+ the path is flat after about 8, so the 21 are about
as good as their best subset.

*Caveat.* Dropping a member that duplicates another understates it, and a
variable can belong in a data collection for reasons prediction cannot see,
such as equity monitoring or comparability with earlier surveys. "Adds
nothing to prediction" is not "should not be collected".

---

## 4. What the rest of the pool adds

### 4.1 Each candidate added alone to the 21

A candidate counts only if it raises AP by at least **0.005 on average and on
at least 4 of 5 splits**.

<!-- AUTO:add_one -->
| Outcome | Clear +0.005 alone | Median gain | All added | Best 5 carry | Best 10 carry | Peak at n added |
|---|---|---|---|---|---|---|
| ANC1+ | 0 of 67 | -0.0001 | +0.0031 | — | — | 11 (+0.0094) |
| ANC4+ | 0 of 67 | -0.0000 | +0.0023 | — | — | 24 (+0.0088) |
| ANC8+ | 8 of 67 | -0.0003 | +0.0392 | 88% | 107% | 15 (+0.0483) |

"All added" is the AP of the 21 plus every other candidate, minus the 21 alone. A share above 100% means the remaining additions, taken together, made the model worse.
<!-- /AUTO:add_one -->

<!-- AUTO:top_additions -->
**ANC1+**

| Addition to the 21 | Code | Gain | Splits | Clears |
|---|---|---|---|---|
| Sex of household head | `v151` | +0.0018 | 5/5 |  |
| Reads newspapers | `v157` | +0.0018 | 5/5 |  |
| Worked in the last year | `v731` | +0.0017 | 5/5 |  |
| Listens to radio weekly | `radio_weekly` | +0.0015 | 5/5 |  |
| Thinks beating justified: neglects children | `v744b` | +0.0013 | 5/5 |  |
| Decides on family visits | `v743d` | +0.0013 | 5/5 |  |
| Listens to radio | `v158` | +0.0013 | 5/5 |  |
| Mother's occupation | `v716` | +0.0012 | 5/5 |  |

**ANC4+**

| Addition to the 21 | Code | Gain | Splits | Clears |
|---|---|---|---|---|
| Listens to radio weekly | `radio_weekly` | +0.0048 | 5/5 |  |
| Household wealth score | `v191` | +0.0033 | 5/5 |  |
| Watches television weekly | `television_weekly` | +0.0031 | 5/5 |  |
| Listens to radio | `v158` | +0.0028 | 5/5 |  |
| Has a bank account | `v170` | +0.0024 | 5/5 |  |
| Watches television | `v159` | +0.0024 | 5/5 |  |
| Partner's schooling minus hers | `spousal_education_gap` | +0.0018 | 4/5 |  |
| Mother's years of schooling | `v133` | +0.0017 | 4/5 |  |

**ANC8+**

| Addition to the 21 | Code | Gain | Splits | Clears |
|---|---|---|---|---|
| Household wealth score | `v191` | +0.0168 | 5/5 | yes |
| Wealth quintile (urban/rural) | `v190a` | +0.0126 | 5/5 | yes |
| Decides on large purchases | `v743b` | +0.0077 | 5/5 | yes |
| Listens to radio weekly | `radio_weekly` | +0.0069 | 5/5 | yes |
| Listens to radio | `v158` | +0.0062 | 5/5 | yes |
| Lives at a health post | `travel_healthpost_is_zero` | +0.0058 | 5/5 | yes |
| Household wealth score (urban/rural) | `v191a` | +0.0056 | 5/5 | yes |
| Drinking water source | `v113` | +0.0052 | 5/5 | yes |
<!-- /AUTO:top_additions -->

For ANC8+, the wealth score leads (+0.017), then the urban/rural wealth
measures, say in large purchases, radio, and living at a health post. For
ANC1+ and ANC4+ nothing passes the bar alone.

### 4.2 All of them together

Stacked onto the 21 in order of their individual gain (fig27), the
development curve rises for a handful of additions and then runs flat. On
held-out women, the answer depends on the rung: the full pool beats the 21
for ANC1+ and ANC4+ with intervals excluding zero, and cannot be separated
from it for ANC8+ (§2). A per-variable bar is good at finding strong
individual predictors and poor at detecting value spread thinly across many;
+0.005 AP is also a much harsher requirement for ANC1+, whose whole room
above prevalence is about 0.14 AP, than for ANC8+ (about 0.31).

---

## 5. Building from nothing: the tiers

Forward selection over the full pool, stopping at the first step that fails
the bar. **Tier 1** is the core, up to 90% of the full pool's lift over
prevalence; **tier 2** is each further step that still passes.

<!-- AUTO:tiers -->
**ANC1+**

| Tier | Variable | Code | AP after adding | Gain | Splits | Re-selected | In the 21 |
|---|---|---|---|---|---|---|---|
| tier 1 | Household wealth score | `v191` | 0.902 | +0.1227 | 5/5 | — |  |
| tier 1 | Region | `region` | 0.911 | +0.0093 | 5/5 | — | yes |
| not selected | Reads newspapers | `v157` | 0.915 | +0.0034 | 5/5 | — |  |

**ANC4+**

| Tier | Variable | Code | AP after adding | Gain | Splits | Re-selected | In the 21 |
|---|---|---|---|---|---|---|---|
| tier 1 | Household wealth score | `v191` | 0.759 | +0.2335 | 5/5 | — |  |
| tier 1 | Pregnancy number | `pregnancy_order_group` | 0.771 | +0.0113 | 5/5 | — | yes |
| tier 2 | Region | `region` | 0.780 | +0.0094 | 5/5 | — | yes |
| tier 2 | Was this pregnancy wanted? | `pregnancy_intention` | 0.786 | +0.0057 | 5/5 | — | yes |
| not selected | Mother's years of schooling | `v133` | 0.790 | +0.0042 | 5/5 | — |  |

**ANC8+**

| Tier | Variable | Code | AP after adding | Gain | Splits | Re-selected | In the 21 |
|---|---|---|---|---|---|---|---|
| tier 1 | Household wealth score | `v191` | 0.471 | +0.2721 | 5/5 | 100% |  |
| tier 1 | Region | `region` | 0.491 | +0.0199 | 5/5 | 80% | yes |
| tier 2 | Decides on large purchases | `v743b` | 0.504 | +0.0130 | 5/5 | 30% |  |
| tier 2 | Was this pregnancy wanted? | `pregnancy_intention` | 0.514 | +0.0106 | 5/5 | 90% | yes |
| tier 2 | Mother's occupation ⚑ | `maternal_occupation_group` | 0.524 | +0.0099 | 5/5 | 30% | yes |
| tier 2 | Children ever born | `v201` | 0.532 | +0.0074 | 5/5 | 20% |  |
| tier 2 | Lives at a health post | `travel_healthpost_is_zero` | 0.537 | +0.0051 | 5/5 | 60% |  |
| tier 2 | Travel time to health post (log) | `travel_healthpost_log` | 0.545 | +0.0078 | 5/5 | 30% |  |
| not selected | Children above her stated ideal ⚑ | `children_over_ideal` | 0.550 | +0.0049 | 5/5 | 10% |  |

⚑ measured at interview rather than during the pregnancy (see DATA_AND_COHORT.md). "Re-selected" is the share of 10 bootstrap resamples in which the same variable was chosen again (ANC8+ only); the last row of each table is the first step that failed the threshold.
<!-- /AUTO:tiers -->

<!-- AUTO:placement -->
| Member of the 21 | ANC1+ | ANC4+ | ANC8+ |
|---|---|---|---|
| Mother's age at the birth | · | · | · |
| Mother's education level | · | · | · |
| Marital status | · | · | · |
| Mother's occupation | · | · | T2 |
| Partner's education | · | · | · |
| Partner's occupation | · | · | · |
| Has a say in her own healthcare | · | · | · |
| Wealth quintile | · | · | · |
| Urban or rural | · | · | · |
| Region | T1 | T2 | T1 |
| Household size | · | · | · |
| Religion | · | · | · |
| Weekly media count (0-3) | · | · | · |
| Internet use | · | · | · |
| Has health insurance | · | · | · |
| Pregnancy number | · | T1 | · |
| Gap since previous pregnancy | · | · | · |
| Was this pregnancy wanted? | · | T2 | T2 |
| Previous pregnancy outcomes | · | · | · |
| Travel time to hospital or health centre | · | · | · |
| Usual transport to care | · | · | · |
| **selected** | 1 | 3 | 3 |

T1 / T2 = chosen in tier 1 / tier 2 when selecting from the full pool; · = not chosen. Age enters as age at the birth.
<!-- /AUTO:placement -->

**Stability.** For ANC8+ the selection was re-run on 10 cluster-bootstrap
resamples of the development women: wealth score 100%, pregnancy intention
90%, region 80% (first language, which is heavily concentrated by region,
took its place in the others), health-post access 60%, and 20-30% for each of
the other tier-2 places. So the reliable core is **three or four variables**
and the rest of tier 2 is "one variable from each of these areas": say in
household decisions, work, parity and health-post access.

### 5.1 The same sets with a different model

Each set was also refitted with LightGBM, tuned per set on development folds,
and scored on held-out women:

<!-- AUTO:sets_heldout -->
| Outcome | Model | Tier 1 | Tier 1+2 | 21-predictor set | Full pool |
|---|---|---|---|---|---|
| ANC1+ | logistic | 0.916 (+0.001 [-0.019, +0.021]) | 0.916 (+0.001 [-0.019, +0.021]) | 0.913 | 0.928 (+0.014 [+0.003, +0.027]) |
| ANC1+ | LightGBM | 0.908 (+0.000 [-0.022, +0.023]) | 0.908 (+0.000 [-0.022, +0.023]) | 0.907 | 0.934 (+0.026 [+0.011, +0.044]) |
| ANC4+ | logistic | 0.773 (-0.010 [-0.035, +0.016]) | 0.776 (-0.006 [-0.037, +0.021]) | 0.782 | 0.806 (+0.023 [+0.011, +0.035]) |
| ANC4+ | LightGBM | 0.756 (-0.039 [-0.068, -0.010]) | 0.754 (-0.040 [-0.067, -0.012]) | 0.795 | 0.819 (+0.024 [+0.004, +0.046]) |
| ANC8+ | logistic | 0.395 (-0.034 [-0.095, +0.028]) | 0.425 (-0.006 [-0.056, +0.033]) | 0.428 | 0.435 (+0.002 [-0.061, +0.052]) |
| ANC8+ | LightGBM | 0.394 (-0.018 [-0.095, +0.057]) | 0.417 (+0.004 [-0.066, +0.075]) | 0.408 | 0.434 (+0.019 [-0.042, +0.075]) |

Held-out AP, each set fitted on development women and scored once on women it never saw. In brackets: the difference from the 21-predictor set and its 95% paired stratified-PSU bootstrap interval. An interval containing 0 means the held-out set cannot tell the two apart.
<!-- /AUTO:sets_heldout -->

**The 21 under three model families.** Logistic regression, random forest and XGBoost on the same 21 predictors, on the held-out women:

<!-- AUTO:models_21 -->
| Outcome | Model | AP | AUROC | AP vs logistic (95% interval) | Calibration slope | Best of three |
|---|---|---|---|---|---|---|
| ANC1+ | Logistic regression | 0.913 | 0.784 | reference | 0.92 | best |
| ANC1+ | Random Forest | 0.909 | 0.788 | -0.005 [-0.017, +0.005] | 1.25 |  |
| ANC1+ | XGBoost | 0.908 | 0.783 | -0.005 [-0.012, +0.002] | 1.08 |  |
| ANC4+ | Logistic regression | 0.782 | 0.769 | reference | 1.08 |  |
| ANC4+ | Random Forest | 0.788 | 0.774 | +0.006 [-0.007, +0.020] | 1.28 |  |
| ANC4+ | XGBoost | 0.797 | 0.779 | +0.014 [-0.005, +0.036] | 0.84 | best |
| ANC8+ | Logistic regression | 0.428 | 0.762 | reference | 0.78 | best |
| ANC8+ | Random Forest | 0.412 | 0.769 | -0.014 [-0.042, +0.010] | 1.01 |  |
| ANC8+ | XGBoost | 0.414 | 0.771 | -0.014 [-0.051, +0.020] | 0.90 |  |

The 21-predictor set under three model families, each fitted on the development women (random forest and XGBoost tuned on development folds, 20 trials) and scored once on the held-out women. "Best of three" is the highest held-out AP; the interval says whether the held-out women can tell it from logistic regression.
<!-- /AUTO:models_21 -->

The ordering holds for ANC8+. For ANC4+ LightGBM makes the compact sets'
shortfall larger (up to −0.04 AP), which confirms that reaching four contacts
needs more than a few variables.

---

## 6. How predictor value changes from ANC1+ to ANC8+

Each predictor's value relative to the 21-predictor set, at every rung, as a
share of that rung's ceiling (full-pool development AP minus prevalence). For
members of the 21 it is the AP lost when dropped; for the rest, the AP gained
when added. T1 / T2 mark where forward selection placed it.

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

**Region and wealth become more valuable up the ladder.** Region is worth
2.7% of the ANC1+ ceiling and 8.7% of the ANC8+ ceiling; the continuous wealth
score 0.3% and 5.4%. Say in large household purchases, the drinking-water
source and living at a health post matter only for completing the schedule.

**Some matter only for reaching care.** Residence, the gap since the
previous pregnancy, sex of the household head, education level and attitudes
to partner violence carry value for ANC1+ and none for ANC8+.

The importance methods (exact EBM contributions, SHAP on XGBoost and drop-one
from the full pool) give an independent view of the same shift, with
duplicates counted once:

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

<!-- AUTO:ladder_patterns -->
**Matter more for completing the schedule**

| Predictor | Domain | Share shift ANC1+ → ANC8+ | Methods agreeing |
|---|---|---|---|
| Household wealth score | Socioeconomic | +0.034 | 2/3 |
| Travel time to health post (log) | Access and distance | +0.029 | 3/3 |
| Was this pregnancy wanted? | Reproductive history | +0.027 | 3/3 |
| First language | Geography and culture | +0.026 | 2/3 |
| Literacy | Education and information | +0.025 | 3/3 |
| Household wealth score (urban/rural) | Socioeconomic | +0.019 | 2/3 |
| Internet use | Education and information | +0.017 | 2/3 |
| Region | Geography and culture | +0.016 | 2/3 |
| Thinks beating justified: burns food | Agency and household | +0.013 | 2/3 |
| Wealth quintile (urban/rural) | Socioeconomic | +0.012 | 2/3 |

**Matter more for reaching care at all**

| Predictor | Domain | Share shift ANC1+ → ANC8+ | Methods agreeing |
|---|---|---|---|
| Sex of household head | Agency and household | -0.029 | 3/3 |
| Attitudes accepting of partner violence | Agency and household | -0.026 | 3/3 |
| Urban or rural | Geography and culture | -0.023 | 3/3 |
| Wealth quintile | Socioeconomic | -0.021 | 2/3 |
| Partner's age minus hers | Agency and household | -0.020 | 2/3 |
| Mother's occupation | Work | -0.020 | 2/3 |
| Mother's years of schooling | Education and information | -0.017 | 3/3 |
| Partner's education level | Agency and household | -0.015 | 2/3 |
| Reads newspapers | Education and information | -0.015 | 3/3 |
| Partner's occupation | Agency and household | -0.013 | 3/3 |
<!-- /AUTO:ladder_patterns -->

The balance moves **from household position to money, distance and
intention**: agency and household factors carry the largest share for
reaching care (28%) and the smallest for completing it (19%), while
socioeconomic factors, reproductive history (chiefly whether the pregnancy
was wanted) and access gain. EBM and SHAP agree well at every rung; drop-one
agrees with neither beyond ANC1+, because one of 85 correlated variables is
easily replaced by the others:

<!-- AUTO:method_agreement -->
| Outcome | Methods | Rank agreement, predictors | Rank agreement, domains |
|---|---|---|---|
| ANC1+ | EBM vs SHAP | 0.75 | 0.64 |
| ANC1+ | EBM vs drop-one | 0.32 | 0.57 |
| ANC1+ | SHAP vs drop-one | 0.41 | 0.79 |
| ANC4+ | EBM vs SHAP | 0.76 | 1.00 |
| ANC4+ | EBM vs drop-one | -0.01 | 0.25 |
| ANC4+ | SHAP vs drop-one | 0.01 | 0.25 |
| ANC8+ | EBM vs SHAP | 0.58 | 0.89 |
| ANC8+ | EBM vs drop-one | 0.08 | 0.43 |
| ANC8+ | SHAP vs drop-one | 0.03 | 0.39 |
<!-- /AUTO:method_agreement -->

---

## 7. Sensitivity: births in the last 24 months

The whole study was repeated on the DHS-8 window (5,037 women). The leading
variables are the same: wealth score first in every run, region in every run,
pregnancy intention for ANC4+ and ANC8+; years of schooling (the continuous
count) also enters for ANC4+ and ANC8+.

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

The 21 under three model families, 24-month window:

<!-- AUTO:models_21_recent -->
| Outcome | Model | AP | AUROC | AP vs logistic (95% interval) | Calibration slope | Best of three |
|---|---|---|---|---|---|---|
| ANC1+ | Logistic regression | 0.921 | 0.777 | reference | 0.86 |  |
| ANC1+ | Random Forest | 0.924 | 0.780 | +0.002 [-0.010, +0.012] | 1.05 | best |
| ANC1+ | XGBoost | 0.914 | 0.768 | -0.007 [-0.020, +0.003] | 0.76 |  |
| ANC4+ | Logistic regression | 0.815 | 0.778 | reference | 1.13 |  |
| ANC4+ | Random Forest | 0.826 | 0.790 | +0.010 [-0.008, +0.027] | 1.19 | best |
| ANC4+ | XGBoost | 0.825 | 0.791 | +0.009 [-0.007, +0.026] | 1.06 |  |
| ANC8+ | Logistic regression | 0.415 | 0.763 | reference | 1.04 |  |
| ANC8+ | Random Forest | 0.451 | 0.783 | +0.034 [-0.021, +0.092] | 1.18 |  |
| ANC8+ | XGBoost | 0.475 | 0.781 | +0.057 [-0.008, +0.118] | 1.14 | best |

The 21-predictor set under three model families, each fitted on the development women (random forest and XGBoost tuned on development folds, 20 trials) and scored once on the held-out women. "Best of three" is the highest held-out AP; the interval says whether the held-out women can tell it from logistic regression.
<!-- /AUTO:models_21_recent -->

<!-- AUTO:tiers_recent -->
**ANC1+**

| Tier | Variable | Code | AP after adding | Gain | Splits | Re-selected | In the 21 |
|---|---|---|---|---|---|---|---|
| tier 1 | Household wealth score | `v191` | 0.906 | +0.1230 | 5/5 | — |  |
| tier 1 | Region | `region` | 0.916 | +0.0105 | 5/5 | — | yes |
| not selected | Mother's years of schooling | `v133` | 0.920 | +0.0033 | 5/5 | — |  |

**ANC4+**

| Tier | Variable | Code | AP after adding | Gain | Splits | Re-selected | In the 21 |
|---|---|---|---|---|---|---|---|
| tier 1 | Household wealth score | `v191` | 0.762 | +0.2323 | 5/5 | — |  |
| tier 1 | Mother's years of schooling | `v133` | 0.777 | +0.0154 | 5/5 | — |  |
| tier 2 | Region | `region` | 0.790 | +0.0132 | 5/5 | — | yes |
| tier 2 | Was this pregnancy wanted? | `pregnancy_intention` | 0.799 | +0.0084 | 5/5 | — | yes |
| not selected | Travel time to hospital or health centre | `travel_time_min` | 0.802 | +0.0031 | 5/5 | — | yes |

**ANC8+**

| Tier | Variable | Code | AP after adding | Gain | Splits | Re-selected | In the 21 |
|---|---|---|---|---|---|---|---|
| tier 1 | Household wealth score | `v191` | 0.469 | +0.2646 | 5/5 | 100% |  |
| tier 2 | Region | `region` | 0.493 | +0.0239 | 5/5 | 90% | yes |
| tier 2 | Mother's years of schooling | `v133` | 0.508 | +0.0154 | 5/5 | 10% |  |
| tier 2 | Was this pregnancy wanted? | `pregnancy_intention` | 0.522 | +0.0137 | 5/5 | 50% | yes |
| not selected | Partner's age minus hers | `spousal_age_gap` | 0.527 | +0.0047 | 5/5 | 40% |  |

⚑ measured at interview rather than during the pregnancy (see DATA_AND_COHORT.md). "Re-selected" is the share of 10 bootstrap resamples in which the same variable was chosen again (ANC8+ only); the last row of each table is the first step that failed the threshold.
<!-- /AUTO:tiers_recent -->

---

## 8. What this means

**For predicting ANC8+,** a short form does the work of the long one: wealth,
region, whether the pregnancy was wanted, the woman's work and standing in
household decisions, and access to a health post. These are questions a
survey or registration form already asks.

**For predicting whether women reach care at all,** keep the full set of
information: the gain is modest per variable and real in total.

**For the 21-predictor set,** its core (region, wealth, pregnancy intention)
is right. Its weak points are measurable: the wealth measure and education are
coarsened into categories, the media count collapses its best component, and
two-thirds of its members add nothing to ANC8+.

**Two cautions.**

- **Prediction is not causation.** A variable that predicts well is not
  necessarily one whose change would change attainment.
- **Some selected variables are measured at interview** (⚑ in the tier
  tables), such as current occupation. For births 2-3 years before interview
  they may partly reflect life after the pregnancy. The 24-month window
  reduces, but does not remove, that concern.

---

**Reproduce:**

```bash
python scripts/run_feature_value.py --cohort full --outcome anc8plus   # stages 0-3
python scripts/run_why21_heldout.py                                     # §2 held-out rows
python scripts/run_predictor_matrix.py                                  # §6
```

Results: `outputs/feature_value/<cohort>/<outcome>/`, `outputs/predictor_value/`.
Figures: fig26-fig30, fig33-fig35. Code: `src/anc8/selection.py`, whose fast
scorer reproduces the full scikit-learn pipeline exactly (0.0 AP difference).
