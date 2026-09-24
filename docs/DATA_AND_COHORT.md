# Data, cohort and the outcome definition

What the analysis is built on, checked against the official Ethiopia DHS
2024-25 report and the DHS Program's own indicator definitions (*Guide to
DHS Statistics*, DHS-8).

---

## 1. The source

**Ethiopia Demographic and Health Survey 2024-25**, Individual Recode
(`ETIR8AFL.DTA`, 6,648 variables). Fieldwork ran from 1 August 2024 to
14 April 2025. The design is a stratified two-stage cluster sample: 805
enumeration areas in 27 strata (each region split urban/rural; Addis Ababa
has no rural stratum) and 28 households per area. 21,395 women aged 15-49
were interviewed, a 96% response rate.

The analysis data match that design exactly: **27 strata and 794 of the 805
enumeration areas** contain at least one woman in the cohort.

---

## 2. The outcome

The number of antenatal care contacts for the most recent pregnancy
(`m14_1`), thresholded three ways:

| Rung | Question | Contacts |
|---|---|---|
| ANC1+ | Did she reach antenatal care at all? | ≥ 1 |
| ANC4+ | The previous WHO minimum | ≥ 4 |
| ANC8+ | The 2016 WHO recommendation | ≥ 8 |

These are nested by construction, and the code asserts it for every woman. A
woman with 8 contacts also has 4 and 1.

The official EDHS key indicators report publishes ANC4+ but not ANC8+,
although the DHS-8 tabulation plan added the 8+ grouping (Guide, Table 9.2).
So ANC4+ can be checked against the report, and ANC8+ cannot.

---

## 3. The cohorts

<!-- AUTO:cohorts -->
| Cohort | Women | Development | Held out | ANC4+ | ANC8+ | Use |
|---|---|---|---|---|---|---|
| Before ANC | 6893 | 5518 | 1375 | 52.4% | 19.2% | Main analysis; horizon 1 (before ANC) |
| ANC entry | 5001 | 4017 | 984 | 67.6% | 24.7% | Horizon 2 (at ANC entry) |
| Last 24 months | 5037 | 4040 | 997 | 53.0% | 19.5% | Sensitivity (DHS-8 24-month window) |

One development / held-out split, drawn once by survey cluster on the full cohort and restricted to each cohort.
<!-- /AUTO:cohorts -->

**All births: 6,893 women,** everyone whose most recent pregnancy has an ANC
count. The main analysis, and the first prediction horizon (before ANC
starts).

**ANC entry: 5,001 women,** those among them who started ANC and know when
their first contact was. The second prediction horizon, which adds whether
the first contact came by 12 weeks or 3 months (`early_anc`; 2,130 of the
5,001 women). Every woman in it has ANC1+, so only ANC4+ and ANC8+ are
defined; 64.6% of these women reach ANC4+ and 23.4% ANC8+ (unweighted).

**Last 24 months: 5,037 women.** The official DHS-8 indicator covers women
with a live birth *or stillbirth* in the **24 months** before interview, for
the most recent birth (Guide, Table 9.2). 28% of the full cohort gave birth
24-35 months before interview. This window is used as a sensitivity check
and, first, as a validity check.

It reproduces the official report closely:

<!-- AUTO:cohort_validation -->
| Region | EDHS report | Last 24 months | diff | All births | diff |
|---|---|---|---|---|---|
| Addis Ababa | 94.8 | 96.2 | +1.4 | 94.1 | -0.7 |
| Afar | 46.2 | 46.0 | -0.2 | 44.0 | -2.2 |
| Amhara | 62.0 | 61.8 | -0.2 | 61.6 | -0.4 |
| Benishangul-Gumuz | 57.2 | 57.1 | -0.1 | 57.3 | +0.1 |
| Central Ethiopia | 58.5 | 58.5 | -0.0 | 58.4 | -0.1 |
| Dire Dawa | 69.1 | 68.5 | -0.6 | 68.0 | -1.1 |
| Gambella | 49.2 | 48.9 | -0.3 | 46.8 | -2.4 |
| Harari | 46.5 | 46.7 | +0.2 | 46.4 | -0.1 |
| Oromia | 48.4 | 48.5 | +0.1 | 48.7 | +0.3 |
| Sidama | 41.5 | 41.5 | +0.0 | 40.7 | -0.8 |
| Somali | 12.7 | 12.5 | -0.2 | 11.4 | -1.3 |
| South Ethiopia | 47.1 | 47.1 | -0.0 | 44.6 | -2.5 |
| South West Ethiopia | 48.1 | 48.7 | +0.6 | 50.6 | +2.5 |
| Tigray | 57.1 | 56.3 | -0.8 | 53.6 | -3.5 |
| **National** | 53.0 | 53.0 | -0.0 | 52.4 | -0.6 |

ANC4+ among women with a recent birth. EDHS figures: 2024-25 EDHS key indicators report, Table 9.
<!-- /AUTO:cohort_validation -->

National ANC4+ matches exactly (53.0%), and 13 of the 14 regions fall within
0.8 points. The one exception is Addis Ababa at +1.4, where a handful of
"don't know" counts in a small sample move the rate that much. The report
keeps those in the denominator; this analysis cannot, because an unknown
count cannot be thresholded.

That match is more than a formality. It confirms, in one check, that the
outcome derivation, the survey weights and the region coding are all right.

### What changes between the windows

<!-- AUTO:recent_cascade -->
| Window | Women | ANC1+ | ANC4+ | ANC8+ | Starters reaching 4 | Those at 4 reaching 8 |
|---|---|---|---|---|---|---|
| All births | 6893 | 77.6% | 52.4% | 19.2% | 68% | 37% |
| Last 24 months | 5037 | 78.2% | 53.0% | 19.5% | 68% | 37% |
<!-- /AUTO:recent_cascade -->

Recent births show slightly higher coverage. That is consistent with an
improving trend, shorter recall, and fewer pregnancies overlapping the Tigray
war (see WARTIME.md). The **substantive findings hold in both windows**:

- the largest loss is between the fourth and eighth contact;
- Somali loses women at the door (65% never start);
- Central Ethiopia loses them after four contacts (16% of those at four reach
  eight).

**The main analysis uses all births**, which keeps the largest sample; every
predictor-set result is repeated on the 24-month window as a sensitivity
check, and the leading variables are the same in both (PREDICTOR_VALUE.md
§7).

### Stillbirths

The DHS-8 definition includes stillbirths, and so does this cohort: 61 women
in the full window and 55 in the 24-month window. The official report's
stillbirth row is 62 weighted women.

Pregnancy timing therefore comes from the **pregnancy history** (`p19_01`,
`p3_01`). The live-birth history (`b19_01`) has no row for a stillbirth, so
using it would silently lose these women.

---

## 4. The survey design, respected throughout

- **Weights** (`v005` / 1e6) are applied to every estimate and every metric,
  so results describe Ethiopia rather than the sample. Weighted ANC8+ is 19.2%;
  unweighted it would be 17.0%.
- **Clusters.** All splits and cross-validation folds are grouped by
  enumeration area (`v021`). Women in one area resemble each other; letting
  an area appear on both sides of a split would make every score optimistic.
  The test suite checks that no area spans two folds.
- **Strata.** The held-out set samples areas within each stratum (`v022`), so
  the design survives the split.
- **Uncertainty.** Confidence intervals come from a stratified cluster
  bootstrap, which resamples areas within strata rather than individual
  women.

The development/held-out split (5,518 / 1,375 women) is drawn once on the
full cohort. The ANC-entry and 24-month cohorts use the *same* split
restricted to their women (4,017 / 984 and 4,040 / 997), so nothing is
re-drawn; for the ANC-entry cohort this is asserted woman for woman.

---

## 5. When each predictor was measured

The *Guide to DHS Statistics* marks most background characteristics as
"**current status at time of survey**". For a birth 2-3 years before
interview, "current" can be well after the pregnancy. Each candidate
predictor was classified accordingly:

| Kind | Examples | How it is handled |
|---|---|---|
| Stable over a pregnancy | region, residence, education, religion, language, wealth, travel time to facilities | used as is |
| Tied to the wrong moment | current age | replaced by **age at the birth**, the figure the EDHS report itself tabulates |
| Could be caused by the pregnancy or its care | worked in the last 12 months (pregnancy itself reduces work), current health insurance (enrolment can follow facility contact), current occupation | kept, but flagged ⚑ wherever selected |
| Shaped by the children already born | ideal number of children, children beyond the ideal | kept, flagged; the Guide notes ideal family size is shaped by existing children |
| Carries information from after the birth | number of living children (falls if the baby died; ANC8+ is 9% where the index child died against 19.5% where the child is alive) | **excluded** |
| Recorded during or after ANC | timing of first visit, place of delivery, tetanus doses, visits by a health worker | **excluded** as leakage (see `src/anc8/features.py`) |
| General, not ANC-specific | problems accessing care "when you are sick" | kept, flagged; covers any illness, not pregnancy care |

The 24-month window shortens every one of these gaps.

---

## 6. Data the survey has that this analysis does not yet use

- **Health expenditure module** (household questionnaire). It records
  out-of-pocket health spending, which bears directly on the finding that
  poorer women who have already attended four times are much less likely to
  reach eight. It lives in the household file, not the women's file, and has
  not been linked.
- **Men's questionnaire.** The partner's own report of his involvement in
  antenatal care (Guide, "men's involvement in maternal health care").
- **Facility data** are not in the DHS at all. The survey can say *where* in
  the cascade women are lost, not *why*. That needs the Ministry's own
  facility records.
