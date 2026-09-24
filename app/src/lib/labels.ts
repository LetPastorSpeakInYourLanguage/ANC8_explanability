/**
 * Human-readable names for DHS variable codes.
 *
 * The analysis carries DHS codes (`v191`, `s1101b`) because that is what makes
 * it traceable back to the source data and to the predictor registers. A user
 * reading an explanation should not have to decode them, so the mapping lives
 * here and the codes stay in the artifacts.
 */

export const PREDICTOR_LABELS: Record<string, string> = {
  // wealth and assets
  v191: "Household wealth score",
  v191a: "Household wealth score (urban/rural)",
  v190: "Wealth quintile",
  v190a: "Wealth quintile (urban/rural)",
  wealth_quintile: "Wealth quintile",
  asset_index: "Household assets owned",
  v119: "Has electricity",
  v120: "Owns a radio",
  v121: "Owns a television",
  v123: "Owns a bicycle",
  v169a: "Owns a mobile phone",
  v170: "Has a bank account",
  v113: "Drinking water source",
  v116: "Toilet facility",
  v127: "Floor material",
  v136: "Household size",
  v137: "Children under 5 at home",
  v138: "Eligible women in household",

  // education and information
  v133: "Mother's years of schooling",
  v106: "Mother's education level",
  v149: "Mother's education (detailed)",
  v155: "Literacy",
  maternal_education: "Mother's education level",
  v157: "Reads newspapers",
  v158: "Listens to radio",
  v159: "Watches television",
  v171a: "Internet use",
  internet_exposure: "Internet use",
  newspaper_weekly: "Reads a newspaper weekly",
  radio_weekly: "Listens to radio weekly",
  television_weekly: "Watches television weekly",

  // access
  s1101: "Travel time to hospital / health centre",
  s1101b: "Travel time to nearest health post",
  s1101a: "Transport to hospital / health centre",
  s1102: "Transport to health post",
  transport_mode_group: "Usual transport to care",
  travel_hospital_log: "Travel time to hospital (log)",
  travel_healthpost_log: "Travel time to health post (log)",
  travel_hospital_is_zero: "Lives at a hospital / health centre",
  travel_healthpost_is_zero: "Lives at a health post",
  travel_hospital_topcoded: "Hospital 10+ hours away",
  travel_healthpost_topcoded: "Health post 10+ hours away",
  healthpost_time_missing: "No health post in range",
  v115: "Time to water source",
  v467b: "Barrier: getting permission",
  v467c: "Barrier: finding the money",
  v467d: "Barrier: distance",
  v467f: "Barrier: not wanting to go alone",
  access_barrier_count: "Number of barriers to care",
  health_insurance: "Has health insurance",
  v481: "Has health insurance",

  // agency and household
  v743b: "Decides on large purchases",
  v743d: "Decides on family visits",
  v743f: "Decides how partner's earnings are spent",
  healthcare_decision_participation: "Has a say in her own healthcare",
  decision_participation_count: "Decisions she takes part in",
  v744a: "Thinks beating justified: goes out",
  v744b: "Thinks beating justified: neglects children",
  v744c: "Thinks beating justified: argues",
  v744d: "Thinks beating justified: refuses sex",
  v744e: "Thinks beating justified: burns food",
  ipv_justification_count: "Attitudes accepting of partner violence",
  v745a: "Owns a house",
  v745b: "Owns land",
  v151: "Sex of household head",
  v152: "Age of household head",
  spousal_education_gap: "Partner's schooling minus hers",
  spousal_age_gap: "Partner's age minus hers",
  v715: "Partner's years of schooling",
  v729: "Partner's education level",
  v730: "Partner's age",
  partner_education: "Partner's education",
  partner_occupation_group: "Partner's occupation",
  maternal_current_union_status: "Marital status",

  // reproductive history
  v201: "Children ever born",
  v212: "Age at first birth",
  v218: "Living children",
  v511: "Age at first marriage",
  v613: "Ideal number of children",
  children_over_ideal: "Children above her stated ideal",
  pregnancy_order_group: "Pregnancy number",
  preceding_pregnancy_interval_group: "Gap since previous pregnancy",
  pregnancy_intention: "Was this pregnancy wanted?",
  previous_pregnancy_history: "Previous pregnancy outcomes",
  v012: "Mother's age",
  traditional_media_weekly_count: "Traditional media accessed weekly",
  household_size: "Household size",
  travel_time_min: "Travel time to care",

  // geography and culture
  v024: "Region",
  region: "Region",
  v025: "Urban or rural",
  residence: "Urban or rural",
  v130: "Religion",
  religion_group: "Religion",
  v045c: "First language",

  // work
  v716: "Mother's occupation",
  v731: "Worked in the last year",
  maternal_occupation_group: "Mother's occupation",

  early_anc: "First ANC visit in the first trimester",
};

export function label(code: string): string {
  return PREDICTOR_LABELS[code] ?? code;
}

export const DOMAIN_COLORS: Record<string, string> = {
  "Access and distance": "#c2703d",
  Socioeconomic: "#2f7d70",
  "Education and information": "#4a6fa5",
  "Agency and household": "#8b5fa8",
  "Reproductive history": "#a8556b",
  "Geography and culture": "#6a8a3a",
  Work: "#7a7268",
  Other: "#8a8a8a",
};
