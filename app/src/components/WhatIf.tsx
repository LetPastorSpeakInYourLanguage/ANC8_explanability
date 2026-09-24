"use client";

import { useEffect, useMemo, useState } from "react";
import { score, type Bundle, type Answers } from "@/lib/ebm";
import { label, DOMAIN_COLORS } from "@/lib/labels";
import type { Insights } from "@/lib/types";

/**
 * "What if?" — move a predictor, watch the prediction respond.
 *
 * Scored entirely in the browser against the additive model, so there is no
 * network round trip and the response is immediate. The contribution bars are
 * exact: they sum, with the intercept, to the log-odds behind the probability
 * shown.
 */

const pct = (p: number) => `${(p * 100).toFixed(1)}%`;

export default function WhatIf({
  bundle,
  insights,
  initial,
}: {
  bundle: Bundle;
  insights: Insights;
  initial: Answers;
}) {
  const modelName = "Explainable Boosting";
  const [answers, setAnswers] = useState<Answers>(initial);
  const [baseline] = useState<Answers>(initial);

  useEffect(() => setAnswers(initial), [initial]);

  const current = useMemo(() => {
    try {
      return score(bundle, modelName, answers);
    } catch {
      return null;
    }
  }, [bundle, answers]);

  const base = useMemo(() => {
    try {
      return score(bundle, modelName, baseline);
    } catch {
      return null;
    }
  }, [bundle, baseline]);

  if (!current || !base) {
    return (
      <div className="card p-4">
        <p className="label">The additive model is not in this deployment.</p>
      </div>
    );
  }

  const delta = current.probability - base.probability;
  const changed = Object.keys(answers).filter(
    (k) => String(answers[k] ?? "") !== String(baseline[k] ?? "")
  );

  const sliders = insights.top_predictors.filter((p) => insights.ranges[p]);
  const maxContribution = Math.max(
    ...current.contributions.slice(0, 10).map((c) => Math.abs(c.contribution)),
    0.01
  );

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <section className="card p-4 sm:p-5">
        <h2 className="font-semibold">Adjust the inputs</h2>
        <p className="label mt-2 leading-relaxed">
          Scored in your browser as you move things, against the additive model.
        </p>

        <div className="mt-5 space-y-5">
          {sliders.map((name) => {
            const range = insights.ranges[name];
            const domain = insights.domains[name] ?? "Other";
            const accent = DOMAIN_COLORS[domain] ?? DOMAIN_COLORS.Other;
            const isChanged = changed.includes(name);

            return (
              <div key={name}>
                <div className="flex items-baseline justify-between gap-2">
                  <label className="text-sm" htmlFor={`wi-${name}`}>
                    {label(name)}
                    {isChanged && (
                      <span className="label" style={{ color: accent }}>
                        {" "}· changed
                      </span>
                    )}
                  </label>
                  <span className="label tabular text-[0.72rem]">
                    {String(answers[name] ?? "—")}
                  </span>
                </div>

                {range.kind === "continuous" ? (
                  <input
                    id={`wi-${name}`}
                    type="range"
                    className="w-full mt-1"
                    min={range.p05}
                    max={range.p95}
                    step={(range.p95 - range.p05) / 100 || 1}
                    value={Number(answers[name] ?? range.median)}
                    onChange={(e) =>
                      setAnswers({ ...answers, [name]: Number(e.target.value) })
                    }
                    style={{ accentColor: accent }}
                  />
                ) : (
                  <select
                    id={`wi-${name}`}
                    className="mt-1"
                    value={String(answers[name] ?? "")}
                    onChange={(e) =>
                      setAnswers({ ...answers, [name]: e.target.value })
                    }
                  >
                    {range.options.map((o) => (
                      <option key={o} value={o}>
                        {o}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            );
          })}
        </div>

        <button
          className="mt-6 text-sm underline"
          style={{ color: "var(--accent)" }}
          onClick={() => setAnswers(baseline)}
        >
          Reset to the starting values
        </button>
      </section>

      <aside className="space-y-4">
        <div className="card p-4">
          <h3 className="font-semibold text-sm">Predicted ANC8+</h3>
          <p className="tabular text-3xl font-semibold mt-2">
            {pct(current.probability)}
          </p>
          {changed.length > 0 && (
            <p className="label mt-1 tabular">
              {delta >= 0 ? "+" : ""}
              {(delta * 100).toFixed(1)} points from {pct(base.probability)}
            </p>
          )}
          <div
            className="mt-3 h-2 rounded-full"
            style={{ background: "var(--line)" }}
          >
            <div
              className="h-2 rounded-full"
              style={{
                width: `${Math.min(100, current.probability * 100)}%`,
                background: "var(--accent)",
              }}
            />
          </div>
        </div>

        <div className="card p-4">
          <h3 className="font-semibold text-sm">Why — exactly</h3>
          <p className="label mt-1 mb-3 leading-relaxed">
            Log-odds contributions. These sum, with the intercept, to the number
            behind the percentage above.
          </p>
          {current.contributions.slice(0, 10).map((c) => {
            const domain = insights.domains[c.predictor] ?? "Other";
            const accent = DOMAIN_COLORS[domain] ?? DOMAIN_COLORS.Other;
            const w = (Math.abs(c.contribution) / maxContribution) * 50;
            const positive = c.contribution >= 0;
            return (
              <div key={c.predictor} className="mb-2">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[0.78rem]">{label(c.predictor)}</span>
                  <span className="label tabular text-[0.7rem]">
                    {c.contribution >= 0 ? "+" : ""}
                    {c.contribution.toFixed(3)}
                  </span>
                </div>
                <div className="relative h-1.5 mt-0.5">
                  <div
                    className="absolute top-0 h-1.5"
                    style={{ left: "50%", width: 1, background: "var(--line)" }}
                  />
                  <div
                    className="absolute top-0 h-1.5 rounded-full"
                    style={{
                      left: positive ? "50%" : `${50 - w}%`,
                      width: `${w}%`,
                      background: accent,
                      opacity: positive ? 1 : 0.55,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <div className="card p-4" style={{ borderColor: "var(--warn)" }}>
          <h3 className="font-semibold text-sm">Read this carefully</h3>
          <p className="label mt-2 leading-relaxed">
            Moving a slider shows what the model predicts for{" "}
            <em>someone with that characteristic</em>. It does not show what
            would happen if you changed it for a particular woman.
          </p>
          <p className="label mt-2 leading-relaxed">
            Wealth, education and region are not interventions, and this model
            is associational. A woman who is wealthier differs in many ways the
            model cannot separate, so the slider moves a prediction — not an
            outcome.
          </p>
        </div>
      </aside>
    </div>
  );
}
