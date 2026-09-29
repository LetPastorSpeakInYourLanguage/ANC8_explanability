"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Download, FileUp, ShieldCheck } from "lucide-react";
import {
  Area, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ReferenceLine, Tooltip, XAxis, YAxis,
} from "recharts";
import DotRows from "@/components/charts/DotRows";
import RankedBars from "@/components/charts/RankedBars";
import { AXIS, ChartBox, GRID, SeriesLegend, TipPanel, tip } from "@/components/charts/rc";
import { DataNote,
  EmptyState, InlineError, Note, Panel, PanelLoading, Screen, Segmented, StatTile, Table, Tag,
} from "@/components/studio/ui";
import { Select } from "@/components/ui/select";
import { useJSON } from "@/lib/data";
import { RUNG_LABEL, pct } from "@/lib/explore";
import {
  aggregate, backtest, forecast, nextPeriods, parseAggregate, parseCSV, type Parsed,
} from "@/lib/forecast";
import { asset } from "@/lib/paths";
import { changeAt, parseCoverage, type ScenarioData } from "@/lib/scenario";
import { score, type Record_, type Screener } from "@/lib/screener";
import { useStudio } from "@/lib/studio";

const SAMPLES = {
  survey: { file: "/samples/survey_regions_quarterly.csv", label: "Survey regions, by quarter",
    note: "Built from the survey: each region's share reaching each rung by quarter of birth, times its births. Real, but survey-sized: about 30–70 women per region and quarter, so it is noisy." },
  synthetic: { file: "/samples/synthetic_woreda_monthly.csv", label: "Synthetic woreda, monthly",
    note: "SYNTHETIC. A made-up woreda of six facilities over four years, shaped like a DHIS2 export, with a rainy-season dip, a slow rise and a three-month disruption at one health post. For trying the tools; not data." },
} as const;
const TEMPLATE = "period,org_unit,expected_pregnancies,anc1,anc4,anc8\n2023-01,Health centre A,95,74,48,15\n2023-02,Health centre A,95,70,45,16\n";
const REGISTER_TEMPLATE = "woman_id,region,age,previous_births,minutes_to_facility,assets,early_first_visit,education,pregnancy_wanted,transport,insured,residence,marital_status\nW001,Oromia,24,1,45,2,0,Primary,Wanted then,Walking,No,Rural,Currently in union\n";

type Measure = "anc1" | "anc4" | "anc8";

export default function YourDataPage() {
  const studio = useStudio();
  const mode = studio.params.get("mode") === "register" ? "register" : "aggregate";
  return (
    <Screen>
      <div data-help="data.mode" className="flex items-center gap-10 flex-wrap">
        <Segmented
          label="What to load"
          size="md"
          options={[
            { key: "aggregate", label: "Monthly or quarterly ANC counts" },
            { key: "register", label: "A register of women (first-visit screen)" },
          ]}
          value={mode}
          onChange={(k) => studio.set({ mode: k === "aggregate" ? undefined : k })}
        />
        <span className="flex items-center gap-5 text-10.5 text-dim">
          <ShieldCheck className="size-13 text-good" />
          Files are read in this browser and never uploaded anywhere.
        </span>
      </div>
      {mode === "aggregate" ? <AggregateMode /> : <RegisterMode />}
    </Screen>
  );
}

// --------------------------------------------------------------- aggregate counts

function AggregateMode() {
  const studio = useStudio();
  const sc = useJSON<ScenarioData>("/data/scenarios.json");
  const [source, setSource] = useState<keyof typeof SAMPLES | "upload">("synthetic");
  const [text, setText] = useState<string | null>(null);
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [unit, setUnit] = useState("");
  const [measure, setMeasure] = useState<Measure>("anc4");
  const [asRate, setAsRate] = useState(false);
  const [horizon, setHorizon] = useState(12);
  const [applyLevers, setApplyLevers] = useState(true);

  useEffect(() => {
    if (source === "upload") return;
    setError(null);
    fetch(asset(SAMPLES[source].file))
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error(`${r.status}`))))
      .then((t) => { setText(t); setFileName(SAMPLES[source].label); setUnit(""); })
      .catch((e) => setError(`Could not load the sample (${e.message}).`));
  }, [source]);

  const parsed: Parsed | null = useMemo(() => (text ? parseAggregate(text) : null), [text]);
  const hasExpected = !!parsed?.rows.some((r) => r.expected != null);
  const rate = asRate && hasExpected;
  const m = parsed?.season ?? 12;
  const h = Math.min(horizon, m === 4 ? 8 : 24);

  const series = useMemo(() => {
    if (!parsed || !parsed.periods.length) return null;
    const units = unit ? [unit] : null;
    const num = aggregate(parsed, units, measure);
    const den = aggregate(parsed, units, "expected");
    const y = num.map((v, i) => (v == null ? null : rate ? (den[i] ? v / (den[i] as number) : null) : v));
    const clean = y.filter((v): v is number => v != null);
    if (clean.length < 4) return null;
    const first = y.findIndex((v) => v != null);
    const ys = y.slice(first) as number[];
    const periods = parsed.periods.slice(first);
    const ranking = backtest(ys, m, h);
    const fc = forecast(ys, m, h, ranking);
    const lastDen = (den.filter((v) => v != null).slice(-1)[0] as number | undefined) ?? null;
    return { ys, periods, ranking, fc, lastDen };
  }, [parsed, unit, measure, rate, m, h]);

  // The planner's levers, from the shared address bar, applied to the forecast: the
  // scenario's change reaches its full size over a year.
  const cov = parseCoverage(studio.params.get("lv"));
  const leverActive = Object.values(cov).some((v) => v > 0);
  const regionIdx = sc.data ? sc.data.regions.indexOf(unit && sc.data.regions.includes(unit) ? unit : "Ethiopia") : -1;
  const leverGain = sc.data && regionIdx >= 0 && leverActive ? changeAt(sc.data, measure, regionIdx, cov) : 0;

  if (error) return <InlineError message={error} />;

  const onFile = (f: File | undefined) => {
    if (!f) return;
    if (f.size > 20 * 1024 * 1024) { setError("That file is over 20 MB; export a smaller period or fewer units."); return; }
    const r = new FileReader();
    r.onload = () => { setSource("upload"); setText(String(r.result)); setFileName(f.name); setUnit(""); setError(null); };
    r.readAsText(f);
  };

  const fmt = (v: number) => (rate ? pct(v, 1) : Math.round(v).toLocaleString());
  const chart = series && series.fc
    ? [
        ...series.ys.map((v, i) => ({ period: series.periods[i], actual: v })),
        ...nextPeriods(series.periods[series.periods.length - 1], h).map((p, i) => {
          const ramp = Math.min(1, (i + 1) / (m === 4 ? 4 : 12));
          const lift = applyLevers && leverActive ? leverGain * ramp * (rate ? 1 : series.lastDen ?? 0) : 0;
          return {
            period: p,
            point: series.fc!.point[i],
            b80: [series.fc!.lo80[i], series.fc!.hi80[i]],
            b95: [series.fc!.lo95[i], series.fc!.hi95[i]],
            levers: lift ? series.fc!.point[i] + lift : undefined,
          };
        }),
      ]
    : [];
  const bridge = chart.length && series ? { ...chart[series.ys.length - 1], point: series.ys[series.ys.length - 1], levers: applyLevers && leverActive ? series.ys[series.ys.length - 1] : undefined } : null;
  if (bridge && series) chart[series.ys.length - 1] = bridge;

  const last = series?.ys[series.ys.length - 1];
  const yearAgo = series && series.ys.length > m ? series.ys[series.ys.length - 1 - m] : null;
  const end = series?.fc?.point[h - 1];

  return (
    <>
      <Panel help="data.source"
        title="Data"
        how="A CSV with one row per period and (optionally) per facility or area. Columns: period (2023-01 or 2023Q1), org_unit, expected_pregnancies (optional), anc1, anc4, anc8. DHIS2 exports with these names work; other names for the same things are recognised."
      >
        <div className="px-14 py-10 flex flex-wrap items-center gap-8">
          <Segmented
            label="Source"
            options={[
              { key: "synthetic", label: "Sample: synthetic woreda" },
              { key: "survey", label: "Sample: survey regions" },
              { key: "upload", label: "Your file" },
            ]}
            value={source}
            onChange={(k) => (k === "upload" ? document.getElementById("agg-file")?.click() : setSource(k))}
          />
          <label className="h-24 px-10 rounded-2 border border-accent bg-accent text-white text-10.5 font-medium flex items-center gap-5 cursor-pointer">
            <FileUp className="size-12" /> Load a CSV
            <input id="agg-file" type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} />
          </label>
          <a href={`data:text/csv;charset=utf-8,${encodeURIComponent(TEMPLATE)}`} download="anc_counts_template.csv"
            className="h-24 px-10 rounded-2 border border-border2 bg-panel2 text-dim text-10.5 flex items-center gap-5 hover:text-text">
            <Download className="size-12" /> Template
          </a>
          <span className="text-10.5 text-dim">{fileName}</span>
        </div>
        {source !== "upload" && (
          <div className="px-14 pb-10">
            <Note tone={source === "synthetic" ? "warn" : "accent"}>{SAMPLES[source].note}</Note>
          </div>
        )}
        {parsed?.problems.length ? (
          <div className="px-14 pb-10 flex flex-col gap-4">
            {parsed.problems.map((p) => <Note key={p} tone="warn">{p}</Note>)}
          </div>
        ) : null}
      </Panel>

      {!parsed ? (
        <PanelLoading rows={6} />
      ) : !series ? (
        <EmptyState title="Not enough to forecast" body="The file needs at least four periods with ANC counts for the chosen measure." />
      ) : (
        <>
          <div data-help="data.tiles" className="grid gap-10 grid-cols-2 lg:grid-cols-4">
            <StatTile label={`Latest · ${series.periods[series.periods.length - 1]}`} value={fmt(last!)}
              sub={`${RUNG_LABEL[measure]}${rate ? " coverage" : " count"} · ${unit || "all units"}`} />
            <StatTile label="Against a year earlier" value={yearAgo != null ? `${last! >= yearAgo ? "+" : "−"}${rate ? `${Math.abs((last! - yearAgo) * 100).toFixed(1)} pt` : Math.abs(Math.round(last! - yearAgo)).toLocaleString()}` : "–"}
              sub={yearAgo != null ? `from ${fmt(yearAgo)}` : "less than a year of data"} tone={yearAgo != null && last! < yearAgo ? "bad" : "good"} />
            <StatTile label={`Forecast · ${h} ${m === 4 ? "quarters" : "months"} ahead`} value={end != null ? fmt(end) : "–"}
              sub={series.fc ? `80%: ${fmt(series.fc.lo80[h - 1])}–${fmt(series.fc.hi80[h - 1])}` : ""} tone="accent" />
            <StatTile label="Forecaster chosen" value={<span className="text-15">{series.ranking[0]?.label ?? "–"}</span>}
              sub={`smallest error in a backtest over ${series.ranking[0]?.origins ?? 0} forecast origins`} />
          </div>

          <Panel help="data.trend"
            title={`Trend and forecast · ${RUNG_LABEL[measure]} ${rate ? "coverage" : "count"}`}
            how="Solid: the data. Dashed: the forecast, from whichever forecaster made the smallest errors when it was tested on this same series (fit on the past, forecast the next periods, compare, repeat). The bands are 80% and 95% ranges built from those real errors. The green line adds the levers set in the scenario planner, reaching their full effect over a year."
            actions={
              <div className="flex items-center gap-8 flex-wrap">
                <Segmented label="Measure" options={(["anc1", "anc4", "anc8"] as Measure[]).map((k) => ({ key: k, label: RUNG_LABEL[k] }))}
                  value={measure} onChange={setMeasure} />
                {hasExpected && (
                  <Segmented label="Scale" options={[{ key: "count", label: "Count" }, { key: "rate", label: "Coverage" }]}
                    value={rate ? "rate" : "count"} onChange={(k) => setAsRate(k === "rate")} />
                )}
                {parsed.units.length > 1 && (
                  <Select value={unit} onChange={(e) => setUnit(e.target.value)} className="w-auto min-w-[150px] h-22 text-10.5" aria-label="Unit">
                    <option value="">All {parsed.units.length} units</option>
                    {parsed.units.map((u) => <option key={u} value={u}>{u}</option>)}
                  </Select>
                )}
                <Segmented label="Horizon" options={(m === 4 ? [4, 8] : [6, 12, 24]).map((n) => ({ key: String(n), label: `${n} ${m === 4 ? "qtr" : "mo"}` }))}
                  value={String(Math.min(horizon, m === 4 ? 8 : 24))} onChange={(k) => setHorizon(Number(k))} />
              </div>
            }
          >
            <ChartBox height={300} className="pt-12 pr-14">
              <ComposedChart data={chart} margin={{ left: 4, right: 6, top: 8, bottom: 0 }}>
                <CartesianGrid {...GRID} />
                <XAxis {...AXIS} dataKey="period" interval="preserveStartEnd" minTickGap={24} />
                <YAxis {...AXIS} tickFormatter={(v) => (rate ? pct(v) : v >= 1e3 ? `${Math.round(v / 1e3)}k` : String(Math.round(v)))} width={48} domain={[0, "auto"]} />
                <ReferenceLine x={series.periods[series.periods.length - 1]} stroke="var(--faint)" strokeDasharray="3 3" />
                <Tooltip
                  content={tip<Record<string, number | number[] | string | undefined>>((d) => (
                    <TipPanel title={String(d.period)} rows={[
                      ...(d.actual != null ? [{ label: "Data", value: fmt(d.actual as number), color: "var(--text)" }] : []),
                      ...(d.point != null && d.actual == null ? [{ label: "Forecast", value: fmt(d.point as number), color: "var(--accent)" }] : []),
                      ...(Array.isArray(d.b80) ? [{ label: "80% range", value: `${fmt(d.b80[0])}–${fmt(d.b80[1])}` }] : []),
                      ...(d.levers != null && d.actual == null ? [{ label: "With the levers", value: fmt(d.levers as number), color: "var(--good)" }] : []),
                    ]} />
                  ))}
                />
                <Area dataKey="b95" stroke="none" fill="var(--accent)" fillOpacity={0.1} isAnimationActive={false} />
                <Area dataKey="b80" stroke="none" fill="var(--accent)" fillOpacity={0.18} isAnimationActive={false} />
                <Line dataKey="actual" stroke="var(--text)" strokeWidth={1.75} dot={{ r: 1.5 }} isAnimationActive={false} />
                <Line dataKey="point" stroke="var(--accent)" strokeWidth={2} strokeDasharray="5 3" dot={false} isAnimationActive={false} />
                {applyLevers && leverActive && (
                  <Line dataKey="levers" stroke="var(--good)" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
                )}
              </ComposedChart>
            </ChartBox>
            <SeriesLegend items={[
              { key: "a", label: "Data", color: "var(--text)" },
              { key: "f", label: `Forecast: ${series.ranking[0]?.label}`, color: "var(--accent)", dashed: true },
              ...(applyLevers && leverActive ? [{ key: "l", label: `With the planner's levers (${leverGain >= 0 ? "+" : "−"}${Math.abs(leverGain * 100).toFixed(1)} pt)`, color: "var(--good)" }] : []),
            ]} />
            <div className="px-14 pb-12 flex flex-wrap items-center gap-10">
              <label className="flex items-center gap-6 text-10.5">
                <input type="checkbox" checked={applyLevers} onChange={(e) => setApplyLevers(e.target.checked)} className="accent-[var(--accent)]" />
                Apply the scenario planner&apos;s levers
              </label>
              {!leverActive && (
                <a href={studio.href("/planner")} className="text-10.5 text-accent hover:underline">Set levers in the planner first</a>
              )}
              {leverActive && (
                <span className="text-10.5 text-dim">
                  using {regionIdx >= 0 && sc.data ? sc.data.regions[regionIdx] : "Ethiopia"}&apos;s expected change{rate ? "" : " times the latest expected pregnancies"}
                </span>
              )}
            </div>
            <DataNote>Five or more years of monthly facility reports would let the seasonal forecasters show their strength; with a few years, simple methods usually win.</DataNote>
          </Panel>

          <div className="grid gap-10 md:gap-14 xl:grid-cols-2">
            <Panel help="data.forecasters"
              title="How each forecaster did on this series"
              how="Each forecaster was fitted on the start of the series and asked to forecast the next periods, over and over, moving forward one period at a time. The bar is its average miss. The shortest bar is used. When a simple method wins, the series has little pattern to learn."
            >
              <RankedBars
                labelWidth={210}
                valueWidth={70}
                rows={series.ranking.map((b, i) => ({
                  key: b.key,
                  label: b.label,
                  sub: `${b.origins} origins`,
                  value: b.mae,
                  display: fmt(b.mae),
                  color: i === 0 ? "var(--accent)" : "var(--faint)",
                }))}
              />
            </Panel>
            {m === 12 && series.ys.length >= 24 ? (
              <Seasonality ys={series.ys} periods={series.periods} />
            ) : (
              <Panel help="data.season" title="By season">
                <div className="px-14 py-12 text-11 text-dim">Seasonal patterns need at least two years of monthly data.</div>
              </Panel>
            )}
          </div>
        </>
      )}
    </>
  );
}

function Seasonality({ ys, periods }: { ys: number[]; periods: string[] }) {
  const names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  // month effect: the average ratio of each month to its centred 12-month mean
  const ratios: number[][] = Array.from({ length: 12 }, () => []);
  for (let i = 6; i < ys.length - 6; i++) {
    const w = ys.slice(i - 6, i + 6);
    const avg = w.reduce((a, b) => a + b, 0) / 12;
    if (avg > 0) ratios[Number(periods[i].slice(5)) - 1].push(ys[i] / avg - 1);
  }
  const data = names.map((n, k) => ({ month: n, v: ratios[k].length ? ratios[k].reduce((a, b) => a + b, 0) / ratios[k].length : 0 }));
  return (
    <Panel help="data.season"
      title="By season"
      how="How much each calendar month runs above or below the year around it, averaged over the years in the file. In the synthetic sample the dip is the main rains (June to September), when roads close."
    >
      <ChartBox height={200} className="pt-10 pr-14">
        <BarChart data={data} margin={{ left: -4, right: 6, top: 6, bottom: 0 }}>
          <CartesianGrid {...GRID} vertical={false} />
          <XAxis {...AXIS} dataKey="month" interval={0} />
          <YAxis {...AXIS} tickFormatter={(v) => `${Math.round(v * 100)}%`} width={44} />
          <ReferenceLine y={0} stroke="var(--border2)" />
          <Tooltip content={tip<{ month: string; v: number }>((d) => <TipPanel title={d.month} rows={[{ label: "Against its year", value: `${d.v >= 0 ? "+" : "−"}${Math.abs(d.v * 100).toFixed(1)}%` }]} />)} />
          <Bar dataKey="v" radius={[2, 2, 0, 0]} isAnimationActive={false}>
            {data.map((d) => <Cell key={d.month} fill={d.v >= 0 ? "var(--accent)" : "var(--bad)"} />)}
          </Bar>
        </BarChart>
      </ChartBox>
    </Panel>
  );
}

// ------------------------------------------------------------------ register mode

function RegisterMode() {
  const scr = useJSON<{ screener?: Screener }>("/data/series.json");
  const [text, setText] = useState<string | null>(null);
  const [fileName, setFileName] = useState("");
  const [rung, setRung] = useState<"anc4" | "anc8">("anc8");
  const [picked, setPicked] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loaded = useRef(false);

  useEffect(() => {
    if (loaded.current) return;
    loaded.current = true;
    fetch(asset("/samples/synthetic_register.csv"))
      .then((r) => r.text())
      .then((t) => { setText(t); setFileName("Sample: synthetic register of 300 women"); })
      .catch(() => setError("Could not load the sample register."));
  }, []);

  const s = scr.data?.screener;
  const women = useMemo(() => {
    if (!text || !s) return [];
    const t = parseCSV(text);
    const head = t[0].map((h) => h.trim());
    return t.slice(1).map((r, i) => {
      const rec: Record_ = {};
      head.forEach((h, j) => { rec[h] = r[j]?.trim() ?? ""; });
      const id = String(rec.woman_id || `Row ${i + 1}`);
      const s4 = score(s, "anc4", rec);
      const s8 = score(s, "anc8", rec);
      return { id, rec, p4: s4.p, p8: s8.p, parts8: s8.parts, parts4: s4.parts };
    });
  }, [text, s]);

  if (scr.error || error) return <InlineError message={scr.error ?? error ?? ""} />;
  if (!s) return <PanelLoading rows={8} />;

  const onFile = (f: File | undefined) => {
    if (!f) return;
    const r = new FileReader();
    r.onload = () => { setText(String(r.result)); setFileName(f.name); setPicked(null); };
    r.readAsText(f);
  };

  const P = (w: (typeof women)[number]) => (rung === "anc4" ? w.p4 : w.p8);
  const ranked = [...women].sort((a, b) => P(a) - P(b));
  const expected = women.reduce((acc, w) => acc + P(w), 0);
  const hi = women.filter((w) => 1 - P(w) >= 0.8).length;
  const sel = women.find((w) => w.id === picked) ?? ranked[0];
  const perf = s.rungs[rung].heldout;
  const ref = s.rungs[rung].reference.find((r) => r.set === "full pool");
  const hist = Array.from({ length: 10 }, (_, i) => ({
    bin: `${i * 10}–${i * 10 + 10}%`,
    n: women.filter((w) => Math.min(9, Math.floor((1 - P(w)) * 10)) === i).length,
    i,
  }));

  return (
    <>
      <Panel help="screener.register"
        title="Register"
        how="One row per woman at her first ANC visit. The columns are the twelve questions of the screener (download the template). The screen runs here, in the browser; the file is not sent anywhere."
      >
        <div className="px-14 py-10 flex flex-wrap items-center gap-8">
          <label className="h-24 px-10 rounded-2 border border-accent bg-accent text-white text-10.5 font-medium flex items-center gap-5 cursor-pointer">
            <FileUp className="size-12" /> Load a register
            <input type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} />
          </label>
          <a href={`data:text/csv;charset=utf-8,${encodeURIComponent(REGISTER_TEMPLATE)}`} download="first_visit_register_template.csv"
            className="h-24 px-10 rounded-2 border border-border2 bg-panel2 text-dim text-10.5 flex items-center gap-5 hover:text-text">
            <Download className="size-12" /> Template
          </a>
          <span className="text-10.5 text-dim">{fileName}</span>
          <span className="flex-1" />
          <Segmented label="Rung" options={[{ key: "anc4", label: "Stop before 4" }, { key: "anc8", label: "Stop before 8" }]}
            value={rung} onChange={setRung} />
        </div>
        {fileName.startsWith("Sample") && (
          <div className="px-14 pb-10">
            <Note tone="warn">
              SYNTHETIC: 300 made-up women. Each column was drawn from the survey&apos;s own distribution within the woman&apos;s region, so the
              values are realistic but no row is a real person.
            </Note>
          </div>
        )}
      </Panel>

      <div data-help="screener.tiles" className="grid gap-10 grid-cols-2 lg:grid-cols-4">
        <StatTile label="Women screened" value={women.length.toLocaleString()} sub={fileName} />
        <StatTile label={`Expected to reach ${RUNG_LABEL[rung]}`} value={Math.round(expected).toLocaleString()}
          sub={`${pct(expected / Math.max(women.length, 1), 0)} of the register, on average`} tone="good" />
        <StatTile label="High risk of stopping" value={hi.toLocaleString()} sub="80% or more chance of stopping early" tone="bad" />
        <StatTile label="How well the screen sorts" value={perf.AUROC.toFixed(2)}
          sub={`AUC on 984 held-out women; the full model: ${ref ? ref.AUROC.toFixed(2) : "–"}`} tone="accent" />
      </div>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <Panel help="screener.list"
          title="Follow-up list"
          how="Women ordered by their chance of stopping before the chosen rung, highest first. The reasons are the answers that raise her risk most in the screener. Click a woman to see all of her answers and what would change her chance."
        >
          <Table
            minWidth={520}
            rows={ranked.slice(0, 25)}
            rowKey={(w) => w.id}
            isActive={(w) => w.id === sel?.id}
            onRowClick={(w) => setPicked(w.id)}
            columns={[
              { header: "Woman", cell: (w) => <span className="font-mono text-10.5">{w.id}</span>, width: "70px" },
              { header: "Region", cell: (w) => String(w.rec.region ?? "") },
              {
                header: "Main reasons",
                cell: (w) => (
                  <span className="text-dim text-10.5">
                    {(rung === "anc4" ? w.parts4 : w.parts8).filter((p) => p.value < -0.15).sort((a, b) => a.value - b.value).slice(0, 2)
                      .map((p) => shortReason(p.key, w.rec)).join(" · ") || "–"}
                  </span>
                ),
              },
              {
                header: "Stops early",
                mono: true,
                cell: (w) => {
                  const r = 1 - P(w);
                  return <Tag tone={r >= 0.8 ? "bad" : r >= 0.5 ? "warn" : "good"}>{pct(r, 0)}</Tag>;
                },
              },
            ]}
          />
        </Panel>

        <div className="flex flex-col gap-10 md:gap-14 min-w-0">
          {sel && (
            <Panel help="screener.why"
              title={`${sel.id} · why this chance`}
              how="Each answer's push on her chance of reaching the rung, on the model's scale: bars to the right raise it, to the left lower it, compared with a typical woman. Below, what the screener expects if one thing were different."
            >
              <RankedBars
                signed
                labelWidth={190}
                rows={(rung === "anc4" ? sel.parts4 : sel.parts8)
                  .slice()
                  .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
                  .slice(0, 8)
                  .map((p) => ({
                    key: p.key,
                    label: `${p.key.replace(/_/g, " ")}: ${String(sel.rec[p.key] ?? "–")}`,
                    value: p.value,
                    display: `${p.value >= 0 ? "+" : "−"}${Math.abs(p.value).toFixed(2)}`,
                    color: p.value >= 0 ? "var(--good)" : "var(--bad)",
                  }))}
              />
              <WhatIf s={s} rung={rung} rec={sel.rec} />
            </Panel>
          )}
          <Panel help="screener.spread" title="Spread of risk in this register" how="How many women fall in each band of risk of stopping early.">
            <ChartBox height={170} className="pt-10 pr-14">
              <BarChart data={hist} margin={{ left: -8, right: 6, top: 6, bottom: 0 }}>
                <CartesianGrid {...GRID} vertical={false} />
                <XAxis {...AXIS} dataKey="bin" interval={1} />
                <YAxis {...AXIS} width={36} allowDecimals={false} />
                <Tooltip content={tip<(typeof hist)[number]>((d) => <TipPanel title={`${d.bin} risk`} rows={[{ label: "Women", value: d.n }]} />)} />
                <Bar dataKey="n" radius={[2, 2, 0, 0]} isAnimationActive={false}>
                  {hist.map((d) => <Cell key={d.bin} fill={d.i >= 8 ? "var(--bad)" : d.i >= 5 ? "var(--warn)" : "var(--good)"} />)}
                </Bar>
              </BarChart>
            </ChartBox>
          </Panel>
        </div>
      </div>

      <Panel help="screener.tested"
        title="The screen, tested"
        how="The screener was fitted on 4,017 development women who started ANC and tested on 984 held-out women it never saw, with survey weights. Its accuracy is set next to models that use the full list of predictors on the same women."
      >
        <DotRows
          rows={(["anc4", "anc8"] as const).map((r) => ({
            key: r,
            label: RUNG_LABEL[r],
            values: {
              chance: s.rungs[r].heldout.prevalence,
              screen: s.rungs[r].heldout.AP,
              full: s.rungs[r].reference.find((x) => x.set === "full pool")?.AP,
            },
            display: `AUC ${s.rungs[r].heldout.AUROC.toFixed(2)}`,
          }))}
          series={[
            { key: "chance", label: "Chance", color: "var(--faint)", hollow: true },
            { key: "screen", label: "12-question screen", color: "var(--accent)" },
            { key: "full", label: "All 89 predictors", color: "var(--cross)", hollow: true },
          ]}
          domain={[0, 1]}
          ticks={[0, 0.25, 0.5, 0.75, 1]}
          format={(v) => v.toFixed(2)}
          labelWidth={90}
          valueWidth={72}
        />
        <div className="px-14 pb-12">
          <Note tone="accent">
            Average precision on held-out women. Twelve questions a midwife can ask give almost the accuracy of the full survey model, so
            the screen does not need a survey. It describes women like her, not her: use it to decide who to call, not who to care for.
          </Note>
        </div>
        <DataNote>Follow-up records from clinics using the screen (did the women it flagged come back?) would validate it where it is used and recalibrate it to local rates.</DataNote>
      </Panel>
    </>
  );
}

function shortReason(key: string, rec: Record_): string {
  const v = rec[key];
  switch (key) {
    case "early_first_visit": return String(v) === "1" ? "early first visit" : "late first visit";
    case "minutes_to_facility": return `${v} min away`;
    case "assets": return `${v}/5 household items`;
    case "previous_births": return `${v} previous births`;
    case "insured": return String(v) === "Yes" ? "insured" : "not insured";
    default: return `${key.replace(/_/g, " ")}: ${v}`;
  }
}

function WhatIf({ s, rung, rec }: { s: Screener; rung: "anc4" | "anc8"; rec: Record_ }) {
  const base = score(s, rung, rec).p;
  const tries: { label: string; patch: Record_ }[] = [
    { label: "Insured", patch: { insured: "Yes" } },
    { label: "Within 30 minutes of care", patch: { minutes_to_facility: Math.min(Number(rec.minutes_to_facility) || 30, 30) } },
    { label: "Pregnancy wanted then", patch: { pregnancy_wanted: "Wanted then" } },
    { label: "Next time: first visit early", patch: { early_first_visit: 1 } },
  ];
  return (
    <div className="border-t border-border px-14 py-10">
      <div className="text-10 font-semibold uppercase tracking-label text-faint mb-5">If one thing were different</div>
      <div className="grid grid-cols-2 gap-6">
        {tries.map((t) => {
          const p = score(s, rung, { ...rec, ...t.patch }).p;
          const d = p - base;
          return (
            <div key={t.label} className="flex items-baseline gap-6 min-w-0">
              <span className="text-10.5 truncate flex-1">{t.label}</span>
              <span className={`font-mono text-10.5 font-semibold ${d > 0.005 ? "text-good" : "text-faint"}`}>
                {Math.abs(d) < 0.005 ? "same" : `${d > 0 ? "+" : "−"}${Math.abs(d * 100).toFixed(0)} pt`}
              </span>
            </div>
          );
        })}
      </div>
      <div className="text-9.5 text-faint mt-5">Chance of reaching {RUNG_LABEL[rung]} now {pct(base, 0)}. Associations in the survey, not promises.</div>
    </div>
  );
}
