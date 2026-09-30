/** Shapes of the artifacts the analysis exports into app/public/. */

export type ShapeFunction = {
  kind: "continuous" | "nominal";
  cuts?: number[];
  values?: string[];
  scores: number[];
  range?: [number, number] | null;
};

export type Range =
  | {
      kind: "continuous";
      min: number;
      max: number;
      median: number;
      p05: number;
      p95: number;
    }
  | { kind: "categorical"; options: string[] };

export type OutcomeSpec = {
  threshold: number;
  label: string;
  question: string;
  meaning: string;
  weighted_prevalence: number;
};

export type LadderPattern = {
  predictor: string;
  domain: string;
  pattern: "access-limited" | "engagement-limited";
  methods_agreeing: number;
  methods_total: number;
  mean_share_shift: number;
};

export type LadderPerformance = {
  rung: string;
  outcome: string;
  weighted_prevalence: number;
  best_model: string;
  AUROC: number;
  AP: number;
  AP_lift_over_prevalence: number;
};

export type Insights = {
  model: string;
  outcomes: Record<string, OutcomeSpec>;
  shape_functions: Record<string, ShapeFunction>;
  ranges: Record<string, Range>;
  domains: Record<string, string>;
  global_importance: Record<string, number>;
  direction: Record<string, string>;
  /** For categorical predictors, whose codes have no order: the levels at
   *  each end of the fitted effect, since "higher increases" is meaningless
   *  when the ordering is alphabetical rather than real. */
  level_extremes?: Record<string, { raises_most: string; lowers_most: string }>;
  top_predictors: string[];
  ladder_patterns: LadderPattern[];
  domain_rollup?: Record<string, Record<string, number>>;
  ladder_performance?: LadderPerformance[];
};

export type Example = {
  label: string;
  answers: Record<string, string | null>;
  probability: number;
  contributions: { predictor: string; contribution: number }[];
  observed: Record<string, number | null>;
};

export type Field = {
  name: string;
  label: string;
  help?: string;
  unit?: string;
  domain: string;
  type: "number" | "select";
  options?: { value: string; label: string }[];
  default?: string | number | null;
  core?: boolean;
};

/** One deployed model, as listed in form_schema.json. */
export type CatalogModel = {
  id: string;
  bundle: string;
  model: string;
  outcome: "anc1plus" | "anc4plus" | "anc8plus";
  horizon: "before" | "entry";
  set: string;
  algorithm: string;
  n_predictors: number;
  fields: string[];
  heldout_AP: number | null;
  heldout_AUROC: number | null;
  threshold?: number | null;
  browser: boolean;
  /** For a tree model scored in the browser: its file, fetched when first chosen. */
  trees?: string | null;
  recommended: boolean;
  headline: boolean;
  note?: string;
};

export type Schema = {
  outcomes: Record<string, string>;
  horizons: Record<string, string>;
  /** keyed "outcome|horizon" */
  prevalence: Record<string, number>;
  fields: Field[];
  models: CatalogModel[];
  not_deployed?: Record<string, Record<string, string>>;
};

export type ModelResult = {
  model: string;
  probability?: number;
  threshold?: number | null;
  classification?: string | null;
  error?: string;
  contributions?: { predictor: string; contribution: number }[];
};

export type GenResult = {
  available: boolean;
  reason?: string;
  models?: ModelResult[];
  n_expected?: number;
  n_supplied?: number;
  imputed?: string[];
  champion?: string | null;
};

export type ApiResponse = {
  result: Record<string, GenResult>;
  comparison?: {
    v1_model: string;
    v2_model: string;
    v1_probability: number;
    v2_probability: number;
    v1_classification: string;
    v2_classification: string;
    disagree: boolean;
    absolute_difference: number;
  } | null;
};
