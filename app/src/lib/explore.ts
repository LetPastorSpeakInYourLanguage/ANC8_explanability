/**
 * The Explore screens' vocabulary: the shape of app/public/data/explore.json, and the
 * names a reader sees for models, predictor sets and rungs.
 *
 * The result tables carry the analysis's working names ("tier 1+2", "V1 XGBoost").
 * Every screen shows them through these helpers, so a predictor set is always named
 * by what it is and how many predictors it has.
 */

import type { Cohort, Rung } from "@/lib/studio";

export type Outcome = "anc1plus" | "anc4plus" | "anc8plus";

export const OUTCOME_OF: Record<Rung, Outcome> = { anc1: "anc1plus", anc4: "anc4plus", anc8: "anc8plus" };
export const RUNG_OF: Record<Outcome, Rung> = { anc1plus: "anc1", anc4plus: "anc4", anc8plus: "anc8" };
export const RUNG_LABEL: Record<string, string> = {
  anc1: "ANC1+", anc4: "ANC4+", anc8: "ANC8+", anc1plus: "ANC1+", anc4plus: "ANC4+", anc8plus: "ANC8+",
};
export const RUNG_COLOR: Record<string, string> = {
  anc1: "var(--rung1)", anc4: "var(--rung4)", anc8: "var(--rung8)",
  anc1plus: "var(--rung1)", anc4plus: "var(--rung4)", anc8plus: "var(--rung8)",
};
export const COHORT_COLOR: Record<Cohort, string> = {
  full: "var(--accent)", entry: "var(--cross)", recent: "var(--good)",
};

/** The two model generations in the leaderboard are two predictor pools. */
export function poolOf(generation: string): "95" | "21" {
  return /^V1/.test(generation) ? "21" : "95";
}

/** "V1 XGBoost" -> "XGBoost · 21 predictors"; other names pass through. */
export function modelName(model: string): string {
  const m = model.match(/^V1 (.+)$/);
  return m ? `${m[1]} · 21 predictors` : model;
}

const SET_NAMES: Record<string, string> = {
  "tier 1": "Strongest few",
  "tier 1+2": "Strongest + next tier",
  "tier set": "Selected set",
  "original 21": "The 21",
  "21": "The 21",
  "all 88": "All 88",
  "full pool": "All 88",
  "21 minus non-contributors": "The 21 without non-contributors",
};

/** A predictor set by what it is; the count is added where known. */
export function setName(set: string, n?: number | null): string {
  const base = SET_NAMES[set] ?? set;
  return n != null && !/\d/.test(base) ? `${base} (${n})` : base;
}

export interface NetworkRow {
  rung: Outcome;
  model: string;
  AP: number;
  AUROC: number;
  Brier: number;
  CITL?: number;
  Calibration_slope: number;
  ICI: number;
}

export interface PairedRow {
  rung: Outcome;
  network: string;
  reference: string;
  d_AP: number; d_AP_lo: number; d_AP_hi: number;
  d_AUROC: number; d_AUROC_lo: number; d_AUROC_hi: number;
}

export interface ExploreData {
  edhs_anc4: { national: number; regions: Record<string, number>; source: string };
  contacts?: Record<Cohort, Record<string, { share: number[]; n: number }>>;
  contact_cap?: number;
}

export const NETWORKS = ["Ladder transformer", "Contact-sequence encoder-decoder"];

export const pct = (v: number | null | undefined, d = 0) =>
  v == null || !Number.isFinite(v) ? "–" : `${(v * 100).toFixed(d)}%`;
export const num = (v: number | null | undefined, d = 3) =>
  v == null || !Number.isFinite(v) ? "–" : v.toFixed(d);
export const signed = (v: number | null | undefined, d = 3) =>
  v == null || !Number.isFinite(v) ? "–" : `${v >= 0 ? "+" : "−"}${Math.abs(v).toFixed(d)}`;
