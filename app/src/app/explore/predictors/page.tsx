"use client";

import { useMemo, useState } from "react";
import { CartesianGrid, ComposedChart, Line, ReferenceLine, Scatter, Tooltip, XAxis, YAxis, LabelList } from "recharts";
import DotRows, { niceTicks } from "@/components/charts/DotRows";
import MatrixHeat from "@/components/charts/MatrixHeat";
import RankedBars from "@/components/charts/RankedBars";
import { AXIS, ChartBox, GRID, SeriesLegend, TipPanel, tip } from "@/components/charts/rc";
import { useRenderTheme } from "@/components/shell/theme-provider";
import { DataNote,
  InlineError, Note, Panel, PanelLoading, Screen, Segmented, StatTile, Table, Tag,
} from "@/components/studio/ui";
import type { Analysis, FeatureValueEntry } from "@/lib/analysis";
import { useJSON } from "@/lib/data";
import { OUTCOME_OF, RUNG_LABEL, RUNG_OF, num, pct, setName, signed, type Outcome } from "@/lib/explore";
import { label } from "@/lib/labels";
import { MODEL_ABBR, type Explained } from "@/lib/modelCards";
import { cohortRungs } from "@/lib/regionsData";
import { COHORTS, RUNGS, useStudio, type Rung } from "@/lib/studio";

const MODEL_COLOR: Record<string, string> = {
  "Logistic regression": "var(--accent)",
  LightGBM: "var(--good)",
  "Random Forest": "var(--warn)",
  XGBoost: "var(--cross)",
};
const SET_ORDER = ["tier 1", "tier 1+2", "original 21", "all 88"];

// A model's name (its share of what that model uses, on the full pool), or the added accuracy.
type Measure = string;
const MARGINAL = "marginal";

export default function PredictorsPage() {
  const studio = useStudio();
  const theme = useRenderTheme();
  const ana = useJSON<Analysis>("/analysis.json");
  const explained = useJSON<Explained>("/data/explain.json");
  const lineup = explained.data?.models ?? [];
  const MEASURES = [
    ...lineup.map((m) => ({ key: m, label: MODEL_ABBR[m] ?? m, title: `Share of what ${m} uses (full pool)` })),
    { key: MARGINAL, label: "Added accuracy", title: "Average precision gained by adding it to the 21, as a share of the ceiling" },
  ];
  const [picked, setMeasure] = useState<Measure>("");
  const measure = MEASURES.some((m) => m.key === picked) ? picked : MEASURES[0]?.key ?? MARGINAL;

  const cohort = studio.cohort;
  const rungs = cohortRungs(cohort);
  const rung = rungs.includes(studio.rung) ? studio.rung : "anc4";
  const outcome = OUTCOME_OF[rung];
  const fv: FeatureValueEntry | undefined = ana.data?.feature_value?.[cohort]?.[outcome];
  const s = fv?.summary;

  // "How many predictors": three routes to a set, on one axis.
  const curve = useMemo(() => {
    if (!fv || !s) return null;
    const fromZero = (fv.steps ?? []).map((r) => ({ n: r.step, AP: r.AP, who: label(r.predictor) }));
    const within21 = (fv.path_within_21 ?? []).map((r) => ({ n: r.step, AP: r.AP, who: label(r.predictor) }));
    const onto21 = (fv.cumulative ?? []).map((r) => ({ n: 21 + r.n_added, AP: r.AP, who: r.added ? label(r.added) : "the 21" }));
    const t1 = s.tier1.length;
    const t12 = t1 + s.tier2.length;
    const at = (n: number) => fv.steps?.find((r) => r.step === n)?.AP;
    const sets = [
      { n: t1, AP: at(t1), name: setName("tier 1", t1), short: `Top ${t1}` },
      ...(s.tier2.length ? [{ n: t12, AP: at(t12), name: setName("tier 1+2", t12), short: `Top ${t12}` }] : []),
      ...(s.stage0 ? [{ n: 21 - s.stage0.n_non_contributors, AP: s.stage0.AP_21_minus_non_contributors,
                        name: setName("21 minus non-contributors", 21 - s.stage0.n_non_contributors),
                        short: `${21 - s.stage0.n_non_contributors} of 21` }] : []),
      { n: 21, AP: s.anchors.original21, name: "The 21", short: "21" },
      { n: s.n_candidates ?? 88, AP: s.anchors.all88, name: `All ${s.n_candidates ?? 88}`, short: `All ${s.n_candidates ?? 88}` },
    ].filter((p) => p.AP != null) as { n: number; AP: number; name: string; short: string }[];
    const all = [...fromZero, ...within21, ...onto21, ...sets].map((p) => p.AP);
    const lo = Math.floor(Math.min(...all, s.anchors.prevalence) * 20) / 20;
    const ticks = niceTicks(lo, Math.max(...all), 4);
    const step = ticks[1] - ticks[0];
    while (ticks[ticks.length - 1] < Math.max(...all) + step * 0.15) ticks.push(+(ticks[ticks.length - 1] + step).toFixed(10));
    return { fromZero, within21, onto21, sets, ticks, domain: [ticks[0], ticks[ticks.length - 1]] as [number, number] };
  }, [fv, s]);

  const matrix = useMemo(() => {
    const by = new Map<string, { domain: string; in21: boolean; v: Record<string, number | null> }>();
    if (measure === MARGINAL) {
      for (const r of ana.data?.predictor_matrix ?? []) {
        const e = by.get(r.predictor) ?? { domain: r.domain ?? "", in21: r.in_21, v: {} };
        e.v[r.rung] = r.marginal_share;
        by.set(r.predictor, e);
      }
    } else {
      for (const [rk, block] of Object.entries(explained.data?.pool ?? {})) {
        for (const [x, info] of Object.entries(block!.predictors)) {
          const e = by.get(x) ?? { domain: info.domain, in21: info.in21, v: {} };
          e.v[OUTCOME_OF[rk as Rung]] = info.shares[measure] ?? null;
          by.set(x, e);
        }
      }
    }
    if (!by.size) return [];
    return [...by.entries()]
      .sort((a, b) => (b[1].v[outcome] ?? -1) - (a[1].v[outcome] ?? -1))
      .slice(0, 24)
      .map(([k, e]) => ({ key: k, label: label(k), title: k, sub: `${e.domain}${e.in21 ? " · in the 21" : ""}`, values: e.v }));
  }, [ana.data, explained.data, measure, outcome]);

  if (ana.error) return <Screen><InlineError message={ana.error} /></Screen>;
  if (!ana.data) return <Screen><PanelLoading rows={8} /></Screen>;
  const a = ana.data;
  const scr = a.screening;
  const stab = a.stability?.[outcome];
  const cohortInfo = COHORTS.find((c) => c.key === cohort)!;

  const rungPicker = (
    <Segmented
      label="Rung"
      options={RUNGS.filter((r) => rungs.includes(r.key)).map((r) => ({ key: r.key, label: r.label }))}
      value={rung}
      onChange={(k) => studio.set({ rung: k })}
    />
  );

  return (
    <Screen>
      <div data-help="predictors.tiles" className="grid gap-10 grid-cols-2 lg:grid-cols-5">
        <StatTile label="Survey columns" value={scr?.n_columns.toLocaleString() ?? "–"} sub="every variable in the women's file" />
        <StatTile label="Observed for enough women" value={scr?.counts.candidate.toLocaleString() ?? "–"}
                  sub={`${scr?.counts.low_coverage.toLocaleString()} observed for fewer than half`} />
        <StatTile label="Tested for selection" value={s?.n_candidates ?? a.redundancy?.summary?.n_predictors ?? "–"}
                  sub="known before or at the start of pregnancy" />
        <StatTile label={`Clear the bar · ${RUNG_LABEL[rung]}`} value={s ? s.tier1.length + s.tier2.length : "–"}
                  sub="each adds accuracy in most resamples" tone="accent" />
        <StatTile label="Strongest few" value={s?.tier1.length ?? "–"}
                  sub={s ? s.tier1.map(label).join(", ") : ""} tone="good" />
      </div>

      <Panel help="predictors.funnel"
        title="From 6,648 survey columns to a handful"
        how="Each bar is how many variables are left after a step, on a log scale so the small sets stay visible. Columns were removed when they were not asked in this survey round, were administrative, were measured at or after the delivery, or were observed for fewer than half the women; then predictors were added one at a time and kept only if they helped in most resamples."
        actions={rungPicker}
      >
        <SelectionFunnel
          steps={[
            { n: scr?.n_columns ?? 6648, label: "Survey columns", note: "the whole women's questionnaire" },
            { n: (scr?.counts.candidate ?? 0) + (scr?.counts.low_coverage ?? 0), label: "Usable in principle",
              note: `${scr?.counts.excluded.toLocaleString()} removed: not asked in this round, empty, administrative, or measured at or after the delivery` },
            { n: scr?.counts.candidate ?? 577, label: "Observed for at least half", note: `${scr?.counts.low_coverage.toLocaleString()} observed for fewer than half the women` },
            { n: a.redundancy?.summary?.n_predictors ?? 95, label: "Kept for modelling", note: "known before ANC starts; the care itself and life after it refused" },
            { n: s?.n_candidates ?? 88, label: "Tested one by one", note: "the pool the selection runs on" },
            ...(s ? [{ n: s.tier1.length + s.tier2.length, label: `Clear the bar at ${RUNG_LABEL[rung]}`, note: [...s.tier1, ...s.tier2].map(label).join(" · ") }] : []),
            ...(s ? [{ n: s.tier1.length, label: "Strongest few", note: s.tier1.map(label).join(" · "), strong: true }] : []),
          ]}
        />
        {a.redundancy?.summary && (
          <div className="px-14 pb-12">
            <Note tone="accent">
              {a.redundancy.summary.n_predictors - a.redundancy.summary.n_after_deduplication} of the{" "}
              {a.redundancy.summary.n_predictors} were near-copies of another (two codings of wealth, of education, of region). Removing
              them changed development accuracy by{" "}
              {signed(a.redundancy.summary.development_AP_deduplicated - a.redundancy.summary.development_AP_full)} average precision
              (ANC8+).
            </Note>
          </div>
        )}
      </Panel>

      <Panel help="predictors.how-many"
        title={`How many predictors does ${RUNG_LABEL[rung]} need? · ${cohortInfo.short} cohort`}
        how="Accuracy (average precision on development women, cross-validated) against the number of predictors, on a log scale. The solid line builds a set from nothing, best predictor first; the dashed line builds within the 21 only; the dotted line adds the other predictors to the 21 one at a time. Big dots are the named sets. Most of the accuracy arrives with the first two or three predictors."
        actions={rungPicker}
      >
        {curve ? (
          <>
            <ChartBox height={290} className="pt-12 pr-16">
              <ComposedChart margin={{ left: -4, right: 10, top: 8, bottom: 4 }}>
                <CartesianGrid {...GRID} />
                <XAxis {...AXIS} dataKey="n" type="number" scale="log" domain={[1, 100]} allowDataOverflow
                  ticks={[1, 2, 3, 5, 8, 13, 21, 34, 55, 88]} />
                <YAxis {...AXIS} dataKey="AP" type="number" domain={curve.domain} ticks={curve.ticks} tickFormatter={(v) => v.toFixed(2)} width={44} />
                <ReferenceLine y={s!.anchors.prevalence} stroke="var(--faint)" strokeDasharray="4 3"
                  label={{ value: "chance", position: "insideBottomRight", fontSize: 10, fill: "var(--faint)" }} />
                <Tooltip
                  content={tip<{ n: number; AP: number; who?: string; name?: string }>((d) => (
                    <TipPanel
                      title={d.name ?? `${d.n} predictor${d.n === 1 ? "" : "s"}`}
                      rows={[
                        { label: "Average precision", value: num(d.AP) },
                        ...(d.who ? [{ label: "Last added", value: d.who }] : []),
                      ]}
                    />
                  ))}
                />
                <Line data={curve.fromZero} dataKey="AP" stroke="var(--accent)" strokeWidth={2} dot={{ r: 2 }} isAnimationActive={false} />
                <Line data={curve.within21} dataKey="AP" stroke="var(--cross)" strokeWidth={1.5} strokeDasharray="5 3" dot={false} isAnimationActive={false} />
                <Line data={curve.onto21} dataKey="AP" stroke="var(--warn)" strokeWidth={1.5} strokeDasharray="1 3" dot={false} isAnimationActive={false} />
                <Scatter data={curve.sets} dataKey="AP" fill="var(--text)" isAnimationActive={false}>
                  <LabelList dataKey="short" position="bottom" offset={8} style={{ fontSize: 10, fill: "var(--dim)" }} />
                </Scatter>
              </ComposedChart>
            </ChartBox>
            <SeriesLegend
              items={[
                { key: "a", label: "Best first, from nothing", color: "var(--accent)" },
                { key: "b", label: "Best first, within the 21", color: "var(--cross)", dashed: true },
                { key: "c", label: "Adding to the 21", color: "var(--warn)", dashed: true },
              ]}
            />
          </>
        ) : (
          <PanelLoading rows={6} />
        )}
        <DataNote>The survey records women&apos;s circumstances, not their care: facility data (quality, staffing, stock-outs, waiting times) is the likeliest route to better ANC8+ prediction.</DataNote>
      </Panel>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-2">
        <Panel help="predictors.add-one"
          title="Adding one predictor to the 21"
          how="Each dot is the accuracy gained by adding that one predictor to the 21, averaged over five resamples; the bar is the range across them. The dashed line is the bar a predictor must clear (+0.005 average precision in most resamples)."
          actions={<Tag>{RUNG_LABEL[rung]} · top 15</Tag>}
        >
          {fv?.add_one ? (
            <DotRows
              rows={fv.add_one.slice(0, 15).map((r) => ({
                key: r.predictor,
                label: label(r.predictor),
                title: r.predictor,
                values: { gain: r.gain },
                lo: { gain: r.gain_min },
                hi: { gain: r.gain_max },
                muted: !r.clears_threshold,
                display: signed(r.gain),
              }))}
              series={[{ key: "gain", label: "Gain", color: "var(--accent)" }]}
              reference={{ value: s!.threshold ?? 0.005, label: "The bar" }}
              format={(v) => signed(v, 3)}
              labelWidth={200}
              showLegend={false}
            />
          ) : (
            <PanelLoading rows={8} />
          )}
        </Panel>

        <Panel help="predictors.drop-one"
          title="Taking one out of the 21"
          how="How much accuracy the 21 lose when one of them is removed. Bars to the right: the predictor carries information the others do not. Bars to the left: the set does better without it."
          actions={
            s?.stage0 ? <Tag tone="accent">{21 - s.stage0.n_non_contributors} of 21 contribute</Tag> : undefined
          }
        >
          {fv?.drop_within_21 ? (
            <RankedBars
              signed
              labelWidth={200}
              rows={fv.drop_within_21.map((r) => ({
                key: r.predictor,
                label: label(r.predictor),
                value: r.loss,
                display: signed(r.loss),
                color: r.contributes ? "var(--accent)" : "var(--faint)",
              }))}
            />
          ) : (
            <div className="px-14 py-12 text-11 text-dim">Not run for the {cohortInfo.label.toLowerCase()}.</div>
          )}
        </Panel>
      </div>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-2">
        <Panel help="predictors.heldout"
          title="Tested on the held-out women"
          how="Average precision of each predictor set on the 1,375 women the selection never saw, under four model families. The dashed line is chance. A small set that matches a large one is the practical win: fewer questions to ask."
        >
          {fv?.heldout ? (
            <DotRows
              rows={SET_ORDER.map((set) => {
                const rs = fv.heldout!.filter((r) => r.set === set);
                return {
                  key: set,
                  label: setName(set, rs[0]?.n_predictors),
                  values: Object.fromEntries(rs.map((r) => [r.model, r.AP])),
                  display: num(Math.max(...rs.map((r) => r.AP))),
                };
              }).filter((r) => Object.keys(r.values).length)}
              series={Object.keys(MODEL_COLOR)
                .filter((m) => fv.heldout!.some((r) => r.model === m))
                .map((m) => ({ key: m, label: m, color: MODEL_COLOR[m] }))}
              reference={{ value: fv.heldout[0].prevalence, label: "Chance" }}
              format={(v) => v.toFixed(2)}
              labelWidth={200}
            />
          ) : (
            <PanelLoading rows={4} />
          )}
        </Panel>

        <Panel help="predictors.frequency"
          title="How often each predictor is picked"
          how="Selection was repeated on resampled development women. The bar is the share of repeats that picked the predictor. A predictor picked every time is a stable finding; one picked half the time is a coin toss."
        >
          {fv?.frequency?.length ? (
            <RankedBars
              labelWidth={200}
              rows={fv.frequency.slice(0, 14).map((r) => ({
                key: r.predictor,
                label: label(r.predictor),
                sub: r.tier === "tier 1" ? "strongest few" : r.tier === "tier 2" ? "next tier" : undefined,
                value: r.selected_share,
                display: pct(r.selected_share),
                color: r.tier === "tier 1" ? "var(--good)" : r.tier === "tier 2" ? "var(--accent)" : "var(--faint)",
              }))}
            />
          ) : (
            <div className="px-14 py-12 text-11 text-dim leading-relaxed">
              The repeated selection was run for ANC8+ only, where the choice of predictors matters most. Switch the rung to ANC8+.
            </div>
          )}
        </Panel>
      </div>

      <Panel help="predictors.matrix"
        title="Every predictor at every rung"
        how="Rows are the 24 predictors that matter most at the chosen rung; columns are the three rungs. The shading is shared by the whole grid, so a cell can be compared with any other. A row that darkens to the right matters more for going further up the ladder."
        actions={<Segmented label="Measure" options={MEASURES} value={measure} onChange={setMeasure} />}
      >
        <MatrixHeat
          theme={theme}
          rows={matrix}
          cols={(["anc1plus", "anc4plus", "anc8plus"] as const).map((o) => ({ key: o, label: RUNG_LABEL[o] }))}
          format={(v) => pct(v, 1)}
          activeCol={outcome}
          onCol={(k) => studio.set({ rung: RUNG_OF[k as Outcome] })}
          labelWidth={230}
          cellWidth={80}
        />
      </Panel>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        {stab && (
          <Panel help="predictors.pool"
            title="Does a bigger pool help? 21 against 95 predictors"
            how="The same model (LightGBM) trained twenty times with different random seeds on the 21 predictors and on all 95. Rings: the 21; dots: the 95. The bar is the 95% interval of the difference; the count is how many of the twenty seeds favoured the bigger pool."
          >
            <DotRows
              rows={rungs.map((r) => {
                const st = a.stability[OUTCOME_OF[r]];
                return {
                  key: r,
                  label: RUNG_LABEL[r],
                  sub: `${st.AP.seeds_enhanced_better}/${st.n_seeds} seeds favour 95`,
                  values: { s21: st.AP.original_mean, s95: st.AP.enhanced_mean },
                  display: signed(st.AP.delta_mean),
                };
              })}
              series={[
                { key: "s21", label: "21 predictors", color: "var(--cross)", hollow: true },
                { key: "s95", label: "95 predictors", color: "var(--accent)" },
              ]}
              format={(v) => v.toFixed(2)}
              labelWidth={170}
              active={rung}
              onSelect={(k) => studio.set({ rung: k as Rung })}
            />
          </Panel>
        )}

        {scr && (
          <Panel help="predictors.too-good"
            title="Columns that looked too good"
            how="The survey columns with the strongest raw link to ANC8+. Nearly all were asked of only a few women (so a perfect score is an accident of small numbers) and were excluded before any model saw them."
          >
            <Table
              minWidth={420}
              rows={scr.top.slice(0, 8)}
              rowKey={(r) => r.variable}
              columns={[
                { header: "Column", cell: (r) => <span title={r.variable}>{r.label}</span> },
                { header: "Raw AUC", mono: true, cell: (r) => r.weighted_auc.toFixed(2), width: "70px" },
                {
                  header: "Why excluded",
                  cell: (r) => <span className="text-dim">{r.exclusion_reason ?? r.screen_status}</span>,
                },
              ]}
            />
          </Panel>
        )}
      </div>
    </Screen>
  );
}

/** Counts shrinking step by step, on a log scale: 6,648 and 2 on one picture. */
function SelectionFunnel({ steps }: { steps: { n: number; label: string; note: string; strong?: boolean }[] }) {
  const max = Math.log10(Math.max(...steps.map((s) => s.n), 10));
  return (
    <div className="px-14 py-12 flex flex-col gap-4">
      {steps.map((s, i) => {
        const w = Math.max(3, (Math.log10(Math.max(s.n, 1)) / max) * 100);
        const last = i === steps.length - 1;
        return (
          <div key={s.label} className="grid gap-10 items-center" style={{ gridTemplateColumns: "min(200px, 36%) minmax(0,1fr)" }}>
            <div className="min-w-0">
              <div className={`text-11 truncate ${s.strong ? "font-semibold" : ""}`}>{s.label}</div>
              <div className="text-9.5 text-faint truncate" title={s.note}>{s.note}</div>
            </div>
            <div className="flex items-center gap-8 min-w-0">
              <div
                className="h-18 rounded-2 transition-all duration-700"
                style={{
                  width: `${w}%`,
                  background: last ? "var(--good)" : i >= steps.length - 2 ? "var(--accent)" : "var(--rung1)",
                  opacity: last || i >= steps.length - 2 ? 1 : 0.55 + (i / steps.length) * 0.45,
                }}
              />
              <span className="font-mono text-11 font-semibold whitespace-nowrap">{s.n.toLocaleString()}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
