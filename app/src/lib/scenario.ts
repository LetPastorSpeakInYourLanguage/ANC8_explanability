/**
 * The planner's engine, over app/public/data/scenarios.json (scripts/run_scenarios.py).
 *
 * Every woman in the survey was re-scored with every on/off combination of the seven
 * levers (128). If a share f_i of the women each lever could move is reached, at
 * random and independently, a region's expected average is
 *
 *     sum over combinations S of  prod(f_i, i in S) * prod(1 - f_j, j not in S) * mean_S
 *
 * which is exact, not an approximation, because averaging is linear. The earlier-
 * first-visit lever comes from a separate model and is added on top. What the page
 * shows is the region's surveyed level plus the model's change; the model's own
 * level is never shown as if it were data.
 *
 * Association-based: what the model expects if circumstances changed, not what an
 * intervention would cause.
 */

export type SRung = "anc1" | "anc4" | "anc8";
export const S_RUNGS: SRung[] = ["anc1", "anc4", "anc8"];

export interface Lever {
  key: string;
  label: string;
  concept: string;
  who: string;
  supported: boolean;
  /** Supported under each lever model (every rung rises). */
  supported_by?: Record<string, boolean>;
  models_agree: boolean;
}

export type ScenarioRungs = Record<SRung, {
  means: number[][];
  gain: number[][];
  lo: number[][];
  hi: number[][];
  targeted: Record<string, number[][]>;
}>;

export interface ScenarioData {
  method: string;
  levers: Lever[];
  regions: string[]; // 14 regions then "Ethiopia"
  subsets: string[]; // "0101000": lever i on when char i is "1"
  eligible: Record<string, number[]>;
  /** The primary model's numbers (the same as by_model[primary].rungs). */
  rungs: ScenarioRungs;
  /** Every lever model's numbers: "ebm" (explainable boosting) and "logistic". */
  by_model?: Record<string, { rungs: ScenarioRungs }>;
  primary?: string;
  model_labels?: Record<string, string>;
  early_visit: {
    who: string;
    eligible: number[];
    rungs: Partial<Record<SRung, { effect: number[]; lo: number[]; hi: number[] }>>;
  };
  bootstrap_resamples: number;
}

export const EARLY = "early";

export const MODEL_SHORT: Record<string, string> = { ebm: "Explainable boosting", logistic: "Logistic regression" };

/** The scenario as one lever model sees it: its numbers and its own "supported" verdicts. */
export function forModel(d: ScenarioData, model: string): ScenarioData {
  const m = d.by_model?.[model];
  if (!m) return d;
  return { ...d, rungs: m.rungs, levers: d.levers.map((l) => ({ ...l, supported: l.supported_by?.[model] ?? l.supported })) };
}

/** Coverage per lever key (0..1), including "early". */
export type Coverage = Record<string, number>;

/** The model's expected change on one rung in one region under a coverage mix. */
export function changeAt(d: ScenarioData, rung: SRung, ri: number, cov: Coverage): number {
  const M = d.rungs[rung].means[ri];
  const f = d.levers.map((l) => cov[l.key] ?? 0);
  let s = 0;
  for (let j = 0; j < d.subsets.length; j++) {
    const bits = d.subsets[j];
    let w = 1;
    for (let i = 0; i < f.length && w > 0; i++) w *= bits[i] === "1" ? f[i] : 1 - f[i];
    if (w > 0) s += w * M[j];
  }
  const early = d.early_visit.rungs[rung]?.effect[ri] ?? 0;
  return s - M[0] + (cov[EARLY] ?? 0) * early;
}

export interface Projection {
  now: Record<SRung, number>;
  then: Record<SRung, number>;
  change: Record<SRung, number>;
}

/** Surveyed level plus the model's change, kept on the ladder (8+ within 4+ within 1+). */
export function project(d: ScenarioData, ri: number, now: Record<SRung, number>, cov: Coverage): Projection {
  const raw = {
    anc1: now.anc1 + changeAt(d, "anc1", ri, cov),
    anc4: now.anc4 + changeAt(d, "anc4", ri, cov),
    anc8: now.anc8 + changeAt(d, "anc8", ri, cov),
  };
  const anc1 = clamp01(raw.anc1);
  const anc4 = Math.min(clamp01(raw.anc4), anc1);
  const then = { anc1, anc4, anc8: Math.min(clamp01(raw.anc8), anc4) };
  return { now, then, change: { anc1: then.anc1 - now.anc1, anc4: then.anc4 - now.anc4, anc8: then.anc8 - now.anc8 } };
}

/** One lever at full reach: its effect and 95% band, per rung, in one region. */
export function leverWeight(d: ScenarioData, key: string, ri: number): Record<SRung, { v: number; lo: number; hi: number } | null> {
  const out = {} as Record<SRung, { v: number; lo: number; hi: number } | null>;
  for (const r of S_RUNGS) {
    if (key === EARLY) {
      const e = d.early_visit.rungs[r];
      out[r] = e ? { v: e.effect[ri], lo: e.lo[ri], hi: e.hi[ri] } : null;
    } else {
      const i = d.levers.findIndex((l) => l.key === key);
      const g = d.rungs[r];
      out[r] = { v: g.gain[ri][i], lo: g.lo[ri][i], hi: g.hi[ri][i] };
    }
  }
  return out;
}

/** The rungs where the model does not expect a lever to help, nationally: the reason a
 *  lever is "not supported" (a lever is supported only when every rung rises). */
export function failingRungs(d: ScenarioData, key: string): SRung[] {
  const w = leverWeight(d, key, d.regions.length - 1);
  return S_RUNGS.filter((r) => w[r] != null && w[r]!.v <= 0);
}

/** "ANC1+", "ANC1+ and ANC4+", "ANC1+, ANC4+ and ANC8+". */
export function rungList(rungs: string[], label: Record<string, string>): string {
  const n = rungs.map((r) => label[r] ?? r);
  return n.length < 2 ? n.join("") : `${n.slice(0, -1).join(", ")} and ${n[n.length - 1]}`;
}

export function eligibleShare(d: ScenarioData, key: string, ri: number): number {
  return key === EARLY ? d.early_visit.eligible[ri] : d.eligible[key]?.[ri] ?? 0;
}

// ------------------------------------------------------------ budget allocation

export interface Allocation {
  region: string;
  lever: string;
  coverage: number; // share of the eligible women reached
  cost: number;
  women: number; // additional women reaching the rung per year
}

/**
 * Spend a budget greedily, a tenth of a lever's eligible women at a time, on the
 * region and lever that buys the most additional women on the chosen rung per unit
 * of cost. Within a lever the women who gain most are reached first (the targeted
 * curves are concave), so taking the best next tenth each time is a sound greedy
 * choice. Levers are treated separately here; combined, their effects overlap a
 * little, so the total is an upper bound and the page says so.
 */
export function allocate(
  d: ScenarioData,
  rung: SRung,
  budget: number,
  unitCost: Record<string, number>,
  births: Record<string, number>,
  levers: string[],
): { rows: Allocation[]; spent: number; women: number } {
  const regions = d.regions.slice(0, -1);
  type Opt = { ri: number; key: string; step: number; cost: number; women: number };
  const next: Opt[] = [];
  const stepOf: Record<string, number> = {};
  const option = (ri: number, key: string, step: number): Opt | null => {
    if (step >= 10) return null;
    const curve = d.rungs[rung].targeted[key]?.[ri];
    if (!curve) return null;
    const b = births[regions[ri]] ?? 0;
    const elig = d.eligible[key][ri];
    const cost = 0.1 * elig * b * (unitCost[key] ?? 0);
    const women = (curve[step + 1] - curve[step]) * b;
    if (!(cost > 0) || !(women > 0)) return null;
    return { ri, key, step, cost, women };
  };
  for (let ri = 0; ri < regions.length; ri++)
    for (const key of levers) {
      const o = option(ri, key, 0);
      if (o) next.push(o);
    }
  let spent = 0;
  let women = 0;
  const taken = new Map<string, Allocation>();
  while (next.length) {
    next.sort((a, b) => b.women / b.cost - a.women / a.cost);
    const o = next.shift()!;
    if (spent + o.cost > budget) continue;
    spent += o.cost;
    women += o.women;
    const id = `${o.ri}|${o.key}`;
    stepOf[id] = o.step + 1;
    const a = taken.get(id) ?? { region: regions[o.ri], lever: o.key, coverage: 0, cost: 0, women: 0 };
    a.coverage = (o.step + 1) / 10;
    a.cost += o.cost;
    a.women += o.women;
    taken.set(id, a);
    const n = option(o.ri, o.key, o.step + 1);
    if (n) next.push(n);
  }
  return { rows: [...taken.values()].sort((a, b) => b.women - a.women), spent, women };
}

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

/** "healthpost:50,early:30" <-> { healthpost: 0.5, early: 0.3 } */
export function parseCoverage(s: string | null): Coverage {
  const out: Coverage = {};
  for (const part of (s ?? "").split(",")) {
    const [k, v] = part.split(":");
    const n = Number(v);
    if (k && Number.isFinite(n)) out[k] = Math.min(1, Math.max(0, n / 100));
  }
  return out;
}
export function formatCoverage(c: Coverage): string | undefined {
  const s = Object.entries(c)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => `${k}:${Math.round(v * 100)}`)
    .join(",");
  return s || undefined;
}
