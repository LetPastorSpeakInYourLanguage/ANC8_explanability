/**
 * Shapes of analysis.json and policy.json — what scripts/export_app_data.py
 * publishes.
 *
 * Almost every field is optional, and deliberately so: rungs and analyses
 * complete at different times, and the views hide a panel whose data is absent
 * rather than rendering an empty frame or inventing a placeholder.
 */

export type OutcomeSpec = {
  threshold: number;
  label: string;
  question: string;
  meaning?: string;
  weighted_prevalence: number;
};

export type LeaderboardRow = {
  model: string;
  generation: string;
  held_AP: number | null;
  held_AUROC: number | null;
  held_Brier: number | null;
  held_slope: number | null;
  held_CITL: number | null;
  sensitivity: number | null;
  specificity: number | null;
  threshold: number | null;
  dev_AP: number | null;
  dev_AUROC: number | null;
  dev_Brier: number | null;
  dev_slope: number | null;
  n_trials: number | null;
  seconds: number | null;
  /** development AP minus held-out AP: how optimistic development was. */
  optimism: number | null;
};

export type CalibrationPoint = { predicted: number; observed: number; n: number };

export type ParameterSensitivity = {
  parameter: string;
  worst_AP_drop: number;
  best_AP_gain: number;
  n_perturbations: number;
};

export type AblationTrial = {
  model: string;
  parameter: string;
  tuned_value: string | number | null;
  perturbed_value: string | number | null;
  AP: number;
  AUROC: number;
  AP_vs_tuned: number;
};

export type ModelAblation = {
  defaults_AP: number | null;
  tuned_AP: number | null;
  gain: number | null;
  parameters: ParameterSensitivity[];
  trials: AblationTrial[];
};

export type StabilitySummary = {
  model: string;
  n_seeds: number;
  n_original_predictors: number;
  n_enhanced_predictors: number;
  AP: DeltaBlock;
  AUROC: DeltaBlock;
};

export type DeltaBlock = {
  original_mean: number;
  enhanced_mean: number;
  delta_mean: number;
  delta_sd: number;
  delta_lo: number;
  delta_hi: number;
  seeds_enhanced_better: number;
};

export type BootstrapCI = {
  champion: string;
  baseline: string;
  d_AP: { point: number; lo: number; hi: number };
  d_AUROC: { point: number; lo: number; hi: number };
  d_AP_excludes_zero: boolean;
  d_AUROC_excludes_zero: boolean;
};

export type SubgroupRow = {
  variable: string;
  level: string;
  n: number;
  weighted_prevalence: number;
  V2_AUROC: number;
  V1_AUROC: number;
};

export type DecisionCurveRow = {
  threshold: number;
  model: number;
  treat_all: number;
  treat_none: number;
  model_name?: string;
  v1_xgboost?: number;
};

export type PreprocessingRow = {
  variant: string;
  AP: number;
  AUROC: number;
  AP_vs_original: number;
};

export type ScreeningRow = {
  variable: string;
  label: string;
  weighted_auc: number;
  screen_status: string;
  exclusion_reason: string | null;
};

export type DuplicatePair = {
  a: string;
  b: string;
  association: number;
  measure: string;
  exact_recoding: boolean;
};

export type GroupedImportance = {
  group: string;
  grouped_importance: number;
  largest_single_member: number;
  n_members: number;
  members: string;
  rank_grouped: number;
  rank_as_single_columns: number;
};

export type LadderPatternRow = {
  predictor: string;
  domain: string;
  pattern: string;
  methods_agreeing: number;
  methods_total: number;
  mean_share_shift: number;
};

export type Analysis = {
  outcomes: Record<string, OutcomeSpec>;
  rungs: string[];
  leaderboard: Record<string, LeaderboardRow[]>;
  calibration: Record<string, Record<string, CalibrationPoint[]>>;
  hyperparameters: Record<string, Record<string, Record<string, unknown>>>;
  ablation: Record<string, Record<string, ModelAblation>>;
  stability: Record<string, StabilitySummary>;
  bootstrap: Record<string, BootstrapCI>;
  subgroups: Record<string, SubgroupRow[]>;
  decision_curve: Record<string, DecisionCurveRow[]>;
  operating_thresholds: Record<string, Record<string, unknown>>;
  optimism?: Record<string, { mean_drop: number; n_models: number }>;
  tuning_gain?: {
    rung: string; model: string; defaults_AP: number; tuned_AP: number; gain: number;
  }[];
  preprocessing?: PreprocessingRow[];
  screening?: {
    n_columns: number;
    counts: Record<string, number>;
    top: ScreeningRow[];
  };
  redundancy?: {
    summary: {
      n_predictors: number;
      n_after_deduplication: number;
      exact_recodings: number;
      development_AP_full: number;
      development_AP_deduplicated: number;
      AP_cost_of_deduplication: number;
      mechanism_check?: Record<string, number>;
    } | null;
    pairs: DuplicatePair[] | null;
    coarsening: { finer: string; coarser: string; determination: number }[] | null;
    grouped: GroupedImportance[];
  };
  ladder?: {
    patterns?: LadderPatternRow[];
    predictor_shares?: { predictor: string; outcome: string; share: number;
                         method?: string; rank?: number }[];
    domain_shares?: { domain: string; outcome: string; share: number }[];
    performance?: Record<string, unknown>[];
    agreement?: Record<string, unknown>[];
    domain_rollup?: Record<string, unknown>[];
  };
  modifiable_hint?: string[];
  feature_value?: FeatureValue;
  predictor_matrix?: MatrixRow[];
  horizons?: Horizons;
};

/** One predictor at one rung: its value relative to the 21-predictor set. */
export type MatrixRow = {
  predictor: string;
  rung: string;
  in_21: boolean;
  marginal: number | null;
  marginal_seeds: number | null;
  marginal_share: number | null;
  pool_loss: number | null;
  pool_loss_share: number | null;
  tier: string | null;
  clears_threshold: boolean;
  ceiling: number;
  ebm?: number | null;
  shap?: number | null;
  domain?: string | null;
};

export type Interval = {
  d_AP: number; d_AP_lo: number; d_AP_hi: number;
  d_AUROC: number; d_AUROC_lo: number; d_AUROC_hi: number;
};

export type Horizons = {
  early_anc?: { outcome: string; base: string; n_base: number; AP_without: number;
                AP_with: number; gain: number; seeds_positive: number;
                prevalence: number }[];
  heldout?: { outcome: string; set: string; early_anc: boolean; n_predictors: number;
              AP: number; AUROC: number; Calibration_slope: number;
              prevalence: number }[];
  cross?: { outcome: string; set: string; trained_on: string; AP: number;
            AUROC: number; prevalence: number }[];
  tiers?: { outcome: string; horizon: string; step: number; predictor: string;
            tier: string; AP: number; gain: number; prevalence: number;
            all_pool_AP: number; set21_AP: number }[];
  bootstrap?: Record<string, Interval> | null;
};

// --------------------------------------------------------------- policy.json

export type RegionalCascadeRow = {
  region: string;
  n: number;
  reach8: number;
  never: number;
  start_lt4: number;
  four_lt8: number;
  continue_1_to_4: number | null;
  continue_4_to_8: number | null;
  biggest_loss: string;
  biggest_loss_share: number;
};

export type Policy = {
  cascade?: {
    reach1: number; reach4: number; reach8: number;
    never: number; start_lt4: number; four_lt8: number;
    continue_1_to_4: number; continue_4_to_8: number; n: number;
  };
  regional_cascade?: RegionalCascadeRow[];
  continuation_equity?: Record<string,
    { level: string; n: number; continue_4_to_8: number }[]>;
  regional_gap?: {
    region: string; rung: string; n: number;
    actual: number; expected_from_circumstances: number; gap: number;
  }[];
  modifiable?: {
    rung: string; outcome: string;
    all_predictors: number; modifiable_only: number; fixed_only: number;
  }[];
  risk_bands?: {
    band: string; n: number; population_share: number; actual_rate: number;
  }[];
  continuation_profile?: Record<string, unknown>[];
  wartime?: Wartime;
};

// ------------------------------------------------------------- predictor value

export type FeatureValueEntry = {
  summary: {
    cohort: string;
    outcome: string;
    threshold: number;
    min_seeds_positive: number;
    n_development: number;
    n_total: number;
    anchors: {
      prevalence: number;
      original21: number;
      original21_C: number | null;
      all88: number;
      all88_C: number | null;
    };
    n_candidates?: number;
    stage0?: { n_non_contributors: number; non_contributors: string[];
               AP_21_minus_non_contributors: number; best_k_within_21: number;
               best_AP_within_21: number };
    stage1?: { n_new: number; n_clear: number; median_gain: number;
               total_gain_all_additions: number };
    tier1: string[];
    tier2: string[];
  };
  add_one?: { predictor: string; AP: number; gain: number; gain_min: number;
              gain_max: number; seeds_positive: number; at_interview: string;
              clears_threshold: boolean }[];
  cumulative?: { n_added: number; added: string; AP: number; AP_sd: number;
                 gain_over_21: number }[];
  steps?: { step: number; predictor: string; AP: number; gain: number;
            seeds_positive: number; runner_up: string | null;
            runner_up_gain: number | null; accepted: boolean; tier: string;
            lift_share: number; in_original_21: boolean; at_interview: string }[];
  frequency?: { predictor: string; selected_share: number; tier: string }[];
  heldout?: { model: string; set: string; n_predictors: number; AP: number;
              AUROC: number; Calibration_slope: number; AP_lift: number;
              prevalence: number }[];
  heldout_bootstrap?: Record<string, { d_AP: number; d_AP_lo: number; d_AP_hi: number;
                                        d_AUROC: number; d_AUROC_lo: number;
                                        d_AUROC_hi: number }> | null;
  lightgbm_check?: { set: string; n: number; LightGBM_AP: number; logistic_AP: number }[];
  original21_placement?: { predictor: string; placement: string }[];
  drop_within_21?: { predictor: string; AP_without: number; loss: number;
                     seeds_positive: number; contributes: boolean }[];
  path_within_21?: { step: number; predictor: string; AP: number; gain: number;
                     seeds_positive: number; clears_threshold: boolean;
                     lift_share_of_88: number }[];
  drop_group_21?: { set: string; n: number; AP: number; C: number; removed: string }[];
};

export type FeatureValue = Record<string, Record<string, FeatureValueEntry>>;

export type Wartime = {
  did?: { measure: string; window_shift_months: number; controls: string; did: number;
          lo: number; hi: number; tigray_during_n: number; tigray_after_n: number;
          tigray_during: number; tigray_after: number;
          control_change_within_region: number }[];
  by_period?: { region: string; period: string; n: number; anc1plus: number;
                anc4plus: number; anc8plus: number; share_exposed: number }[];
  exposure_counts?: { window: string; region: string; n_exposed: number }[];
  interactions?: { outcome: string; term: string; odds_ratio: number; lo: number;
                   hi: number; p: number; n: number }[];
  regional_gap?: { cohort: string; outcome: string; region: string; n: number;
                   actual: number; expected: number; gap: number }[];
  by_war_period?: { region: string; period: string; n: number; anc1plus: number;
                    anc4plus: number; anc8plus: number; never: number }[];
  windows?: { window: string; regions: string; start: string; end: string;
              note: string; source: string }[];
};
