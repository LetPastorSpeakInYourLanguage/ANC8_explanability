/**
 * Browser-side scoring for the additive models: explainable boosting and
 * logistic regression.
 *
 * WHY THIS EXISTS
 * ---------------
 * The Predict tab needs a probability on every change of an answer. A round trip to
 * the Python function costs 100-300ms and can stall entirely on a cold start,
 * which makes exploration feel broken.
 *
 * The EBM is a generalised additive model: the prediction is an intercept plus
 * one score per predictor, each read out of a binned lookup table. Ported to
 * TypeScript that is a few hundred bytes of arithmetic over a 27 KB bundle, so
 * sliders respond instantly.
 *
 * It also buys something the boosters cannot offer. Because the model is
 * additive, the contribution of each predictor IS the number the model adds --
 * not a SHAP estimate of an attribution the model never literally computes.
 * The bars in the UI sum exactly to the log-odds behind the probability.
 *
 * FIDELITY
 * --------
 * scripts/check_ts_parity.py scores every held-out woman through this file
 * (via node) and through app/api/_lib/scorer.py, and fails if they disagree by
 * more than 1e-9. A re-implementation that silently drifts from the fitted
 * model would be worse than no re-implementation at all.
 */

export type EbmBins = {
  kind: "continuous" | "nominal";
  cuts?: number[];
  mapping?: Record<string, number>;
};

/** One feature's term: a step function over its bins. */
export type EbmSingle = EbmBins & { feature: number; scores: number[] };

/** A pair term: a table over two features' bins. */
export type EbmPair = { kind: "pair"; features: [number, number]; dims: [EbmBins, EbmBins]; scores: number[][] };

export type EbmTerm = EbmSingle | EbmPair;

export type EbmModel = {
  kind: "ebm";
  intercept: number;
  terms: EbmTerm[];
  preprocessor: string;
  threshold?: number | null;
};

export type Preprocessor = {
  numeric: string[];
  binary: string[];
  categorical: string[];
  extra: string[];
  numeric_impute: Record<string, number>;
  binary_impute: Record<string, string>;
  categorical_impute: Record<string, string>;
  extra_impute: Record<string, number>;
  categories: Record<string, string[]>;
  numeric_scale: { mean: number[]; scale: number[] } | null;
  encoding: "onehot" | "ordinal";
};

export type LogisticModel = {
  kind: "logistic";
  coef: number[];
  intercept: number;
  preprocessor: string;
  threshold?: number | null;
};

/** A random forest: sklearn trees, each leaf holding the class-1 probability. */
export type ForestModel = {
  kind: "forest";
  trees: { children_left: number[]; children_right: number[]; feature: number[]; threshold: number[]; value: number[] }[];
  preprocessor: string;
  threshold?: number | null;
};

/** XGBoost: trees whose leaves add to a log-odds score. */
export type XgbModel = {
  kind: "xgboost";
  trees: { left: number[]; right: number[]; split_feature: number[]; split_condition: number[];
           default_left: number[]; leaf_value: number[] }[];
  base_score: number;
  zero_is_missing?: boolean;
  preprocessor: string;
  threshold?: number | null;
};

export type Bundle = {
  generation?: string;
  predictors?: string[];
  champion?: string;
  preprocessors: Record<string, Preprocessor>;
  models: Record<string, EbmModel | LogisticModel | ForestModel | XgbModel>;
};

export type Answers = Record<string, string | number | null | undefined>;

export type Contribution = {
  predictor: string;
  contribution: number;
};

export type Scored = {
  probability: number;
  logOdds: number;
  intercept: number;
  threshold?: number | null;
  contributions: Contribution[];
};

const sigmoid = (z: number) => 1 / (1 + Math.exp(-z));

/**
 * Build the model's feature vector from raw answers.
 *
 * Mirrors the fitted ColumnTransformer block for block, in the order it emits
 * them: numeric (median-imputed, optionally scaled), binary (fixed 0/1 order,
 * NOT scaled), categorical (one-hot or ordinal), then any trailing block.
 */
export function applyPreprocessor(spec: Preprocessor, row: Answers): number[] {
  const out: number[] = [];

  const asNumber = (v: unknown, fallback: number): number => {
    if (v === null || v === undefined || v === "") return fallback;
    const n = typeof v === "number" ? v : Number(v);
    return Number.isFinite(n) ? n : fallback;
  };

  // numeric
  const numericBlock = spec.numeric.map((col) =>
    asNumber(row[col], spec.numeric_impute[col] ?? 0)
  );
  if (spec.numeric_scale) {
    const { mean, scale } = spec.numeric_scale;
    numericBlock.forEach((v, i) => out.push((v - mean[i]) / scale[i]));
  } else {
    numericBlock.forEach((v) => out.push(v));
  }

  // binary — a fixed category order used purely as a text -> 0/1 converter
  for (const col of spec.binary ?? []) {
    const cats = spec.categories[col] ?? [];
    const raw = row[col];
    const v = raw === null || raw === undefined || raw === ""
      ? spec.binary_impute[col]
      : String(raw);
    const idx = cats.indexOf(v);
    out.push(idx >= 0 ? idx : 0);
  }

  // categorical
  if (spec.encoding === "onehot") {
    for (const col of spec.categorical) {
      const cats = spec.categories[col] ?? [];
      const raw = row[col];
      const v = raw === null || raw === undefined || raw === ""
        ? spec.categorical_impute[col]
        : String(raw);
      const hit = cats.indexOf(v);
      // An unseen category yields an all-zero block, matching
      // OneHotEncoder(handle_unknown="ignore").
      cats.forEach((_, i) => out.push(i === hit ? 1 : 0));
    }
  } else {
    for (const col of spec.categorical) {
      const cats = spec.categories[col] ?? [];
      const raw = row[col];
      const v = raw === null || raw === undefined || raw === ""
        ? spec.categorical_impute[col]
        : String(raw);
      const idx = cats.indexOf(v);
      out.push(idx >= 0 ? idx : -1);
    }
  }

  // trailing block (e.g. the ANC-entry models' separate early_anc transformer)
  for (const col of spec.extra ?? []) {
    out.push(asNumber(row[col], spec.extra_impute[col] ?? 0));
  }

  return out;
}

/** The predictor behind each column of applyPreprocessor's output. */
export function encodedNames(spec: Preprocessor): string[] {
  const out: string[] = [...spec.numeric, ...(spec.binary ?? [])];
  for (const col of spec.categorical) {
    const width = spec.encoding === "onehot" ? (spec.categories[col] ?? []).length : 1;
    for (let i = 0; i < width; i++) out.push(col);
  }
  out.push(...(spec.extra ?? []));
  return out;
}

/**
 * The log-odds contribution of one additive term.
 *
 * Bin index convention, matching interpret's own scoring:
 *   0            missing
 *   1..n         the n+1 intervals defined by n cut points
 *   last         unseen / out of range
 */
function binOf(spec: EbmBins, v: number): number {
  if (spec.kind === "nominal") {
    const key = Number.isInteger(v) ? String(v) : String(v);
    return spec.mapping?.[key] ?? 0;
  }
  if (!Number.isFinite(v)) return 0;
  // searchsorted(cuts, v, side="right") + 1
  const cuts = spec.cuts ?? [];
  let lo = 0;
  let hi = cuts.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (v < cuts[mid]) hi = mid;
    else lo = mid + 1;
  }
  return lo + 1;
}

function termContribution(term: EbmTerm, x: number[]): number {
  if (term.kind === "pair") {
    const i = Math.min(binOf(term.dims[0], x[term.features[0]]), term.scores.length - 1);
    const row = term.scores[i];
    return row[Math.min(binOf(term.dims[1], x[term.features[1]]), row.length - 1)];
  }
  return term.scores[Math.min(binOf(term, x[term.feature]), term.scores.length - 1)];
}

/**
 * Score one woman, returning the probability and the exact decomposition.
 *
 * `contributions` are on the log-odds scale, positive meaning the value pushes
 * towards attaining the outcome. They sum, with the intercept, to `logOdds` --
 * which is what makes this an explanation rather than an estimate of one.
 */
/*
 * The tree models, as api/_lib/scorer.py walks them (the export gate checks that
 * scorer against the fitted models to 1e-9, and scripts/check_ts_parity.py checks
 * this one against it). sklearn compares a float32 copy of the input with its split
 * point, `<=`; XGBoost compares float32 with float32, strictly `<`, and sends a
 * missing value the way `default_left` says. Math.fround is the float32 rounding.
 */
function walkForest(t: ForestModel["trees"][number], x: number[]): number {
  let node = 0;
  while (t.children_left[node] !== -1) {
    node = Math.fround(x[t.feature[node]]) <= t.threshold[node] ? t.children_left[node] : t.children_right[node];
  }
  return t.value[node];
}

function walkXgb(t: XgbModel["trees"][number], x: number[], zeroIsMissing: boolean): number {
  let node = 0;
  for (;;) {
    const left = t.left[node];
    if (left === -1) return t.leaf_value[node];
    const v = Math.fround(x[t.split_feature[node]]);
    const missing = !Number.isFinite(v) || (zeroIsMissing && v === 0);
    if (missing) node = t.default_left[node] ? left : t.right[node];
    else node = v < Math.fround(t.split_condition[node]) ? left : t.right[node];
  }
}

export function score(bundle: Bundle, modelName: string, row: Answers): Scored {
  const model = bundle.models[modelName];
  if (!model) throw new Error(`model not in bundle: ${modelName}`);

  const spec = bundle.preprocessors[model.preprocessor];
  const x = applyPreprocessor(spec, row);

  // The tree models have no exact split of the score into answers: no bars.
  if (model.kind === "forest") {
    const p = model.trees.reduce((a, t) => a + walkForest(t, x), 0) / model.trees.length;
    return { probability: p, logOdds: Math.log(p / (1 - p)), intercept: 0, threshold: model.threshold ?? null, contributions: [] };
  }
  if (model.kind === "xgboost") {
    const z = model.trees.reduce((a, t) => a + walkXgb(t, x, !!model.zero_is_missing), 0) + model.base_score;
    return { probability: sigmoid(z), logOdds: z, intercept: 0, threshold: model.threshold ?? null, contributions: [] };
  }
  const contributions: Contribution[] = [];
  let total = model.intercept;

  if (model.kind === "logistic") {
    // Also additive: coefficient times encoded value, summed back to the
    // predictor each encoded column came from (all of a one-hot block).
    const source = encodedNames(spec);
    const by = new Map<string, number>();
    model.coef.forEach((c, i) => {
      const v = c * x[i];
      total += v;
      by.set(source[i], (by.get(source[i]) ?? 0) + v);
    });
    by.forEach((contribution, predictor) => contributions.push({ predictor, contribution }));
  } else if (model.kind === "ebm") {
    const names = [
      ...spec.numeric,
      ...(spec.binary ?? []),
      ...spec.categorical,
      ...(spec.extra ?? []),
    ];
    // A pair term's contribution is split equally between its two predictors, so the
    // bars still sum exactly to the log-odds.
    const by = new Map<string, number>();
    for (const term of model.terms) {
      const c = termContribution(term, x);
      total += c;
      const feats = term.kind === "pair" ? term.features : [term.feature];
      for (const f of feats) {
        const name = names[f] ?? `feature_${f}`;
        by.set(name, (by.get(name) ?? 0) + c / feats.length);
      }
    }
    by.forEach((contribution, predictor) => contributions.push({ predictor, contribution }));
  } else {
    throw new Error("browser scoring supports additive models only");
  }

  contributions.sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution));

  return {
    probability: sigmoid(total),
    logOdds: total,
    intercept: model.intercept,
    threshold: model.threshold ?? null,
    contributions,
  };
}

/**
 * The fitted response curve for one predictor: what the model adds at each
 * value, holding everything else aside.
 *
 * This is what makes a slider meaningful rather than decorative -- the user can
 * see the shape the model learned, not just the endpoint they landed on.
 */
export function shapeFunction(
  bundle: Bundle,
  modelName: string,
  predictor: string
): { values: (number | string)[]; scores: number[]; kind: string } | null {
  const model = bundle.models[modelName];
  if (!model || model.kind !== "ebm") return null;
  const spec = bundle.preprocessors[model.preprocessor];
  const names = [
    ...spec.numeric,
    ...(spec.binary ?? []),
    ...spec.categorical,
    ...(spec.extra ?? []),
  ];
  const f = names.indexOf(predictor);
  if (f < 0) return null;

  const term = model.terms.find((t): t is EbmSingle => t.kind !== "pair" && t.feature === f);
  if (!term) return null;

  if (term.kind === "nominal") {
    const mapping = term.mapping ?? {};
    const values = Object.keys(mapping);
    return {
      values,
      scores: values.map((v) => term.scores[Math.min(mapping[v], term.scores.length - 1)]),
      kind: "nominal",
    };
  }

  const cuts = term.cuts ?? [];
  // Interior bins only: index 0 is the missing bin and the last is "unseen",
  // neither of which corresponds to a value a user can choose.
  return {
    values: cuts,
    scores: cuts.map((_, i) => term.scores[Math.min(i + 1, term.scores.length - 1)]),
    kind: "continuous",
  };
}
