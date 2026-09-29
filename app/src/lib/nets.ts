/**
 * The two networks (src/anc8/deep.py) run in the browser, from their exported weights.
 *
 *   ladder transformer   one token per predictor, a [CLS] token, two pre-norm
 *                        attention blocks, and a head that predicts ANC1+, then
 *                        ANC4+ given ANC1+, then ANC8+ given ANC4+, so the three
 *                        probabilities can never cross.
 *   contact sequence     the same encoder (one block), then a GRU decoder that
 *                        steps through contacts 1..9 and, at each step, attends to
 *                        the predictor tokens and outputs the chance of going on to
 *                        the next contact. The product of those is the whole
 *                        distribution of the contact count.
 *
 * A parity check in scripts/run_tests.py runs this file on the held-out women and
 * compares with PyTorch. The weights are stored to six decimals, so agreement is to
 * about 1e-5, not to the last bit.
 */

type M = number[][];
type V = number[];

export interface Prep {
  numeric: string[];
  categorical: string[];
  med: Record<string, number>;
  mean: Record<string, number>;
  std: Record<string, number>;
  levels: Record<string, Record<string, number>>;
}

export interface NetBundle {
  prep: Prep;
  state: Record<string, unknown>;
  arch: { d: number; heads: number; ffn: number; layers: number; steps: number };
}

export interface Nets {
  ladder: NetBundle;
  sequence: NetBundle;
}

/** A woman as raw values: numbers (or null when unknown) and category labels as
 *  strings, written the way Python's str() writes them ("2.0", "Rural"). */
export type RawRecord = Record<string, number | string | null | undefined>;

// ------------------------------------------------------------------ small algebra

const matvec = (W: M, x: V, b?: V): V => W.map((row, i) => row.reduce((s, w, j) => s + w * x[j], b ? b[i] : 0));
const add = (a: V, b: V): V => a.map((v, i) => v + b[i]);
const sigmoid = (x: number) => 1 / (1 + Math.exp(-x));

function layerNorm(x: V, w: V, b: V, eps = 1e-5): V {
  const n = x.length;
  const mu = x.reduce((s, v) => s + v, 0) / n;
  const va = x.reduce((s, v) => s + (v - mu) ** 2, 0) / n;
  const inv = 1 / Math.sqrt(va + eps);
  return x.map((v, i) => (v - mu) * inv * w[i] + b[i]);
}

/** erf to about 1e-12 (series for small x, continued fraction beyond). */
function erf(x: number): number {
  const s = Math.sign(x);
  const a = Math.abs(x);
  if (a < 2.5) {
    let sum = a, term = a;
    for (let n = 1; n < 60; n++) {
      term *= (-a * a) / n;
      const t = term / (2 * n + 1);
      sum += t;
      if (Math.abs(t) < 1e-17) break;
    }
    return (s * 2 * sum) / Math.sqrt(Math.PI);
  }
  // erfc continued fraction (Lentz)
  let f = a, C = a, D = 0;
  for (let n = 1; n < 100; n++) {
    const an = n / 2;
    D = a + an * D; D = D === 0 ? 1e-300 : 1 / D;
    C = a + an / C; C = C === 0 ? 1e-300 : C;
    const delta = C * D;
    f *= delta;
    if (Math.abs(delta - 1) < 1e-16) break;
  }
  const erfc = Math.exp(-a * a) / (f * Math.sqrt(Math.PI));
  return s * (1 - erfc);
}
const gelu = (x: number) => 0.5 * x * (1 + erf(x / Math.SQRT2));

function softmax(v: V): V {
  const m = Math.max(...v);
  const e = v.map((x) => Math.exp(x - m));
  const s = e.reduce((a, b) => a + b, 0);
  return e.map((x) => x / s);
}

// ------------------------------------------------------------------ layers

function S(bundle: NetBundle, key: string) {
  const v = bundle.state[key];
  if (v === undefined) throw new Error(`weight ${key} missing`);
  return v as M & V;
}

/** Predictor tokens from a raw record: the Prep transform, then the tokenizer. */
function tokens(b: NetBundle, rec: RawRecord): M {
  const { prep } = b;
  const w = S(b, "tok.w") as M, bb = S(b, "tok.b") as M, miss = S(b, "tok.miss") as M;
  const out: M = [];
  prep.numeric.forEach((c, j) => {
    const raw = rec[c];
    const n = raw == null || raw === "" ? NaN : Number(raw);
    const m = Number.isFinite(n) ? 0 : 1;
    const x = ((Number.isFinite(n) ? n : prep.med[c]) - prep.mean[c]) / prep.std[c];
    out.push(w[j].map((wj, k) => x * wj + bb[j][k] + m * miss[j][k]));
  });
  prep.categorical.forEach((c, j) => {
    const raw = rec[c];
    const key = raw == null ? "__na__" : String(raw);
    const code = prep.levels[c][key] ?? 0;
    out.push((S(b, `tok.emb.${j}.weight`) as M)[code].slice());
  });
  return out;
}

/** One pre-norm attention block; returns the new tokens and the head-averaged
 *  attention matrix (queries x keys). */
function block(b: NetBundle, i: number, x: M): { x: M; att: M } {
  const d = b.arch.d, H = b.arch.heads, dh = d / H;
  const p = `blocks.${i}.`;
  const h = x.map((t) => layerNorm(t, S(b, p + "n1.weight"), S(b, p + "n1.bias")));
  const Win = S(b, p + "att.in_proj_weight") as M, bin = S(b, p + "att.in_proj_bias") as V;
  const qkv = h.map((t) => matvec(Win, t, bin));
  const Q = qkv.map((r) => r.slice(0, d)), K = qkv.map((r) => r.slice(d, 2 * d)), Vv = qkv.map((r) => r.slice(2 * d));
  const n = x.length;
  const att: M = Array.from({ length: n }, () => Array(n).fill(0));
  const heads: M = Array.from({ length: n }, () => Array(d).fill(0));
  const scale = 1 / Math.sqrt(dh);
  for (let hd = 0; hd < H; hd++) {
    const o = hd * dh;
    for (let qi = 0; qi < n; qi++) {
      const sc = K.map((k) => {
        let s = 0;
        for (let t = 0; t < dh; t++) s += Q[qi][o + t] * k[o + t];
        return s * scale;
      });
      const a = softmax(sc);
      for (let ki = 0; ki < n; ki++) {
        att[qi][ki] += a[ki] / H;
        for (let t = 0; t < dh; t++) heads[qi][o + t] += a[ki] * Vv[ki][o + t];
      }
    }
  }
  const Wo = S(b, p + "att.out_proj.weight") as M, bo = S(b, p + "att.out_proj.bias") as V;
  let y = x.map((t, r) => add(t, matvec(Wo, heads[r], bo)));
  const W1 = S(b, p + "ff.0.weight") as M, b1 = S(b, p + "ff.0.bias") as V;
  const W2 = S(b, p + "ff.3.weight") as M, b2 = S(b, p + "ff.3.bias") as V;
  y = y.map((t) => {
    const u = layerNorm(t, S(b, p + "n2.weight"), S(b, p + "n2.bias"));
    const f = matvec(W2, matvec(W1, u, b1).map(gelu), b2);
    return add(t, f);
  });
  return { x: y, att };
}

function encode(b: NetBundle, rec: RawRecord): { x: M; clsAtt: V[] } {
  let x: M = [(S(b, "cls") as unknown as M[])[0][0].slice(), ...tokens(b, rec)];
  const clsAtt: V[] = [];
  for (let i = 0; i < b.arch.layers; i++) {
    const r = block(b, i, x);
    x = r.x;
    clsAtt.push(r.att[0].slice(1));
  }
  return { x, clsAtt };
}

export interface LadderResult {
  p: [number, number, number];
  /** what [CLS] attends to, per predictor (averaged over layers), in prep order:
   *  numeric predictors first, then categorical */
  attention: V;
}

export function ladder(n: Nets, rec: RawRecord): LadderResult {
  const b = n.ladder;
  const { x, clsAtt } = encode(b, rec);
  const h = layerNorm(x[0], S(b, "norm.weight"), S(b, "norm.bias"));
  const a = matvec(S(b, "head.weight") as M, h, S(b, "head.bias") as V).map(sigmoid);
  const p1 = a[0], p4 = p1 * a[1], p8 = p4 * a[2];
  const attention = clsAtt[0].map((_, j) => clsAtt.reduce((s, l) => s + l[j], 0) / clsAtt.length);
  return { p: [p1, p4, p8], attention };
}

export interface SequenceResult {
  /** P(reach contact k+1 | reached k), k = 0..8 */
  cont: V;
  /** P(count >= k), k = 0..9 */
  survival: V;
  /** P(count = k), k = 0..8, and the last entry is 9 or more */
  distribution: V;
  p: [number, number, number];
  /** attention over predictors at each decoder step (9 x predictors) */
  attention: M;
}

export function sequence(n: Nets, rec: RawRecord): SequenceResult {
  const b = n.sequence;
  const { x: enc } = encode(b, rec);
  const x = enc.map((t) => layerNorm(t, S(b, "norm.weight"), S(b, "norm.bias")));
  let h = x[0];
  const mem = x.slice(1);
  const keys = mem.map((t) => matvec(S(b, "k.weight") as M, t, S(b, "k.bias") as V));
  const scale = 1 / Math.sqrt(b.arch.d);
  const Wih = S(b, "gru.weight_ih") as M, Whh = S(b, "gru.weight_hh") as M;
  const bih = S(b, "gru.bias_ih") as V, bhh = S(b, "gru.bias_hh") as V;
  const d = b.arch.d;
  let ctx: V = Array(d).fill(0);
  const cont: V = [];
  const attention: M = [];
  for (let k = 0; k < b.arch.steps; k++) {
    const e = (S(b, "step_emb.weight") as M)[k];
    const inp = [...e, ...ctx];
    const gi = matvec(Wih, inp, bih), gh = matvec(Whh, h, bhh);
    const r = gi.slice(0, d).map((v, i) => sigmoid(v + gh[i]));
    const z = gi.slice(d, 2 * d).map((v, i) => sigmoid(v + gh[d + i]));
    const nn = gi.slice(2 * d).map((v, i) => Math.tanh(v + r[i] * gh[2 * d + i]));
    h = nn.map((v, i) => (1 - z[i]) * v + z[i] * h[i]);
    const q = matvec(S(b, "q.weight") as M, h, S(b, "q.bias") as V);
    const a = softmax(keys.map((kk) => kk.reduce((s, v, i) => s + v * q[i], 0) * scale));
    ctx = Array(d).fill(0);
    a.forEach((w, j) => { for (let t = 0; t < d; t++) ctx[t] += w * mem[j][t]; });
    const o1 = matvec(S(b, "out.0.weight") as M, [...h, ...ctx], S(b, "out.0.bias") as V).map(gelu);
    const z2 = matvec(S(b, "out.2.weight") as M, o1, S(b, "out.2.bias") as V)[0];
    cont.push(sigmoid(z2));
    attention.push(a);
  }
  const survival = [1];
  for (const c of cont) survival.push(survival[survival.length - 1] * c);
  const distribution = survival.slice(0, -1).map((s, k) => s - survival[k + 1]);
  distribution.push(survival[survival.length - 1]);
  return { cont, survival, distribution, p: [survival[1], survival[4], survival[8]], attention };
}

/** The predictors in token order, to label attention. */
export function tokenNames(n: Nets): string[] {
  return [...n.ladder.prep.numeric, ...n.ladder.prep.categorical];
}
