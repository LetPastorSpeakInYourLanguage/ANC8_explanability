# What the data says about antenatal care in Ethiopia

Written for a general reader. Technical detail is in `FINDINGS.md`; the numbers
behind every claim are in `outputs/`.

Based on the 2024–25 Ethiopia Demographic and Health Survey: 6,893 women who
had a recent birth and could say how many antenatal care visits they had.
Everything is survey-weighted, so it describes the country rather than just the
women who were interviewed.

---

## The headline: the problem is not getting women through the door

The WHO recommends eight antenatal contacts during pregnancy. In Ethiopia:

| | Share of women |
|---|---|
| Reach antenatal care at least once | **77.6%** |
| Reach four or more contacts | **52.4%** |
| Reach eight or more contacts | **19.2%** |

It is tempting to read that as an access problem. It is mostly not.

**Three quarters of Ethiopian women already reach antenatal care.** The system
then loses them:

- of the women who start, **32% never reach four contacts**;
- of the women who reach four, **64% never reach eight**.

The single largest loss in the whole cascade is between the fourth contact and
the eighth. That is not a problem of women failing to find the health system.
It is a problem of the health system failing to hold on to women who have
already found it.

---

## The finding that should change how programmes are targeted

Regions with almost identical ANC8 coverage are failing for **opposite
reasons**, and a single national programme would be wrong for most of them.

| Region | Reach 8+ | Never start | Start, stop before 4 | Reach 4, stop before 8 |
|---|---|---|---|---|
| Somali | 3.8% | **66%** | 22% | 8% |
| South Ethiopia | 7.8% | 25% | 30% | **37%** |
| Sidama | 9.4% | 15% | **44%** | 31% |
| Central Ethiopia | 10.0% | 14% | 28% | **48%** |
| Tigray | 11.6% | 13% | 34% | **42%** |
| Addis Ababa | 66.1% | 1% | 5% | 28% |

This table uses every birth in the survey, reaching back to mid-2021. Using
only births in the last two years, the official DHS definition, changes no
conclusion: Somali still loses 65% of women at the door, and Central Ethiopia
still keeps only 16% of those who reach four contacts through to eight.

Read the bold figures. These regions look similar on the headline number and
are nothing alike underneath:

**Somali has an access problem.** Two thirds of women never reach antenatal
care at all. Nothing that improves the *quality* or *continuity* of care will
help them, because they are not in contact with it. What Somali needs is
outreach — getting the service to women who currently never meet it.

**Central Ethiopia has the opposite problem.** Eighty-six percent of women
reach care, which is close to Addis Ababa's coverage. But of those who get to
four contacts, only **17%** go on to eight — the lowest continuation rate in
the country. Building more facilities there would be solving a problem that has
already been solved. What Central Ethiopia needs is retention: follow-up,
reminders, and reducing the cost of the fifth through eighth visits.

**Sidama loses women early.** Most women start, but 44% drop out before the
fourth contact — the loss is concentrated in the first half of pregnancy.

A programme designed for Somali would waste its budget in Central Ethiopia, and
one designed for Central Ethiopia would not reach a single Somali woman who
needs it.

### What "good" looks like

Addis Ababa retains **95%** of starters through to four contacts and **70%**
from four to eight. That is the demonstrated ceiling within Ethiopia, under
Ethiopian conditions — not an imported benchmark.

---

## Who is being left behind, once they are already in the system

Among women who had *already reached four contacts* — so, women the system has
demonstrably reached — whether they go on to eight depends heavily on who they
are:

| | Continue from 4 to 8 |
|---|---|
| Richest fifth | 51.7% |
| Richer | 37.5% |
| Middle | 30.5% |
| Poorer | 19.5% |
| Poorest fifth | 19.9% |
| | |
| Urban | 45.2% |
| Rural | 30.3% |

A woman in the richest fifth who reaches four contacts is **two and a half
times** as likely to complete the schedule as an equally-engaged woman in the
poorest fifth. Both have already shown they will attend. The difference is in
what it costs them to keep attending.

This points at the practical barriers to *repeat* visits — transport fares paid
eight times instead of four, days of work lost, childcare — rather than at
whether women value antenatal care. They have already demonstrated that they do.

---

## What actually predicts attainment

The strongest single factor is **where a woman lives**, followed by whether the
pregnancy was wanted, her first language, and household wealth. Weighted
attainment of eight contacts runs from **66% in Addis Ababa to under 4% in
Somali** — a seventeen-fold difference within one country.

Two things are worth saying plainly about this:

**Wealth matters more than it first appears.** The survey records household
wealth both as a detailed score and as a simple five-group ranking. The
detailed score alone predicts ANC8 attainment nearly as well as a whole
twenty-one-factor model. Rounding wealth into five groups throws away
information that matters.

**Language and region are entangled.** A woman's first language is among the
strongest predictors, but each language group is about three-quarters
concentrated in a single region — so it is largely standing in for geography
and ethnicity. This is flagged rather than buried: a tool that scores a woman
lower because of her language needs an explicit justification. For directing
outreach to underserved groups that may be defensible; it should be a decision
someone makes, not a side effect nobody noticed.

---

## A few facts about a woman carry most of the prediction

The survey records hundreds of things about each woman. We tested how many
are needed to predict whether she reaches antenatal care, and whether she
completes it.

- **The same two come first every time: how wealthy her household is, and
  which region she lives in.**
- **Whether the pregnancy was wanted** matters for staying in care (four and
  eight contacts), not for reaching it at all.
- **For completing care, seven or eight facts are enough.** Wealth, region,
  whether the pregnancy was wanted, the woman's work and her say in household
  decisions, and access to a health post predict eight-contact attainment as
  well as 21 or 88 characteristics do, on women the models never saw.

But the rest of the survey is not useless, and the picture differs by
question:

- **For reaching care at all**, no single extra characteristic adds much.
  Together, though, the many small ones (distance, transport, radio and
  television, water and sanitation) do make predictions measurably better on
  women the model has never seen. Getting to a clinic depends on many small
  things at once.
- **For completing eight contacts**, a handful of characteristics carry the
  prediction and the rest add nothing we can detect.

Two things follow. **A tool for directing outreach can be short**: four
questions get most of the way, and fewer questions mean better data. And of
the strong predictors, **access to a health post is the one the health
service directly controls**. The others describe a woman's circumstances,
which a health programme cannot hand out.

---

## What the war did to antenatal care in Tigray

The survey reaches back to births in mid-2021, so many Tigrayan women in it
were pregnant during the war (November 2020 to November 2022). Comparing
their care with women who became pregnant after the ceasefire shows what the
war did:

| Tigrayan women | pregnant during the war | pregnant after the ceasefire |
|---|---|---|
| Received **no** antenatal care | **1 in 5** (19.5%) | **1 in 13** (7.7%) |
| Reached four contacts | 46% | 59% |
| Reached eight contacts | 10% | 12% |

Other regions barely changed over the same period, so this is not a national
trend or women misremembering older pregnancies. Once they are subtracted,
the war is associated with about **13 percentage points more women getting no
antenatal care at all**.

Two things follow:

**The war cut women off from care entirely.** It did not mainly make women
drop out partway; it stopped them arriving. That is what rebuilding should
target first, and after the ceasefire it largely recovered.

**Recovery restored access, not the full schedule.** Women who came back to
care mostly reached four contacts and stopped. Eight contacts barely moved.
Post-war Tigray now does *better* than its population's circumstances would
predict at getting women to care, and still falls short on completing it. It
has become a retention problem, like Central Ethiopia.

The true wartime damage is probably larger than this shows. Women who fled the
region or died are not in the survey, and some areas were too insecure to
survey at all.

---

## Two cautions on reading any of this

**These are patterns, not causes.** The analysis shows which women attain eight
contacts. It does not show what would happen if you changed a woman's
circumstances. Wealth and education are not things a health programme hands
out, and a wealthier woman differs in many ways this data cannot separate.

The regional cascade findings are the sturdiest thing here, because they are
descriptive: they count where women are actually being lost, and counting does
not require any causal assumption.

**The predictions are moderately accurate, not precise.** The models rank women
correctly about 78% of the time (AUROC ≈ 0.78), which is useful for directing
attention across a population and far too blunt for a decision about any
individual woman.

One point worth knowing, because it is easy to get wrong in both
directions: on the raw accuracy measure, predicting *any* ANC contact looks
far easier (0.93) than predicting eight (0.43). Part of that is an illusion.
78% of women attain the first and only 19% the second, so a model that
guessed blindly would already "score" 0.78 on the first. But a fairer
measure, which does not depend on how common the outcome is, agrees in
direction. **Knowing in advance who will complete eight contacts is genuinely
harder than knowing who will reach care at all.** Reaching care tracks a
woman's settled circumstances; completing it depends on what happens across
a whole pregnancy.

---

## What this suggests, concretely

1. **Stop treating ANC8 coverage as one national problem.** Target by where in
   the cascade each region loses women, not by its headline coverage.
2. **Somali, and to a lesser extent Oromia and Afar, need outreach** — a third
   or more of women never make contact at all.
3. **Central Ethiopia, Tigray, South Ethiopia and Sidama need retention** —
   women arrive and are lost partway. Continuation from four to eight contacts
   is where the national number will move.
4. **Cost of repeat attendance looks like a binding constraint** for poorer
   women who have already engaged. That is a narrower, cheaper problem than
   generalised demand creation.
5. **Addis Ababa's continuation rates show the ceiling is reachable** within
   Ethiopia — 95% and 70% at the two transitions.
