/**
 * The conflict simulator's engine: the model scripts/run_war_model.py fitted on the
 * Tigray war, run forward for any region, month by month, in the browser.
 *
 *   disruption  each month carries a level. While fighting runs it is 1 (a siege,
 *               as in Tigray) or it decays as services adapt (as in Amhara). After
 *               a ceasefire it decays with the recovery lag tau, or stays where it
 *               was if services are not restored.
 *   exposure    a birth's exposure is the average disruption over the nine months of
 *               its pregnancy, so the effect arrives and fades with the pregnancies
 *               that overlap the conflict, not on the day it starts.
 *   effect      each rung's log-odds move by intensity x shock x exposure, from the
 *               region's own current level. The shock depends on the recovery lag
 *               (the data cannot separate a deep shock with slow recovery from a
 *               shallower one with fast recovery), so each lag carries its own.
 *
 * Bands come from the bootstrap: each resample's shocks, rescaled to the chosen lag.
 * It is association-based and transfers Tigray's disruption to another region; the
 * page says so next to every number.
 */

export type WarRung = "anc1" | "anc4" | "anc8";
export const WAR_RUNGS: WarRung[] = ["anc1", "anc4", "anc8"];

export interface WarData {
  method: string;
  fit: {
    n: number;
    n_tigray: number;
    regions: string[];
    tau: number;
    tau_supported: [number, number];
    shock: Record<WarRung, { log_odds: number; lo: number; hi: number }>;
    profile: ({ tau: number; delta_ll: number } & Record<WarRung, number>)[];
  };
  draws: Record<WarRung, number>[];
  fitted_tigray: ({ half: string; exposure: number } & Record<string, number | string>)[];
  did_check: Record<WarRung, { model: number; did: number; lo: number; hi: number }>;
  backtest: {
    n_baseline: number;
    n_exposed: number;
    intensity_fit: number;
    intensity_lo: number;
    intensity_hi: number;
    kappa_fit: number | null;
    kappa_interval: [number, number];
    rows: ({ half: string; n: number; exposure: number } & Record<string, number | string>)[];
  };
  observed: Record<string, ({ half: string; n: number } & Record<string, number | string>)[]>;
  windows: { window: string; regions: string; start: string; end: string; note: string; source: string }[];
  bootstrap_resamples: number;
}

export interface Scenario {
  /** quarter (0-based) in which the fighting starts */
  startQ: number;
  /** quarters of fighting */
  durationQ: number;
  /** 1 = the Tigray war */
  intensity: number;
  /** services cut until a ceasefire, or services adapting while fighting continues */
  pattern: "siege" | "adapt";
  /** after the ceasefire, services come back (with lag tau) or stay down */
  restored: boolean;
  /** recovery lag after the ceasefire, months */
  tau: number;
  /** adaptation time while fighting continues, months (the Amhara fit) */
  kappa: number;
  horizonQ: number;
}

const expit = (x: number) => 1 / (1 + Math.exp(-x));
const logit = (p: number) => Math.log(p / (1 - p));
const PREG = 9;

/** Disruption level for each month of the horizon. */
export function disruption(s: Scenario): number[] {
  const n = s.horizonQ * 3;
  const start = s.startQ * 3;
  const end = (s.startQ + s.durationQ) * 3 - 1;
  const out: number[] = [];
  const inside = (m: number) => (s.pattern === "adapt" ? Math.exp(-(m - start) / Math.max(s.kappa, 0.1)) : 1);
  const atEnd = inside(end);
  for (let m = 0; m < n; m++) {
    if (m < start) out.push(0);
    else if (m <= end) out.push(inside(m));
    else if (!s.restored) out.push(atEnd);
    else out.push(s.tau > 0 ? atEnd * Math.exp(-(m - end) / s.tau) : 0);
  }
  return out;
}

/** Average exposure of births in each quarter: each birth averages its nine months. */
export function quarterExposure(s: Scenario): number[] {
  const d = disruption(s);
  const at = (m: number) => (m < 0 || m >= d.length ? 0 : d[m]);
  const out: number[] = [];
  for (let q = 0; q < s.horizonQ; q++) {
    let tot = 0;
    for (let b = q * 3; b < q * 3 + 3; b++) {
      let e = 0;
      for (let k = 0; k < PREG; k++) e += at(b - k);
      tot += e / PREG;
    }
    out.push(tot / 3);
  }
  return out;
}

/** The shock for each rung at recovery lag tau, interpolated along the profile. */
export function shockAt(w: WarData, tau: number): Record<WarRung, number> {
  const pr = [...w.fit.profile].sort((a, b) => a.tau - b.tau);
  const i = pr.findIndex((p) => p.tau >= tau);
  if (i <= 0) return { anc1: pr[Math.max(i, 0)].anc1, anc4: pr[Math.max(i, 0)].anc4, anc8: pr[Math.max(i, 0)].anc8 };
  const a = pr[i - 1];
  const b = pr[i];
  const t = (tau - a.tau) / (b.tau - a.tau || 1);
  return {
    anc1: a.anc1 + t * (b.anc1 - a.anc1),
    anc4: a.anc4 + t * (b.anc4 - a.anc4),
    anc8: a.anc8 + t * (b.anc8 - a.anc8),
  };
}

function ladder(p: Record<WarRung, number>): Record<WarRung, number> {
  const anc1 = p.anc1;
  const anc4 = Math.min(p.anc4, anc1);
  return { anc1, anc4, anc8: Math.min(p.anc8, anc4) };
}

export interface QuarterResult {
  q: number;
  exposure: number;
  /** point estimate per rung */
  p: Record<WarRung, number>;
  lo: Record<WarRung, number>;
  hi: Record<WarRung, number>;
}

/** One region's path through the scenario. */
export function simulate(w: WarData, s: Scenario, base: Record<WarRung, number>): QuarterResult[] {
  const x = quarterExposure(s);
  const shock = shockAt(w, s.tau);
  const point = w.fit.shock;
  // each bootstrap resample's shocks, rescaled from the fitted lag to the chosen one
  const draws = w.draws.map((d) => ({
    anc1: shock.anc1 * (d.anc1 / point.anc1.log_odds),
    anc4: shock.anc4 * (d.anc4 / point.anc4.log_odds),
    anc8: shock.anc8 * (d.anc8 / point.anc8.log_odds),
  }));
  const L = { anc1: logit(clamp(base.anc1)), anc4: logit(clamp(base.anc4)), anc8: logit(clamp(base.anc8)) };
  const at = (sh: Record<WarRung, number>, e: number) =>
    ladder({
      anc1: expit(L.anc1 + s.intensity * sh.anc1 * e),
      anc4: expit(L.anc4 + s.intensity * sh.anc4 * e),
      anc8: expit(L.anc8 + s.intensity * sh.anc8 * e),
    });
  return x.map((e, q) => {
    const p = at(shock, e);
    const sims = draws.map((d) => at(d, e));
    const pc = (r: WarRung, f: number) => percentile(sims.map((v) => v[r]), f);
    return {
      q,
      exposure: e,
      p,
      lo: { anc1: pc("anc1", 0.025), anc4: pc("anc4", 0.025), anc8: pc("anc8", 0.025) },
      hi: { anc1: pc("anc1", 0.975), anc4: pc("anc4", 0.975), anc8: pc("anc8", 0.975) },
    };
  });
}

export interface Summary {
  /** additional women per rung who do not reach it, over the horizon */
  lost: Record<WarRung, number>;
  lostLo: Record<WarRung, number>;
  lostHi: Record<WarRung, number>;
  /** deepest drop, in shares, and when */
  peak: Record<WarRung, { drop: number; q: number }>;
  /** quarters after the ceasefire until every rung is within one point of its level */
  recoverQ: number | null;
}

export function summarise(path: QuarterResult[], base: Record<WarRung, number>, birthsPerYear: number, s: Scenario): Summary {
  const perQ = birthsPerYear / 4;
  const lost = { anc1: 0, anc4: 0, anc8: 0 };
  const lostLo = { anc1: 0, anc4: 0, anc8: 0 };
  const lostHi = { anc1: 0, anc4: 0, anc8: 0 };
  const peak = { anc1: { drop: 0, q: 0 }, anc4: { drop: 0, q: 0 }, anc8: { drop: 0, q: 0 } };
  for (const r of path) {
    for (const k of WAR_RUNGS) {
      const drop = base[k] - r.p[k];
      lost[k] += perQ * drop;
      // the band's upper probability is the smaller loss
      lostLo[k] += perQ * (base[k] - r.hi[k]);
      lostHi[k] += perQ * (base[k] - r.lo[k]);
      if (drop > peak[k].drop) peak[k] = { drop, q: r.q };
    }
  }
  const endQ = s.startQ + s.durationQ;
  let recoverQ: number | null = null;
  for (const r of path) {
    if (r.q < endQ) continue;
    if (WAR_RUNGS.every((k) => base[k] - r.p[k] < 0.01)) {
      recoverQ = r.q - endQ + 1;
      break;
    }
  }
  return { lost, lostLo, lostHi, peak, recoverQ };
}

const clamp = (p: number) => Math.min(0.999, Math.max(0.001, p));

function percentile(v: number[], f: number): number {
  const s = [...v].sort((a, b) => a - b);
  const pos = f * (s.length - 1);
  const lo = Math.floor(pos);
  return s[lo] + (s[Math.min(lo + 1, s.length - 1)] - s[lo]) * (pos - lo);
}
