/**
 * The shape of app/public/data/regions.json (scripts/export_viz_data.py), and the
 * small helpers the map, the heatmap and the region panel share.
 */

import type { Cohort, Rung } from "@/lib/studio";

export type CascadeKey =
  | "reach1" | "reach4" | "reach8" | "never" | "start_lt4" | "four_lt8"
  | "continue_1_to_4" | "continue_4_to_8";

export type Cascade = Record<CascadeKey, number> & {
  [K in `${CascadeKey}_ci`]: [number, number];
} & {
  n: number;
  clusters: number;
  loss: "never" | "start_lt4" | "four_lt8";
  action: string;
};

export interface SubgroupRow {
  level: string;
  n: number;
  small: boolean;
  reach1: number;
  reach4: number;
  reach8: number;
  never: number;
  continue_4_to_8: number;
}

export interface Concept {
  key: string;
  label: string;
  modifiable: boolean;
  lever: string;
}

export type Drivers = Record<Rung, {
  national_predicted: number;
  regions: Record<string, { predicted: number; concepts: Record<string, number> }>;
}>;

export interface RegionsData {
  source: string;
  min_n: number;
  population: {
    births_per_year: number;
    source: string;
    method: string;
    regions: Record<string, { share: number; births: number }>;
  };
  concepts: Concept[];
  cohorts: Record<Cohort, { national: Cascade; regions: Record<string, Cascade> }>;
  subgroups: Record<Cohort, Record<string, Record<string, SubgroupRow[]>>>;
  profile_meta: { key: string; label: string; modifiable: boolean }[];
  profile: Record<Cohort, Record<string, Record<string, number>>>;
  drivers: Drivers;
  /** The same split under each additive model: "ebm" (explainable boosting), "logistic". */
  drivers_by_model?: Record<string, Drivers>;
  drivers_primary?: string;
  gap: Partial<Record<Cohort, Partial<Record<Rung, Record<string, {
    actual: number; expected: number; gap: number; n: number;
  }>>>>>;
}

export const REACH_OF: Record<Rung, CascadeKey> = { anc1: "reach1", anc4: "reach4", anc8: "reach8" };

/** The ANC-entry cohort has no ANC1+ (every woman in it started ANC). */
export function cohortRungs(cohort: Cohort): Rung[] {
  return cohort === "entry" ? ["anc4", "anc8"] : ["anc1", "anc4", "anc8"];
}
