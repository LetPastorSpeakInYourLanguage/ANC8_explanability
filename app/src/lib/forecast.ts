/**
 * Forecasting an uploaded ANC series in the browser, honestly.
 *
 * Six forecasters, from the simplest to exponential smoothing with seasonality. None
 * is assumed to be best: every one is run through a rolling-origin backtest on the
 * user's own series (fit on the first k periods, forecast the next h, move k on by
 * one, repeat), and the one with the smallest average error is used. Its bands come
 * from the same backtest: the spread of its real errors at each horizon, so a series
 * that is hard to forecast gets wide bands.
 *
 * Nothing leaves the browser.
 */

export interface Forecaster {
  key: string;
  label: string;
  /** smallest history it needs */
  minLength: (m: number) => number;
  /** forecasts for the next h periods from history y with season length m */
  fit: (y: number[], m: number) => (h: number) => number[];
}

const mean = (a: number[]) => a.reduce((s, v) => s + v, 0) / Math.max(a.length, 1);

const naive: Forecaster = {
  key: "naive", label: "Last value", minLength: () => 1,
  fit: (y) => (h) => Array(h).fill(y[y.length - 1]),
};

const seasonalNaive: Forecaster = {
  key: "snaive", label: "Same period last year", minLength: (m) => m + 1,
  fit: (y, m) => (h) => Array.from({ length: h }, (_, i) => y[y.length - m + (i % m)]),
};

const movingAverage: Forecaster = {
  key: "ma", label: "Average of the last year", minLength: (m) => Math.max(m, 2),
  fit: (y, m) => {
    const v = mean(y.slice(-Math.max(m, 2)));
    return (h) => Array(h).fill(v);
  },
};

const linear: Forecaster = {
  key: "linear", label: "Straight-line trend", minLength: () => 4,
  fit: (y) => {
    const n = y.length;
    const tm = (n - 1) / 2;
    const ym = mean(y);
    let sxy = 0, sxx = 0;
    y.forEach((v, t) => { sxy += (t - tm) * (v - ym); sxx += (t - tm) ** 2; });
    const b = sxx ? sxy / sxx : 0;
    const a = ym - b * tm;
    return (h) => Array.from({ length: h }, (_, i) => a + b * (n + i));
  },
};

/** Holt's linear exponential smoothing, damped, with parameters chosen on a grid. */
const holt: Forecaster = {
  key: "holt", label: "Smoothed trend (Holt)", minLength: () => 5,
  fit: (y) => {
    const grid = [0.1, 0.3, 0.5, 0.7, 0.9];
    let best = { sse: Infinity, l: y[0], b: 0, phi: 0.9 };
    for (const al of grid)
      for (const be of [0.05, 0.1, 0.2, 0.4])
        for (const phi of [0.8, 0.9, 0.98]) {
          let l = y[0], b = y[1] - y[0], sse = 0;
          for (let t = 1; t < y.length; t++) {
            const f = l + phi * b;
            sse += (y[t] - f) ** 2;
            const ln = al * y[t] + (1 - al) * (l + phi * b);
            b = be * (ln - l) + (1 - be) * phi * b;
            l = ln;
          }
          if (sse < best.sse) best = { sse, l, b, phi };
        }
    return (h) => {
      const out: number[] = [];
      let damp = 0;
      for (let i = 1; i <= h; i++) {
        damp += best.phi ** i;
        out.push(best.l + damp * best.b);
      }
      return out;
    };
  },
};

/** Holt-Winters additive seasonality (season m), parameters on a grid. */
const holtWinters: Forecaster = {
  key: "hw", label: "Trend and season (Holt-Winters)", minLength: (m) => 2 * m + 2,
  fit: (y, m) => {
    const first = mean(y.slice(0, m));
    const second = mean(y.slice(m, 2 * m));
    const s0 = y.slice(0, m).map((v) => v - first);
    const b0 = (second - first) / m;
    let best = { sse: Infinity, l: first, b: b0, s: s0.slice(), n: y.length };
    for (const al of [0.1, 0.3, 0.5, 0.7])
      for (const be of [0.01, 0.05, 0.15])
        for (const ga of [0.05, 0.2, 0.4]) {
          let l = first, b = b0;
          const s = s0.slice();
          let sse = 0;
          for (let t = m; t < y.length; t++) {
            const si = s[t % m];
            const f = l + b + si;
            sse += (y[t] - f) ** 2;
            const ln = al * (y[t] - si) + (1 - al) * (l + b);
            b = be * (ln - l) + (1 - be) * b;
            s[t % m] = ga * (y[t] - ln) + (1 - ga) * si;
            l = ln;
          }
          if (sse < best.sse) best = { sse, l, b, s, n: y.length };
        }
    return (h) => Array.from({ length: h }, (_, i) => best.l + (i + 1) * best.b + best.s[(best.n + i) % m]);
  },
};

export const FORECASTERS: Forecaster[] = [naive, seasonalNaive, movingAverage, linear, holt, holtWinters];

export interface Backtest {
  key: string;
  label: string;
  /** mean absolute error over all origins and horizons */
  mae: number;
  /** mean absolute error at each horizon 1..h */
  byHorizon: number[];
  /** root mean squared error at each horizon, for the bands */
  rmse: number[];
  origins: number;
}

/** Rolling-origin backtest of every forecaster that the series is long enough for. */
export function backtest(y: number[], m: number, h: number): Backtest[] {
  const out: Backtest[] = [];
  for (const f of FORECASTERS) {
    const start = Math.max(f.minLength(m), Math.ceil(y.length * 0.5));
    const errs: number[][] = Array.from({ length: h }, () => []);
    for (let k = start; k < y.length; k++) {
      const pred = f.fit(y.slice(0, k), m)(h);
      for (let i = 0; i < h && k + i < y.length; i++) errs[i].push(y[k + i] - pred[i]);
    }
    const all = errs.flat();
    if (all.length < 3) continue;
    const byHorizon = errs.map((e) => (e.length ? mean(e.map(Math.abs)) : NaN));
    const rmse = errs.map((e) => (e.length ? Math.sqrt(mean(e.map((v) => v * v))) : NaN));
    // Horizons the backtest could not reach borrow the last one, widened.
    for (let i = 1; i < h; i++) {
      if (!Number.isFinite(rmse[i])) rmse[i] = rmse[i - 1] * Math.sqrt((i + 1) / i);
      if (!Number.isFinite(byHorizon[i])) byHorizon[i] = byHorizon[i - 1];
    }
    out.push({ key: f.key, label: f.label, mae: mean(all.map(Math.abs)), byHorizon, rmse, origins: y.length - start });
  }
  return out.sort((a, b) => a.mae - b.mae);
}

export interface Forecast {
  model: Backtest;
  point: number[];
  lo80: number[];
  hi80: number[];
  lo95: number[];
  hi95: number[];
}

/** Forecast h periods with the backtest's winner, bands from its own errors. */
export function forecast(y: number[], m: number, h: number, ranking?: Backtest[]): Forecast | null {
  const bt = ranking ?? backtest(y, m, h);
  if (!bt.length) return null;
  const best = bt[0];
  const f = FORECASTERS.find((x) => x.key === best.key)!;
  const point = f.fit(y, m)(h).map((v) => Math.max(0, v));
  const band = (z: number, s: 1 | -1) => point.map((p, i) => Math.max(0, p + s * z * best.rmse[i]));
  return { model: best, point, lo80: band(1.2816, -1), hi80: band(1.2816, 1), lo95: band(1.96, -1), hi95: band(1.96, 1) };
}

// ------------------------------------------------------------------ parsing

export interface Row {
  period: string;
  org_unit: string;
  expected: number | null;
  anc1: number | null;
  anc4: number | null;
  anc8: number | null;
}

export interface Parsed {
  rows: Row[];
  periods: string[];
  units: string[];
  /** 12 for months, 4 for quarters */
  season: number;
  problems: string[];
}

const ALIASES: Record<string, keyof Row> = {
  period: "period", month: "period", quarter: "period", date: "period", periodname: "period",
  org_unit: "org_unit", orgunit: "org_unit", organisationunit: "org_unit", facility: "org_unit", region: "org_unit", woreda: "org_unit",
  expected_pregnancies: "expected", expected: "expected", denominator: "expected", pregnancies: "expected",
  anc1: "anc1", anc_1: "anc1", anc1st: "anc1", anc_first: "anc1",
  anc4: "anc4", anc_4: "anc4", anc4th: "anc4", anc4plus: "anc4",
  anc8: "anc8", anc_8: "anc8", anc8plus: "anc8", anc8th: "anc8",
};

/** Normalises "2023-01", "2023-1", "Jan 2023", "202301" to YYYY-MM and "2023Q1" to YYYYQn. */
export function normalisePeriod(raw: string): string | null {
  const s = raw.trim();
  let m = s.match(/^(\d{4})[- ]?Q([1-4])$/i);
  if (m) return `${m[1]}Q${m[2]}`;
  m = s.match(/^(\d{4})[-/]?(\d{1,2})$/);
  if (m && +m[2] >= 1 && +m[2] <= 12) return `${m[1]}-${m[2].padStart(2, "0")}`;
  const months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
  m = s.toLowerCase().match(/^([a-z]{3})[a-z]*[ -](\d{4})$/);
  if (m && months.includes(m[1])) return `${m[2]}-${String(months.indexOf(m[1]) + 1).padStart(2, "0")}`;
  return null;
}

/** A small CSV reader: quoted fields, commas or semicolons, a header row. */
export function parseCSV(text: string): string[][] {
  const delim = (text.split("\n")[0].match(/;/g)?.length ?? 0) > (text.split("\n")[0].match(/,/g)?.length ?? 0) ? ";" : ",";
  const rows: string[][] = [];
  let row: string[] = [], cell = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (c === '"') q = false;
      else cell += c;
    } else if (c === '"') q = true;
    else if (c === delim) { row.push(cell); cell = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(cell); cell = "";
      if (row.some((x) => x.trim() !== "")) rows.push(row);
      row = [];
    } else cell += c;
  }
  row.push(cell);
  if (row.some((x) => x.trim() !== "")) rows.push(row);
  return rows;
}

export function parseAggregate(text: string): Parsed {
  const table = parseCSV(text);
  const problems: string[] = [];
  if (table.length < 2) return { rows: [], periods: [], units: [], season: 12, problems: ["The file has no data rows."] };
  const header = table[0].map((h) => ALIASES[h.trim().toLowerCase().replace(/[^a-z0-9_]/g, "")] ?? null);
  if (!header.includes("period")) problems.push("No period column (expected 'period', 'month' or 'quarter').");
  if (!header.some((h) => h === "anc1" || h === "anc4" || h === "anc8")) problems.push("No ANC count columns (expected anc1, anc4 or anc8).");
  const rows: Row[] = [];
  let bad = 0;
  for (const r of table.slice(1)) {
    const o: Row = { period: "", org_unit: "All", expected: null, anc1: null, anc4: null, anc8: null };
    header.forEach((h, i) => {
      if (!h) return;
      const v = (r[i] ?? "").trim();
      if (h === "period") o.period = normalisePeriod(v) ?? "";
      else if (h === "org_unit") o.org_unit = v || "All";
      else {
        const n = Number(v.replace(/,/g, ""));
        (o as unknown as Record<string, number | null>)[h] = v === "" || !Number.isFinite(n) ? null : n;
      }
    });
    if (!o.period) { bad++; continue; }
    rows.push(o);
  }
  if (bad) problems.push(`${bad} row${bad === 1 ? "" : "s"} skipped: the period could not be read.`);
  const periods = [...new Set(rows.map((r) => r.period))].sort();
  const units = [...new Set(rows.map((r) => r.org_unit))].sort();
  const season = periods.some((p) => p.includes("Q")) ? 4 : 12;
  if (periods.some((p) => p.includes("Q")) && periods.some((p) => p.includes("-")))
    problems.push("The file mixes months and quarters; use one.");
  // gaps
  const all = fillPeriods(periods[0], periods[periods.length - 1]);
  const missing = all.filter((p) => !periods.includes(p));
  if (missing.length) problems.push(`${missing.length} period${missing.length === 1 ? " is" : "s are"} missing (e.g. ${missing[0]}); they are filled by interpolation.`);
  return { rows, periods: all, units, season, problems };
}

/** Every period from a to b inclusive. */
export function fillPeriods(a: string, b: string): string[] {
  if (!a || !b) return [];
  const out: string[] = [];
  if (a.includes("Q")) {
    let [y, q] = [Number(a.slice(0, 4)), Number(a.slice(5))];
    const [yb, qb] = [Number(b.slice(0, 4)), Number(b.slice(5))];
    while (y < yb || (y === yb && q <= qb)) { out.push(`${y}Q${q}`); q++; if (q > 4) { q = 1; y++; } }
  } else {
    let [y, m] = [Number(a.slice(0, 4)), Number(a.slice(5))];
    const [yb, mb] = [Number(b.slice(0, 4)), Number(b.slice(5))];
    while (y < yb || (y === yb && m <= mb)) { out.push(`${y}-${String(m).padStart(2, "0")}`); m++; if (m > 12) { m = 1; y++; } }
  }
  return out;
}

/** The period after the last one, n times. */
export function nextPeriods(last: string, n: number): string[] {
  const out: string[] = [];
  let p = last;
  for (let i = 0; i < n; i++) {
    if (p.includes("Q")) {
      let [y, q] = [Number(p.slice(0, 4)), Number(p.slice(5)) + 1];
      if (q > 4) { q = 1; y++; }
      p = `${y}Q${q}`;
    } else {
      let [y, m] = [Number(p.slice(0, 4)), Number(p.slice(5)) + 1];
      if (m > 12) { m = 1; y++; }
      p = `${y}-${String(m).padStart(2, "0")}`;
    }
    out.push(p);
  }
  return out;
}

/** Sum the selected units by period; linear interpolation fills gaps. */
export function aggregate(p: Parsed, units: string[] | null, key: "anc1" | "anc4" | "anc8" | "expected"): (number | null)[] {
  const sel = units && units.length ? new Set(units) : null;
  const by = new Map<string, { v: number; any: boolean }>();
  for (const r of p.rows) {
    if (sel && !sel.has(r.org_unit)) continue;
    const v = r[key];
    const cur = by.get(r.period) ?? { v: 0, any: false };
    if (v != null) { cur.v += v; cur.any = true; }
    by.set(r.period, cur);
  }
  const raw = p.periods.map((per) => (by.get(per)?.any ? by.get(per)!.v : null));
  return interpolate(raw);
}

export function interpolate(a: (number | null)[]): (number | null)[] {
  const out = a.slice();
  const idx = out.map((v, i) => (v == null ? -1 : i)).filter((i) => i >= 0);
  if (!idx.length) return out;
  for (let i = 0; i < out.length; i++) {
    if (out[i] != null) continue;
    const lo = [...idx].reverse().find((j) => j < i);
    const hi = idx.find((j) => j > i);
    if (lo == null || hi == null) continue;
    out[i] = (out[lo] as number) + ((out[hi] as number) - (out[lo] as number)) * ((i - lo) / (hi - lo));
  }
  return out;
}
