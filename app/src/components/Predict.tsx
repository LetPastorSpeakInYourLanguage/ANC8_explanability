"use client";

import { useEffect, useMemo, useState } from "react";
import type { ApiResponse, Field, GenResult, Schema } from "@/lib/types";
import { PREDICT_API } from "@/lib/paths";

/**
 * Score one woman across every deployed model and show where they disagree.
 *
 * The 21-predictor models at both prediction horizons (before ANC, and at ANC
 * entry with and without early ANC) and the full-pool model, all on one set of
 * answers, because the useful question is not any single number but whether
 * the predictor sets reach the same conclusion about the same woman.
 */

const pct = (p: number) => `${(p * 100).toFixed(1)}%`;

const GENERATIONS: { key: string; title: string; subtitle: string; accent: string }[] = [
  { key: "v1", title: "21-predictor models · before ANC", subtitle: "logistic regression, random forest, XGBoost", accent: "var(--set21)" },
  { key: "v1_anc_entry", title: "21-predictor models · at ANC entry", subtitle: "for women who already started ANC, with and without early ANC", accent: "var(--set21)" },
  { key: "v2", title: "Full-pool model", subtitle: "the full candidate pool, before ANC", accent: "var(--accent)" },
];

function ProbabilityBar({ p, threshold, accent }: { p: number; threshold?: number | null; accent: string }) {
  return (
    <div className="relative h-2 w-full rounded-full" style={{ background: "var(--line)" }}>
      <div className="absolute left-0 top-0 h-2 rounded-full"
           style={{ width: `${Math.min(100, p * 100)}%`, background: accent }} />
      {threshold != null && (
        <div className="absolute -top-1 h-4 w-[2px]"
             style={{ left: `${Math.min(100, threshold * 100)}%`, background: "var(--fg)" }}
             title={`operating threshold ${pct(threshold)}`} />
      )}
    </div>
  );
}

export default function Predict({ schema }: { schema: Schema }) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ApiResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    const init: Record<string, string> = {};
    const all = [
      ...schema.v1.fields,
      ...(schema.v1_anc_entry?.fields ?? []),
      ...(schema.v2?.fields ?? []),
    ];
    for (const f of all) {
      if (init[f.name] === undefined && f.default != null) init[f.name] = String(f.default);
    }
    setAnswers(init);
  }, [schema]);

  const { primary, extra } = useMemo(() => {
    const seen = new Set<string>();
    const merged: Field[] = [];
    for (const f of [
      ...schema.v1.fields,
      ...(schema.v1_anc_entry?.fields ?? []),
      ...(schema.v2?.fields ?? []),
    ]) {
      if (seen.has(f.name)) continue;
      seen.add(f.name);
      merged.push(f);
    }
    const v1Names = new Set(schema.v1.fields.map((f) => f.name));
    const core = new Set(schema.v2?.core_predictors ?? []);
    const gate = schema.v1_anc_entry?.gating_field;
    const isPrimary = (n: string) => v1Names.has(n) || core.has(n) || n === gate;
    return {
      primary: merged.filter((f) => isPrimary(f.name)),
      extra: merged.filter((f) => !isPrimary(f.name)),
    };
  }, [schema]);

  const submit = async () => {
    if (!PREDICT_API) {
      setError("Scoring needs the prediction service, which this static copy of "
        + "the site does not have. Every other tab works here; What if scores "
        + "the explainable model in your browser.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(PREDICT_API, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers, generations: ["v1", "v1_anc_entry", "v2"] }),
      });
      const json = await res.json();
      if (json.error) throw new Error(json.error);
      setResult(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const renderField = (f: Field) => (
    <div key={f.name}>
      <label className="label block mb-1" htmlFor={f.name}>
        {f.label}
        {f.unit ? ` (${f.unit})` : ""}
      </label>
      {f.type === "number" ? (
        <input id={f.name} type="number" step="any" value={answers[f.name] ?? ""}
               onChange={(e) => setAnswers({ ...answers, [f.name]: e.target.value })} />
      ) : (
        <select id={f.name} value={answers[f.name] ?? ""}
                onChange={(e) => setAnswers({ ...answers, [f.name]: e.target.value })}>
          <option value="">Not answered</option>
          {f.options?.map((o) => (
            <option key={String(o.value)} value={String(o.value)}>{String(o.label)}</option>
          ))}
        </select>
      )}
      {f.help ? <p className="label mt-1 text-[0.72rem] leading-snug">{f.help}</p> : null}
    </div>
  );

  const groups = (fields: Field[]) => {
    const by: Record<string, Field[]> = {};
    for (const f of fields) (by[f.domain] ??= []).push(f);
    return Object.entries(by);
  };

  const genBlock = (key: string, title: string, subtitle: string, accent: string, gen?: GenResult) => {
    if (!gen) return null;
    if (!gen.available) {
      return (
        <div className="card p-4" key={key}>
          <h3 className="font-semibold text-sm">{title}</h3>
          <p className="label mt-1">Not deployed: {gen.reason}</p>
        </div>
      );
    }
    const models = (gen.models ?? []).filter((m) => m.probability != null);
    const broken = (gen.models ?? []).filter((m) => m.error);
    models.sort((a, b) =>
      gen.champion === a.model ? -1 : gen.champion === b.model ? 1 : a.model.localeCompare(b.model)
    );

    return (
      <div className="card p-4" key={key}>
        <div className="flex items-baseline justify-between gap-3 flex-wrap">
          <h3 className="font-semibold text-sm" style={{ color: accent }}>{title}</h3>
          <span className="label">{subtitle}</span>
        </div>
        <div className="mt-4 space-y-4">
          {models.map((m) => (
            <div key={m.model}>
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-sm">{m.model}</span>
                <span className="tabular text-sm font-semibold">{pct(m.probability!)}</span>
              </div>
              <div className="mt-1.5">
                <ProbabilityBar p={m.probability!} threshold={m.threshold} accent={accent} />
              </div>
              <p className="label mt-1">
                {m.classification}
                {m.threshold != null ? ` · threshold ${pct(m.threshold)}` : ""}
              </p>
            </div>
          ))}
        </div>
        {broken.length > 0 && (
          <div className="mt-4 pt-3" style={{ borderTop: "1px solid var(--line)" }}>
            <p className="label" style={{ color: "var(--warn)" }}>
              {broken.length} model{broken.length > 1 ? "s" : ""} failed to score:
            </p>
            {broken.map((m) => (
              <p key={m.model} className="label mt-1 text-[0.7rem]">{m.model} — {m.error}</p>
            ))}
          </div>
        )}
        <p className="label mt-4 pt-3" style={{ borderTop: "1px solid var(--line)" }}>
          {gen.n_supplied} of {gen.n_expected} inputs supplied
          {gen.imputed && gen.imputed.length > 0
            ? ` · ${gen.imputed.length} filled from training medians`
            : ""}
        </p>
      </div>
    );
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
      <section className="card p-4 sm:p-5">
        <h2 className="font-semibold mb-4">Answers</h2>
        {groups(primary).map(([domain, fields]) => (
          <fieldset key={domain} className="mb-6">
            <legend className="text-sm font-medium mb-3">{domain}</legend>
            <div className="grid gap-4 sm:grid-cols-2">{fields.map(renderField)}</div>
          </fieldset>
        ))}

        {extra.length > 0 && (
          <>
            <button type="button" onClick={() => setShowAll((s) => !s)}
                    className="text-sm underline" style={{ color: "var(--accent)" }}>
              {showAll ? "Hide" : "Show"} {extra.length} additional full-pool questions
            </button>
            <p className="label mt-1">
              Optional. Anything left blank is filled from the training median,
              and the result panel says how many were.
            </p>
            {showAll &&
              groups(extra).map(([domain, fields]) => (
                <fieldset key={domain} className="mt-6">
                  <legend className="text-sm font-medium mb-3">{domain}</legend>
                  <div className="grid gap-4 sm:grid-cols-2">{fields.map(renderField)}</div>
                </fieldset>
              ))}
          </>
        )}

        <div className="mt-6 flex items-center gap-3">
          <button onClick={submit} disabled={busy}
                  className="rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
                  style={{ background: "var(--accent)" }}>
            {busy ? "Scoring…" : "Predict"}
          </button>
          {error && <span className="label" style={{ color: "var(--warn)" }}>{error}</span>}
        </div>
      </section>

      <aside className="space-y-4">
        {result?.comparison && (
          <div className="card p-4"
               style={result.comparison.disagree ? { borderColor: "var(--warn)" } : undefined}>
            <h3 className="font-semibold text-sm">
              {result.comparison.disagree
                ? "The two predictor sets disagree"
                : "Both predictor sets agree"}
            </h3>
            <p className="label mt-2 leading-relaxed">
              {result.comparison.v1_model} (21 predictors) says{" "}
              <strong>{pct(result.comparison.v1_probability)}</strong>.
              <br />
              {result.comparison.v2_model} (full pool) says{" "}
              <strong>{pct(result.comparison.v2_probability)}</strong>.
            </p>
            {result.comparison.disagree && (
              <p className="label mt-2">
                They fall on opposite sides of their operating thresholds, so
                the choice of model changes the answer for this woman.
              </p>
            )}
          </div>
        )}

        {result
          ? GENERATIONS.map((g) =>
              genBlock(g.key, g.title, g.subtitle, g.accent, result.result[g.key])
            )
          : (
            <div className="card p-4">
              <p className="label leading-relaxed">
                Fill in what you know and press Predict. Every deployed model
                scores the same answers so you can see where they differ.
              </p>
            </div>
          )}
      </aside>
    </div>
  );
}
