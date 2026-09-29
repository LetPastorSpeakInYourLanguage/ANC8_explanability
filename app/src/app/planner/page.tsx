"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type { FeatureCollection } from "geojson";
import { RotateCcw } from "lucide-react";
import DotRows from "@/components/charts/DotRows";
import MatrixHeat from "@/components/charts/MatrixHeat";
import RankedBars from "@/components/charts/RankedBars";
import FixedVsAdjustable from "@/components/planner/FixedVsAdjustable";
import { useRenderTheme } from "@/components/shell/theme-provider";
import { DataNote,
  InlineError, Note, Panel, PanelLoading, Screen, Segmented, StatTile, Table, Tag,
} from "@/components/studio/ui";
import { Input } from "@/components/ui/input";
import { classify, colorOf, inkOn } from "@/lib/colors";
import { useJSON } from "@/lib/data";
import { RUNG_COLOR, RUNG_LABEL, pct, signed } from "@/lib/explore";
import { REGION_NAMES } from "@/lib/regions";
import type { RegionsData } from "@/lib/regionsData";
import {
  EARLY, MODEL_SHORT, S_RUNGS, allocate, eligibleShare, forModel, formatCoverage, leverWeight, parseCoverage, project,
  type Coverage, type SRung, type ScenarioData,
} from "@/lib/scenario";
import { useStudio } from "@/lib/studio";

const RegionMap = dynamic(() => import("@/components/map/RegionMap"), {
  ssr: false,
  loading: () => <div className="h-[380px] bg-panel2" />,
});

// Placeholder unit costs, birr per woman reached, for the allocator to have something
// to work with. The page labels them as examples to replace.
const EXAMPLE_COST: Record<string, number> = {
  healthpost: 2500, hospital: 5000, insurance: 800, intention: 400, [EARLY]: 150,
  barriers: 600, information: 100, agency: 300,
};

const fmtN = (v: number) =>
  Math.abs(v) >= 1e6 ? `${(v / 1e6).toFixed(2)}M` : Math.abs(v) >= 1e4 ? `${Math.round(v / 1e3)}k` : Math.round(v).toLocaleString();
const pts = (v: number, d = 1) => `${v >= 0 ? "+" : "−"}${Math.abs(v * 100).toFixed(d)}`;

export default function PlannerPage() {
  const studio = useStudio();
  const theme = useRenderTheme();
  const sc = useJSON<ScenarioData>("/data/scenarios.json");
  const reg = useJSON<RegionsData>("/data/regions.json");
  const geo = useJSON<FeatureCollection>("/geo/regions.geojson");
  const [showAll, setShowAll] = useState(false);
  const [budget, setBudget] = useState(500_000_000);
  const [costs, setCosts] = useState<Record<string, number>>(EXAMPLE_COST);
  const [target, setTarget] = useState(0.3);

  const cov: Coverage = parseCoverage(studio.params.get("lv"));
  const setCov = (k: string, v: number) => studio.set({ lv: formatCoverage({ ...cov, [k]: v }) });
  const rung: SRung = studio.rung;
  const scope = studio.region || "Ethiopia";
  // Which model scores the levers: explainable boosting or logistic regression.
  const models = Object.keys(sc.data?.by_model ?? {});
  const lmAsked = studio.params.get("lm") ?? "";
  const lm = models.includes(lmAsked) ? lmAsked : sc.data?.primary ?? models[0] ?? "";

  const view = useMemo(() => {
    if (!sc.data || !reg.data) return null;
    const d = forModel(sc.data, lm);
    const now = (r: string | null) => {
      const c = r ? reg.data!.cohorts.recent.regions[r] : reg.data!.cohorts.recent.national;
      return { anc1: c.reach1, anc4: c.reach4, anc8: c.reach8 };
    };
    const byRegion = Object.fromEntries(
      REGION_NAMES.map((r) => [r, project(d, d.regions.indexOf(r), now(r), cov)]),
    );
    const national = project(d, d.regions.length - 1, now(null), cov);
    const births = Object.fromEntries(REGION_NAMES.map((r) => [r, reg.data!.population.regions[r]?.births ?? 0]));
    const gained = Object.fromEntries(
      S_RUNGS.map((k) => [k, REGION_NAMES.reduce((s, r) => s + byRegion[r].change[k] * births[r], 0)]),
    ) as Record<SRung, number>;
    // the same scenario under every lever model, for the comparison
    const byModel = Object.fromEntries(models.map((m) => {
      const dm = forModel(sc.data!, m);
      return [m, {
        national: project(dm, dm.regions.length - 1, now(null), cov),
        byRegion: Object.fromEntries(REGION_NAMES.map((r) => [r, project(dm, dm.regions.indexOf(r), now(r), cov)])),
      }];
    }));
    return { byRegion, national, births, gained, byModel };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sc.data, reg.data, studio.params.get("lv"), lm]);

  const err = sc.error ?? reg.error ?? geo.error;
  if (err) return <Screen><InlineError message={err} /></Screen>;
  if (!sc.data || !reg.data || !view) return <Screen><PanelLoading rows={10} /></Screen>;
  const d = forModel(sc.data, lm);
  const modelPicker = models.length > 1 ? (
    <Segmented label="Levers from" options={models.map((m) => ({ key: m, label: m === "ebm" ? "Boosting" : "Logistic", title: MODEL_SHORT[m] }))}
      value={lm} onChange={(k) => studio.set({ lm: k })} />
  ) : null;
  const ri = d.regions.indexOf(scope);
  const P = studio.region ? view.byRegion[studio.region] : view.national;

  const levers = [
    ...d.levers.filter((l) => l.supported),
    { key: EARLY, label: "Earlier first visit (first trimester)", who: d.early_visit.who, supported: true, models_agree: true, concept: "timing" },
  ];
  const unsupported = d.levers.filter((l) => !l.supported);
  const shown = showAll ? [...levers, ...unsupported] : levers;
  const active = Object.values(cov).some((v) => v > 0);

  // map: the scenario's change on the chosen rung
  const vals = REGION_NAMES.map((r) => view.byRegion[r].change[rung]);
  const classes = classify(vals.map((v) => (v > 0 ? v : null)), "good", theme);
  const mapData = Object.fromEntries(
    REGION_NAMES.map((r, i) => {
      const fill = vals[i] > 0.0005 ? colorOf(vals[i], classes, theme) : theme === "dark" ? "#1f2830" : "#dfe5ec";
      return [r, { value: vals[i] > 0.0005 ? pts(vals[i], 1) : "", fill, ink: inkOn(fill, theme) }];
    }),
  );

  const supportedKeys = levers.map((l) => l.key).filter((k) => k !== EARLY || rung !== "anc1");
  const alloc = allocate(d, rung, budget, costs, view.births, supportedKeys.filter((k) => k !== EARLY));
  const gap = reg.data.gap?.full?.[rung];

  return (
    <Screen>
      <div data-help="planner.tiles" className="grid gap-10 grid-cols-2 lg:grid-cols-4">
        {S_RUNGS.map((k) => (
          <StatTile
            key={k}
            label={`${RUNG_LABEL[k]} · ${scope}`}
            value={pct(P.then[k], 1)}
            sub={`now ${pct(P.now[k], 1)} · ${active ? `${pts(P.change[k])} points` : "move a lever"}`}
            tone={P.change[k] > 0.001 ? "good" : undefined}
            active={rung === k}
            onClick={() => studio.set({ rung: k })}
          />
        ))}
        <StatTile
          label={`More women reaching ${RUNG_LABEL[rung]} each year`}
          value={fmtN(view.gained[rung])}
          sub="across the 14 regions, from UN population estimates of births"
          tone="accent"
        />
      </div>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-[minmax(0,430px)_minmax(0,1fr)]">
        <Panel help="planner.levers"
          title={`Levers · ${scope}`}
          how="Each slider is the share of the women a lever could move who are actually reached. Under each lever: who it applies to in the current scope, and its weight, the change the model expects on each rung if all of them are reached (with the 95% band). Levers combine exactly, not by adding up. The switch chooses the model that scores them. Association-based: what the model expects if circumstances changed, not what a programme would cause."
          actions={
            <span className="flex items-center gap-8">
            {modelPicker}
            <button type="button" onClick={() => studio.set({ lv: undefined })} className="text-faint hover:text-accent"
              title="Clear all levers" aria-label="Clear all levers">
              <RotateCcw className="size-12" />
            </button>
            </span>
          }
        >
          <div className="flex flex-col">
            {shown.map((l) => {
              const w = leverWeight(d, l.key, ri);
              const v = cov[l.key] ?? 0;
              return (
                <div key={l.key} className={`px-14 py-10 border-b border-border last:border-b-0 ${l.supported ? "" : "bg-panel2"}`}>
                  <div className="flex items-baseline gap-8">
                    <span className="text-11 font-semibold flex-1 min-w-0">{l.label}</span>
                    {!l.supported && <Tag tone="warn">not supported</Tag>}
                    <span className="font-mono text-11 font-semibold w-40 text-right">{Math.round(v * 100)}%</span>
                  </div>
                  <div className="text-9.5 text-faint mt-1">
                    {pct(eligibleShare(d, l.key, ri), 0)} of women: {l.who}
                  </div>
                  <input type="range" min={0} max={100} step={5} value={Math.round(v * 100)}
                    onChange={(e) => setCov(l.key, Number(e.target.value) / 100)}
                    aria-label={l.label} className="w-full h-16 mt-4 accent-[var(--accent)] cursor-pointer" />
                  <div className="grid grid-cols-3 gap-6 mt-3">
                    {S_RUNGS.map((k) => {
                      const x = w[k];
                      return (
                        <div key={k} className="min-w-0" title={x ? `${RUNG_LABEL[k]}: ${pts(x.v, 2)} points (${pts(x.lo, 2)} to ${pts(x.hi, 2)}) if every eligible woman is reached` : "not defined"}>
                          <div className="flex items-baseline gap-4">
                            <span className="text-9.5 text-faint">{RUNG_LABEL[k]}</span>
                            <span className={`font-mono text-10 font-semibold ${x && x.v < 0 ? "text-bad" : ""}`}>{x ? pts(x.v) : "–"}</span>
                          </div>
                          <WeightBar x={x} color={RUNG_COLOR[k]} />
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="px-14 py-10 border-t border-border flex items-center gap-8">
            <button type="button" onClick={() => setShowAll((s) => !s)} className="text-10.5 text-accent hover:underline">
              {showAll ? "Hide" : "Show"} the {unsupported.length} levers the data do not support
            </button>
          </div>
        </Panel>

        <div className="flex flex-col gap-10 md:gap-14 min-w-0">
          <Panel help="planner.where"
            title={`Where the scenario moves ${RUNG_LABEL[rung]}`}
            how="Each region shaded by the change the scenario brings on the chosen rung, in percentage points; the list ranks regions by women gained per year (the change times the region's births). Grey: no change. Click a region to plan for it alone."
            actions={
              <Segmented label="Rung" options={S_RUNGS.map((k) => ({ key: k, label: RUNG_LABEL[k] }))} value={rung}
                onChange={(k) => studio.set({ rung: k })} />
            }
          >
            <div className="grid lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
              {geo.data ? (
                <RegionMap geo={geo.data} data={mapData} selected={studio.region} basemap={false} theme={theme} labels
                  onSelect={(r) => studio.set({ region: r === studio.region ? "" : r })} height={380} />
              ) : (
                <div className="h-[380px] bg-panel2" />
              )}
              <div className="lg:border-l border-border min-w-0">
                {active ? (
                  <RankedBars
                    labelWidth={140}
                    valueWidth={64}
                    active={studio.region}
                    onSelect={(r) => studio.set({ region: r === studio.region ? "" : r })}
                    rows={REGION_NAMES.map((r) => ({
                      key: r,
                      label: r,
                      sub: `${pct(view.byRegion[r].now[rung], 0)} → ${pct(view.byRegion[r].then[rung], 0)}`,
                      value: view.byRegion[r].change[rung] * view.births[r],
                      display: fmtN(view.byRegion[r].change[rung] * view.births[r]),
                      color: RUNG_COLOR[rung],
                    })).sort((a, b) => (b.value ?? 0) - (a.value ?? 0))}
                  />
                ) : (
                  <div className="px-14 py-14 text-11 text-dim leading-relaxed">
                    Move a lever to see which regions gain. Each lever&apos;s weight, the change it brings if every woman it applies to is
                    reached, is shown under its slider.
                  </div>
                )}
              </div>
            </div>
          </Panel>

          <Panel help="planner.grid"
            title="Every region, every rung"
            how="The scenario's change for each region on each rung, in percentage points, with one shading for the whole grid. Clicking a region plans for it."
          >
            <MatrixHeat
              theme={theme}
              rows={REGION_NAMES.map((r) => ({
                key: r,
                label: r,
                values: Object.fromEntries(S_RUNGS.map((k) => [k, active ? view.byRegion[r].change[k] : null])),
              }))}
              cols={S_RUNGS.map((k) => ({ key: k, label: RUNG_LABEL[k] }))}
              format={(v) => pts(v)}
              active={studio.region}
              activeCol={rung}
              onRow={(r) => studio.set({ region: r === studio.region ? "" : r })}
              onCol={(k) => studio.set({ rung: k as SRung })}
              labelWidth={150}
              cellWidth={70}
            />
          </Panel>
        </div>
      </div>

      {models.length > 1 && (
        <Panel help="planner.models"
          title={`The two models side by side · ${scope} · ${RUNG_LABEL[rung]}`}
          how="Each lever's weight (the change on the chosen rung if every woman it applies to is reached) under explainable boosting and under logistic regression, in the current scope. Close dots: the models agree. The last row is your current scenario under both. Where they part, the answer rests on how the model bends, not on the data alone."
        >
          <DotRows
            rows={[
              ...sc.data.levers.map((l) => {
                const vals = Object.fromEntries(models.map((m) => [m, leverWeight(forModel(sc.data!, m), l.key, ri)[rung]?.v ?? null]));
                const [a, b] = models.map((m) => vals[m]);
                return {
                  key: l.key, label: l.label,
                  sub: a != null && b != null && (a > 0) !== (b > 0) ? `the models disagree on direction at ${RUNG_LABEL[rung]}` : undefined,
                  values: vals,
                  display: a != null && b != null ? pts(a - b, 2) : "–",
                };
              }),
              ...(active ? [{
                key: "scenario", label: "Your scenario",
                values: Object.fromEntries(models.map((m) => [m,
                  studio.region ? view.byModel[m].byRegion[studio.region].change[rung] : view.byModel[m].national.change[rung]])),
                display: "",
              }] : []),
            ]}
            series={models.map((m, i) => ({ key: m, label: MODEL_SHORT[m], color: i === 0 ? "var(--accent)" : "var(--cross)", hollow: m !== lm }))}
            reference={{ value: 0, label: "No change" }}
            format={(v) => pts(v, 1)}
            labelWidth={230}
          />
          <DataNote>Solid: the model the page is using; change it with the switch on the Levers panel. At the right: explainable boosting minus logistic regression, in points.</DataNote>
        </Panel>
      )}

      <FixedVsAdjustable reg={reg.data} sc={d} rung={rung} region={studio.region} cov={cov} setCov={setCov} model={lm} />

      <div className="grid gap-10 md:gap-14 xl:grid-cols-2">
        <Panel help="planner.budget"
          title={`Spend a budget · ${RUNG_LABEL[rung]}`}
          how="The budget is spent a tenth of a lever's women at a time, always on the region and lever that buys the most additional women on the chosen rung per birr, reaching the women who gain most first. The costs below are placeholders: replace them with your own. Levers are counted separately, so the total is an upper bound."
        >
          <div className="px-14 py-10 grid grid-cols-2 sm:grid-cols-3 gap-8 border-b border-border">
            <label className="col-span-2 sm:col-span-3">
              <span className="text-10.5 font-medium">Budget (birr)</span>
              <Input type="number" value={budget} min={0} step={10_000_000} onChange={(e) => setBudget(Math.max(0, Number(e.target.value) || 0))}
                className="mt-2 font-mono" />
            </label>
            {levers.filter((l) => l.key !== EARLY).map((l) => (
              <label key={l.key} className="min-w-0">
                <span className="text-9.5 text-dim truncate block" title={l.label}>{l.label}</span>
                <Input type="number" value={costs[l.key] ?? 0} min={0} step={50}
                  onChange={(e) => setCosts((c) => ({ ...c, [l.key]: Math.max(0, Number(e.target.value) || 0) }))}
                  className="mt-2 font-mono h-22 text-10.5" />
              </label>
            ))}
          </div>
          <div className="grid grid-cols-2 border-b border-border">
            <div className="px-14 py-10 border-r border-border">
              <div className="text-9.5 uppercase tracking-label text-faint font-semibold">More women reaching {RUNG_LABEL[rung]}</div>
              <div className="font-mono text-19 font-semibold text-good mt-2">{fmtN(alloc.women)}</div>
              <div className="text-9.5 text-dim">per year of births</div>
            </div>
            <div className="px-14 py-10">
              <div className="text-9.5 uppercase tracking-label text-faint font-semibold">Spent</div>
              <div className="font-mono text-19 font-semibold mt-2">{fmtN(alloc.spent)}</div>
              <div className="text-9.5 text-dim">birr of {fmtN(budget)}</div>
            </div>
          </div>
          {alloc.rows.length ? (
            <Table
              minWidth={420}
              rows={alloc.rows.slice(0, 12)}
              rowKey={(r) => `${r.region}|${r.lever}`}
              isActive={(r) => r.region === studio.region}
              onRowClick={(r) => studio.set({ region: r.region })}
              columns={[
                { header: "Region", cell: (r) => r.region },
                { header: "Lever", cell: (r) => <span className="text-dim">{levers.find((l) => l.key === r.lever)?.label}</span> },
                { header: "Reach", mono: true, cell: (r) => pct(r.coverage) },
                { header: "Women", mono: true, cell: (r) => fmtN(r.women) },
                { header: "Birr / woman", mono: true, cell: (r) => fmtN(r.cost / Math.max(r.women, 1)) },
              ]}
            />
          ) : (
            <div className="px-14 py-12 text-11 text-dim">Nothing affordable at these costs.</div>
          )}
          <DataNote>The Ministry&apos;s own unit costs would replace the placeholders, and the allocation would become a costed plan.</DataNote>
        </Panel>

        <div className="flex flex-col gap-10 md:gap-14 min-w-0">
          <Panel help="planner.target"
            title={`Who reaches a target · ${RUNG_LABEL[rung]}`}
            how="Rings: each region now (24-month cohort). Dots: under the current scenario. The dashed line is the target. A region reaches it when its dot crosses the line."
            actions={
              <label className="flex items-center gap-6 text-10.5">
                Target
                <input type="range" min={0.1} max={0.95} step={0.05} value={target} onChange={(e) => setTarget(Number(e.target.value))}
                  className="w-90 accent-[var(--accent)]" aria-label="Target" />
                <span className="font-mono font-semibold w-32">{pct(target)}</span>
              </label>
            }
          >
            <DotRows
              rows={[...REGION_NAMES]
                .sort((a, b) => view.byRegion[b].then[rung] - view.byRegion[a].then[rung])
                .map((r) => {
                  const p = view.byRegion[r];
                  const hit = p.then[rung] >= target;
                  return {
                    key: r,
                    label: r,
                    values: { now: p.now[rung], then: p.then[rung] },
                    display: hit ? <span className="text-good">reached</span> : `${pts(target - p.then[rung], 0)} pt`,
                  };
                })}
              series={[
                { key: "now", label: "Now", color: "var(--dim)", hollow: true },
                { key: "then", label: "With the scenario", color: RUNG_COLOR[rung] },
              ]}
              reference={{ value: target, label: "Target" }}
              domain={[0, 1]}
              ticks={[0, 0.25, 0.5, 0.75, 1]}
              format={(v) => pct(v)}
              active={studio.region}
              onSelect={(r) => studio.set({ region: r === studio.region ? "" : r })}
              labelWidth={150}
              valueWidth={64}
            />
          </Panel>

          {gap && (
            <Panel help="planner.gap"
              title={`Doing better or worse than its women's circumstances predict · ${RUNG_LABEL[rung]}`}
              how="For each region, the share reaching the rung minus what the model predicts from its women's circumstances alone (full cohort). Right of zero: the region does better than its population would suggest, a place to learn from. Left: something about the region itself, services, conflict or geography, holds women back beyond their circumstances."
            >
              <RankedBars
                signed
                labelWidth={150}
                active={studio.region}
                onSelect={(r) => studio.set({ region: r === studio.region ? "" : r })}
                rows={REGION_NAMES.filter((r) => gap[r]).map((r) => ({
                  key: r,
                  label: r,
                  sub: `${pct(gap[r].actual, 0)} actual, ${pct(gap[r].expected, 0)} expected`,
                  value: gap[r].gap,
                  display: `${signed(gap[r].gap * 100, 1)} pt`,
                  color: gap[r].gap >= 0 ? "var(--good)" : "var(--bad)",
                })).sort((a, b) => (b.value ?? 0) - (a.value ?? 0))}
              />
            </Panel>
          )}
        </div>
      </div>

      <Panel help="planner.unsupported"
        title="Levers the data do not support"
        how="Levers where the chosen model expects at least one rung to fall, not rise, when the lever is applied. Every lever model is shown. These are associations: women who listen to the radio weekly, for example, are no more likely to use ANC in this survey, once everything else about them is known. They are not evidence that the programmes would harm; they are evidence that the survey cannot show they would help."
      >
        <Table
          minWidth={620}
          rows={unsupported}
          rowKey={(l) => l.key}
          columns={[
            { header: "Lever", cell: (l) => l.label },
            ...S_RUNGS.map((k) => ({
              header: `${RUNG_LABEL[k]} · ${models.map((m) => (m === "ebm" ? "EBM" : "LR")).join(" / ")}`,
              mono: true,
              cell: (l: (typeof unsupported)[number]) => {
                const i = d.levers.findIndex((x) => x.key === l.key);
                const vals = models.map((m) => sc.data!.by_model![m].rungs[k].gain[d.regions.length - 1][i]);
                return (
                  <span>
                    {vals.map((v, j) => (
                      <span key={j} className={j === 0 ? (v < 0 ? "text-bad" : "") : "text-faint"}>{j > 0 ? " / " : ""}{pts(v)}</span>
                    ))}
                  </span>
                );
              },
            })),
          ]}
        />
        <div className="px-14 py-10">
          <Note tone="warn">
            Every number on this page is association-based: g-computation with the fitted models, not the effect of a programme. Bands come
            from {d.bootstrap_resamples} cluster resamples of who lives where; they do not include the uncertainty in the model itself.
          </Note>
        </div>
        <DataNote>Results from programmes actually delivered (enrolment drives, new health posts, family-planning outreach), with ANC counts before and after, would turn these associations into effect estimates.</DataNote>
      </Panel>
    </Screen>
  );
}

/** A lever's weight on one rung: the bar is the effect at full reach, the whisker its band. */
function WeightBar({ x, color }: { x: { v: number; lo: number; hi: number } | null; color: string }) {
  // Most levers move a rung by under a point; the earlier first visit by ten. The scale
  // is set for the small ones and the large one runs off the end of its track.
  const MAX = 0.03;
  if (!x) return <div className="h-6 mt-2" />;
  const pos = (v: number) => `${50 + (Math.max(-MAX, Math.min(MAX, v)) / MAX) * 50}%`;
  return (
    <div className="relative h-6 mt-2 rounded-full bg-panel3">
      <div className="absolute inset-y-0 left-1/2 w-px bg-border2" />
      <div className="absolute inset-y-0 rounded-full transition-all duration-500"
        style={{ left: x.v >= 0 ? "50%" : pos(x.v), width: `calc(${pos(Math.abs(x.v))} - 50%)`, background: x.v >= 0 ? color : "var(--bad)" }} />
      <div className="absolute -inset-y-1 border-x border-text opacity-40" style={{ left: pos(x.lo), width: `calc(${pos(x.hi)} - ${pos(x.lo)})` }} />
    </div>
  );
}
