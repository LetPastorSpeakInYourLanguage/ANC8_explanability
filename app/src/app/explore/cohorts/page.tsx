"use client";

import { useMemo } from "react";
import { CartesianGrid, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import DotRows from "@/components/charts/DotRows";
import RankedBars from "@/components/charts/RankedBars";
import { AXIS, ChartBox, GRID, SeriesLegend, TipPanel, tip } from "@/components/charts/rc";
import { DataNote, InlineError, Note, Panel, PanelLoading, Screen, Segmented, StatTile, Tag } from "@/components/studio/ui";
import type { Analysis } from "@/lib/analysis";
import { useJSON } from "@/lib/data";
import { COHORT_COLOR, OUTCOME_OF, RUNG_LABEL, num, pct, setName, signed, type ExploreData } from "@/lib/explore";
import { label } from "@/lib/labels";
import { REGION_NAMES } from "@/lib/regions";
import { REACH_OF, type RegionsData } from "@/lib/regionsData";
import { COHORTS, RUNGS, useStudio, type Cohort, type Rung } from "@/lib/studio";

const HORIZON_SETS = ["21"];

export default function CohortsPage() {
  const studio = useStudio();
  const reg = useJSON<RegionsData>("/data/regions.json");
  const exp = useJSON<ExploreData>("/data/explore.json");
  const ana = useJSON<Analysis>("/analysis.json");

  const rung = studio.rung;
  const place = studio.region || "Ethiopia";
  // ANC entry has no ANC1+ (everyone in it started), and the horizon analyses cover ANC4+ and ANC8+.
  const hRung: Rung = rung === "anc1" ? "anc8" : rung;
  const hOut = OUTCOME_OF[hRung];

  const reach = (c: Cohort, r: Rung, region: string | null) => {
    if (!reg.data || (c === "entry" && r === "anc1")) return null;
    const x = region ? reg.data.cohorts[c].regions[region] : reg.data.cohorts[c].national;
    return x ? x[REACH_OF[r]] : null;
  };
  const ci = (c: Cohort, r: Rung, region: string | null, i: 0 | 1) => {
    if (!reg.data || (c === "entry" && r === "anc1")) return null;
    const x = region ? reg.data.cohorts[c].regions[region] : reg.data.cohorts[c].national;
    return x ? x[`${REACH_OF[r]}_ci`][i] : null;
  };

  const contactLines = useMemo(() => {
    const c = exp.data?.contacts;
    if (!c) return null;
    const cap = exp.data?.contact_cap ?? 12;
    return Array.from({ length: cap + 1 }, (_, k) => ({
      k: k === cap ? `${cap}+` : String(k),
      ...Object.fromEntries(COHORTS.map((co) => [co.key, c[co.key]?.[place]?.share[k] ?? null])),
    }));
  }, [exp.data, place]);

  const edhs = useMemo(() => {
    if (!reg.data || !exp.data) return null;
    const rows = REGION_NAMES.map((r) => ({
      region: r,
      ours: reg.data!.cohorts.recent.regions[r]?.reach4 ?? null,
      report: exp.data!.edhs_anc4.regions[r] ?? null,
    }));
    const diffs = rows.filter((r) => r.ours != null && r.report != null).map((r) => Math.abs(r.ours! - r.report!));
    return {
      rows: rows.sort((a, b) => (b.report ?? 0) - (a.report ?? 0)),
      mad: diffs.reduce((a, b) => a + b, 0) / diffs.length,
      worst: Math.max(...diffs),
      national: reg.data.cohorts.recent.national.reach4,
      reportNational: exp.data.edhs_anc4.national,
    };
  }, [reg.data, exp.data]);

  const err = reg.error ?? exp.error ?? ana.error;
  if (err) return <Screen><InlineError message={err} /></Screen>;

  const H = ana.data?.horizons;
  const boot = H?.bootstrap ?? {};

  return (
    <Screen>
      <div data-help="cohorts.tiles" className="grid gap-10 grid-cols-1 md:grid-cols-3">
        {COHORTS.map((c) => (
          <StatTile
            key={c.key}
            label={c.label}
            value={c.n.toLocaleString()}
            sub={c.blurb}
            active={studio.cohort === c.key}
            onClick={() => studio.set({ cohort: c.key })}
          >
            <div className="mt-8 flex gap-10 font-mono text-10.5">
              {RUNGS.map((r) => (
                <span key={r.key} className="text-dim">
                  {r.label} <span className="text-text font-semibold">{pct(reach(c.key, r.key, null))}</span>
                </span>
              ))}
            </div>
          </StatTile>
        ))}
      </div>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-2">
        <Panel help="cohorts.ladder"
          title={`The ladder in each cohort · ${place}`}
          how="Each row is a rung; each dot is one cohort's share reaching it, with its 95% interval. The ANC-entry cohort starts at ANC1+ by definition (every woman in it had a first visit), so its ANC4+ and ANC8+ are higher: they are shares of women who started."
        >
          {reg.data ? (
            <DotRows
              rows={RUNGS.map((r) => ({
                key: r.key,
                label: r.label,
                values: Object.fromEntries(COHORTS.map((c) => [c.key, reach(c.key, r.key, studio.region || null)])),
                lo: Object.fromEntries(COHORTS.map((c) => [c.key, ci(c.key, r.key, studio.region || null, 0)])),
                hi: Object.fromEntries(COHORTS.map((c) => [c.key, ci(c.key, r.key, studio.region || null, 1)])),
                display: pct(reach(studio.cohort, r.key, studio.region || null)),
              }))}
              series={COHORTS.map((c) => ({ key: c.key, label: c.label, color: COHORT_COLOR[c.key] }))}
              domain={[0, 1]}
              ticks={[0, 0.25, 0.5, 0.75, 1]}
              format={(v) => pct(v)}
              connect={false}
              active={rung}
              onSelect={(k) => studio.set({ rung: k as Rung })}
              labelWidth={90}
            />
          ) : (
            <PanelLoading rows={3} />
          )}
        </Panel>

        <Panel help="cohorts.contacts"
          title={`Contact counts in each cohort · ${place}`}
          how="The share of women with each number of contacts, one line per cohort. The full and 24-month cohorts nearly coincide; the ANC-entry line has no zero and so sits higher everywhere else."
        >
          {contactLines ? (
            <>
              <ChartBox height={210} className="pt-10 pr-14">
                <LineChart data={contactLines} margin={{ left: -8, right: 6, top: 6, bottom: 0 }}>
                  <CartesianGrid {...GRID} vertical={false} />
                  <XAxis {...AXIS} dataKey="k" interval={0} />
                  <YAxis {...AXIS} tickFormatter={(v) => pct(v)} width={44} />
                  <Tooltip
                    content={tip<Record<string, number | string>>((d) => (
                      <TipPanel
                        title={`${d.k} contacts`}
                        rows={COHORTS.map((c) => ({ label: c.label, value: pct(d[c.key] as number, 1), color: COHORT_COLOR[c.key] }))}
                      />
                    ))}
                  />
                  {COHORTS.map((c) => (
                    <Line key={c.key} dataKey={c.key} stroke={COHORT_COLOR[c.key]} strokeWidth={studio.cohort === c.key ? 2.5 : 1.5}
                      dot={{ r: 2, strokeWidth: 0, fill: COHORT_COLOR[c.key] }} isAnimationActive={false} connectNulls />
                  ))}
                </LineChart>
              </ChartBox>
              <SeriesLegend items={COHORTS.map((c) => ({ key: c.key, label: c.label, color: COHORT_COLOR[c.key] }))} />
            </>
          ) : (
            <PanelLoading rows={5} />
          )}
        </Panel>
      </div>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-2">
        <Panel help="cohorts.regions"
          title={`Region by region, three cohorts · ${RUNG_LABEL[rung]}`}
          how="Each region's share reaching the rung in the three cohorts. Where the full-cohort dot sits left of the 24-month dot, the older births (24 to 35 months before interview) did worse: in Tigray those pregnancies fell in the war."
          actions={
            <Segmented label="Rung" options={RUNGS.map((r) => ({ key: r.key, label: r.label }))} value={rung}
              onChange={(k) => studio.set({ rung: k })} />
          }
        >
          {reg.data ? (
            <DotRows
              rows={[...REGION_NAMES]
                .sort((a, b) => (reach("full", rung, b) ?? 0) - (reach("full", rung, a) ?? 0))
                .map((r) => ({
                  key: r,
                  label: r,
                  values: Object.fromEntries(COHORTS.map((c) => [c.key, reach(c.key, rung, r)])),
                  display: signed(((reach("recent", rung, r) ?? 0) - (reach("full", rung, r) ?? 0)) * 100, 1),
                }))}
              series={COHORTS.map((c) => ({ key: c.key, label: c.label, color: COHORT_COLOR[c.key] }))}
              domain={[0, 1]}
              ticks={[0, 0.25, 0.5, 0.75, 1]}
              format={(v) => pct(v)}
              active={studio.region}
              onSelect={(k) => studio.set({ region: k === studio.region ? "" : k })}
              labelWidth={150}
              valueWidth={48}
            />
          ) : (
            <PanelLoading rows={10} />
          )}
          <div className="px-14 pb-12">
            <Note tone="accent">The number at the right is the 24-month cohort minus the full cohort, in percentage points.</Note>
          </div>
          <DataNote>Earlier EDHS rounds would give a trend across surveys rather than one reconstructed from birth dates.</DataNote>
        </Panel>

        <Panel help="cohorts.edhs"
          title="The 24-month cohort reproduces the EDHS report"
          how="ANC4+ by region: rings are the EDHS 2024–25 report's table (women with a live birth in the two years before the survey), dots are this study's 24-month cohort computed from the raw data. Matching them is the check that the cohort, the weights and the contact count are built the way DHS builds them."
          actions={edhs ? <Tag tone="good">mean gap {(edhs.mad * 100).toFixed(1)} pt</Tag> : undefined}
        >
          {edhs ? (
            <>
              <DotRows
                rows={[
                  {
                    key: "Ethiopia",
                    label: <span className="font-semibold">Ethiopia</span>,
                    values: { report: edhs.reportNational, ours: edhs.national },
                    display: signed((edhs.national - edhs.reportNational) * 100, 1),
                  },
                  ...edhs.rows.map((r) => ({
                    key: r.region,
                    label: r.region,
                    values: { report: r.report, ours: r.ours },
                    display: r.ours != null && r.report != null ? signed((r.ours - r.report) * 100, 1) : "–",
                  })),
                ]}
                series={[
                  { key: "report", label: "EDHS report", color: "var(--dim)", hollow: true },
                  { key: "ours", label: "This study, 24-month cohort", color: "var(--good)" },
                ]}
                domain={[0, 1]}
                ticks={[0, 0.25, 0.5, 0.75, 1]}
                format={(v) => pct(v)}
                active={studio.region}
                onSelect={(k) => k !== "Ethiopia" && studio.set({ region: k === studio.region ? "" : k })}
                labelWidth={150}
                valueWidth={48}
              />
              <div className="px-14 pb-12">
                <Note tone="good">
                  Largest regional gap {(edhs.worst * 100).toFixed(1)} points; national {pct(edhs.national, 1)} against the report&apos;s{" "}
                  {pct(edhs.reportNational, 1)}.
                </Note>
              </div>
            </>
          ) : (
            <PanelLoading rows={10} />
          )}
        </Panel>
      </div>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-2">
        <Panel help="cohorts.first-visit"
          title={`What the first visit adds · ${RUNG_LABEL[hRung]}`}
          how="Predicting at a woman's first ANC visit, rather than before it, adds one fact: whether that visit came in the first trimester. Rings: held-out accuracy without it; dots: with it. Under each set, the held-out gain and its 95% interval from 1,000 resamples."
          actions={
            <Segmented label="Rung" options={[{ key: "anc4", label: "ANC4+" }, { key: "anc8", label: "ANC8+" }]} value={hRung}
              onChange={(k) => studio.set({ rung: k as Rung })} />
          }
        >
          {H?.heldout ? (
            <DotRows
              rows={HORIZON_SETS.map((set) => {
                const rs = H.heldout!.filter((r) => r.outcome === hOut && r.set === set);
                const without = rs.find((r) => !r.early_anc);
                const withE = rs.find((r) => r.early_anc);
                const b = boot[`${hOut} | ${set} + early ANC vs ${set}`];
                return {
                  key: set,
                  label: setName(set, without?.n_predictors),
                  sub: b ? `gain ${signed(b.d_AP)} (${signed(b.d_AP_lo)} to ${signed(b.d_AP_hi)})` : undefined,
                  values: { without: without?.AP, with: withE?.AP },
                  display: signed((withE?.AP ?? 0) - (without?.AP ?? 0)),
                };
              })}
              series={[
                { key: "without", label: "Without first-visit timing", color: "var(--dim)", hollow: true },
                { key: "with", label: "With it", color: "var(--cross)" },
              ]}
              reference={{ value: H.heldout.find((r) => r.outcome === hOut)?.prevalence ?? 0, label: "Chance" }}
              format={(v) => v.toFixed(2)}
              labelWidth={210}
            />
          ) : (
            <PanelLoading rows={3} />
          )}
        </Panel>

        <Panel help="cohorts.train-on"
          title={`Train on everyone, or only on women who started? · ${RUNG_LABEL[hRung]}`}
          how="Scored on the same held-out women who started ANC. Rings: a model trained on the whole cohort; dots: trained only on women who started. Accuracy is close; the difference is calibration. Under each row, calibration-in-the-large (0 is perfect): the whole-cohort model underestimates women who have already started."
        >
          {H?.cross ? (
            <DotRows
              rows={["21"].map((set) => {
                const f = H.cross!.find((r) => r.outcome === hOut && r.set === set && r.trained_on.startsWith("full"));
                const e = H.cross!.find((r) => r.outcome === hOut && r.set === set && r.trained_on.startsWith("ANC-entry"));
                return {
                  key: set,
                  label: setName(set, set === "21" ? 21 : 88),
                  sub: f && e ? `calibration-in-the-large ${num(f.CITL, 2)} → ${num(e.CITL, 2)}` : undefined,
                  values: { full: f?.AP, entry: e?.AP },
                  display: signed((e?.AP ?? 0) - (f?.AP ?? 0)),
                };
              })}
              series={[
                { key: "full", label: "Trained on the full cohort", color: "var(--accent)", hollow: true },
                { key: "entry", label: "Trained on ANC-entry women", color: "var(--cross)" },
              ]}
              format={(v) => v.toFixed(3)}
              labelWidth={250}
            />
          ) : (
            <PanelLoading rows={2} />
          )}
        </Panel>
      </div>

      {H?.tiers && (
        <Panel help="cohorts.moments"
          title={`What each moment selects · ${RUNG_LABEL[hRung]}`}
          how="Forward selection run separately for the two prediction moments. Bars are the accuracy each predictor adds when it joins (step order from the top). At the first visit, its timing (purple) enters near the front of the queue."
        >
          <div className="grid md:grid-cols-2">
            {(["before ANC", "ANC entry"] as const).map((h) => {
              const rs = H.tiers!.filter((r) => r.outcome === hOut && r.horizon === h).sort((a, b) => a.step - b.step);
              return (
                <div key={h} className="min-w-0 md:first:border-r border-border">
                  <div className="px-16 pt-10 text-10 font-semibold uppercase tracking-label text-dim">
                    {h === "before ANC" ? "Before ANC starts" : "At the first visit"}
                  </div>
                  <RankedBars
                    labelWidth={220}
                    rows={rs.map((r) => ({
                      key: r.predictor,
                      label: `${r.step}. ${label(r.predictor)}`,
                      sub: r.tier === "tier 1" ? "strongest few" : "next tier",
                      value: r.gain,
                      display: signed(r.gain),
                      color: r.predictor === "early_anc" ? "var(--cross)" : r.tier === "tier 1" ? "var(--good)" : "var(--accent)",
                    }))}
                  />
                </div>
              );
            })}
          </div>
        </Panel>
      )}
    </Screen>
  );
}
