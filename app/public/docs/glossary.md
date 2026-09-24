# Understanding the numbers

A guide to every term, score and chart used in this analysis, written for
someone with no background in statistics. Read "Start here" first: it builds
the main accuracy measures from one simple example. The terms that follow can
then be looked up as needed, and the last section explains how to read each
figure.

What was tested, and how, is recorded analysis by analysis in
`docs/ANALYSIS_RECORD.md`.

---

## Start here: 100 women

Imagine 100 women who gave birth recently. **19 of them completed eight or
more antenatal care contacts (ANC8+)** and 81 did not. That is close to the
real national figure of 19.2%.

A model looks at facts about each woman (her household's wealth, her region,
whether she wanted the pregnancy, and so on) and gives her a score between 0
and 1: its estimate of how likely she is to reach eight contacts.

**Why we don't report "accuracy".** Accuracy is the share of women the model
labels correctly. A "model" that ignores every fact and says *no woman will
reach eight contacts* is right about the 81 who did not. Its accuracy is 81%,
and it is completely useless. When one outcome is much rarer than the other,
accuracy rewards ignoring the rare one. So this analysis uses measures that
cannot be gamed this way.

**Ranking, not labelling.** Sort the 100 women from highest score to lowest.
A good model puts most of the 19 near the top. Every measure below is a way
of asking *how near the top?*

**Precision and recall.** Suppose a programme can visit the 20 women with the
highest scores. If 10 of those 20 actually reached eight contacts:

- **precision** is 10 out of 20 = 50%: of the women we picked, how many were
  right;
- **recall** is 10 out of 19 = 53%: of all the women who really reached eight
  contacts, how many we found.

Visiting more women raises recall and usually lowers precision.

**Average precision (AP).** Walk down the sorted list and record the
precision each time you reach another woman who really attained the outcome.
AP is the average of those precisions. It is 1.0 if all 19 are at the very
top. If the model ranks at random, AP is about **0.19**: the share of women
who attain the outcome, because a random pick is right 19% of the time. So:

> **AP always has to be read against the prevalence.** An AP of 0.43 on
> ANC8+ (prevalence 0.19) is a real signal. An AP of 0.43 on ANC1+
> (prevalence 0.78) would be worse than guessing.

**AUROC (also written AUC).** Pick one woman who reached eight contacts and
one who did not, at random. AUROC is the chance that the model gave the first
woman the higher score. A coin flip gives **0.5**, perfect ranking gives
**1.0**. Our models score about **0.76 to 0.83**: they put the right woman of
the pair higher about three times in four. AUROC does not depend on how
common the outcome is. That is why it is the measure used to compare ANC1+,
ANC4+ and ANC8+ with each other.

**Lift.** AP minus the prevalence: how much better than a blind guess. On
ANC8+, AP 0.427 minus 0.192 = lift **+0.236**.

**Calibration.** Take all the women the model gave a score of about 30%. If
about 30 in 100 of them really reached eight contacts, the model is **well
calibrated**: its scores can be read as rates. A model can rank well and
still be badly calibrated, for example by saying 60% where the true rate is
40%.

**The size of differences in this analysis.** Most comparisons here are
changes in AP of **0.005 to 0.04**, which is half a point to four points out
of 100. When one set of predictors "adds +0.03 AP", the model's ranking of
women improved by about three points on that 0-to-1 scale.

---

## The outcomes

### Antenatal care (ANC)
<!-- id: anc | aka: ANC contact, antenatal visit -->
**In plain words.** Health checks during pregnancy with a doctor, nurse,
midwife or health officer. Each check is a "contact".

**In this analysis.** The number of contacts a woman reported for her most
recent pregnancy, taken from the survey.

### ANC1+, ANC4+ and ANC8+
<!-- id: anc-rungs | aka: ANC1+, ANC4+, ANC8+, rung, ladder -->
**In plain words.** At least one, at least four, and at least eight
contacts. Eight is the World Health Organization's recommendation (2016);
four was the earlier standard.

**In this analysis.** Nationally 77.6%, 52.4% and 19.2% of women reach each
level (survey-weighted, all 6,893 women). We call the three levels the
"ladder", and each level a "rung".

### Cascade
<!-- id: cascade | aka: drop-off, where women are lost -->
**In plain words.** The ladder read as a sequence of losses: women who never
start, who start but stop before four, who reach four but stop before eight,
and who reach eight.

**In this analysis.** Counted directly from the survey, with no model
involved. This makes it the sturdiest evidence in the analysis.

### Continuation
<!-- id: continuation | aka: retention, continue 4 to 8 -->
**In plain words.** Of the women who reached one rung, the share who went on
to the next.

**In this analysis.** 68% of women who start go on to four contacts. Only
37% of those who reach four go on to eight.

### Prevalence
<!-- id: prevalence | aka: base rate, attainment rate, no-information AP -->
**In plain words.** How common the outcome is: the share of women who
attained it.

**In this analysis.** 0.776 for ANC1+, 0.524 for ANC4+ and 0.192 for ANC8+.
It is also the AP a model with no information would get, so it is the floor
every AP must be read against.

---

## The data

### DHS (Demographic and Health Survey)
<!-- id: dhs | aka: EDHS, EDHS 2024-25, Individual Recode, IR file -->
**In plain words.** A large national household survey, run in many countries
with the same questions, so results can be compared.

**In this analysis.** The 2024-25 Ethiopia DHS women's file (the
"Individual Recode"). It has 6,648 columns, one row per woman interviewed.

### Cohort
<!-- id: cohort | aka: study population, analytic cohort, 6,893 women -->
**In plain words.** The group of women an analysis is about.

**In this analysis.** Three groups:
- the **6,893 women** whose most recent pregnancy has a recorded ANC count
  (the main analysis, and the first prediction horizon);
- the **5,001 women** among them who started ANC and know when their first
  contact was (the second prediction horizon);
- the **5,037 women** who gave birth in the 24 months before interview (a
  sensitivity check).

### 24-month window
<!-- id: window24 | aka: recent births, DHS-8 window, last 24 months, recent cohort -->
**In plain words.** The official survey definition only counts births in the
two years before the interview. Older births are recalled less reliably.

**In this analysis.** 5,037 women. With this window, our numbers reproduce
the official EDHS report's national ANC4+ figure exactly (53.0% against
53.0%). About 28% of the 6,893 women gave birth 2-3 years before
interview. Used as a sensitivity check on the main results.

### Survey weight
<!-- id: weight | aka: weighted, survey-weighted, v005 -->
**In plain words.** The survey deliberately samples some areas more heavily
than others. Each woman carries a weight so that the results represent the
whole country, not just the sample.

**In this analysis.** Every percentage and every accuracy score is weighted.

### Cluster (PSU)
<!-- id: cluster | aka: PSU, primary sampling unit, enumeration area, v021 -->
**In plain words.** The survey visits small areas (villages or city blocks)
and interviews several women in each. Women in the same area resemble each
other.

**In this analysis.** A cluster is never split between training and testing.
If it were, the model would be tested partly on the neighbours of women it
learned from, which flatters it.

### Stratum
<!-- id: stratum | aka: strata, v022 -->
**In plain words.** The survey divides the country into groups (region ×
urban/rural) and samples inside each group separately.

**In this analysis.** There are 27 strata. Test sets and bootstrap resamples
keep every stratum represented.

### Predictor
<!-- id: predictor | aka: feature, variable, characteristic, input -->
**In plain words.** One fact about a woman that the model uses: her region,
her household's wealth, whether she wanted the pregnancy, and so on.

**In this analysis.** Two sets are compared throughout. The
**21-predictor set** is the study's pre-specified set of constructs across
four domains. The **full candidate pool** comes from screening all 6,648
survey columns: 95 columns, which are 85 distinct variables because 10 were
copies of each other. The predictor-value study uses 88: the 85 plus 3
constructs that exist only in the 21-predictor set.

### Temporality
<!-- id: temporality | aka: before the pregnancy, measured at interview -->
**In plain words.** A predictor must describe something known *before or
early in* the pregnancy. Otherwise the model would be "predicting" care from
facts that come after it.

**In this analysis.** Predictors measured at interview (for example "worked
in the last year") are marked ⚑. They may partly describe life after the
birth.

### Leakage
<!-- id: leakage | aka: leak, leaky variable -->
**In plain words.** A predictor that secretly contains the answer. For
example, "visited a health facility in the last 12 months" is partly the ANC
visits themselves. A model using it looks excellent and is useless.

**In this analysis.** Excluded, each with a stated reason:
- timing of the first ANC visit;
- place of delivery;
- tetanus doses;
- HIV testing (routine at ANC);
- contraception measured at interview;
- number of living children (it falls if the baby died).

---

## How models are tested

### Development set and held-out set
<!-- id: heldout | aka: held-out, locked held-out, test set, development set, training, 1,375 women -->
**In plain words.** The women are split once:
- the **development set** (5,518 women) is used to build, compare and tune
  models;
- the **held-out set** (1,375 women) is locked away and used only at the
  end, to see how a finished model does on women it has never seen.

This is the only fair test.

**In this analysis.** One split, drawn once by survey cluster and used for
every analysis, outcome and horizon, so every result is scored on the same
women. The held-out set has only 229 women who reached ANC8+, so its
verdicts come with wide uncertainty. At the ANC-entry horizon the split is
the same one, restricted to the 5,001 women who started ANC (4,017
development, 984 held out).

### Cross-validation and folds
<!-- id: cv | aka: cross-validation, fold, out-of-fold, OOF, development AP -->
**In plain words.** A way to test inside the development set without
touching the held-out women:
1. cut the development women into 5 groups ("folds");
2. train on 4 of them and score the 5th;
3. repeat until every group has been scored once.

The resulting "out-of-fold" score uses every development woman exactly once
as a test case.

**In this analysis.** Folds are cut by cluster and balanced by stratum.
"Development AP" always means this out-of-fold AP.

### Repeated splits and seeds
<!-- id: repeated | aka: repeated splits, seed, 20 splits, 20/20, 10/10 -->
**In plain words.** One split into groups can be lucky or unlucky, so the
whole comparison is repeated with different random splits. The "seed" is the
number that fixes one random split, so it can be reproduced exactly.

**In this analysis.** "Better in 20 of 20 splits" means the comparison was
run on 20 different random splits and one side won every time. That is
strong evidence even when each individual gain is small.

### Overfitting and optimism
<!-- id: overfitting | aka: optimism, optimistic, development-to-held-out drop -->
**In plain words.** A model or a choice fitted too closely to the data it was
built on does better there than on new data. Any choice made by comparing
scores on the same folds (which model, which settings, which predictors)
makes those folds' scores optimistic.

**In this analysis.** Every model's development AP ran about **0.08 higher**
than its held-out AP. So a development gain smaller than 0.08 is not, on its
own, proof of a better model.

### Champion
<!-- id: champion | aka: best model, development champion -->
**In plain words.** The model chosen as the best.

**In this analysis.** The champion is always chosen on **development**
scores and only then scored on held-out women. Choosing it by the held-out
score would make that score optimistic. That mistake was made once and
corrected.

### Paired comparison
<!-- id: paired | aka: paired, head-to-head -->
**In plain words.** Two models scored on exactly the same women, so the
difference reflects the models and not which women happened to be tested.

**In this analysis.** Every "A vs B" difference is paired.

---

## Accuracy measures

### Accuracy
<!-- id: accuracy | aka: percent correct -->
**In plain words.** The share of women labelled correctly.

**In this analysis.** Not used. With 19% prevalence, labelling everyone "no"
scores 81% (see "Start here").

### Precision and recall
<!-- id: precision-recall | aka: precision, recall, sensitivity, PPV, specificity -->
**In plain words.**
- **Precision:** of the women the model flags, the share who really attain
  the outcome.
- **Recall** (also called sensitivity): of the women who really attain it,
  the share the model flags.
- **Specificity** is recall for the other group.

**In this analysis.** They depend on where you draw the line (the
threshold), so they are reported only at stated thresholds. AP summarises
them across all thresholds.

### Average precision (AP)
<!-- id: ap | aka: AP, average precision, PR-AUC -->
**In plain words.** How well the model packs the women who attain the
outcome at the top of its ranking, averaged over the whole list. It runs
from the prevalence (random) to 1.0 (perfect).

**In this analysis.** The headline measure *within* one outcome, because it
focuses on the rarer group. Never compare raw AP across ANC1+, ANC4+ and
ANC8+: their floors are 0.78, 0.52 and 0.19.

**A good value looks like.** Clearly above the prevalence. On ANC8+ the
models reach 0.40 to 0.46 on held-out women, against a floor of 0.19.

### AUROC (AUC)
<!-- id: auroc | aka: AUC, AUROC, ROC, C-statistic, discrimination -->
**In plain words.** Take one woman who attained the outcome and one who did
not. AUROC is the chance the model scored the first one higher. 0.5 is a
coin flip, 1.0 is perfect.

**In this analysis.** The measure used to compare rungs, because it ignores
prevalence. The champions score 0.826 (ANC1+), 0.789 (ANC4+) and 0.759
(ANC8+) on held-out women: completing care is harder to predict than
reaching it.

**A good value looks like.** 0.7 to 0.8 is typical and useful for
population health. Above 0.9 is rare for survey data, and suspicious if seen
(check for leakage).

### Lift
<!-- id: lift | aka: AP lift, lift over prevalence, above prevalence, share of possible lift -->
**In plain words.** AP minus the prevalence: the improvement over a blind
guess. "Share of possible lift" divides it by the most it could be
(1 − prevalence).

**In this analysis.** Used alongside AUROC for fair cross-rung comparisons.

### Univariate AUC
<!-- id: univariate-auc | aka: single-variable AUC, screening AUC -->
**In plain words.** The AUROC of one variable on its own: how well that
single fact ranks women.

**In this analysis.** The continuous wealth score alone reaches 0.755,
nearly as high as the whole 21-predictor XGBoost model (0.761).

### Calibration
<!-- id: calibration | aka: calibrated, calibration curve, reliability -->
**In plain words.** Whether the scores can be read as rates. Among women
given 30%, do about 30% attain the outcome?

**In this analysis.** Checked on held-out women. A calibration map (Platt
scaling) was added because the raw scores were too extreme.

### Calibration slope
<!-- id: calibration-slope | aka: slope, CITL, calibration-in-the-large -->
**In plain words.**
- **Slope 1.0** is ideal.
- **Below 1** means the scores are too spread out: too confident at both
  ends, the usual sign of overfitting.
- **Above 1** means they are too timid.

"Calibration-in-the-large" (CITL) asks whether the average score matches the
average outcome. 0 is ideal.

**In this analysis.** The 21-predictor models had slopes of 0.78 to 0.86.
After Platt scaling the full-pool model's slope is 0.99.

### Brier score
<!-- id: brier -->
**In plain words.** The average squared gap between the score and what
happened (1 or 0). Lower is better. It rewards both ranking and calibration.

**In this analysis.** Reported in the tables, for example 0.113 for the
21-predictor XGBoost. It is not a headline measure.

### Net benefit and decision curves
<!-- id: net-benefit | aka: decision curve, decision-curve analysis, treat all, treat none -->
**In plain words.** Would using the model to decide whom to act on beat the
simple alternatives of acting on everyone or on no one? Net benefit counts
correct actions and subtracts wrong ones, weighted by how costly a wrong
action is judged to be (the threshold).

**In this analysis.** The models beat both defaults across the useful range
of thresholds, but the 21-predictor and full-pool models are nearly
identical on this measure.

### Threshold (operating point)
<!-- id: operating-threshold | aka: operating threshold, cut-off, risk band -->
**In plain words.** The score above which a woman is flagged. Changing it
trades precision against recall.

**In this analysis.** Thresholds were set on development data, never on
held-out women. "Risk bands" group women by their predicted probability.

---

## Uncertainty

### Bootstrap
<!-- id: bootstrap | aka: resample, stratified PSU bootstrap, cluster bootstrap -->
**In plain words.** A way to see how much a result could have varied with a
different sample:
1. redraw the sample many times from itself, with replacement;
2. recompute the result each time;
3. read the spread of those results.

**In this analysis.** Clusters are redrawn whole and each stratum is kept,
matching how the survey was designed. That makes the intervals honest rather
than too narrow.

### Confidence interval
<!-- id: ci | aka: CI, 95% interval, interval, [low, high] -->
**In plain words.** A range, written like [−0.036, +0.075], that the true
value very probably lies in. A narrow range means a precise estimate; a wide
range means we don't know the value well.

**In this analysis.** 95% intervals from the bootstrap, written in square
brackets after the estimate.

### "The interval includes zero"
<!-- id: spans-zero | aka: includes zero, spans zero, cannot tell apart, not significant -->
**In plain words.** If the range for a *difference* runs from negative to
positive, the data cannot tell whether A or B is really better. That is not
proof they are equal, only that this sample is too small to separate them.

**In this analysis.** The full-pool model's held-out advantage over the
21-predictor XGBoost (+0.021 AP) has an interval of [−0.036, +0.075], so this
held-out set alone cannot confirm it. The claim therefore rests on repeated
splits (20 of 20).

### Significance
<!-- id: significance | aka: significant, significantly better -->
**In plain words.** A shorthand for "the interval for the difference
excludes zero".

**In this analysis.** With the 21 predictors, XGBoost was *not*
significantly better than logistic regression on any measure.

---

## Models

### Logistic regression
<!-- id: logistic | aka: LR, logistic, regularisation, C -->
**In plain words.** The classic statistical model. Each predictor adds or
subtracts a fixed amount from a woman's log-odds (see "Log-odds"), and the
total becomes a probability. "Regularisation" shrinks the effects so the
model doesn't chase noise. Its strength is called C.

**In this analysis.** Used as the fixed model when comparing predictor sets,
because it has almost nothing to tune and so cannot favour one set through
its settings.

### Tree ensembles
<!-- id: trees | aka: random forest, extra trees, XGBoost, LightGBM, HistGradientBoosting, CatBoost, gradient boosting, booster -->
**In plain words.** Models built from hundreds of simple yes/no decision
trees:
- **random forest** and **extra trees** average many trees grown
  independently;
- **gradient boosting** (XGBoost, LightGBM, HistGradientBoosting, CatBoost)
  grows trees one after another, each correcting the previous ones.

They capture interactions automatically.

**In this analysis.** All were tried. None beat the others by a meaningful
margin: the spread across ten families was about 0.02 development AP.

### Explainable Boosting Machine (EBM)
<!-- id: ebm | aka: EBM, Explainable Boosting, glass-box, additive model, GAM -->
**In plain words.** A model that learns one curve per predictor and adds
them up. Every prediction can be read exactly as the sum of its parts.

**In this analysis.** It matched the best tree ensemble on AUROC and is the
model behind the What-if tab. Offered up to ten interactions between
predictors, it chose none: ANC8+ attainment behaves additively.

### Neural network (MLP)
<!-- id: mlp | aka: MLP, multilayer perceptron, neural network -->
**In plain words.** Layers of simple arithmetic units trained together, the
same family as modern AI, here very small.

**In this analysis.** One of the ten families. It had the best held-out AP
on ANC8+ (0.463), but it was not the development champion. Picking it
because of its held-out score would be the selection mistake described under
"Champion".

### Ordinal (cumulative-link) model
<!-- id: ordinal | aka: cumulative link, ordinal arm, contact count model -->
**In plain words.** Instead of a yes/no outcome, it models the contact count
itself (at least 1, at least 2, ...) and reads off "at least 8".

**In this analysis.** Better in development (0.500 against 0.494 AP), worse
on held-out women (0.402 against 0.427). Reported, not used.

### Hyperparameters and tuning
<!-- id: tuning | aka: hyperparameter, tuning, Optuna, trials, search, library defaults, ablation of parameters -->
**In plain words.** Settings chosen before training, such as how deep a tree
may grow or how strongly to regularise. **Tuning** tries many combinations
and keeps the best. **Optuna** is the tool that runs this search.
**Library defaults** are the settings a model ships with.

**In this analysis.** Tuning raised development AP by +0.02 to +0.04 over
library defaults. That is less than the 0.08 optimism gap, so it is not
evidence that tuned models generalise better.

### Platt scaling
<!-- id: platt | aka: Platt, isotonic, calibration map, calibrator -->
**In plain words.** A small correction applied after the model, fitted on
separate data, that turns over- or under-confident scores into honest rates.
**Isotonic** is a more flexible alternative.

**In this analysis.** Platt raised the calibration slope from 0.62 to 0.99
at almost no cost in ranking (−0.005 AP). It is the calibration that ships.

### The 21-predictor set and the full pool
<!-- id: versions | aka: 21-predictor set, the 21, full pool, full candidate pool, 88, 95 -->
**In plain words.** The two predictor sets every comparison is built around.
- **The 21-predictor set:** 21 constructs chosen in advance from the
  literature, in four domains (maternal, household, pregnancy, access),
  modelled with logistic regression, random forest and XGBoost.
- **The full candidate pool:** everything that survived screening the whole
  survey file for timing and leakage, modelled with ten model families.

**In this analysis.** The question is not which set "wins" but which of their
members carry the prediction: how few are needed, which of the 21 add
nothing, and what the rest of the pool adds.

### Prediction horizon
<!-- id: horizon | aka: horizon, before ANC, at ANC entry, ANC-entry, full cohort -->
**In plain words.** The moment a prediction is made, which decides what can
be known.
- **Before ANC starts:** only who the woman is, her household and where she
  lives.
- **At ANC entry:** the same, plus when her first contact happened.

**In this analysis.** The predictor-value study is run at both horizons. At
ANC entry every woman has at least one contact, so only ANC4+ and ANC8+ can
be predicted.

### Early ANC
<!-- id: early-anc | aka: early_anc, early initiation, first contact by 3 months -->
**In plain words.** Whether the first antenatal contact came in the first
trimester (by 12 weeks or 3 months).

**In this analysis.** Admissible only at the ANC-entry horizon: before a
woman starts care it is not yet known, and using it there would be leakage.

---

## Explaining models

### Feature importance
<!-- id: importance | aka: importance, driver, share of importance, global importance -->
**In plain words.** How much the model relies on each predictor. It says
nothing about cause.

**In this analysis.** Measured three independent ways (EBM, SHAP and
drop-one). Each is turned into a share of the total within each rung, so the
rungs can be compared.

### Log-odds
<!-- id: log-odds | aka: logit, log-odds scale, contribution to the log-odds -->
**In plain words.** A way of writing a probability that makes effects
add up:
- **0** is 50%;
- **+1** raises the odds about 2.7 times;
- **−1** lowers them by the same factor.

Small values such as ±0.1 mean small nudges.

**In this analysis.** Importance and shape-function charts use this scale.

### SHAP
<!-- id: shap | aka: SHAP, Shapley values -->
**In plain words.** A method that splits one prediction into
contributions from each predictor, borrowed from game theory ("how much did
each player contribute to the team's score?").

**In this analysis.** Computed on XGBoost for every rung. An earlier run
computed ANC4+ SHAP on a model type the method mishandles. That was caught
and corrected.

### Drop-one importance
<!-- id: drop-one | aka: drop-one, leave-one-out, remove one, AP lost when removed -->
**In plain words.** Refit the model without one predictor and see how much
AP falls. A negative value means the model is *better* without it.

**In this analysis.** Removing members of the 21 one at a time, 8 add
nothing for ANC1+, 10 for ANC4+ and 14 for ANC8+. Drop-one understates
predictors that have a close substitute, because the substitute compensates,
so it is treated as the weakest of the three importance methods.

### Shape function
<!-- id: shape-function | aka: shape function, learned curve, partial effect -->
**In plain words.** The EBM's learned curve for one predictor: how a
woman's score moves as that one fact changes, with everything else held
fixed. Above the zero line raises the chance; below lowers it.

**In this analysis.** Shown in the What drives it and What if tabs. For
categories such as region, each level gets its own bar.

### Two methods must agree
<!-- id: agreement | aka: method agreement, corroborated, rank agreement -->
**In plain words.** Each importance method has quirks, so a pattern is
reported only when at least two of the three methods show it. "Rank
agreement" is a correlation between two methods' rankings: 1 means the same
order, 0 means unrelated.

**In this analysis.** EBM and SHAP agree well (0.58 to 0.76). Drop-one
agrees weakly.

### Domain
<!-- id: domain | aka: domains, domain roll-up -->
**In plain words.** A group of related predictors:
- socioeconomic;
- agency and household;
- reproductive history;
- access and distance;
- geography and culture;
- education and information;
- work.

**In this analysis.** Importance summed by domain shows the balance
shifting from household power (reaching care) to money, distance and
pregnancy intention (completing care).

---

## Choosing predictors

### Screening
<!-- id: screening | aka: candidate screening, systematic screening -->
**In plain words.** Scoring every available column on its own to find
candidates worth reviewing. Each candidate was then checked for timing
(temporality) and leakage.

**In this analysis.** All 6,648 columns were screened, and 61 new variables
were admitted. Rerunning the screening on development women only admits the
same 61.

### Duplicates
<!-- id: duplicate | aka: duplicate, redundancy, Theil's U, copies -->
**In plain words.** The same information present twice under two names
(for example `region` and `v024`). Duplicates split importance between the
copies, so each looks half as important as it is. **Theil's U** measures how
much knowing one variable tells you about another. Checking both directions
separates true copies from variables that merely nest inside each other.

**In this analysis.** 10 of the 95 were copies, leaving 85 distinct.
Removing them changes accuracy by 0.002 AP.

### Ablation
<!-- id: ablation | aka: ablation, ablation study -->
**In plain words.** Removing or changing one part of an analysis to see
what it was contributing.

**In this analysis.** Done for:
- predictors (removing and adding);
- preprocessing;
- hyperparameters.

### Add-one test
<!-- id: add-one | aka: add-one, increase, adding to the 21 -->
**In plain words.** Start from the 21-predictor set and add one other
candidate at a time, measuring the gain.

**In this analysis.** None of the 67 candidates clears the bar alone for
ANC1+ or ANC4+. Six to eight do for ANC8+.

### Remove-one test
<!-- id: remove-one | aka: remove-one, reduce, removing from the 88 -->
**In plain words.** Start from everything and remove one predictor at a
time.

**In this analysis.** Almost every removal costs nothing, because
correlated predictors stand in for each other.

### Forward selection
<!-- id: forward-selection | aka: forward selection, greedy, stepwise, building from nothing -->
**In plain words.** Build a set from nothing. At each step, add whichever
predictor helps most. Stop when nothing helps enough.

**In this analysis.** Run on the 88 candidates for three outcomes, and
again within the 21 alone to find how many of them are needed. Repeated at
the ANC-entry horizon and in the 24-month window.

### The +0.005 bar
<!-- id: bar | aka: threshold, +0.005 AP, 4 of 5 splits, clears the bar -->
**In plain words.** A variable "pays its way" only if adding it raises AP by
at least 0.005 on average **and** it helps on at least 4 of 5 repeated
splits.

**In this analysis.** Fixed before any selection result was seen, so the
rule could not be bent to fit the results.

### Tiers
<!-- id: tier | aka: tier 1, tier 2, core, valuable bump -->
**In plain words.**
- **Tier 1 (core):** the first variables chosen, up to the point where the
  set reaches 90% of what all 88 achieve above prevalence.
- **Tier 2 ("valuable bump"):** further variables that still clear the bar.

**In this analysis.** Tier 1 is 1 or 2 variables and tier 1+2 is 2 to 8,
depending on the outcome.

### Selection frequency
<!-- id: selection-frequency | aka: re-selected, stability, bootstrap re-selection -->
**In plain words.** Forward selection is repeated on resampled data. A
variable chosen in most resamples is reliable; one chosen in 20% of them
could easily have been another.

**In this analysis.** For ANC8+:
- wealth 100%;
- pregnancy intention 90%;
- region 80%;
- health-post access 60%;
- the rest 10-40%.

---

## Analysing the war

### Difference-in-differences
<!-- id: did | aka: DiD, difference-in-differences, change beyond -->
**In plain words.** Compare the change over time in one place with the
change over the same time elsewhere. Anything that affected everyone (the
national trend, women forgetting older births) cancels out. What remains is
the change specific to that place.

**In this analysis.** Tigray, wartime pregnancies against post-war ones,
minus the change in other regions over the same calendar periods. Result: 13
points fewer women with no ANC at all after the war. The survey records ANC
only for births from about mid-2021, so there are no pre-war pregnancies to
compare with.

### Comparison regions
<!-- id: comparison-regions | aka: control regions, peaceful regions -->
**In plain words.** The places used as the "elsewhere" in a
difference-in-differences.

**In this analysis.** Regions without major conflict. Their own change was
near zero (−1.2 to +1.2 points).

### Simpson's paradox
<!-- id: simpsons | aka: Simpson's paradox, pooling -->
**In plain words.** A group average can move one way while every subgroup
moves the other way, because the mix of subgroups changed.

**In this analysis.** Pooled together, the comparison regions seem to fall
5 points between the periods while each region is flat or rising, because
the mix of regions differs between the periods. The estimate therefore
averages the change within each region.

### Recall bias and survivorship
<!-- id: biases | aka: recall bias, survivorship, displacement -->
**In plain words.**
- **Recall bias:** women remember older pregnancies less accurately.
- **Survivorship:** women who died, or fled the area, are never
  interviewed.

**In this analysis.** Both would make the war look *less* damaging than it
was, so the estimates are more likely too small than too large.

### Regions against their circumstances
<!-- id: regional-gap | aka: regional gap, expected attainment, beat their circumstances -->
**In plain words.** Predict each region's attainment from its women's
wealth, education and household profile, leaving region out. Then compare
with what actually happened. A positive gap means the region does better
than its population would suggest.

**In this analysis.** Afar is about 15 points above expectation for ANC8+.
Tigray is about 4 below.

---

## Reading the figures

Every figure in the Reports tab, in order. For each one: what it shows, how
to read it, and the one thing to take away.

### fig01_cascade
<!-- fig -->
**What it shows.** How far women get on the antenatal care ladder.

**How to read it.** The left panel has one bar per rung. Taller means more
women reached it. The right panel shows, of the women who reached one rung,
the share who went on (dark) or were lost (grey).

**Takeaway.** 78% start and only 19% finish. The biggest loss is between the
fourth and eighth contacts: 63% of women at four go no further.

### fig02_regional_cascade
<!-- fig -->
**What it shows.** Where each region loses its women.

**How to read it.** Each row is a region, split into four colours that add
up to 100%:
- red: never start;
- orange: stop before four;
- light green: stop between four and eight;
- dark green: reach eight.

The widest non-green block is that region's biggest problem.

**Takeaway.** Somali loses two-thirds at the door (red). Central Ethiopia
loses almost half between four and eight (light green). Regions with similar
ANC8+ need opposite programmes.

### fig03_continuation_equity
<!-- fig -->
**What it shows.** Among women who **already** reached four contacts, the
share who went on to eight, by wealth, residence and education.

**How to read it.** Longer bars mean more of these women continued. Because
everyone shown has already attended four times, differences reflect the
cost of returning rather than interest in care.

**Takeaway.** The richest fifth continue 52% of the time and the poorest
fifth 20%.

### fig04_leaderboard_anc8plus
<!-- fig -->
**What it shows.** Each of the ten model families' AP in development (grey
dot) and on held-out women (teal dot).

**How to read it.** Further right is better. The grey line is the drop from
development to held-out. Look at how long the lines are compared with how
far apart the models are.

**Takeaway.** Every model drops about 0.08 on new women, which is larger
than the differences between models. The choice of algorithm was never what
limited accuracy.

### fig05_calibration
<!-- fig -->
**What it shows.** Whether predicted probabilities match reality, on
held-out women.

**How to read it.** Women are grouped into ten bins by predicted
probability. Each dot plots the bin's average prediction (across) against
the share who actually reached ANC8+ (up). The dashed diagonal is perfect
calibration. Dots below it mean the model over-predicts; dots above it mean
it under-predicts.

**Takeaway.** All models follow the diagonal reasonably well. The zig-zag at
low probabilities is noise from small bins.

### fig06_stability
<!-- fig -->
**What it shows.** The 21-predictor set against the full pool (95 columns),
compared on 20 different random splits.

**How to read it.** In the left panel each row is one split: an orange dot
(21 predictors) joined to a teal dot (95). Teal to the right means the 95
won. The right panel collects the 20 gains. The red line at zero is "no
difference".

**Takeaway.** The full pool wins on all 20 splits, by +0.031 AP on
average.

### fig07_bootstrap
<!-- fig -->
**What it shows.** How certain the held-out comparison between the full-pool
model and the 21-predictor XGBoost is.

**How to read it.** Each histogram shows 2,000 bootstrap re-draws of the
held-out difference. The shaded band is the 95% interval, the dashed line
the estimate, and the red line zero. If the band covers zero, the data
cannot tell the two models apart.

**Takeaway.** Both intervals include zero. One held-out set of 1,375 women
is too small to confirm a gain this size, which is why fig06 carries the
claim.

### fig08_global_importance
<!-- fig -->
**What it shows.** How much the explainable model relies on each
predictor.

**How to read it.** A longer bar means a larger average push on women's
scores, in either direction. The colour gives the domain. Names such as
`v191` are survey codes (v191 is the wealth score; v045c is first
language).

**Takeaway.** Region, pregnancy intention, first language and the wealth
measures lead. Note that several wealth columns appear separately, so each
looks smaller than wealth really is (see fig24).

### fig09_shape_functions
<!-- fig -->
**What it shows.** The explainable model's learned effect of each top
predictor.

**How to read it.** Green bars or curve above zero raise a woman's chance of
ANC8+; red below zero lowers it, on the log-odds scale. For continuous
predictors (such as the wealth score v191), follow the curve from left to
right. For categories, compare the bars.

**Takeaway.** "Wanted later" pregnancies and the poorest quintiles pull
scores down most. Addis Ababa and Afar pull them up.

### fig10_decision_curve
<!-- fig -->
**What it shows.** Whether acting on the model's predictions beats acting
on everyone or no one.

**How to read it.** Across the bottom is the risk threshold at which you
would act; up the side is net benefit. The model is useful where its line
sits above both "treat all" (grey curve) and "treat none" (flat dotted line
at zero).

**Takeaway.** Both models beat the defaults across most thresholds, and the
21-predictor and full-pool models are almost indistinguishable.

### fig11_subgroups
<!-- fig -->
**What it shows.** AUROC within each region, wealth group, education level
and residence, for the 21-predictor model (orange) and the full-pool model
(teal).

**How to read it.** Further right is better. The dotted red line at 0.5 is a
coin flip. Subgroups are small, so single dots are noisy.

**Takeaway.** The national AUROC hides regions where the model barely ranks
women at all (Gambella, Central Ethiopia, South West Ethiopia). Within most
regions, the model ranks women less well than it does nationally.

### fig14_screening
<!-- fig -->
**What it shows.** The strongest single columns in the whole survey file
(left) and how the screening sorted all columns (right).

**How to read it.** In the left panel, bar length is each column's
univariate AUC. Grey bars were excluded, nearly all because they record
things after or during care (leakage). Teal bars were admitted.

**Takeaway.** The strongest columns in the survey are leaks. The strongest
legitimate one is the continuous wealth score (v191, 0.755); the
21-predictor set uses its five-group version.

### fig15_preprocessing
<!-- fig -->
**What it shows.** How much AP changes under different ways of preparing
the data (filling gaps, encoding categories).

**How to read it.** Bars to the right of zero improved AP; bars to the left
reduced it. Note the tiny scale: the axis spans less than 0.01.

**Takeaway.** Preprocessing barely matters: +0.003 at best, an order of
magnitude less than changing the predictors.

### fig16_hyperparameters
<!-- fig -->
**What it shows.** For each tuned setting, the worst AP loss from moving it
away from the tuned value while holding the others fixed.

**How to read it.** A long bar means the setting matters; a short bar means
the search bought little for it.

**Takeaway.** Most settings matter little. The exceptions are the share of
data and columns each tree sees (XGBoost), whether the EBM may use
interactions, and the regularisation strength C (logistic regression).

### fig17_tuning_gain
<!-- fig -->
**What it shows.** How much the whole tuning search improved each model
over its library defaults.

**How to read it.** A longer bar means tuning helped more. Read it against
the roughly 0.08 drop every model suffers on new women (fig04).

**Takeaway.** Tuning bought 0.00 to 0.04 AP, which is less than the
optimism gap, so it is not evidence that tuned models generalise better.

### fig18_ladder_performance
<!-- fig -->
**What it shows.** Performance on the three rungs, measured three ways.

**How to read it.**
- **Left:** prevalence, which is what a blind guess scores in AP.
- **Middle:** raw AP, with the dashed box marking that floor. The
  comparable part is the height *above* the box.
- **Right:** AUROC, which does not depend on prevalence (0.5 is chance).

**Takeaway.** Raw AP makes ANC1+ look easiest only because its floor is
highest. AUROC shows the real ordering: reaching care (0.83) is easier to
predict than completing it (0.76).

### fig19_ladder_importance
<!-- fig -->
**What it shows.** Each predictor's share of importance at ANC1+ (light),
ANC4+ (mid) and ANC8+ (dark).

**How to read it.** Follow each row from light to dark dot.
- **Green connecting line:** the predictor matters more as the bar rises
  (completion-limited).
- **Red line:** it matters less (access-limited).

**Takeaway.** Wealth, pregnancy intention and travel time to a health post
grow in importance for completion. Household headship and attitudes to
partner violence matter mostly for reaching care at all.

### fig20_domain_rollup
<!-- fig -->
**What it shows.** The same importance, summed into seven domains, across
the three rungs.

**How to read it.** A line rising from left to right means that domain
matters more for completing care than for reaching it.

**Takeaway.** Agency and household falls (28% → 19%), while socioeconomic
(20% → 26%), reproductive history and access rise.

### fig21_regional_gap
<!-- fig -->
**What it shows.** Each region's actual ANC8+ minus what its population
profile predicts.

**How to read it.** A green bar to the right means the region does better
than its circumstances; a red bar to the left means worse. Units are
percentage points.

**Takeaway.** Afar (+15), Addis Ababa and Dire Dawa outperform. Tigray,
Gambella and Somali fall short of what their circumstances predict.

### fig22_modifiable
<!-- fig -->
**What it shows.** AUROC using everything, using only things a health
service can change (access, services), or using only fixed circumstances.

**How to read it.** Compare the bar heights within each rung. The dotted
line at 0.5 is chance.

**Takeaway.** Fixed circumstances alone nearly match the full model. The
service-related factors carry less predictive signal, though that does not
mean they matter less for policy.

### fig23_risk_bands
<!-- fig -->
**What it shows.** Women grouped by predicted chance of ANC8+.

**How to read it.**
- **Bars (left axis):** the share in each band who actually reached eight
  contacts.
- **Line (right axis):** the share of all women in that band.

**Takeaway.** Actual attainment rises steadily with the prediction, so the
ranking works. Most women sit in the low bands.

### fig24_redundancy
<!-- fig -->
**What it shows.** Importance before and after counting duplicate columns
as one variable.

**How to read it.** The teal part is what one column received; the grey
extension is what its copies added. The note gives the rank now and before.

**Takeaway.** Travel time to hospital rises from rank 10 to rank 2 once its
copy is counted. Duplicates made important variables look minor.

### fig25_set_comparison
<!-- fig -->
**What it shows.** The gain in AP from using the full pool, 85 distinct
variables or 95 columns, instead of the 21-predictor set, on every repeated
split.

**How to read it.** Each dot is one split; the black bar is the mean. The
red line at zero is no gain. Dots all above zero means a consistent gain.

**Takeaway.** Small for ANC1+ (+0.008) and ANC4+ (+0.013), larger for ANC8+
(+0.042). The 10 duplicates add nothing (85 ≈ 95).

### fig26_add_one
<!-- fig -->
**What it shows.** Each of the 67 pool candidates outside the 21 added
**alone** to the 21, sorted by gain. Top row: all births (the main
analysis); bottom row: the 24-month window (sensitivity).

**How to read it.** Each thin bar is one candidate. The dashed red line is
the +0.005 bar. Teal bars clear it consistently.

**Takeaway.** For ANC1+ and ANC4+ no candidate clears the bar. For ANC8+, 6
to 8 do. Most candidates sit at zero.

### fig27_diminishing_returns
<!-- fig -->
**What it shows.** Development AP as the 67 candidates are stacked onto the
21, best first.

**How to read it.**
- A curve that rises and then flattens or falls means a few additions carry
  the gain and the rest add nothing or add noise.
- The dashed line is the 21 alone.
- The shaded band shows variation across splits.

**Takeaway.** On ANC8+ the first handful give most of the gain. Beyond the
peak, extra variables make development scores worse. The held-out test
(fig30) tells a different story for ANC1+ and ANC4+.

### fig28_tier_ladders
<!-- fig -->
**What it shows.** Forward selection from nothing: which variable was chosen
at each step, and how much it lifted AP above prevalence.

**How to read it.**
- Rows go top to bottom in the order chosen. Bar length is AP above
  prevalence after adding that variable.
- Dark teal is tier 1, light teal tier 2, grey the first step that failed
  the bar.
- The dashed line is the 21-predictor set and the dotted line is the full
  pool.

**Takeaway.** The household wealth score is chosen first in every run.
Two to eight variables reach roughly the level of the 21.

### fig29_selection_frequency
<!-- fig -->
**What it shows.** How often each variable was chosen again when selection
was re-run on ten resamples (ANC8+).

**How to read it.** Longer means more reliably chosen. Below the dashed 70%
line, a variable's place is not dependable: another similar variable could
take it.

**Takeaway.** Wealth, region and pregnancy intention are reliable. Most
tier-2 places rotate.

### fig30_heldout_sets
<!-- fig -->
**What it shows.** The fair test. Each predictor set was fitted on
development women and scored once on held-out women, by outcome (top row: all
births; bottom row: 24-month sensitivity window).

**How to read it.** Bar height is AP above prevalence (higher is better),
with dark bars for logistic regression and light bars for LightGBM. The
number under each set is how many predictors it uses.

**Takeaway.** The full pool does best for ANC1+ and ANC4+. Compact sets roughly match
the 21 for ANC1+ and ANC8+ and fall short for ANC4+. Most ANC8+ differences
are within the uncertainty.

### fig33_drop_within_21
<!-- fig -->
**What it shows.** Each member of the 21-predictor set removed from it in
turn, at each rung, and the AP lost.

**How to read it.** A green bar to the right means the set needs that
predictor. A grey bar at or left of zero means the set does as well or
better without it. Rows are ordered by ANC8+.

**Takeaway.** Region, pregnancy intention and wealth carry the 21 at every
rung. The number that add nothing grows up the ladder: 8 of 21 for ANC1+, 10
for ANC4+, 14 for ANC8+.

### fig34_why21
<!-- fig -->
**What it shows.** How much of the full pool's lift over prevalence a set
reaches, by how many predictors it has: taking the best of the 21 one at a
time (orange), and selecting from the whole pool (teal).

**How to read it.** 100% is what the full pool reaches. The dashed line is
all 21 together. An orange point above the dashed line is a smaller subset of
the 21 that does better than all 21. These are development scores, so the
chosen sets are optimistic.

**Takeaway.** For ANC8+ the best 7 of the 21 already reach the full pool,
and adding the other 14 lowers the score. For ANC1+ and ANC4+ the curve is
flat: the 21 are about as good as their best subset. The held-out check is
in PREDICTOR_VALUE.md.

### fig35_predictor_rung_matrix
<!-- fig -->
**What it shows.** Each predictor's value relative to the 21-predictor set at
ANC1+, ANC4+ and ANC8+, on one comparable scale.

**How to read it.** For members of the 21 (marked [21]) the number is the AP
lost when dropped; for the rest, the AP gained when added. Both are shown as
a percentage of each rung's ceiling (full-pool AP minus prevalence). Green is
value, brown is harm. Rows run from most ANC1+-weighted (top) to most
ANC8+-weighted (bottom).

**Takeaway.** Region and the wealth measures become far more valuable at
ANC8+. Residence, education level and the gap since the previous pregnancy
matter for reaching care and not for completing it.

### fig31_tigray_did
<!-- fig -->
**What it shows.** Antenatal care in Tigray for pregnancies during and after
the war (left), and the change beyond what other regions saw over the same
calendar periods (right).

**How to read it.**
- **Left:** a red dot for wartime, a teal dot for post-war. The gap is the
  raw change.
- **Right:** the difference-in-differences. A bar right of zero means more
  after the war. The whiskers are the 95% interval; a whisker crossing zero
  means no clear change.

**Takeaway.** The war mainly stopped women reaching any care: no-ANC fell
13 points after it. ANC4+ recovered, but ANC8+ did not clearly change.

### fig32_regional_gap_cohort
<!-- fig -->
**What it shows.** The regions-against-circumstances gap (fig21), computed
separately for all births (orange) and for births in the last 24 months
(teal).

**How to read it.** Where the two dots sit close together, the result does
not depend on which window is used.

**Takeaway.** The ranking is stable. Tigray's shortfall is not just an
artefact of older, wartime births.

### fig36_horizons
<!-- fig -->
**What it shows.** Held-out AUROC for predictor sets at the ANC-entry
horizon, with and without early ANC, and the same sets fitted before ANC,
all scored on the same 984 women who started ANC.

**How to read it.** Light bars are without early ANC, dark bars with it,
brown bars the sets fitted on all women before ANC. Longer is better; 0.5 is
chance.

**Takeaway.** Adding early ANC lengthens every bar, most clearly for ANC4+.
Fitting on the entry women instead of all women barely changes anything.

### fig37_early_anc
<!-- fig -->
**What it shows.** How much held-out AUROC early ANC adds to each predictor
set, with a 95% interval.

**How to read it.** Each dot is the gain from adding early ANC; the line is
its interval. An interval entirely right of the red zero line is a confirmed
gain.

**Takeaway.** For ANC4+ the gain is confirmed whatever it is added to. For
ANC8+ it is positive but confirmed only when added to the full pool.

### fig38_tigray_regions_by_period
<!-- fig -->
**What it shows.** Every region's antenatal care over the same two calendar
periods: pregnancies during the Tigray war window, and pregnancies conceived
after the ceasefire.

**How to read it.** A red dot for the wartime period, a teal dot for the
post-war period; a longer grey line is a larger change. Tigray is
highlighted.

**Takeaway.** Tigray has the largest change of any region in reaching care:
no-ANC falls from 20% to 8% and ANC4+ rises from 46% to 59%, while most
regions move a few points. Its ANC8+ barely moves (10% to 12%).
