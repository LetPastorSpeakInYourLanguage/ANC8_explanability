# Antenatal care during the Tigray war

**Question.** The survey's oldest births (from mid-2021) include pregnancies
that ran during the Tigray war. What happened to antenatal care for those
women, how does Tigray compare with the other regions over the same period,
and does the war distort the other findings?

**Scope.** The survey records antenatal care only for births from about
mid-2021, so no Tigrayan pregnancy before the war (November 2020) is
observed. The comparison is **wartime against post-war**, set against every
other region over the same calendar periods.

**Short answer.**

- **About one wartime pregnancy in five** in Tigray received no antenatal care
  at all, against **one in thirteen** after the ceasefire. Beyond the change
  seen in peaceful regions over the same period, that is **13 percentage
  points** (95% interval 6 to 20).
- **The damage was at the door.** Women were cut off from care entirely,
  rather than starting and dropping out.
- **Recovery restored access, not completion.** Four-contact coverage
  recovered; eight-contact coverage did not measurably change.
- **Post-war Tigray** now does better than its circumstances predict at
  getting women to care, and still falls short on completing the schedule.

---

## 1. Who was exposed

Each pregnancy is dated from the pregnancy history: the date it ended, and
the nine months before. A pregnancy counts as **exposed** if at least 3 of
those 9 months fall inside a conflict window for the woman's region. Exposure
is assigned by calendar date, not by how long ago the birth was, because the
conflicts do not line up with birth age. The Amhara insurgency falls on the
*recent* births.

| Window | Regions | Dates | Source |
|---|---|---|---|
| Tigray war | Tigray | Nov 2020 - Nov 2022 | war from 3 Nov 2020; Pretoria cessation of hostilities signed 2 Nov 2022 |
| Northern incursion | Afar, Amhara | Jul - Dec 2021 | Tigrayan forces entered in July; withdrew after the federal offensive ended 23 Dec 2021 |
| Fano insurgency | Amhara | Aug 2023 - fieldwork end | state of emergency declared 4 Aug 2023; ongoing through April 2025 |

Full citations are in `docs/conflict_windows.csv`.

Pregnancies exposed in this survey window: **Tigray 259**, Afar 102 and
Amhara 61 (the 2021 incursion), and Amhara 231 (the Fano insurgency). Only
the Tigray war has enough exposed and unexposed women in one region to
analyse. The 2021 incursion falls at the very start of the survey window,
where few births are recorded.

---

## 2. The estimate: difference-in-differences

Comparing wartime and post-war pregnancies *within Tigray alone* would mix
the war with two other things that also differ between older and newer
births:

- **the national trend** in antenatal care, and
- **recall.** A contact count remembered three years later is less reliable
  than one remembered a few months later.

Regions without major conflict in the period were exposed to both of those
and not to the war. The estimate is therefore:

> (Tigray: post-war − wartime) − (peaceful regions: the same calendar
> periods, averaged *within* each region)

The comparison group is Sidama, South Ethiopia, South West Ethiopia, Central
Ethiopia, Gambella, Harari, Dire Dawa, Addis Ababa and Somali. Oromia and
Benishangul-Gumuz had their own armed conflicts in the period, so they are
left out of the main comparison and added back as a sensitivity check.

**Why the comparison is averaged within regions.** The *pooled* mean of the
comparison regions falls 5 points between the periods while every region in
it is flat or rising: the regional mix of births differs between the two
periods (Simpson's paradox). Subtracting that from Tigray would inflate the
war estimate. So the comparison change is the average of the within-region
changes. It is near zero (−1.2 to +1.2 points), which also shows that recall
and trend effects are small here.

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

95% intervals come from a stratified cluster bootstrap (1,000 resamples) that
resamples Tigray and the comparison regions together, as they were sampled.

---

## 3. Tigray against every region

The same two calendar periods in every region: pregnancies with at least 3
months inside the war window, and pregnancies conceived after the ceasefire
(fig38).

<!-- AUTO:tigray_regions -->
| Region | n wartime / post-war | No ANC (%) | ANC1+ (%) | ANC4+ (%) | ANC8+ (%) | ANC4+ change (pts) |
|---|---|---|---|---|---|---|
| **Tigray** | 259 / 323 | 20 → 8 | 80 → 92 | 46 → 59 | 10 → 12 | +13.7 |
| Addis Ababa | 152 / 123 | 2 → 1 | 98 → 99 | 91 → 98 | 63 → 68 | +7.4 |
| South Ethiopia | 235 / 317 | 26 → 26 | 74 → 74 | 42 → 45 | 7 → 8 | +3.8 |
| Gambella | 211 / 193 | 20 → 26 | 80 → 74 | 46 → 48 | 13 → 8 | +2.0 |
| Afar | 283 / 331 | 32 → 29 | 68 → 71 | 42 → 44 | 25 → 22 | +1.9 |
| Oromia | 299 / 359 | 31 → 29 | 69 → 71 | 47 → 48 | 15 → 15 | +1.0 |
| Harari | 144 / 154 | 26 → 21 | 74 → 79 | 47 → 47 | 26 → 25 | -0.5 |
| Somali | 243 / 411 | 69 → 67 | 31 → 33 | 11 → 10 | 6 → 2 | -1.0 |
| Amhara | 221 / 267 | 10 → 11 | 90 → 89 | 64 → 61 | 29 → 30 | -3.0 |
| Central Ethiopia | 239 / 212 | 10 → 18 | 90 → 82 | 60 → 56 | 10 → 11 | -3.9 |
| Sidama | 248 / 181 | 13 → 17 | 87 → 83 | 42 → 37 | 9 → 10 | -5.4 |
| South West Ethiopia | 209 / 226 | 27 → 27 | 73 → 73 | 54 → 48 | 19 → 16 | -6.2 |
| Benishangul-Gumuz | 194 / 218 | 30 → 31 | 70 → 69 | 62 → 54 | 22 → 20 | -7.8 |
| Dire Dawa | 121 / 155 | 14 → 15 | 86 → 85 | 72 → 64 | 33 → 45 | -8.0 |

Every region over the same two calendar periods: pregnancies with at least 3 months inside the Tigray war window (Nov 2020 - Nov 2022), and pregnancies conceived after the ceasefire. Survey-weighted. Sorted by the ANC4+ change.
<!-- /AUTO:tigray_regions -->

Tigray's change in reaching care is the largest of any region: no-ANC falls
12 points and ANC4+ rises 14 points, while most regions move by a few points
in either direction. Its ANC8+ barely moves. The few regions with a large
ANC8+ change (Dire Dawa, Addis Ababa) are small urban samples.

---

## 4. What it shows

**The war cut women off from care.** The whole shift is in the first rung.
Women who would otherwise have received some antenatal care received none.
The share who started and stopped before four contacts did not change. The
war stopped women arriving; it did not mainly make them drop out.

**Recovery reached four contacts, not eight.** After the ceasefire the women
who came back into care mostly went on to reach four contacts ("reached 4,
stopped before 8" rises 11.6 points). The share reaching eight rose only
2 points, with an interval that includes zero.

**The drivers did not change.** Across the three northern regions, war
exposure did not measurably change how much wealth or distance to a health
post mattered for ANC4+:

| | odds ratio | 95% interval |
|---|---|---|
| Wealth (per SD), overall | 2.14 | 1.38 - 3.30 |
| Distance to health post (per SD), overall | 0.68 | 0.51 - 0.91 |
| Wealth × exposure | 0.92 | 0.53 - 1.57 |
| Distance × exposure | 0.87 | 0.60 - 1.25 |

Weighted logistic regression with region fixed effects and cluster-robust
errors, n = 1,243 (women in the three northern regions with a recorded
health-post travel time). With samples this size the test rules out only large
changes.

---

## 5. Does the war distort the other findings?

Mostly not, and where it could, it has now been checked.

**Regional ranking.** The analysis comparing each region with what its
population profile predicts (wealth, education, household; region withheld)
gives the same ranking in both birth windows:

<!-- AUTO:regional_gap -->
| Region | All births | Post-war pregnancies only | Last 24 months (sensitivity) |
|---|---|---|---|
| Afar | +15.0 | — | +15.9 |
| Addis Ababa | +12.0 | — | +12.8 |
| Dire Dawa | +9.8 | — | +12.6 |
| South West Ethiopia | +6.9 | — | +6.1 |
| Amhara | +4.2 | — | +5.2 |
| Benishangul-Gumuz | +3.2 | — | +3.8 |
| Harari | +2.8 | — | +2.3 |
| Oromia | +1.6 | — | +1.4 |
| South Ethiopia | -1.5 | — | -1.3 |
| Sidama | -2.0 | — | -3.9 |
| Central Ethiopia | -2.1 | — | -2.7 |
| Somali | -2.2 | — | -1.4 |
| Gambella | -3.3 | — | -5.9 |
| Tigray | -4.1 | -2.8 | -3.8 |

ANC8+ attainment minus what the region's population profile implies (predicted with region withheld), percentage points.
<!-- /AUTO:regional_gap -->

**Tigray's shortfall is not only a war artefact.** Over all births Tigray
sits about 4 points below what its population profile implies on ANC8+. On
post-war pregnancies alone it is above expectation for reaching care (ANC1+
+6.3, ANC4+ +7.4 points) and still below it for completing the schedule
(ANC8+ −2.8).

**The regional cascade.** The headline contrast holds in the official
24-month window: Somali loses 65% of women at the door, and Central Ethiopia
keeps only 16% of women from four contacts to eight. See DATA_AND_COHORT.md.

---

## 6. What this cannot see

- **Pregnancies before the war.** Not recorded in this survey, so the
  analysis cannot say how far post-war care has returned to pre-war levels.
- **Women who are not in the survey.** Women displaced out of the region, or
  who died, were not interviewed. Some enumeration areas were excluded for
  security reasons. These are plausibly the worst-affected, so the wartime
  shortfall is **more likely understated than overstated**.
- **Recall.** The comparison regions absorb the average recall effect. If
  recall degraded *more* for traumatic wartime pregnancies, some of the
  effect would be misreporting rather than missed care.
- **Small samples.** 259 and 323 Tigrayan women. The direction is robust; the
  exact size is uncertain.

**Robustness checked:** war window shifted three months earlier and later;
comparison group with and without Oromia and Benishangul-Gumuz. The ANC4+
effect stays between +11 and +14 points throughout.

---

**Reproduce:** `python scripts/run_wartime_analysis.py`. Results:
`outputs/wartime/`. Figures: `fig31_tigray_did`, `fig32_regional_gap_cohort`,
`fig38_tigray_regions_by_period`.
