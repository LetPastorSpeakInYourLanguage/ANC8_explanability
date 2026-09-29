/**
 * The shape of app/public/data/models.json (scripts/run_model_cards.py): one card per
 * model and rung, every number scored on the same held-out women.
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
}

export interface Family {
  key: string;
  name: string;
  group: string;
  what: string;
  pre: string;
  pool: 95 | 21 | 10;
}

export interface ModelsData {
  meta: { n_development: number; n_heldout: number; resamples: number };
  families: Record<string, Family>;
  cards: Record<string, Partial<Record<Rung, Card>>>;
  cross: { key: string; rung: Rung; ap: number; auroc: number; brier: number; slope: number; lift: number }[];
}

export const GROUPS = ["Linear", "Trees & boosting", "Neural", "Ensembles & calibrated", "Reduced sets"];

/** The best model at a rung, by held-out average precision. */
export function bestAt(d: ModelsData, rung: Rung): string {
  let best = "";
  let v = -1;
  for (const [k, by] of Object.entries(d.cards)) {
    const c = by[rung];
    if (c && c.ap > v) {
      v = c.ap;
      best = k;
    }
  }
  return best;
}
