"use client";

import { Lock, SlidersHorizontal } from "lucide-react";
import RankedBars from "@/components/charts/RankedBars";
import { DataNote, Panel, Tag } from "@/components/studio/ui";
import { RUNG_LABEL } from "@/lib/explore";
import { REGION_NAMES } from "@/lib/regions";
import type { RegionsData } from "@/lib/regionsData";
import { leverWeight, type Coverage, type SRung, type ScenarioData } from "@/lib/scenario";

/**
 * The feature filter: what holds a region back, split into what a ministry cannot
 * move directly (wealth, region, schooling, culture, household, history, work),
 * which every scenario holds fixed, and what programmes can move, each with its
 * own slider on the same shared scenario as the rest of the planner.
 *
 * The split is exact: the chosen additive model (explainable boosting or logistic
 * regression, the planner's switch) predicts a sum of terms,
 * so the gap between a region's average and the country's is the sum of each
 * concept's gap. Terms are on the log-odds scale; they are shown as approximate
 * percentage points at the national level of the rung.
 */
export default function FixedVsAdjustable({
  reg, sc, rung, region, cov, setCov, model,
}: {
  reg: RegionsData;
  sc: ScenarioData;
  rung: SRung;
  region: string;
  cov: Coverage;
  setCov: (key: string, v: number) => void;
  /** The lever model: "ebm" or "logistic". */
  model?: string;
}) {
  const dr = ((model && reg.drivers_by_model?.[model]) || reg.drivers)[rung];
  const p = dr.national_predicted;
  const toPts = (lo: number) => lo * p * (1 - p);
  const concepts = reg.concepts;

  // A region: its own gap from the country. The country: how much each concept
  // separates the regions (average absolute gap, weighted by births).
  const value = (key: string): number => {
    if (region) return toPts(dr.regions[region]?.concepts[key] ?? 0);
    let s = 0, w = 0;
    for (const r of REGION_NAMES) {
      const b = reg.population.regions[r]?.births ?? 0;
      s += b * Math.abs(dr.regions[r]?.concepts[key] ?? 0);
      w += b;
    }
    return toPts(w ? s / w : 0);
  };
  const rows = concepts.map((c) => ({ ...c, v: value(c.key) }));
  const fixed = rows.filter((c) => !c.modifiable);
  const adjustable = rows.filter((c) => c.modifiable);

  // Share of what holds the region back (or, for the country, of what separates
  // regions) that sits in the adjustable concepts.
  const sign = region ? (rows.reduce((s, c) => s + c.v, 0) < 0 ? -1 : 1) : 1;
  const mass = (xs: typeof rows) => xs.reduce((s, c) => s + Math.max(0, sign * c.v), 0);
  const total = mass(rows) || 1;
  const adjShare = mass(adjustable) / total;
  const ri = sc.regions.indexOf(region || "Ethiopia");

  return (
    <Panel help="planner.fixed"
      title={`What can move and what cannot · ${region || "between regions"} · ${RUNG_LABEL[rung]}`}
      how={region
        ? `Why ${region}'s predicted ${RUNG_LABEL[rung]} differs from Ethiopia's, split exactly across groups of circumstances by the explainable boosting model, in approximate percentage points. Left: circumstances a ministry cannot change directly, held fixed in every scenario. Right: circumstances programmes can move; their sliders are the planner's own, so the map and charts above change as you drag.`
        : "How much each group of circumstances separates the regions from one another (the births-weighted average gap, in approximate percentage points). Pick a region on the map to see what holds that region back."}
    >
      <div className="px-14 py-10 border-b border-border">
        <div className="flex items-center gap-8 text-11">
          <span className="flex-1">
            {region ? `Of what ${sign < 0 ? "holds" : "lifts"} ${region} ${sign < 0 ? "below" : "above"} the country` : "Of what separates the regions"},{" "}
            <b className="font-mono">{Math.round(adjShare * 100)}%</b> is in circumstances programmes can move.
          </span>
        </div>
        <div className="flex h-10 mt-6 rounded-2 overflow-hidden" aria-hidden>
          <div className="bg-border2 transition-all duration-500" style={{ width: `${(1 - adjShare) * 100}%` }} />
          <div className="bg-accent transition-all duration-500" style={{ width: `${adjShare * 100}%` }} />
        </div>
        <div className="flex justify-between text-9.5 text-faint mt-2">
          <span>held fixed</span>
          <span>adjustable</span>
        </div>
      </div>
      <div className="grid md:grid-cols-2">
        <div className="md:border-r border-border min-w-0">
          <div className="px-14 pt-10 flex items-center gap-6 text-10 font-semibold uppercase tracking-label text-faint">
            <Lock className="size-11" /> Held fixed in every scenario
          </div>
          <RankedBars
            signed={!!region}
            labelWidth={170}
            rows={fixed
              .sort((a, b) => Math.abs(b.v) - Math.abs(a.v))
              .map((c) => ({ key: c.key, label: c.label, value: c.v, display: fmtPts(c.v, !!region), color: "var(--faint)" }))}
          />
        </div>
        <div className="min-w-0">
          <div className="px-14 pt-10 flex items-center gap-6 text-10 font-semibold uppercase tracking-label text-accent">
            <SlidersHorizontal className="size-11" /> Adjustable by programmes
          </div>
          <div className="px-10 py-6 flex flex-col">
            {adjustable
              .sort((a, b) => Math.abs(b.v) - Math.abs(a.v))
              .map((c) => {
                const lever = sc.levers.find((l) => l.key === c.key);
                const cv = cov[c.key] ?? 0;
                const w = lever ? leverWeight(sc, c.key, ri)[rung] : null;
                return (
                  <div key={c.key} className="px-6 py-5 border-b border-border last:border-b-0">
                    <div className="flex items-baseline gap-6">
                      <span className="text-10.5 font-medium flex-1 min-w-0 truncate" title={c.label}>{c.label}</span>
                      <span className={`font-mono text-10 ${c.v < 0 ? "text-bad" : "text-good"}`}>{fmtPts(c.v, !!region)}</span>
                    </div>
                    {lever ? (
                      <div className="flex items-center gap-8 mt-2">
                        <input type="range" min={0} max={100} step={5} value={Math.round(cv * 100)}
                          onChange={(e) => setCov(c.key, Number(e.target.value) / 100)}
                          aria-label={`${lever.label}: share reached`} className="flex-1 h-14 accent-[var(--accent)] cursor-pointer" />
                        <span className="font-mono text-10 w-32 text-right">{Math.round(cv * 100)}%</span>
                        {lever.supported ? (
                          <span className={`font-mono text-10 w-52 text-right ${w && w.v * cv > 0.0005 ? "text-good" : "text-faint"}`}>
                            {w ? `${w.v * cv >= 0 ? "+" : "−"}${Math.abs(w.v * cv * 100).toFixed(1)} pt` : "–"}
                          </span>
                        ) : (
                          <Tag tone="warn">not supported</Tag>
                        )}
                      </div>
                    ) : null}
                  </div>
                );
              })}
          </div>
        </div>
      </div>
      <DataNote className="px-14 py-8 border-t border-border">
        With facility data (staffing, stock-outs, opening hours, quality of care), the adjustable side could include the services
        themselves, which this survey does not record; today it holds only the women&apos;s own circumstances.
      </DataNote>
    </Panel>
  );
}

function fmtPts(v: number, signed: boolean): string {
  const s = Math.abs(v * 100).toFixed(1);
  return signed ? `${v >= 0 ? "+" : "−"}${s} pt` : `${s} pt`;
}
