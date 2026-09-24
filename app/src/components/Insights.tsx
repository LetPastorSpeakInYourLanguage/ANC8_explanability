"use client";

import { useMemo, useState } from "react";
import { label, DOMAIN_COLORS } from "@/lib/labels";
import type { Insights } from "@/lib/types";
import type { Analysis } from "@/lib/analysis";
import { BarRow, Caveat, Panel, Table, num, signed } from "./viz";

/**
 * What drives attainment: global importance, direction, and the fitted shape
 * of each predictor.
 *
 * Importance here is the mean absolute log-odds contribution across the
 * held-out women. For an additive model that is not an *estimate* of
 * importance; it is the amount the model actually moves predictions by, which
 * is why no SHAP approximation is involved.
 *
 * Two corrections to the naive reading are built in rather than left to a
 * footnote. Importance can be shown grouped, because several variables are
 * present twice under different names and per-column ranking halves them. And
 * a categorical predictor's shape is drawn as a bar per level, never as a
 * curve over its integer codes, which would imply an ordering the data does
 * not have.
 */

function ContinuousCurve({
  shape,
  accent,
}: {
  shape: Insights["shape_functions"][string];
  accent: string;
}) {
  const pts = useMemo(() => {
    const scores = shape.scores ?? [];
    if (scores.length < 2) return null;
    const lo = Math.min(...scores);
    const hi = Math.max(...scores);
    const span = hi - lo || 1;
    const W = 200;
    const H = 44;
    return scores
      .map((s, i) => {
        const x = (i / (scores.length - 1)) * W;
        const y = H - ((s - lo) / span) * H;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  }, [shape]);
  if (!pts) return null;

  const cuts = shape.cuts ?? [];
  const lo = cuts.length ? cuts[0] : null;
  const hi = cuts.length ? cuts[cuts.length - 1] : null;

  return (
    <div>
      <svg viewBox="0 0 200 44" className="w-full h-11" preserveAspectRatio="none"
           role="img" aria-label="fitted response curve">
        <polyline points={pts} fill="none" stroke={accent} strokeWidth="2"
                  vectorEffect="non-scaling-stroke" />
      </svg>
      {lo != null && hi != null && (
        <div className="flex justify-between label text-[0.66rem] tabular">
          <span>{lo.toLocaleString()}</span>
          <span>{hi.toLocaleString()}</span>
        </div>
      )}
    </div>
  );
}

function LevelEffects({
  shape,
}: {
  shape: Insights["shape_functions"][string];
}) {
  const rows = useMemo(() => {
    const vals = shape.values ?? [];
    const scores = shape.scores ?? [];
    return vals
      .map((v, i) => ({ level: String(v), score: scores[i] ?? 0 }))
      .sort((a, b) => b.score - a.score);
  }, [shape]);
  if (!rows.length) return null;
  const scale = Math.max(...rows.map((r) => Math.abs(r.score)), 1e-6);

  return (
    <div className="space-y-1.5">
      {rows.map((r) => {
        const half = (Math.abs(r.score) / scale) * 50;
        const up = r.score >= 0;
        return (
          <div key={r.level} className="flex items-center gap-2">
            <span className="text-[0.75rem] w-32 shrink-0 truncate" title={r.level}>
              {r.level}
            </span>
            <div className="flex-1 h-2 relative rounded-full"
                 style={{ background: "var(--line)" }}>
              <div
                className="absolute top-0 h-2 rounded-full"
                style={{
                  left: up ? "50%" : `${50 - half}%`,
                  width: `${half}%`,
                  background: up ? "var(--accent)" : "var(--warn)",
                }}
              />
              <div className="absolute top-[-2px] h-3 w-px"
                   style={{ left: "50%", background: "var(--muted)" }} />
            </div>
            <span className="label tabular text-[0.68rem] w-12 text-right shrink-0">
              {signed(r.score, 2)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function InsightsView({
  data,
  analysis,
}: {
  data: Insights;
  analysis?: Analysis;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const grouped = analysis?.redundancy?.grouped ?? [];
  const canGroup = grouped.some((g) => g.n_members > 1);
  const [mode, setMode] = useState<"grouped" | "columns">(
    canGroup ? "grouped" : "columns"
  );

  const perColumn = useMemo(
    () => Object.entries(data.global_importance).slice(0, 25),
    [data]
  );

  const ranked = useMemo(() => {
    if (mode === "columns" || !canGroup) return perColumn;
    return grouped
      .slice(0, 25)
      .map((g) => [g.group, g.grouped_importance] as [string, number]);
  }, [mode, canGroup, grouped, perColumn]);

  const max = ranked.length ? Math.max(...ranked.map(([, v]) => v)) : 1;
  const memberOf = useMemo(() => {
    const m: Record<string, string[]> = {};
    for (const g of grouped) {
      if (g.n_members > 1) m[g.group] = g.members.split("; ");
    }
    return m;
  }, [grouped]);

  return (
    <div className="space-y-6">
      <Panel
        title="What the model actually uses"
        lede={
          <>
            Each bar is how much that predictor moves the prediction, averaged
            over the held-out women, on the log-odds scale. The model is
            additive, so these are not estimated importances — they are the
            numbers the model adds up. Colour shows the domain; click a bar for
            the fitted effect.
          </>
        }
        aside={
          canGroup ? (
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as typeof mode)}
              className="text-xs"
              style={{ width: "auto", padding: "0.3rem 0.45rem" }}
              aria-label="how to count importance"
            >
              <option value="grouped">group duplicate variables</option>
              <option value="columns">one row per column</option>
            </select>
          ) : undefined
        }
      >
        {canGroup && mode === "grouped" && (
          <p className="label mb-4 leading-relaxed">
            Several variables appear in the survey twice under different names.
            Ranking by column splits their weight between the copies, so they
            are added back together here. Switch to &ldquo;one row per
            column&rdquo; to see what the naive ranking would have said.
          </p>
        )}

        <div className="space-y-2">
          {ranked.map(([name, value]) => {
            const domain = data.domains[name] ?? "Other";
            const accent = DOMAIN_COLORS[domain] ?? DOMAIN_COLORS.Other;
            const shape = data.shape_functions[name];
            const open = expanded === name;
            const dir = data.direction?.[name];
            const extremes = data.level_extremes?.[name];
            const members = memberOf[name];

            return (
              <div key={name}>
                <BarRow
                  label={label(name)}
                  value={value}
                  max={max}
                  display={
                    extremes
                      ? `highest: ${extremes.raises_most}`
                      : dir ?? num(value, 3)
                  }
                  color={accent}
                  note={
                    members
                      ? `also present as ${members
                          .filter((m) => m !== name)
                          .map((m) => label(m))
                          .join(", ")}`
                      : undefined
                  }
                  onClick={() => setExpanded(open ? null : name)}
                  active={open}
                />
                {open && shape && (
                  <div className="mt-2 mb-3 pl-1">
                    <p className="label text-[0.72rem] mb-2">
                      {domain} ·{" "}
                      {shape.kind === "nominal"
                        ? "fitted effect of each level, relative to the average"
                        : "fitted response across the observed range"}
                    </p>
                    {shape.kind === "nominal" ? (
                      <LevelEffects shape={shape} />
                    ) : (
                      <ContinuousCurve shape={shape} accent={accent} />
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <Caveat>
          These describe how the model generates predictions. They are
          associations in survey data, not causal effects — nothing here says
          that changing a woman&apos;s circumstances would change her outcome by
          this amount.
        </Caveat>
      </Panel>

      {analysis?.redundancy?.pairs && analysis.redundancy.pairs.length > 0 && (
        <Panel
          title="Why the ranking needs grouping at all"
          lede="These pairs carry the same information in both directions — in
                most cases literally the same survey variable, admitted once
                under its DHS code and once under a readable name."
        >
          <Table
            head={["one name", "the other", "association"]}
            rows={analysis.redundancy.pairs.slice(0, 10).map((p) => [
              label(p.a),
              label(p.b),
              p.exact_recoding ? "the same variable" : num(p.association),
            ])}
          />
        </Panel>
      )}

      <Panel
        title="A caution about the categorical effects"
        lede="Worth knowing before reading any single region's or language
              group's effect as a finding."
      >
        <p className="text-sm leading-relaxed">
          The shared preprocessor gives every model integer codes for
          categorical predictors, so the additive model sees region as a number
          with an arbitrary order. It can still fit any shape, but binning over
          an arbitrary ordering pulls the fitted effect toward being monotone in
          that order. Regional effects read off one shape function are therefore
          less trustworthy than the model&apos;s overall predictions — and the
          duplicate-splitting above compounds it, because region is present
          twice.
        </p>
        <Caveat>
          For anything about regions, read the cascade under{" "}
          <strong>Findings</strong> instead. It counts where women are actually
          lost and involves no model at all.
        </Caveat>
      </Panel>
    </div>
  );
}
