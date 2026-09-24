# Limitations

What this analysis cannot support, stated plainly. If you are deciding whether
to use any of it, read this before the findings rather than after.

---

## 1. Nothing here is causal

The models describe **which women attained antenatal care**, not what would
happen if a woman's circumstances changed. Wealth, education and language are
not things a health programme hands out, and a wealthier woman differs from a
poorer one in many ways the survey does not record.

This matters most for the what-if surface in the web app. Moving the wealth
control shows what the model predicts **for women who have that wealth level**.
It does not estimate the effect of making someone wealthier. The interface
says so where the controls are, not in a footnote, because the control itself
is what invites the causal reading.

The descriptive cascade — where each region loses women — is the sturdiest
part of the work precisely because it is not a model. It counts. Counting
needs no causal assumption.

---

## 2. The held-out set cannot resolve small differences

1,375 women, 229 of them attaining ANC8+; at the ANC-entry horizon, 984
women. Most ANC8+ comparisons between predictor sets on these women have
intervals that include zero: for example, the full-pool model against the
21-predictor XGBoost gives **+0.021 AP [-0.036, +0.075]**.

Where a claim about predictor sets is made, it rests on **repeated
splitting** of the development women (for example 20/20 splits, +0.031 AP for
the full pool over the 21), with the held-out result always reported next to
it. That is legitimate evidence, but it is not the same thing as a
significant result on held-out women, and the two should not be conflated.

A related caution applies to every set chosen by searching: the selected
sets, and the best subsets of the 21, were chosen on the development folds,
so their development scores are optimistic. Only their held-out scores are a
fair comparison.

---

## 3. Discrimination is moderate, and worse in some places than the headline

The best models reach AUROC ≈ 0.78 nationally. That is useful for directing
attention across a population and far too blunt for a decision about an
individual woman.

Subgroup analysis is worse than the headline in specific places. Several
regional subgroups sit at or near chance — Gambella below 0.5, Central
Ethiopia and South West Ethiopia around 0.52 on the full-pool model. Subgroup
sample sizes are small (60–150 women), so these are indicative rather than
precise, but they are the right thing to look at before deploying a national
tool regionally. A model that works nationally and not in the regions with the
worst coverage is the wrong tool for the places that need it most.

---

## 4. One survey round, one country, no external validation

The 2024-25 Ethiopia DHS is the only data used. There is no temporal
validation (no later round to test on), no external validation (no other
country or data source), and no prospective evaluation. Nothing measured here
supports applying these models outside Ethiopia or outside this period.

---

## 5. The outcome is self-reported and recalled

The number of antenatal contacts comes from the woman's recollection at
interview, potentially years after the birth. Recall error is likely to be
non-random — more attentive engagement may be remembered more precisely, and
"eight or more" is a harder count to recall accurately than "none". The
direction of any resulting bias is not identified here.

Women who had a recent birth but could not report a contact count were
excluded rather than imputed. If the ability to recall correlates with
attainment, that exclusion is not neutral.

---

## 6. An equity problem the model does not solve

`v045c`, the woman's native language, is among the strongest predictors in the
full pool. Each language group is roughly three-quarters concentrated in a
single region, so it is largely standing in for geography and ethnicity.

Dropping it costs **0.003 AP** — essentially nothing.

It is retained in the reported model and flagged rather than quietly removed,
because the decision belongs to whoever deploys this. For directing outreach
to underserved language groups, using it may be entirely defensible. For
anything that scores an individual woman lower because of the language she
speaks, it needs an explicit justification. What should not happen is for it
to sit in a model because nobody noticed it was there.

The same caution applies less sharply to region and religion.

---

## 7. Interpretation artefacts

**Duplicated predictors split their importance.** About a fifth of the full
pool consists of variables present twice under different names. A
per-column importance table ranks those variables at roughly half their true
weight — travel time to hospital moves from rank 10 to rank 2 once its
duplicate is folded back in. Importance is read at the group level; the
grouped table is in `outputs/enhanced/redundancy/`. The same effect hides a
duplicated variable's value in the drop-one studies: dropping one copy costs
nothing while the other remains.

**Categorical shape functions are biased toward monotonicity.** The shared
preprocessor ordinal-encodes categoricals, so the additive model sees region
as an integer with an arbitrary order and its binning favours curves that are
monotone in that arbitrary order. Regional effects read off a single shape
function are less trustworthy than the model's predictions. Use the
descriptive cascade for regional conclusions.

**Development scores are optimistic by about 0.08 AP.** Every model's
development out-of-fold AP ran roughly 0.08 above its held-out AP. That is the
signature of selecting among many models on the same folds, not of one model
generalising badly. It is the reason the hyperparameter ablation asks what
tuning bought *over library defaults* rather than treating the tuned score as
the result.

---

## 8. The war analysis sees only wartime and after

The survey records antenatal care only for births from about mid-2021, so no
Tigrayan pregnancy before the war is observed; the comparison is wartime
against post-war, net of other regions. Women displaced out of the region or
who died were not interviewed, and some enumeration areas were excluded for
security reasons, so the wartime shortfall is more likely understated than
overstated.

---

## 9. What the survey does not contain

No facility data. No information about what happened at any contact — quality,
waiting time, staff, cost, whether the woman was treated respectfully. No
supply-side variables at all beyond self-reported travel time.

So a finding such as "Central Ethiopia loses women between the fourth and
eighth contact" locates the problem in the cascade and says nothing about its
cause. The obvious candidates — cost of repeat travel, clinic hours, stockouts,
how women are treated — are not in this data and cannot be distinguished with
it. That is a question for the Ministry's own facility records, and this
analysis is best read as telling them where to look.

---

## 10. Intended use

A research and educational tool. Not clinical advice, not validated for
decisions about individuals, and not a substitute for local knowledge about
why a particular woman or district is under-served.
