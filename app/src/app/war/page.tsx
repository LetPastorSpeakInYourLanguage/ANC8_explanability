"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import type { FeatureCollection } from "geojson";
import { Pause, Play, RotateCcw } from "lucide-react";
import {
  Area, CartesianGrid, ComposedChart, Line, ReferenceArea, ReferenceLine, Tooltip, XAxis, YAxis,
} from "recharts";
import DotRows from "@/components/charts/DotRows";
import { AXIS, ChartBox, GRID, SeriesLegend, TipPanel, tip } from "@/components/charts/rc";
import { useRenderTheme } from "@/components/shell/theme-provider";
import { DataNote,
  InlineError, Note, Panel, PanelLoading, Range, Screen, Segmented, StatTile, Tag,
} from "@/components/studio/ui";
import { NO_DATA, inkOn } from "@/lib/colors";
import { useJSON } from "@/lib/data";
import { RUNG_COLOR, RUNG_LABEL, pct, signed } from "@/lib/explore";
import { REGION_NAMES } from "@/lib/regions";
import type { RegionsData } from "@/lib/regionsData";
import { useStudio } from "@/lib/studio";
import { WAR_RUNGS, simulate, summarise, type Scenario, type WarData, type WarRung } from "@/lib/war";

const RegionMap = dynamic(() => import("@/components/map/RegionMap"), {
  ssr: false,
  loading: () => <div className="h-[420px] bg-panel2" />,
});

const HORIZON = 24;
const START = 1;
// Drops in percentage points, five classes: the map reads as "how much is lost here now".
const DROP_BREAKS = [0.01, 0.03, 0.06, 0.1];
const DROP_RAMP = {
  light: ["#f8e4e5", "#eeb2b4", "#d97a7d", "#bd4a4e", "#8f2528"],
  dark: ["#31191b", "#5a2729", "#8e3a3d", "#c7575b", "#f0999b"],
};
const TAUS = [0, 6, 12, 24];

const fmtN = (v: number) =>
  Math.abs(v) >= 1e6 ? `${(v / 1e6).toFixed(2)}M` : Math.abs(v) >= 1e4 ? `${Math.round(v / 1e3)}k` : Math.round(v).toLocaleString();
/** A band of women lost; a lower end below zero means the band includes no loss. */
const band = (lo: number, hi: number) => `${lo <= 0 ? "none" : fmtN(lo)}–${fmtN(hi)}`;
const qLabel = (q: number) => `Y${Math.floor(q / 4) + 1} Q${(q % 4) + 1}`;

export default function WarPage() {
  const studio = useStudio();
  const theme = useRenderTheme();
  const war = useJSON<WarData>("/data/war.json");
  const reg = useJSON<RegionsData>("/data/regions.json");
  const geo = useJSON<FeatureCollection>("/geo/regions.geojson");

  // The scenario lives in the address bar, so a configured scenario can be sent as a link.
  const P = studio.params;
  const affected = (P.get("hit") ?? (studio.region || "Amhara")).split(",").filter((r) => REGION_NAMES.includes(r));
  const pattern = (P.get("pattern") === "adapt" ? "adapt" : "siege") as Scenario["pattern"];
  const durationQ = clampInt(Number(P.get("dur") ?? 8), 1, 12);
  const intensity = clampNum(Number(P.get("int") ?? 1), 0, 1.5);
  const restored = P.get("restored") !== "no";
  // Number(null) is 0, a valid lag: read the parameter only when it is there.
  const tauParam = P.get("tau");
  const tau = tauParam != null && TAUS.includes(Number(tauParam)) ? Number(tauParam) : war.data?.fit.tau ?? 12;
  const setP = (patch: Record<string, string | undefined>) => studio.set(patch);

  const [q, setQ] = useState(START + 3);
  const [playing, setPlaying] = useState(false);
  const rung: WarRung = studio.rung;
  const focus = affected.includes(studio.region) ? studio.region : affected[0] ?? "";

  const scenario: Scenario | null = war.data
    ? {
        startQ: START, durationQ, intensity, pattern, restored, tau,
        kappa: war.data.backtest.kappa_fit ?? 2, horizonQ: HORIZON,
      }
    : null;

  const runs = useMemo(() => {
    if (!war.data || !reg.data || !scenario) return null;
    const out: Record<string, { path: ReturnType<typeof simulate>; base: Record<WarRung, number>; sum: ReturnType<typeof summarise> }> = {};
    for (const r of affected) {
      const c = reg.data.cohorts.recent.regions[r];
      if (!c) continue;
      const base = { anc1: c.reach1, anc4: c.reach4, anc8: c.reach8 };
      const path = simulate(war.data, scenario, base);
      out[r] = { path, base, sum: summarise(path, base, reg.data.population.regions[r]?.births ?? 0, scenario) };
    }
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [war.data, reg.data, affected.join(","), durationQ, intensity, pattern, restored, tau]);

  useEffect(() => {
    if (!playing) return;
    const t = setInterval(() => setQ((x) => (x + 1) % HORIZON), 650);
    return () => clearInterval(t);
  }, [playing]);

  const err = war.error ?? reg.error ?? geo.error;
  if (err) return <Screen><InlineError message={err} /></Screen>;
  if (!war.data || !reg.data || !runs || !scenario) return <Screen><PanelLoading rows={10} /></Screen>;
  const W = war.data;

  const total = WAR_RUNGS.reduce(
    (acc, k) => ({
      ...acc,
      [k]: Object.values(runs).reduce((s, r) => s + r.sum.lost[k], 0),
      [`${k}_lo`]: Object.values(runs).reduce((s, r) => s + r.sum.lostLo[k], 0),
      [`${k}_hi`]: Object.values(runs).reduce((s, r) => s + r.sum.lostHi[k], 0),
    }),
    {} as Record<string, number>,
  );
  const f = runs[focus];
  const endQ = START + durationQ;

  const mapData = Object.fromEntries(
    REGION_NAMES.map((r) => {
      const run = runs[r];
      if (!run) return [r, { value: "", fill: NO_DATA[theme], ink: inkOn(NO_DATA[theme], theme) }];
      const drop = run.base[rung] - run.path[q].p[rung];
      let i = 0;
      while (i < DROP_BREAKS.length && drop > DROP_BREAKS[i]) i++;
      const fill = DROP_RAMP[theme][i];
      return [r, { value: drop >= 0.005 ? `−${(drop * 100).toFixed(0)}` : "0", fill, ink: inkOn(fill, theme) }];
    }),
  );

  const toggle = (r: string) => {
    const next = affected.includes(r) ? affected.filter((x) => x !== r) : [...affected, r];
    setP({ hit: next.length ? next.join(",") : "none" });
  };

  const traj = f?.path.map((r) => ({
    q: r.q,
    ...Object.fromEntries(WAR_RUNGS.flatMap((k) => [[k, r.p[k]], [`${k}_band`, [r.lo[k], r.hi[k]]]])),
  }));

  return (
    <Screen>
      <div data-help="war.tiles" className="grid gap-10 grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="More women with no ANC at all"
          value={fmtN(total.anc1)}
          sub={`${band(total.anc1_lo, total.anc1_hi)} over ${HORIZON / 4} years · ${affected.length} region${affected.length === 1 ? "" : "s"}`}
          tone="bad"
          active={rung === "anc1"}
          onClick={() => studio.set({ rung: "anc1" })}
        />
        <StatTile
          label="Fewer reaching ANC4+"
          value={fmtN(total.anc4)}
          sub={`${band(total.anc4_lo, total.anc4_hi)} women, 95% band`}
          tone="warn"
          active={rung === "anc4"}
          onClick={() => studio.set({ rung: "anc4" })}
        />
        <StatTile
          label="Fewer reaching ANC8+"
          value={fmtN(total.anc8)}
          sub={`${band(total.anc8_lo, total.anc8_hi)} women, 95% band`}
          active={rung === "anc8"}
          onClick={() => studio.set({ rung: "anc8" })}
        />
        <StatTile
          label={`Back to normal · ${focus || "–"}`}
          value={f?.sum.recoverQ != null ? `${f.sum.recoverQ} qtr` : restored ? "> horizon" : "never"}
          sub={restored ? "after the ceasefire, every rung within 1 point of its level" : "services are not restored in this scenario"}
          tone="accent"
        />
      </div>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-[320px_minmax(0,1fr)]">
        <Panel help="war.scenario"
          title="Scenario"
          how="Choose where the conflict happens and how it runs. Siege: services cut until a ceasefire, as in Tigray. Insurgency: the same shock at onset, then services adapt within a few months while fighting continues, as the Amhara data show. Intensity 1 is the Tigray war."
          actions={
            <button type="button" onClick={() => studio.set({ hit: undefined, pattern: undefined, dur: undefined, int: undefined, restored: undefined, tau: undefined })}
              className="text-faint hover:text-accent" title="Reset the scenario" aria-label="Reset the scenario">
              <RotateCcw className="size-12" />
            </button>
          }
        >
          <div className="px-14 py-12 flex flex-col gap-14">
            <div>
              <div className="text-10.5 font-medium mb-5">Pattern</div>
              <Segmented
                label="Pattern"
                size="md"
                options={[
                  { key: "siege", label: "Siege · Tigray", title: "Services cut until a ceasefire" },
                  { key: "adapt", label: "Insurgency · Amhara", title: "Shock at onset, services adapt while fighting goes on" },
                ]}
                value={pattern}
                onChange={(k) => setP({ pattern: k === "siege" ? undefined : k })}
              />
            </div>
            <div>
              <div className="text-10.5 font-medium mb-5">Regions in conflict <span className="text-faint font-normal">(or click the map)</span></div>
              <div className="flex flex-wrap gap-4">
                {REGION_NAMES.map((r) => {
                  const on = affected.includes(r);
                  return (
                    <button key={r} type="button" onClick={() => toggle(r)} aria-pressed={on}
                      className={`h-22 px-7 rounded-2 border text-9.5 ${on ? "bg-bad text-white border-bad" : "bg-panel2 border-border2 text-dim hover:text-text"}`}>
                      {r}
                    </button>
                  );
                })}
              </div>
            </div>
            <Range label="Fighting lasts" value={durationQ} min={1} max={12} step={1}
              format={(v) => `${v} quarter${v === 1 ? "" : "s"}`} onChange={(v) => setP({ dur: v === 8 ? undefined : String(v) })}
              hint="The Tigray war lasted eight quarters." />
            <Range label="Intensity" value={intensity} min={0} max={1.5} step={0.05}
              format={(v) => `${v.toFixed(2)}×`} onChange={(v) => setP({ int: v === 1 ? undefined : String(v) })}
              hint="1× reproduces the Tigray war; 0× is no effect." />
            <div>
              <div className="text-10.5 font-medium mb-5">After the ceasefire</div>
              <Segmented
                label="After the ceasefire"
                options={[{ key: "yes", label: "Services return" }, { key: "no", label: "Services stay down" }]}
                value={restored ? "yes" : "no"}
                onChange={(k) => setP({ restored: k === "yes" ? undefined : "no" })}
              />
            </div>
            {restored && (
              <div>
                <div className="text-10.5 font-medium mb-5">Recovery time</div>
                <Segmented
                  label="Recovery time"
                  options={TAUS.map((t) => ({ key: String(t), label: t === 0 ? "at once" : `${t} mo${t === W.fit.tau ? " ·fit" : ""}` }))}
                  value={String(tau)}
                  onChange={(k) => setP({ tau: Number(k) === W.fit.tau ? undefined : k })}
                />
                <div className="text-9.5 text-faint leading-snug mt-4">
                  The Tigray data fit anything from {W.fit.tau_supported[0]} to {W.fit.tau_supported[1]} months about equally well; each
                  choice carries the shock that reproduces Tigray with it.
                </div>
              </div>
            )}
          </div>
        </Panel>

        <div className="flex flex-col gap-10 md:gap-14 min-w-0">
          <Panel help="war.map"
            title={`Map · drop in ${RUNG_LABEL[rung]} · ${qLabel(q)}`}
            how="Each affected region shaded by how many percentage points of women it loses on the chosen rung in this quarter, against its own current level. Press play to watch the conflict arrive through the pregnancies it overlaps and fade after the ceasefire. Grey regions are not in the scenario."
            actions={
              <Segmented label="Rung" options={WAR_RUNGS.map((k) => ({ key: k, label: RUNG_LABEL[k] }))} value={rung}
                onChange={(k) => studio.set({ rung: k })} />
            }
          >
            {geo.data ? (
              <div className="relative">
                <RegionMap geo={geo.data} data={mapData} selected={focus} onSelect={toggle} basemap={false} theme={theme} labels height={400} />
                <div className="absolute right-10 bottom-10 z-[500] bg-panel border border-border2 rounded-3 px-10 py-8">
                  <div className="text-10 font-semibold">Points lost this quarter</div>
                  <div className="flex gap-1 mt-5">
                    {DROP_RAMP[theme].map((c, i) => (
                      <div key={c} className="w-40">
                        <div className="h-9 rounded-1" style={{ background: c }} />
                        <div className="text-8.5 font-mono text-faint mt-2">
                          {i === 0 ? "<1" : i === 4 ? "10+" : `${DROP_BREAKS[i - 1] * 100}–${DROP_BREAKS[i] * 100}`}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-[400px] bg-panel2" />
            )}
            <Timeline q={q} setQ={(v) => { setPlaying(false); setQ(v); }} playing={playing} setPlaying={setPlaying} start={START} end={endQ} />
          </Panel>

          <Panel help="war.trajectory"
            title={`${focus || "No region"} · the ladder through the conflict`}
            how="The share of women reaching each rung, by quarter of birth, with the 95% band from the bootstrap. Dashed: the region's level without conflict. The shaded span is the fighting; the vertical line is the quarter on the map. Click an affected region on the map or in the list to follow it."
            actions={
              affected.length > 1 ? (
                <Segmented label="Region" options={affected.map((r) => ({ key: r, label: r }))} value={focus}
                  onChange={(r) => studio.set({ region: r })} />
              ) : undefined
            }
          >
            {f && traj ? (
              <>
                <ChartBox height={260} className="pt-10 pr-14">
                  <ComposedChart data={traj} margin={{ left: -4, right: 6, top: 8, bottom: 0 }}>
                    <CartesianGrid {...GRID} />
                    <XAxis {...AXIS} dataKey="q" type="number" domain={[0, HORIZON - 1]} ticks={[0, 4, 8, 12, 16, 20]} tickFormatter={(v) => `Y${v / 4 + 1}`} />
                    <YAxis {...AXIS} domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tickFormatter={(v) => pct(v)} width={44} />
                    <ReferenceArea x1={START} x2={endQ - 1} fill="var(--bad)" fillOpacity={0.07} />
                    <ReferenceLine x={q} stroke="var(--text)" strokeOpacity={0.5} />
                    {WAR_RUNGS.map((k) => (
                      <ReferenceLine key={`b${k}`} y={f.base[k]} stroke={RUNG_COLOR[k]} strokeDasharray="4 3" strokeOpacity={0.8} />
                    ))}
                    <Tooltip
                      content={tip<Record<string, number>>((d) => (
                        <TipPanel
                          title={qLabel(d.q)}
                          rows={WAR_RUNGS.map((k) => ({
                            label: RUNG_LABEL[k],
                            value: `${pct(d[k], 0)} (${signed((d[k] - f.base[k]) * 100, 0)} pt)`,
                            color: RUNG_COLOR[k],
                          }))}
                        />
                      ))}
                    />
                    {WAR_RUNGS.map((k) => (
                      <Area key={`a${k}`} dataKey={`${k}_band`} stroke="none" fill={RUNG_COLOR[k]} fillOpacity={0.18} isAnimationActive={false} />
                    ))}
                    {WAR_RUNGS.map((k) => (
                      <Line key={k} dataKey={k} stroke={RUNG_COLOR[k]} strokeWidth={2.25} dot={false} isAnimationActive={false} />
                    ))}
                  </ComposedChart>
                </ChartBox>
                <SeriesLegend
                  items={[
                    ...WAR_RUNGS.map((k) => ({ key: k, label: RUNG_LABEL[k], color: RUNG_COLOR[k] })),
                    { key: "base", label: "without conflict", color: "var(--dim)", dashed: true },
                  ]}
                />
              </>
            ) : (
              <div className="px-14 py-12 text-11 text-dim">Choose at least one region.</div>
            )}
          </Panel>
        </div>
      </div>

      {f && (
        <Panel help="war.breaks"
          title={`Which rung breaks first · ${focus}`}
          how="The deepest drop on each rung during the scenario, in percentage points and as a share of the rung's own level. In Tigray the war mostly stopped women from starting and from reaching four contacts; eight contacts were already rare, so there was less to lose."
        >
          <DotRows
            rows={WAR_RUNGS.map((k) => ({
              key: k,
              label: RUNG_LABEL[k],
              sub: `peak at ${qLabel(f.sum.peak[k].q)} · ${pct(f.sum.peak[k].drop / f.base[k], 0)} of its level`,
              values: { now: f.base[k], low: f.base[k] - f.sum.peak[k].drop },
              display: `−${(f.sum.peak[k].drop * 100).toFixed(1)} pt`,
            }))}
            series={[
              { key: "low", label: "At the worst quarter", color: "var(--bad)" },
              { key: "now", label: "Without conflict", color: "var(--dim)", hollow: true },
            ]}
            domain={[0, 1]}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            format={(v) => pct(v)}
            labelWidth={260}
            valueWidth={66}
          />
        </Panel>
      )}

      <div className="grid gap-10 md:gap-14 xl:grid-cols-3">
        <TigrayEvidence w={W} />
        <AmharaBacktest w={W} />
        <Panel help="war.reproduce"
          title="Does the model reproduce Tigray?"
          how="The simulator's model, run on Tigray at intensity 1, against the difference-in-differences estimated directly from the survey (Tigray's change from wartime to post-war births, minus the change in regions without conflict). Rings: that estimate with its 95% interval; dots: the model."
        >
          <DotRows
            rows={WAR_RUNGS.map((k) => ({
              key: k,
              label: RUNG_LABEL[k],
              values: { did: W.did_check[k].did, model: W.did_check[k].model },
              lo: { did: W.did_check[k].lo },
              hi: { did: W.did_check[k].hi },
              display: `${(W.did_check[k].model * 100).toFixed(1)} pt`,
            }))}
            series={[
              { key: "did", label: "Survey estimate (DiD)", color: "var(--dim)", hollow: true },
              { key: "model", label: "Simulator model", color: "var(--accent)" },
            ]}
            reference={{ value: 0, label: "No effect" }}
            format={(v) => `${(v * 100).toFixed(0)} pt`}
            labelWidth={80}
            valueWidth={60}
          />
          <div className="px-14 pb-12 flex flex-col gap-8">
            <Note tone="accent">
              Fitted on {W.fit.n.toLocaleString()} women ({W.fit.n_tigray} in Tigray) with region and half-year fixed effects; bands from{" "}
              {W.bootstrap_resamples} cluster resamples.
            </Note>
            <Note tone="warn">
              Women displaced out of Tigray, and clusters not surveyed for security, are missing, so the war&apos;s real effect is more likely
              larger than shown. Moving it to another region assumes the same kind of disruption to services.
            </Note>
          </div>
        </Panel>
      </div>
    </Screen>
  );
}

function Timeline({ q, setQ, playing, setPlaying, start, end }: {
  q: number; setQ: (v: number) => void; playing: boolean; setPlaying: (f: (p: boolean) => boolean) => void; start: number; end: number;
}) {
  return (
    <div className="px-14 py-10 border-t border-border flex items-center gap-10">
      <button type="button" onClick={() => setPlaying((p) => !p)}
        className={`h-24 px-9 rounded-2 border text-10.5 font-medium flex items-center gap-5 ${playing ? "bg-accent text-white border-accent" : "bg-panel2 border-border2 text-dim hover:text-text"}`}>
        {playing ? <Pause className="size-12" /> : <Play className="size-12" />}
        {playing ? "Pause" : "Play"}
      </button>
      <div className="relative flex-1 min-w-0">
        <div className="absolute inset-x-0 top-1/2 -mt-3 h-6 rounded-full bg-panel3" />
        <div className="absolute top-1/2 -mt-3 h-6 bg-bad opacity-50 rounded-full"
          style={{ left: `${(start / (HORIZON - 1)) * 100}%`, width: `${((end - 1 - start) / (HORIZON - 1)) * 100}%` }} />
        <input type="range" min={0} max={HORIZON - 1} step={1} value={q} onChange={(e) => setQ(Number(e.target.value))}
          aria-label="Quarter" className="relative w-full accent-[var(--text)] cursor-pointer bg-transparent" />
      </div>
      <Tag tone={q >= start && q < end ? "bad" : "neutral"}>{qLabel(q)}{q >= start && q < end ? " · fighting" : q >= end ? " · after" : " · before"}</Tag>
    </div>
  );
}

/** What happened in Tigray: the survey by half-year of birth, and the model's reading of it. */
function TigrayEvidence({ w }: { w: WarData }) {
  const [k, setK] = useState<WarRung>("anc1");
  const obs = w.observed.Tigray ?? [];
  const ctrl = w.observed["Regions without conflict"] ?? [];
  const data = obs.map((o) => {
    const fit = w.fitted_tigray.find((r) => r.half === o.half);
    const c = ctrl.find((r) => r.half === o.half);
    return {
      half: o.half,
      obs: Number(o[k]),
      band: [Number(o[`${k}_lo`]), Number(o[`${k}_hi`])],
      fit: fit ? Number(fit[k]) : null,
      nowar: fit ? Number(fit[`${k}_no_war`]) : null,
      ctrl: c ? Number(c[k]) : null,
      n: o.n,
    };
  });
  return (
    <Panel help="war.tigray"
      title="What happened in Tigray"
      how="The survey itself: the share of Tigray women reaching the rung, by half-year of the birth, with 95% intervals (the band). The solid line is the model; the dashed line is the model with the war switched off. The dotted line is the regions without conflict. The war ended in November 2022; births after mid-2023 were conceived in peace."
      actions={<Segmented label="Rung" options={WAR_RUNGS.map((r) => ({ key: r, label: RUNG_LABEL[r] }))} value={k} onChange={setK} />}
    >
      <ChartBox height={230} className="pt-10 pr-14">
        <ComposedChart data={data} margin={{ left: -4, right: 6, top: 8, bottom: 0 }}>
          <CartesianGrid {...GRID} />
          <XAxis {...AXIS} dataKey="half" />
          <YAxis {...AXIS} domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tickFormatter={(v) => pct(v)} width={44} />
          <Tooltip
            content={tip<(typeof data)[number]>((d) => (
              <TipPanel title={`${d.half} · n ${d.n}`} rows={[
                { label: "Observed", value: pct(d.obs, 0), color: "var(--bad)" },
                { label: "Model", value: pct(d.fit, 0), color: "var(--accent)" },
                { label: "Model, no war", value: pct(d.nowar, 0) },
                { label: "Regions without conflict", value: pct(d.ctrl, 0) },
              ]} />
            ))}
          />
          <Area dataKey="band" stroke="none" fill="var(--bad)" fillOpacity={0.15} isAnimationActive={false} />
          <Line dataKey="ctrl" stroke="var(--faint)" strokeDasharray="1 3" strokeWidth={1.5} dot={false} isAnimationActive={false} />
          <Line dataKey="nowar" stroke="var(--accent)" strokeDasharray="4 3" strokeWidth={1.5} dot={false} isAnimationActive={false} />
          <Line dataKey="fit" stroke="var(--accent)" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line dataKey="obs" stroke="var(--bad)" strokeWidth={0} dot={{ r: 3.5, fill: "var(--bad)", strokeWidth: 0 }} isAnimationActive={false} />
        </ComposedChart>
      </ChartBox>
      <SeriesLegend items={[
        { key: "o", label: "Observed", color: "var(--bad)" },
        { key: "f", label: "Model", color: "var(--accent)" },
        { key: "n", label: "No war", color: "var(--accent)", dashed: true },
        { key: "c", label: "No-conflict regions", color: "var(--faint)", dashed: true },
      ]} />
      <DataNote>Monthly DHIS2 ANC counts for Tigray and Amhara from 2020 onwards, and interviews with displaced women, would measure the shock and the recovery directly instead of from births recalled in one survey.</DataNote>
    </Panel>
  );
}

/** The out-of-sample check: Amhara's Fano period, which the model never saw. */
function AmharaBacktest({ w }: { w: WarData }) {
  const [k, setK] = useState<WarRung>("anc1");
  const b = w.backtest;
  const data = b.rows.map((r) => ({
    half: r.half,
    n: r.n,
    exposure: r.exposure,
    obs: Number(r[`observed_${k}`]),
    siege: Number(r[`full_${k}`]),
    adapt: Number(r[`adapt_${k}`]),
    none: Number(r[`none_${k}`]),
  }));
  return (
    <Panel help="war.amhara"
      title="Checking on Amhara"
      how="The model was fitted without Amhara. From August 2023 the Fano insurgency put Amhara pregnancies under conflict. Red dots: what happened. The siege line applies the full Tigray disruption; it predicts the first half-year well and then far too deep a collapse. The adapting line keeps the same shock at onset but lets services adapt; that adaptation time is fitted to Amhara, so it is a description, not a test."
      actions={<Segmented label="Rung" options={WAR_RUNGS.map((r) => ({ key: r, label: RUNG_LABEL[r] }))} value={k} onChange={setK} />}
    >
      <ChartBox height={230} className="pt-10 pr-14">
        <ComposedChart data={data} margin={{ left: -4, right: 6, top: 8, bottom: 0 }}>
          <CartesianGrid {...GRID} />
          <XAxis {...AXIS} dataKey="half" />
          <YAxis {...AXIS} domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tickFormatter={(v) => pct(v)} width={44} />
          <Tooltip
            content={tip<(typeof data)[number]>((d) => (
              <TipPanel title={`${d.half} · n ${d.n} · exposure ${d.exposure.toFixed(2)}`} rows={[
                { label: "Observed", value: pct(d.obs, 0), color: "var(--bad)" },
                { label: "Siege (Tigray)", value: pct(d.siege, 0), color: "var(--warn)" },
                { label: "Services adapt", value: pct(d.adapt, 0), color: "var(--good)" },
                { label: "No conflict", value: pct(d.none, 0) },
              ]} />
            ))}
          />
          <Line dataKey="none" stroke="var(--faint)" strokeDasharray="4 3" strokeWidth={1.5} dot={false} isAnimationActive={false} />
          <Line dataKey="siege" stroke="var(--warn)" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line dataKey="adapt" stroke="var(--good)" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line dataKey="obs" stroke="var(--bad)" strokeWidth={0} dot={{ r: 3.5, fill: "var(--bad)", strokeWidth: 0 }} isAnimationActive={false} />
        </ComposedChart>
      </ChartBox>
      <SeriesLegend items={[
        { key: "o", label: "Observed", color: "var(--bad)" },
        { key: "s", label: "Siege (Tigray)", color: "var(--warn)" },
        { key: "a", label: `Adapt in ~${b.kappa_fit ?? "?"} mo`, color: "var(--good)" },
        { key: "n", label: "No conflict", color: "var(--faint)", dashed: true },
      ]} />
      <div className="px-14 pb-12">
        <Note tone="warn">
          Scaling the Tigray shock down to fit Amhara gives an intensity of {b.intensity_fit.toFixed(2)} ({b.intensity_lo.toFixed(2)}–
          {b.intensity_hi.toFixed(2)}): after the first months, Amhara&apos;s services held up. A siege and an insurgency are different
          disruptions, which is why the simulator offers both.
        </Note>
      </div>
      <DataNote>Records of which facilities stayed open, and when, would tell a siege from an insurgency on evidence rather than by fitting.</DataNote>
    </Panel>
  );
}

function clampInt(v: number, lo: number, hi: number) {
  return Number.isFinite(v) ? Math.min(hi, Math.max(lo, Math.round(v))) : lo;
}
function clampNum(v: number, lo: number, hi: number) {
  return Number.isFinite(v) ? Math.min(hi, Math.max(lo, v)) : 1;
}
