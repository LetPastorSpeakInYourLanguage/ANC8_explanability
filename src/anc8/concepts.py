"""Predictors grouped into the concepts a planner thinks in.

The model uses 95 survey columns, and several of them measure one idea several ways:
household wealth appears as a score, an urban/rural score, two quintile versions and
an asset count. Shown one column at a time, wealth looks weak because its weight is
split five ways. Grouped, it is the largest single influence on completing care.

Every predictor belongs to exactly one concept (checked by `check_coverage`). Each
concept says whether a health system can move it within a planning cycle, and if so
through what: that is what turns an importance chart into a list of things to work
on. The grouping is additive, so for the explainable boosting model a concept's
contribution is exactly the sum of its predictors' contributions.
"""

from __future__ import annotations

CONCEPTS: list[dict] = [
    # ---- things a health system can move within a planning cycle
    {"key": "healthpost", "label": "Health post access", "modifiable": True,
     "lever": "More health posts, outreach days, health extension workers",
     "members": ["travel_healthpost_log", "travel_healthpost_is_zero", "travel_healthpost_topcoded",
                 "healthpost_time_missing", "s1101", "s1101a", "s1101b", "s1102"]},
    {"key": "hospital", "label": "Distance to a hospital or health centre", "modifiable": True,
     "lever": "Referral transport, health centre coverage",
     "members": ["travel_hospital_log", "travel_hospital_is_zero", "travel_hospital_topcoded",
                 "transport_mode_group", "v115"]},
    {"key": "barriers", "label": "Barriers to reaching care", "modifiable": True,
     "lever": "Transport vouchers, fee waivers, accompanied visits",
     "members": ["v467b", "v467c", "v467d", "v467f", "access_barrier_count"]},
    {"key": "insurance", "label": "Health insurance", "modifiable": True,
     "lever": "Community-based health insurance enrolment",
     "members": ["health_insurance", "v481"]},
    {"key": "information", "label": "Information and media", "modifiable": True,
     "lever": "Radio, TV and mobile health messaging",
     "members": ["v157", "v158", "v159", "v171a", "internet_exposure",
                 "newspaper_weekly", "radio_weekly", "television_weekly", "v169a"]},
    {"key": "intention", "label": "Wanted pregnancy and family size", "modifiable": True,
     "lever": "Family planning services and counselling",
     "members": ["pregnancy_intention", "children_over_ideal", "v613"]},
    {"key": "agency", "label": "Women's say in decisions", "modifiable": True,
     "lever": "Community dialogue, women's development groups",
     "members": ["healthcare_decision_participation", "decision_participation_count",
                 "v743b", "v743d", "v743f", "v744a", "v744b", "v744c", "v744d", "v744e",
                 "ipv_justification_count", "v745a", "v745b"]},
    # ---- circumstances: slow-moving, but they decide where effort is needed
    {"key": "wealth", "label": "Household wealth", "modifiable": False,
     "lever": "Target support to the poorest; the gradient itself moves with development",
     "members": ["v191", "v191a", "v190", "v190a", "wealth_quintile", "asset_index",
                 "v119", "v120", "v121", "v123", "v170", "v113", "v116", "v127"]},
    {"key": "education", "label": "Her education", "modifiable": False,
     "lever": "Long-term: girls' schooling",
     "members": ["maternal_education", "v106", "v133", "v149", "v155"]},
    {"key": "place", "label": "Region", "modifiable": False,
     "lever": "What is left once the women themselves are accounted for: the region's services",
     "members": ["region", "v024"]},
    {"key": "urban", "label": "Urban or rural", "modifiable": False, "lever": "",
     "members": ["residence", "v025"]},
    {"key": "culture", "label": "Language and religion", "modifiable": False, "lever": "",
     "members": ["v045c", "v130", "religion_group"]},
    {"key": "history", "label": "Age and pregnancy history", "modifiable": False, "lever": "",
     "members": ["v012", "pregnancy_order_group", "preceding_pregnancy_interval_group",
                 "previous_pregnancy_history", "v201", "v212", "v218", "v511"]},
    {"key": "household", "label": "Partner and household", "modifiable": False, "lever": "",
     "members": ["partner_education", "partner_occupation_group", "v715", "v729", "v730",
                 "spousal_education_gap", "spousal_age_gap", "maternal_current_union_status",
                 "v151", "v152", "v136", "v137", "v138"]},
    {"key": "work", "label": "Her work", "modifiable": False, "lever": "",
     "members": ["maternal_occupation_group", "v716", "v731"]},
]

CONCEPT_OF: dict[str, str] = {m: c["key"] for c in CONCEPTS for m in c["members"]}
BY_KEY: dict[str, dict] = {c["key"]: c for c in CONCEPTS}


def concept_of(predictor: str) -> str:
    """Concept key for a predictor or an interaction term ('a x b' uses a)."""
    return CONCEPT_OF.get(predictor.split(" x ")[0], "other")


def check_coverage(predictors: list[str]) -> list[str]:
    """Predictors that belong to no concept (should be empty)."""
    return [p for p in predictors if p not in CONCEPT_OF]
