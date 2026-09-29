/**
 * The shape of app/public/data/models/ (scripts/run_model_cards.py, split by
 * scripts/export_viz_data.py): one card per model, predictor set and rung, every number
 * scored on the same held-out women. A card key is `<set>.<slug>`; the slug names the
 * model family across sets.
 *
 *   index.json    families and a summary of every card: enough for rankings and heatmaps
 *   <set>.json    the full cards of one predictor set, fetched when that set is on screen
 */

import type { Rung } from "@/lib/studio";

export type Interval = [number, number];

export interface Paired {
  vs: string;
  key: string;
  ap: number;
  ap_ci: Interval;
  auroc: number;
  auroc_ci: Interval;
}

export interface SpaceRow {
  param: string;
  kind: "float" | "int" | "cat";
  low?: number;
  high?: number;
  step?: number;
  log?: boolean;
  choices?: (string | number)[];
  chosen: string | number;
}

export interface Tuning {
  tuned: boolean;
  how?: string;
  sampler?: string;
  objective?: string;
  folds?: string;
  trials?: number | null;
  seconds?: number | null;
  space?: SpaceRow[];
  defaults_ap?: number;
  tuned_ap?: number;
  ablation?: { param: string; worst: number; best: number }[];
  network?: {
    epochs: number; batch: number; lr: number; weight_decay: number; patience: number;
    val_share: number; seeds: number[]; layers: number; width: number; heads: number;
  };
}

export interface Operating {
  threshold: number; sensitivity: number; specificity: number; ppv: number; npv: number;
  flagged: number; tp: number; fp: number; fn: number; tn: number;
}

export interface Cell {
  level: string;
  n: number;
  auroc: number;
}

export interface Card {
  ap: number; ap_ci: Interval; auroc: number; auroc_ci: Interval;
  brier: number; citl: number; slope: number; ici: number;
  prevalence: number; target: "miss" | "reach"; target_share: number;
  lift: number; ratio: number; rank: number; of: number;
  dev_ap: number | null; dev_auroc: number | null; optimism: number | null;
  top10: number; top20: number;
  gains: number[];
  roc: [number[], number[]];
  pr: [number[], number[]];
  calibration: { predicted: number; observed: number; n: number }[];
  operating: Operating | null;
  subgroups: Record<"region" | "wealth" | "education" | "residence", Cell[]>;
  vs_best: Paired | null;
  vs_logistic: Paired | null;
  tuning: Tuning;
  n_predictors: number;
  predictors: string[];
  /** The study's own importance shares, for explainable boosting and XGBoost on the pool. */
  shares?: { kind: "ebm" | "shap"; rows: { predictor: string; share: number }[] };
}

/** The part of a card the rankings and heatmaps need. */
export type Summary = Pick<Card, "ap" | "ap_ci" | "auroc" | "auroc_ci" | "brier" | "slope" | "lift"
  | "prevalence" | "dev_ap" | "rank" | "of" | "n_predictors">;

export interface Family {
  key: string;
  name: string;
  group: string;
  what: string;
  pre: string;
  slug: string;
  set: string;
}

export interface ModelsIndex {
  meta: { n_development: number; n_heldout: number; resamples: number; sets: { key: string; label: string }[] };
  families: Record<string, Family>;
  summary: Record<string, Partial<Record<Rung, Summary>>>;
  cross: { key: string; set: string; rung: Rung; ap: number; auroc: number; brier: number; slope: number; lift: number }[];
}

export interface ModelsSet {
  cards: Record<string, Partial<Record<Rung, Card>>>;
}

export const MODELS_INDEX = "/data/models/index.json";
export const SETS = ["pool", "s21", "short", "pars"];
export const setFile = (set: string) => `/data/models/${SETS.includes(set) ? set : "pool"}.json`;

export const GROUPS = ["Linear", "Trees & boosting", "Neural", "Ensembles & calibrated"];

/** Short labels for the predictor-set switch. */
export const SET_SHORT: Record<string, string> = { pool: "Full pool", s21: "21 set", short: "Short set", pars: "Parsimonious" };

/** The best model on a predictor set at a rung, by held-out average precision. */
export function bestAt(d: ModelsIndex, rung: Rung, set: string): string {
  let best = "";
  let v = -1;
  for (const [k, by] of Object.entries(d.summary)) {
    if (d.families[k]?.set !== set) continue;
    const c = by[rung];
    if (c && c.ap > v) {
      v = c.ap;
      best = k;
    }
  }
  return best;
}
