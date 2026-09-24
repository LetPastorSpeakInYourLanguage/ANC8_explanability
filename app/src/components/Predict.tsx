"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { score, type Bundle, type Answers } from "@/lib/ebm";
import { PREDICTOR_LABELS, DOMAIN_COLORS } from "@/lib/labels";
import type { ApiResponse, CatalogModel, Field, Insights, Schema } from "@/lib/types";
import { PREDICT_API } from "@/lib/paths";

/**
 * Predict: choose what to predict, when, and with which model, then change
 * the answers and watch the probability respond.
 *
 * The additive models (explainable boosting, logistic regression) are scored
 * in the browser, so they respond at once and show exactly how much each
 * answer adds. Every other model is scored by the prediction service.
 */

const pct = (p: number) => `${(p * 100).toFixed(1)}%`;

// The predictor registers group questions differently from the colour key the
// rest of the app uses; this maps one onto the other.
const REGISTER_DOMAIN: Record<string, string> = {
  "Geographic": "Geography and culture",
  "Health service and access": "Access and distance",
  "Household and socioeconomic": "Socioeconomic",
  "Maternal and sociodemographic": "Education and information",
  "Partner and empowerment": "Agency and household",
  "Pregnancy and obstetric": "Reproductive history",
};

const OUTCOME_ORDER = ["anc1plus", "anc4plus", "anc8plus"] as const;

type Scored = {
  probability: number;
  threshold?: number | null;
  classification?: string | null;
  contributions?: { predictor: string; contribution: number }[];
  imputed?: number;
  error?: string;
};

function modelLabel(m: CatalogModel) {
  return m.set === "Full pool" || m.set.startsWith("21")
    ? `${m.algorithm} · ${m.set.toLowerCase()}`
    : `${m.set} · ${m.algorithm.toLowerCase()}`;
}

async function scoreRemote(answers: Answers, models: CatalogModel[]): Promise<Record<string, Scored>> {
  if (!PREDICT_API) throw new Error("no prediction service in this copy of the site");
  const byBundle: Record<string, string[]> = {};
  for (const m of models) (byBundle[m.bundle] ??= []).push(m.model);
  const res = await fetch(PREDICT_API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers, models: byBundle }),
  });
  const json = (await res.json()) as ApiResponse & { error?: string };
  if (json.error) throw new Error(json.error);
  const out: Record<string, Scored> = {};
  for (const [bundle, gen] of Object.entries(json.result)) {
    for (const r of gen.models ?? []) {
      out[`${bundle}::${r.model}`] = r.error
        ? { probability: NaN, error: r.error }
        : { probability: r.probability!, threshold: r.threshold,
            classification: r.classification, contributions: r.contributions,
            imputed: gen.imputed?.length ?? 0 };
    }
  }
  return out;
}

function scoreLocal(bundle: Bundle, m: CatalogModel, answers: Answers): Scored {
  const s = score(bundle, m.id, answers);
  return { probability: s.probability, threshold: m.threshold, contributions: s.contributions };
}

function Bar({ p, threshold, base, accent }: { p: number; threshold?: number | null; base?: number; accent: string }) {
  return (
    <div className="relative h-2.5 w-full rounded-full" style={{ background: "var(--line)" }}>
      <div className="absolute left-0 top-0 h-2.5 rounded-full"
           style={{ width: `${Math.min(100, p * 100)}%`, background: accent }} />
      {base != null && (
        <div className="absolute -top-1 h-[18px] w-[2px]" title={`base rate ${pct(base)}`}
             style={{ left: `${base * 100}%`, background: "var(--muted)" }} />
      )}
      {threshold != null && (
        <div className="absolute -top-1 h-[18px] w-[2px]" title={`threshold ${pct(threshold)}`}
             style={{ left: `${Math.min(100, threshold * 100)}%`, background: "var(--fg)" }} />
      )}
    </div>
  );
}

export default function Predict({
  schema, browser, insights, initial,
}: {
  schema: Schema;
  browser: Bundle | null;
  insights: Insights;
  initial: Answers;
}) {
  const canRemote = !!PREDICT_API;
  const usable = (m: CatalogModel) => (m.browser && !!browser) || canRemote;
  const fieldsByName = useMemo(
    () => Object.fromEntries(schema.fields.map((f) => [f.name, f])) as Record<string, Field>,
    [schema]
  );

  const start = useMemo<Answers>(() => {
    const a: Answers = {};
    for (const f of schema.fields) a[f.name] = f.default == null ? "" : String(f.default);
    for (const [k, v] of Object.entries(initial)) if (k in a && v != null) a[k] = String(v);
    return a;
  }, [schema, initial]);

  const [outcome, setOutcome] = useState<string>("anc8plus");
  const [horizon, setHorizon] = useState<string>("before");
  const [modelId, setModelId] = useState<string>("");
  const [answers, setAnswers] = useState<Answers>(start);
  const [showAll, setShowAll] = useState(false);
  const [current, setCurrent] = useState<Scored | null>(null);
  const [baseline, setBaseline] = useState<Scored | null>(null);
  const [baselineFor, setBaselineFor] = useState("");
  const [busy, setBusy] = useState(false);
  const [compare, setCompare] = useState<Record<string, Scored> | null>(null);

  useEffect(() => setAnswers(start), [start]);

  const choices = useMemo(() => {
    return schema.models
      .filter((m) => m.outcome === outcome && m.horizon === horizon)
      .sort((a, b) => Number(b.recommended) - Number(a.recommended)
        || (b.heldout_AP ?? 0) - (a.heldout_AP ?? 0));
  }, [schema, outcome, horizon]);

  // Keep the chosen model when it still fits; otherwise the study's
  // recommendation, or the best model this copy of the site can score.
  useEffect(() => {
    if (choices.some((m) => m.id === modelId)) return;
    const pick = choices.find((m) => m.recommended && usable(m)) ?? choices.find(usable) ?? choices[0];
    setModelId(pick?.id ?? "");
    setCompare(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [choices]);

  const model = choices.find((m) => m.id === modelId);
  const base = schema.prevalence[`${outcome}|${horizon}`];
  const outcomeLabel = schema.outcomes[outcome];

  // Score as the answers change: at once in the browser, after a short pause
  // for the service.
  const seq = useRef(0);
  useEffect(() => {
    if (!model) return;
    const id = ++seq.current;
    if (model.browser && browser) {
      setBusy(false);
      try {
        setCurrent(scoreLocal(browser, model, answers));
        setBaseline(scoreLocal(browser, model, start));
        setBaselineFor(model.id);
      } catch (e) {
        setCurrent({ probability: NaN, error: String(e) });
      }
      return;
    }
    if (!canRemote) {
      setCurrent(null);
      return;
    }
    setBusy(true);
    const t = setTimeout(async () => {
      try {
        const [now, then] = await Promise.all([
          scoreRemote(answers, [model]),
          baseline && baselineFor === model.id
            ? Promise.resolve({ [model.id]: baseline })
            : scoreRemote(start, [model]),
        ]);
        if (id !== seq.current) return;
        setCurrent(now[model.id] ?? null);
        setBaseline(then[model.id] ?? null);
        setBaselineFor(model.id);
      } catch (e) {
        if (id === seq.current) setCurrent({ probability: NaN, error: e instanceof Error ? e.message : String(e) });
      } finally {
        if (id === seq.current) setBusy(false);
      }
    }, 450);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [model?.id, answers, browser]);

  const runCompare = async () => {
    const local: Record<string, Scored> = {};
    const remote: CatalogModel[] = [];
    for (const m of choices) {
      if (m.browser && browser) local[m.id] = scoreLocal(browser, m, answers);
      else if (canRemote) remote.push(m);
    }
    setCompare(local);
    if (remote.length) {
      try {
        const r = await scoreRemote(answers, remote);
        setCompare({ ...local, ...r });
      } catch (e) {
        setCompare({ ...local, _error: { probability: NaN, error: String(e) } });
      }
    }
  };

  // The questions the chosen model asks: the most influential first.
  const asked = useMemo(() => {
    if (!model) return { top: [] as Field[], rest: [] as Field[] };
    const rank = new Map(insights.top_predictors.map((p, i) => [p, i]));
    const list = model.fields.map((n) => fieldsByName[n]).filter(Boolean);
    if (list.length <= 24) return { top: list, rest: [] as Field[] };
    const sorted = [...list].sort((a, b) => (rank.get(a.name) ?? 999) - (rank.get(b.name) ?? 999));
    return { top: sorted.slice(0, 12), rest: sorted.slice(12) };
  }, [model, fieldsByName, insights]);

  const colorOf = (n: string) =>
    DOMAIN_COLORS[insights.domains[n] ?? REGISTER_DOMAIN[fieldsByName[n]?.domain] ?? "Other"]
    ?? DOMAIN_COLORS.Other;
  const nameOf = (n: string) => PREDICTOR_LABELS[n] ?? fieldsByName[n]?.label ?? n;
  const changed = (n: string) => String(answers[n] ?? "") !== String(start[n] ?? "");
  const set = (n: string, v: string) => setAnswers((a) => ({ ...a, [n]: v }));

  const renderField = (f: Field) => {
    const accent = colorOf(f.name);
    const range = insights.ranges[f.name];
    const value = String(answers[f.name] ?? "");
    return (
      <div key={f.name}>
        <div className="flex items-baseline justify-between gap-2">
          <label className="text-sm" htmlFor={`q-${f.name}`}>
            {nameOf(f.name)}{f.unit ? ` (${f.unit})` : ""}
            {changed(f.name) && <span className="label" style={{ color: accent }}> · changed</span>}
          </label>
          {f.type === "number" && (
            <span className="label tabular text-[0.72rem]">
              {value === "" ? "—" : Number.isFinite(Number(value)) ? String(+Number(value).toFixed(2)) : value}
            </span>
          )}
        </div>
        {f.type === "number" ? (
          range && range.kind === "continuous" ? (
            <input id={`q-${f.name}`} type="range" className="w-full mt-1"
                   min={range.p05} max={range.p95} step={(range.p95 - range.p05) / 100 || 1}
                   value={Number(value || range.median)} style={{ accentColor: accent }}
                   onChange={(e) => set(f.name, e.target.value)} />
          ) : (
            <input id={`q-${f.name}`} type="number" step="any" className="mt-1" value={value}
                   onChange={(e) => set(f.name, e.target.value)} />
          )
        ) : (
          <select id={`q-${f.name}`} className="mt-1" value={value}
                  onChange={(e) => set(f.name, e.target.value)}>
            <option value="">Not answered</option>
            {f.options?.map((o) => (
              <option key={String(o.value)} value={String(o.value)}>{String(o.label)}</option>
            ))}
          </select>
        )}
      </div>
    );
  };

  const seg = (on: boolean, disabled = false) => ({
    background: on ? "var(--accent)" : "transparent",
    color: on ? "white" : disabled ? "var(--line)" : "var(--fg)",
    border: "1px solid var(--line)",
    cursor: disabled ? "not-allowed" : "pointer",
  });

  const delta = current && baseline && Number.isFinite(current.probability) && Number.isFinite(baseline.probability)
    ? current.probability - baseline.probability : null;
  const changedCount = model ? model.fields.filter(changed).length : 0;
  const top = (current?.contributions ?? []).slice(0, 8);
  const maxC = Math.max(...top.map((c) => Math.abs(c.contribution)), 0.01);

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
      <section className="card p-4 sm:p-5 space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <p className="label mb-1.5">Predict</p>
            <div className="flex">
              {OUTCOME_ORDER.map((o, i) => (
                <button key={o} className={`px-3 py-1.5 text-sm ${i === 0 ? "rounded-l-lg" : ""} ${i === 2 ? "rounded-r-lg" : ""}`}
                        style={seg(outcome === o)}
                        onClick={() => { setOutcome(o); if (o === "anc1plus") setHorizon("before"); }}>
                  {schema.outcomes[o]}
                </button>
              ))}
            </div>
          </div>
          <div>
            <p className="label mb-1.5">When</p>
            <div className="flex">
              {(["before", "entry"] as const).map((h, i) => {
                const disabled = h === "entry" && outcome === "anc1plus";
                return (
                  <button key={h} disabled={disabled}
                          className={`px-3 py-1.5 text-sm ${i === 0 ? "rounded-l-lg" : "rounded-r-lg"}`}
                          style={seg(horizon === h, disabled)}
                          title={disabled ? "Every woman at her first visit already has ANC1+" : undefined}
                          onClick={() => setHorizon(h)}>
                    {schema.horizons[h]}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div>
          <label className="label block mb-1.5" htmlFor="model">Model</label>
          <select id="model" value={modelId} onChange={(e) => { setModelId(e.target.value); setCompare(null); }}>
            {choices.map((m) => (
              <option key={m.id} value={m.id} disabled={!usable(m)}>
                {m.recommended ? "★ " : ""}{modelLabel(m)} — AP {m.heldout_AP?.toFixed(3) ?? "–"}
                {" · "}{m.n_predictors} predictors{m.browser ? " · instant" : ""}
              </option>
            ))}
          </select>
          {model && (
            <p className="label mt-1.5 leading-relaxed">
              {model.recommended ? "★ The study's recommended model for this question. " : ""}
              Held-out AP {model.heldout_AP?.toFixed(3) ?? "–"}
              {model.heldout_AUROC != null ? `, AUROC ${model.heldout_AUROC.toFixed(3)}` : ""}
              {base != null ? `, against a base rate of ${pct(base)}` : ""}.{" "}
              {model.browser
                ? "Scored in your browser as you change the answers, with an exact breakdown."
                : canRemote ? "Scored by the prediction service." : "Needs the prediction service, which this copy of the site does not have."}
              {model.note ? ` Uses ${model.note}.` : ""}
            </p>
          )}
        </div>

        <div style={{ borderTop: "1px solid var(--line)" }} className="pt-4">
          <div className="flex items-baseline justify-between gap-3 mb-3">
            <h2 className="font-semibold text-sm">
              {model?.fields.length ?? 0} questions{changedCount > 0 ? ` · ${changedCount} changed` : ""}
            </h2>
            <button className="text-sm underline" style={{ color: "var(--accent)" }}
                    onClick={() => setAnswers(start)}>
              Reset to the example woman
            </button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">{asked.top.map(renderField)}</div>
          {asked.rest.length > 0 && (
            <>
              <button type="button" onClick={() => setShowAll((s) => !s)}
                      className="mt-5 text-sm underline" style={{ color: "var(--accent)" }}>
                {showAll ? "Hide" : "Show"} {asked.rest.length} more questions
              </button>
              {showAll && <div className="grid gap-4 sm:grid-cols-2 mt-4">{asked.rest.map(renderField)}</div>}
            </>
          )}
        </div>
      </section>

      <aside className="space-y-4 lg:sticky lg:top-4 self-start">
        <div className="card p-4">
          <h3 className="font-semibold text-sm">Chance of reaching {outcomeLabel}</h3>
          {current && Number.isFinite(current.probability) ? (
            <>
              <p className="tabular text-3xl font-semibold mt-2" style={{ opacity: busy ? 0.5 : 1 }}>
                {pct(current.probability)}
              </p>
              {delta != null && changedCount > 0 && (
                <p className="label mt-1 tabular">
                  {delta >= 0 ? "+" : ""}{(delta * 100).toFixed(1)} points from the example woman ({pct(baseline!.probability)})
                </p>
              )}
              <div className="mt-3">
                <Bar p={current.probability} threshold={current.threshold} base={base} accent="var(--accent)" />
              </div>
              <p className="label mt-2 leading-relaxed">
                Grey mark: base rate{base != null ? ` ${pct(base)}` : ""}.
                {current.threshold != null && ` Dark mark: the model's threshold ${pct(current.threshold)}`}
                {current.classification ? ` — ${current.classification}.` : current.threshold != null ? "." : ""}
                {current.imputed ? ` ${current.imputed} unanswered questions filled from training medians.` : ""}
              </p>
            </>
          ) : (
            <p className="label mt-2 leading-relaxed" style={current?.error ? { color: "var(--warn)" } : undefined}>
              {current?.error ?? (busy ? "Scoring…" : canRemote || model?.browser
                ? "Scoring…" : "This model needs the prediction service. Choose a model marked instant.")}
            </p>
          )}
        </div>

        {top.length > 0 && (
          <div className="card p-4">
            <h3 className="font-semibold text-sm">Why — exactly</h3>
            <p className="label mt-1 mb-3 leading-relaxed">
              What each answer adds on the log-odds scale. With the intercept they sum to the number behind the percentage.
            </p>
            {top.map((c) => {
              const accent = colorOf(c.predictor);
              const w = (Math.abs(c.contribution) / maxC) * 50;
              const up = c.contribution >= 0;
              return (
                <div key={c.predictor} className="mb-2">
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-[0.78rem]">{nameOf(c.predictor)}</span>
                    <span className="label tabular text-[0.7rem]">{up ? "+" : ""}{c.contribution.toFixed(3)}</span>
                  </div>
                  <div className="relative h-1.5 mt-0.5">
                    <div className="absolute top-0 h-1.5" style={{ left: "50%", width: 1, background: "var(--line)" }} />
                    <div className="absolute top-0 h-1.5 rounded-full"
                         style={{ left: up ? "50%" : `${50 - w}%`, width: `${w}%`, background: accent, opacity: up ? 1 : 0.55 }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="card p-4">
          <div className="flex items-baseline justify-between gap-2">
            <h3 className="font-semibold text-sm">Every {outcomeLabel} model</h3>
            <button className="text-sm underline" style={{ color: "var(--accent)" }} onClick={runCompare}>
              {compare ? "Refresh" : "Compare"}
            </button>
          </div>
          {compare ? (
            <div className="mt-3 space-y-3">
              {choices.map((m) => {
                const r = compare[m.id];
                return (
                  <div key={m.id}>
                    <div className="flex items-baseline justify-between gap-2">
                      <button className="text-[0.78rem] text-left underline-offset-2 hover:underline"
                              onClick={() => setModelId(m.id)}
                              style={{ fontWeight: m.id === modelId ? 600 : 400 }}>
                        {m.recommended ? "★ " : ""}{modelLabel(m)}
                      </button>
                      <span className="label tabular text-[0.72rem]">
                        {r && Number.isFinite(r.probability) ? pct(r.probability) : r?.error ? "error" : "–"}
                      </span>
                    </div>
                    {r && Number.isFinite(r.probability) && (
                      <div className="mt-1"><Bar p={r.probability} threshold={r.threshold} base={base}
                                                 accent={m.id === modelId ? "var(--accent)" : "var(--set21)"} /></div>
                    )}
                  </div>
                );
              })}
              {compare._error && <p className="label" style={{ color: "var(--warn)" }}>{compare._error.error}</p>}
            </div>
          ) : (
            <p className="label mt-2 leading-relaxed">
              Score these answers with all {choices.length} models for this question, to see whether they agree.
            </p>
          )}
        </div>

        <p className="label leading-relaxed px-1">
          A prediction describes women with similar recorded characteristics. Changing an answer
          shows what the model predicts for someone like that, not what would happen if that
          woman&apos;s circumstances changed.
        </p>
      </aside>
    </div>
  );
}
