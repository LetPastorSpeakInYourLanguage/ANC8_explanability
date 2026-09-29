/**
 * The first-visit screener (scripts/run_clinic_screener.py) scored in the browser.
 *
 * A logistic regression on a dozen facts a clinic records at a woman's first visit.
 * Numbers are median-filled and standardised with the development women's values;
 * categories are one-hot against the first level. A category the model has not seen
 * scores as the reference level, as in Python. A parity check in run_tests.py runs
 * this file on held-out women and compares with the fitted model.
 */

export interface ScreenerField {
  key: string;
  kind: "numeric" | "categorical";
  question: string;
  levels?: string[];
  median?: number;
  mean?: number;
  sd?: number;
}

export interface ScreenerRung {
  intercept: number;
  coefficients: Record<string, number>;
  heldout: { AP: number; AUROC: number; calibration_slope: number; prevalence: number };
  reference: { set: string; n_predictors: number; AP: number; AUROC: number }[];
}

export interface Screener {
  fields: ScreenerField[];
  assets: string[];
  rungs: Record<"anc4" | "anc8", ScreenerRung>;
  n_development: number;
  n_heldout: number;
}

export type Record_ = Record<string, string | number | null | undefined>;

/** Log-odds contribution of each field, and the probability. */
export function score(s: Screener, rung: "anc4" | "anc8", rec: Record_): { p: number; parts: { key: string; value: number }[] } {
  const m = s.rungs[rung];
  let z = m.intercept;
  const parts: { key: string; value: number }[] = [];
  for (const f of s.fields) {
    let c = 0;
    const raw = rec[f.key];
    if (f.kind === "numeric") {
      const n = raw == null || raw === "" ? NaN : Number(raw);
      const v = Number.isFinite(n) ? n : (f.median as number);
      c = ((v - (f.mean as number)) / (f.sd as number)) * (m.coefficients[f.key] ?? 0);
    } else {
      const v = raw == null ? "" : String(raw);
      c = m.coefficients[`${f.key}=${v}`] ?? 0;
    }
    z += c;
    parts.push({ key: f.key, value: c });
  }
  return { p: 1 / (1 + Math.exp(-z)), parts };
}
