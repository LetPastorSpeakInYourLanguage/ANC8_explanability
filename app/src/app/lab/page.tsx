"use client";

import { useEffect, useMemo, useState } from "react";
import { Cpu } from "lucide-react";
import { Bar, CartesianGrid, Cell, ComposedChart, Line, Tooltip, XAxis, YAxis } from "recharts";
import DotRows from "@/components/charts/DotRows";
import MatrixHeat from "@/components/charts/MatrixHeat";
import RankedBars from "@/components/charts/RankedBars";
import { AXIS, ChartBox, GRID, SeriesLegend, TipPanel, tip } from "@/components/charts/rc";
import { useRenderTheme } from "@/components/shell/theme-provider";
import { DataNote, InlineError, Note, Panel, PanelLoading, Screen, Segmented, StatTile, Tag } from "@/components/studio/ui";
import { Select } from "@/components/ui/select";
import { label as predictorLabel } from "@/lib/labels";
import { loadJSON, useJSON } from "@/lib/data";
import { NETWORKS, OUTCOME_OF, RUNG_LABEL, num, pct, signed, type ExploreData } from "@/lib/explore";
import { ladder, sequence, type Nets, type RawRecord } from "@/lib/nets";
import { REGION_NAMES } from "@/lib/regions";
import { RUNGS, useStudio } from "@/lib/studio";

interface LabData {
  concepts: { key: string; label: string; modifiable: boolean }[];
  token_concept: number[];
  tokens: string[];
  attention: { ladder: Record<string, number[]>; sequence: Record<string, number[][]> };
  dropoff: Record<string, { contact: number; predicted: number; observed: number }[]>;
  distribution: { contacts: number; predicted: number; observed: number }[];
  profiles: { min_n: number; profiles: { region: string; wealth: string | null; n: number; record: RawRecord }[] };
}

const QUINTILES = ["Poorest", "Poorer", "Middle", "Richer", "Richest"];
const TREES = ["XGBoost", "Explainable Boosting", "Logistic regression"];
const MODEL_COLOR: Record<string, string> = {
  XGBoost: "var(--cross)", "Explainable Boosting": "var(--good)", "Logistic regression": "var(--accent)",
  "Ladder transformer": "var(--warn)", "Contact-sequence encoder-decoder": "var(--net)",
};

// What a planner might change about the composite woman, as edits to her record.
const EDITS: { key: string; label: string; apply: (r: RawRecord) => RawRecord }[] = [
  { key: "insured", label: "Insured", apply: (r) => ({ ...r, health_insurance: "Yes", v481: "1" }) },
  { key: "wanted", label: "Pregnancy wanted then", apply: (r) => ({ ...r, pregnancy_intention: "Wanted then" }) },
  {
    key: "post", label: "Health post within 30 min",
    apply: (r) => (Number(r.s1101b) > 30 ? { ...r, s1101b: 30, travel_healthpost_log: Math.log1p(30), travel_healthpost_topcoded: 0 } : r),
  },
];

export default function LabPage() {
  const studio = useStudio();
  const theme = useRenderTheme();
  const lab = useJSON<LabData>("/data/lab.json");
  const exp = useJSON<ExploreData>("/data/explore.json");
  const [nets, setNets] = useState<Nets | null>(null);
  const [netErr, setNetErr] = useState<string | null>(null);
  const [wealth, setWealth] = useState<string>("");
  const [edits, setEdits] = useState<string[]>([]);
  const [focusStep, setFocusStep] = useState<number | null>(null);

  const region = studio.region || "Ethiopia";
  const rung = studio.rung;

  // The weights are 1.4 MB, so they load only here, and only once.
  useEffect(() => {
    loadJSON<Nets>("/data/nets.json").then(setNets).catch((e) => setNetErr(String(e)));
  }, []);

  const profile = lab.data?.profiles.profiles.find((p) => p.region === region && (p.wealth ?? "") === wealth)
    ?? lab.data?.profiles.profiles.find((p) => p.region === region && p.wealth == null);

  const run = useMemo(() => {
    if (!nets || !profile) return null;
    const rec = EDITS.filter((e) => edits.includes(e.key)).reduce((r, e) => e.apply(r), { ...profile.record });
    const base = { l: ladder(nets, profile.record), s: sequence(nets, profile.record) };
    return { l: ladder(nets, rec), s: sequence(nets, rec), base };
  }, [nets, profile, edits]);

  const err = lab.error ?? exp.error ?? netErr;
  if (err) return <Screen><InlineError message={err} /></Screen>;
  if (!lab.data || !exp.data?.networks) return <Screen><PanelLoading rows={10} /></Screen>;
  const L = lab.data;
  const N = exp.data.networks;
  const concepts = L.concepts;

  // attention summed from predictors to planning concepts
  const toConcepts = (att: number[]) => {
    const out = Array(concepts.length).fill(0);
    att.forEach((a, j) => { const c = L.token_concept[j]; if (c >= 0) out[c] += a; });
    return out;
  };
  const outcome = OUTCOME_OF[rung];
  const held = N.heldout.filter((r) => r.rung === outcome);
  const seqHeld = held.find((r) => r.model === NETWORKS[1]);
  const ebmHeld = held.find((r) => r.model === "Explainable Boosting");

  const seqAtt = run ? run.s.attention.map(toConcepts) : null;
  const drop = L.dropoff[region] ?? L.dropoff.Ethiopia;

  return (
    <Screen>
      <div className="grid gap-10 grid-cols-2 lg:grid-cols-4">
        <StatTile label={`Sequence network · ${RUNG_LABEL[rung]}`} value={num(seqHeld?.AP)}
          sub={`average precision on held-out women; explainable boosting ${num(ebmHeld?.AP)}`} tone="accent"
        />
        <StatTile label="Ladder broken" value={pct(N.ladder_violations["Ladder transformer"] ?? 0, 1)}
          sub={`networks; three separate XGBoost models: ${pct(N.ladder_violations["XGBoost, three separate models"] ?? 0, 1)} of women`} tone="good" />
        <StatTile label="What the sequence adds" value="9 steps" sub="a chance for every next contact, so the whole count, not three yes/no answers" />
        <StatTile label="Runs here" value={<span className="flex items-center gap-6"><Cpu className="size-16" />{nets ? "ready" : "loading"}</span>}
          sub="the networks run in this browser from their weights, checked against PyTorch" />
      </div>

      <Panel
        title={`Networks against the trees, on the same held-out women · ${RUNG_LABEL[rung]}`}
        how="Average precision on the 1,375 held-out women for the two networks and the three reference models, all trained on the same development women with the same 95 predictors. Rings: the networks' development score (cross-validated, three seeds). On tables of this size, gradient-boosted trees usually match or beat networks; here the sequence network ties at ANC8+ and trails at ANC1+ and ANC4+."
        actions={<Segmented label="Rung" options={RUNGS.map((r) => ({ key: r.key, label: r.label }))} value={rung} onChange={(k) => studio.set({ rung: k })} />}
      >
        <DotRows
          rows={[...TREES, ...NETWORKS].map((m) => {
            const h = held.find((r) => r.model === m);
            const d = N.development.find((r) => r.rung === outcome && r.model === m);
            return {
              key: m,
              label: m,
              tag: NETWORKS.includes(m) ? <Tag tone="warn">network</Tag> : undefined,
              values: { dev: d?.AP ?? null, held: h?.AP ?? null },
              lo: d ? { dev: d.AP - 2 * d.AP_sd } : undefined,
              hi: d ? { dev: d.AP + 2 * d.AP_sd } : undefined,
              sub: h ? `AUC ${h.AUROC.toFixed(3)} · calibration slope ${h.Calibration_slope.toFixed(2)}` : undefined,
              display: num(h?.AP),
            };
          }).sort((a, b) => (b.values.held ?? 0) - (a.values.held ?? 0))}
          series={[
            { key: "dev", label: "Development (networks, ±2 sd over seeds)", color: "var(--dim)", hollow: true },
            { key: "held", label: "Held-out women", color: "var(--accent)" },
          ]}
          format={(v) => v.toFixed(3)}
          labelWidth={260}
        />
        <DataNote>Networks usually need tens of thousands of records to overtake trees on tables like this; pooling survey rounds and countries would test whether they then pull ahead.</DataNote>
      </Panel>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
        <Panel
          title="Try it: a composite woman"
          how="Pick a region and a wealth group. The woman is a composite: every answer is the most common one among the survey's women in that group (at least 25 of them), so she is nobody in particular. Both networks run on her in this browser. Tick a change to see how their predictions move."
        >
          <div className="px-14 py-10 flex flex-wrap items-center gap-8 border-b border-border">
            <Select value={region} onChange={(e) => studio.set({ region: e.target.value === "Ethiopia" ? "" : e.target.value })}
              className="w-auto min-w-[160px] h-24 text-10.5" aria-label="Region">
              {["Ethiopia", ...REGION_NAMES].map((r) => <option key={r} value={r}>{r}</option>)}
            </Select>
            <Select value={wealth} onChange={(e) => setWealth(e.target.value)} className="w-auto min-w-[130px] h-24 text-10.5" aria-label="Wealth group">
              <option value="">Any wealth</option>
              {QUINTILES.map((q) => (
                <option key={q} value={q} disabled={!L.profiles.profiles.some((p) => p.region === region && p.wealth === q)}>{q}</option>
              ))}
            </Select>
            {profile && <span className="text-10 text-faint">composite of {profile.n.toLocaleString()} women</span>}
          </div>
          <div className="px-14 py-8 flex flex-wrap gap-12 border-b border-border">
            {EDITS.map((e) => (
              <label key={e.key} className="flex items-center gap-5 text-10.5">
                <input type="checkbox" checked={edits.includes(e.key)} className="accent-[var(--accent)]"
                  onChange={(ev) => setEdits((s) => (ev.target.checked ? [...s, e.key] : s.filter((k) => k !== e.key)))} />
                {e.label}
              </label>
            ))}
          </div>
          {run ? (
            <>
              <DotRows
                rows={(["anc1", "anc4", "anc8"] as const).map((k, i) => ({
                  key: k,
                  label: RUNG_LABEL[k],
                  values: { ladder: run.l.p[i], seq: run.s.p[i] },
                  sub: edits.length ? `was ${pct(run.base.s.p[i], 0)} (sequence) · ${pct(run.base.l.p[i], 0)} (ladder)` : undefined,
                  display: edits.length ? `${signed((run.s.p[i] - run.base.s.p[i]) * 100, 1)} pt` : pct(run.s.p[i], 0),
                }))}
                series={[
                  { key: "ladder", label: "Ladder transformer", color: MODEL_COLOR["Ladder transformer"] },
                  { key: "seq", label: "Sequence network", color: MODEL_COLOR[NETWORKS[1]] },
                ]}
                domain={[0, 1]}
                ticks={[0, 0.25, 0.5, 0.75, 1]}
                format={(v) => pct(v)}
                labelWidth={130}
                valueWidth={66}
              />
              <div className="border-t border-border">
                <div className="px-14 pt-10 text-10 font-semibold uppercase tracking-label text-faint">
                  Her contact count, as the sequence network sees it
                </div>
                <ChartBox height={190} className="pt-6 pr-14">
                  <ComposedChart
                    data={run.s.distribution.map((p, k) => ({ k: k === 9 ? "9+" : String(k), p, surv: run.s.survival[k], base: run.base.s.distribution[k] }))}
                    margin={{ left: -8, right: 6, top: 6, bottom: 0 }}
                  >
                    <CartesianGrid {...GRID} vertical={false} />
                    <XAxis {...AXIS} dataKey="k" interval={0} />
                    <YAxis {...AXIS} tickFormatter={(v) => pct(v)} width={40} domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} />
                    <Tooltip content={tip<{ k: string; p: number; surv: number }>((d) => (
                      <TipPanel title={`${d.k} contacts`} rows={[
                        { label: "Exactly this many", value: pct(d.p, 1), color: "var(--net)" },
                        { label: "At least this many", value: pct(d.surv, 1), color: "var(--text)" },
                      ]} />
                    ))} />
                    <Bar dataKey="p" radius={[2, 2, 0, 0]} isAnimationActive={false}>
                      {run.s.distribution.map((_, k) => <Cell key={k} fill={k === 0 ? "var(--bad)" : k < 4 ? "var(--rung1)" : k < 8 ? "var(--rung4)" : "var(--rung8)"} />)}
                    </Bar>
                    <Line dataKey="surv" stroke="var(--text)" strokeWidth={1.5} dot={{ r: 2 }} type="stepAfter" isAnimationActive={false} />
                  </ComposedChart>
                </ChartBox>
                <SeriesLegend items={[
                  { key: "b", label: "Chance of exactly k contacts", color: "var(--rung4)" },
                  { key: "s", label: "Still in care at contact k", color: "var(--text)" },
                ]} />
              </div>
            </>
          ) : (
            <PanelLoading rows={6} />
          )}
        </Panel>

        <Panel
          title="What the decoder looks at before each next contact"
          how="The sequence network decides, one contact at a time, whether this woman goes on to the next. Before each decision it attends to her answers. Rows are the decisions (after contact 0, 1, … 8); columns are groups of answers; darker means more attention. Hover a row to pick it out. Attention shows where the network looks, not why a woman stops."
        >
          {seqAtt ? (
            <>
              <MatrixHeat
                theme={theme}
                rows={seqAtt.map((row, k) => ({
                  key: String(k),
                  label: k === 0 ? "Start at all" : `After contact ${k}`,
                  sub: `goes on: ${pct(run!.s.cont[k], 0)}`,
                  values: Object.fromEntries(concepts.map((c, j) => [c.key, row[j]])),
                }))}
                cols={concepts.map((c) => ({ key: c.key, label: shortConcept(c.label), title: `${c.label}${c.modifiable ? " (a health system can change it)" : ""}` }))}
                format={(v) => (v * 100).toFixed(0)}
                active={focusStep != null ? String(focusStep) : undefined}
                onRow={(k) => setFocusStep((f) => (f === Number(k) ? null : Number(k)))}
                labelWidth={130}
                cellWidth={44}
              />
              <div className="px-14 pb-12">
                <Note tone="accent">
                  Numbers are the share of attention (%) at each step. Groups a health system can change: {concepts.filter((c) => c.modifiable).map((c) => c.label.toLowerCase()).join(", ")}.
                </Note>
              </div>
            </>
          ) : (
            <PanelLoading rows={9} />
          )}
        </Panel>
      </div>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-2">
        <Panel
          title={`Where women stop, contact by contact · ${region}`}
          how="The share of women still in care at each contact: dots are what the survey's women reported, the line is what the sequence network predicts for the same women. The ladder rungs are the points at 1, 4 and 8. Agreement here is a check that the network has learned the whole count, not only the three thresholds."
        >
          <ChartBox height={230} className="pt-10 pr-14">
            <ComposedChart data={drop} margin={{ left: -8, right: 6, top: 6, bottom: 0 }}>
              <CartesianGrid {...GRID} />
              <XAxis {...AXIS} dataKey="contact" type="number" domain={[0, 9]} ticks={[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]} />
              <YAxis {...AXIS} domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tickFormatter={(v) => pct(v)} width={44} />
              <Tooltip content={tip<{ contact: number; predicted: number; observed: number }>((d) => (
                <TipPanel title={`${d.contact} or more contacts`} rows={[
                  { label: "Survey", value: pct(d.observed, 1), color: "var(--bad)" },
                  { label: "Network", value: pct(d.predicted, 1), color: "var(--net)" },
                ]} />
              ))} />
              <Line dataKey="predicted" stroke="var(--net)" strokeWidth={2} dot={false} type="stepAfter" isAnimationActive={false} />
              <Line dataKey="observed" stroke="var(--bad)" strokeWidth={0} dot={{ r: 3, fill: "var(--bad)", strokeWidth: 0 }} isAnimationActive={false} />
            </ComposedChart>
          </ChartBox>
          <SeriesLegend items={[
            { key: "o", label: "Survey", color: "var(--bad)" },
            { key: "p", label: "Sequence network", color: "var(--net)" },
          ]} />
        </Panel>

        <Panel
          title="What the ladder network attends to, region by region"
          how="For the women of each region, the average attention the ladder transformer's summary token pays to each group of answers. One shading for the grid. A region whose row differs from the others is one where the network leans on different information."
        >
          <MatrixHeat
            theme={theme}
            rows={["Ethiopia", ...REGION_NAMES].filter((r) => L.attention.ladder[r]).map((r) => ({
              key: r,
              label: r,
              values: Object.fromEntries(concepts.map((c, j) => [c.key, L.attention.ladder[r][j]])),
            }))}
            cols={concepts.map((c) => ({ key: c.key, label: shortConcept(c.label), title: c.label }))}
            format={(v) => (v * 100).toFixed(0)}
            active={region}
            onRow={(r) => studio.set({ region: r === "Ethiopia" || r === studio.region ? "" : r })}
            labelWidth={130}
            cellWidth={44}
          />
        </Panel>
      </div>

      {run && (
        <Panel
          title="Her answers the ladder network attends to most"
          how="The composite woman's twelve answers that the ladder transformer's summary token attends to most, averaged over its two layers."
        >
          <RankedBars
            labelWidth={220}
            rows={run.l.attention
              .map((a, j) => ({ a, j }))
              .sort((x, y) => y.a - x.a)
              .slice(0, 12)
              .map(({ a, j }) => ({
                key: L.tokens[j],
                label: predictorLabel(L.tokens[j]),
                sub: concepts[L.token_concept[j]]?.label,
                value: a,
                display: `${(a * 100).toFixed(1)}%`,
                color: concepts[L.token_concept[j]]?.modifiable ? "var(--accent)" : "var(--faint)",
              }))}
          />
          <div className="px-14 pb-12">
            <Note tone="warn">
              Attention is where a network looks, not a measure of cause or even of importance; the explainable boosting model&apos;s terms
              (Explore › The ANC ladder) are the better guide to what matters. The networks are here for what trees cannot do: a coherent
              ladder, a whole contact-count distribution, and a view of the decision contact by contact.
            </Note>
          </div>
        </Panel>
      )}
    </Screen>
  );
}

function shortConcept(label: string): string {
  const m: Record<string, string> = {
    "Health post access": "Health post", "Distance to a hospital or health centre": "Hospital",
    "Barriers to reaching care": "Barriers", "Health insurance": "Insurance", "Information and media": "Media",
    "Wanted pregnancy and family size": "Wanted", "Women's say in decisions": "Her say", "Household wealth": "Wealth",
    "Her education": "Education", Region: "Region", "Urban or rural": "Urban", "Language and religion": "Culture",
    "Age and pregnancy history": "History", "Partner and household": "Household", "Her work": "Work",
  };
  return m[label] ?? label;
}

