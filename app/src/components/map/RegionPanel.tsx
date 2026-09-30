"use client";

import { useEffect, useState } from "react";
import { ArrowRight, X } from "lucide-react";
import Funnel from "@/components/charts/Funnel";
import { Hint, Note, Segmented, Tag } from "@/components/studio/ui";
import { helpHref } from "@/lib/help/href";
import { REACH_OF, cohortRungs, type RegionsData } from "@/lib/regionsData";
import { RUNGS, useStudio, type Cohort, type Rung } from "@/lib/studio";

/**
 * Everything the studio knows about one region, in the order a planner asks:
 * how far women get, where they are lost, what to work on, why the region differs,
 * who is left behind, and how many women that is each year.
 *
 * Docked beside the map (a full-screen sheet on a phone) so the map stays in view.
 * Every number is survey-weighted; intervals are 95% from the cluster bootstrap.
 */

const pct = (v: number | null | undefined, d = 0) => (v == null ? "—" : `${(v * 100).toFixed(d)}%`);
const people = (v: number) => (v >= 1e6 ? `${(v / 1e6).toFixed(2)} million` : v >= 1e4 ? `${Math.round(v / 1e3)},000` : `${Math.round(v).toLocaleString()}`);

const ACTION_TONE: Record<string, "bad" | "warn" | "accent"> = {
  Outreach: "bad",
  "Early engagement": "warn",
  Retention: "accent",
};
const ACTION_WHAT: Record<string, string> = {
  Outreach: "bring the service to women it does not yet reach",
  "Early engagement": "hold women through the first half of pregnancy",
  Retention: "follow-up, reminders, and a lower cost for each return visit",
};

const DIMENSIONS = ["Wealth", "Education", "Residence", "Pregnancy wanted", "Health post", "Age at birth"] as const;

function Section({ title, how, help, children, right }: {
  title: string; how?: string; help?: string; children: React.ReactNode; right?: React.ReactNode;
}) {
  return (
    <section data-help={help} className="px-14 py-10 border-b border-border">
      <div className="flex items-center gap-8 mb-7">
        <div className="text-9.5 uppercase tracking-label text-faint font-semibold flex-1">{title}</div>
        {right}
        {how && <Hint more={help ? helpHref(help) : undefined}>{how}</Hint>}
      </div>
      {children}
    </section>
  );
}

function LossBar({ label, c }: { label: string; c: { never: number; start_lt4: number; four_lt8: number; reach8: number } }) {
  const parts = [
    { k: "never", v: c.never, bg: "var(--bad)", name: "never start" },
    { k: "start_lt4", v: c.start_lt4, bg: "var(--warn)", name: "stop before 4" },
    { k: "four_lt8", v: c.four_lt8, bg: "var(--cross)", name: "stop between 4 and 8" },
    { k: "reach8", v: c.reach8, bg: "var(--good)", name: "reach 8" },
  ];
  return (
    <div className="grid grid-cols-[64px_minmax(0,1fr)] items-center gap-8">
      <span className="text-10.5 text-dim truncate">{label}</span>
      <div className="flex h-18 rounded-2 overflow-hidden">
        {parts.map((p) => (
          <div
            key={p.k}
            title={`${p.name}: ${pct(p.v)}`}
            className="h-full flex items-center justify-center font-mono text-9.5 text-white transition-all duration-500"
            style={{ width: `${Math.max(p.v, 0) * 100}%`, background: p.bg }}
          >
            {p.v >= 0.08 ? pct(p.v) : ""}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function RegionPanel({
  data,
  region,
  cohort,
  rung,
  onRung,
  onClose,
  onOpenPlanner,
}: {
  data: RegionsData;
  region: string;
  cohort: Cohort;
  rung: Rung;
  onRung: (r: Rung) => void;
  onClose: () => void;
  onOpenPlanner: () => void;
}) {
  const [dim, setDim] = useState<(typeof DIMENSIONS)[number]>("Wealth");
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);

  const studio = useStudio();
  const rungs = cohortRungs(cohort);
  const r = rungs.includes(rung) ? rung : "anc8";
  const rungLabel = RUNGS.find((x) => x.key === r)!.label;
  const c = data.cohorts[cohort].regions[region];
  const nat = data.cohorts[cohort].national;
  if (!c) return null;
  const reachKey = REACH_OF[r] as "reach1" | "reach4" | "reach8";

  // Why the region differs: an additive model's exact split (full cohort, full pool).
  // The model follows the planner's switch (the `lm` setting): explainable boosting or
  // logistic regression.
  const driverModels = Object.keys(data.drivers_by_model ?? {});
  const lmAsked = studio.params.get("lm") ?? "";
  const lm = driverModels.includes(lmAsked) ? lmAsked : data.drivers_primary ?? driverModels[0] ?? "";
  const D = data.drivers_by_model?.[lm] ?? data.drivers;
  const drv = D[r]?.regions[region];
  const conceptMeta = Object.fromEntries(data.concepts.map((k) => [k.key, k]));
  const drivers = drv
    ? Object.entries(drv.concepts)
        .map(([key, v]) => ({ ...conceptMeta[key], key, v }))
        .filter((d) => d.label)
        .sort((a, b) => a.v - b.v)
    : [];
  const maxAbs = Math.max(1e-6, ...drivers.map((d) => Math.abs(d.v)));
  const pulling = drivers.filter((d) => d.modifiable && d.v < -0.01).slice(0, 3);

  const sub = data.subgroups[cohort]?.[region]?.[dim] ?? [];
  const subNat = data.subgroups[cohort]?.["Ethiopia"]?.[dim] ?? [];
  const prof = data.profile[cohort]?.[region] ?? {};
  const profNat = data.profile[cohort]?.["Ethiopia"] ?? {};
  const gap = data.gap[cohort]?.[r]?.[region];
  const births = data.population.regions[region]?.births ?? null;

  const lossShare = c.loss === "never" ? c.never : c.loss === "start_lt4" ? c.start_lt4 : c.four_lt8;
  const lossName = c.loss === "never" ? "never start" : c.loss === "start_lt4" ? "start but stop before four" : "reach four and stop before eight";

  return (
    <aside
      data-help="map.region"
      aria-label={`${region}: region analysis`}
      className="bg-panel border-l border-border flex flex-col min-h-0 h-full overflow-hidden"
    >
      <div className="flex items-center gap-8 px-14 h-36 border-b border-border flex-none">
        <div className="text-13 font-semibold flex-1 truncate">{region}</div>
        <Tag tone={ACTION_TONE[c.action] ?? "neutral"}>{c.action}</Tag>
        <button onClick={onClose} aria-label="Close region panel" className="text-faint hover:text-text">
          <X className="size-14" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="px-14 pt-9 pb-8 border-b border-border flex items-center gap-10 flex-wrap">
          <span className="text-10 font-mono text-dim">
            {c.n.toLocaleString()} women · {c.clusters} clusters
          </span>
          <div className="flex-1" />
          <Segmented
            label="Rung"
            options={rungs.map((k) => ({ key: k, label: RUNGS.find((x) => x.key === k)!.label }))}
            value={r}
            onChange={onRung}
          />
        </div>

        <Section help="map.region-far" title="How far women get" how="Bars: share of all women in the region who reached each rung, with how many continued between rungs. The grey marks on the right are Ethiopia's values.">
          <div className="grid grid-cols-[minmax(0,1fr)_64px] gap-x-8">
            <Funnel
              compact
              steps={rungs.map((k) => ({ key: k, label: RUNGS.find((x) => x.key === k)!.label, value: c[REACH_OF[k]] }))}
              active={r}
              onSelect={(k) => onRung(k as Rung)}
            />
            <div className="flex flex-col justify-around text-right">
              {rungs.map((k) => (
                <div key={k} className="font-mono text-10 text-faint leading-tight">
                  <div>ETH {pct(nat[REACH_OF[k]])}</div>
                  <div className="text-9.5">
                    [{pct(c[`${REACH_OF[k]}_ci`][0])}–{pct(c[`${REACH_OF[k]}_ci`][1])}]
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Section>

        {cohort !== "entry" && (
          <Section help="map.region-lost" title="Where women are lost" how="Every woman falls in exactly one of these four groups; the widest red, orange or purple block is where the region loses most women.">
            <div className="flex flex-col gap-5">
              <LossBar label={region.length > 10 ? region.slice(0, 9) + "…" : region} c={c} />
              <LossBar label="Ethiopia" c={nat} />
            </div>
            <div className="flex flex-wrap gap-x-10 gap-y-2 mt-6 text-9.5 text-dim">
              {[["var(--bad)", "never start"], ["var(--warn)", "stop before 4"], ["var(--cross)", "stop 4–8"], ["var(--good)", "reach 8"]].map(([bg, l]) => (
                <span key={l} className="flex items-center gap-4">
                  <span className="w-8 h-8 rounded-1" style={{ background: bg }} />
                  {l}
                </span>
              ))}
            </div>
          </Section>
        )}

        <Section help="map.region-work" title="What to work on">
          <div className="flex flex-col gap-8">
            <Note tone={ACTION_TONE[c.action] === "bad" ? "bad" : ACTION_TONE[c.action] === "warn" ? "warn" : "accent"}>
              <span className="text-text font-semibold">{c.action}.</span> The biggest loss here is women who {lossName}:{" "}
              <span className="font-mono text-text">{pct(lossShare)}</span> of all women. Needed: {ACTION_WHAT[c.action]}.
            </Note>
            {pulling.length > 0 && (
              <Note tone="accent">
                <span className="text-text font-semibold">Changeable factors pulling {rungLabel} down here:</span>{" "}
                {pulling.map((p, i) => (
                  <span key={p.key}>
                    {i > 0 && "; "}
                    {p.label.toLowerCase()} <span className="text-faint">({p.lever.toLowerCase()})</span>
                  </span>
                ))}
                .
              </Note>
            )}
            {gap && Math.abs(gap.gap) >= 0.03 && (
              <Note tone={gap.gap > 0 ? "good" : "bad"}>
                {gap.gap > 0 ? (
                  <>
                    <span className="text-text font-semibold">A region to learn from.</span> {rungLabel} is{" "}
                    <span className="font-mono text-text">{(gap.gap * 100).toFixed(1)} points</span> above what its women&apos;s circumstances predict.
                  </>
                ) : (
                  <>
                    <span className="text-text font-semibold">Below its circumstances.</span> {rungLabel} is{" "}
                    <span className="font-mono text-text">{(-gap.gap * 100).toFixed(1)} points</span> below what its women&apos;s circumstances predict: the shortfall is more about services than about the population.
                  </>
                )}
              </Note>
            )}
            <button onClick={onOpenPlanner} className="self-start flex items-center gap-5 text-11 text-accent hover:underline">
              Try scenarios for {region} <ArrowRight className="size-12" />
            </button>
          </div>
        </Section>

        {drivers.length > 0 && (
          <Section
            help="map.region-why"
            title={`Why ${rungLabel} differs from Ethiopia`}
            how={`The model predicts each woman's chance as a sum of one term per factor (${driverModels.length > 1 ? "explainable boosting or logistic regression: the switch chooses" : "logistic regression"}). The region's average minus the national average splits exactly across factors: bars to the left pull this region below Ethiopia, bars to the right lift it. Factors a health system can change are marked. This is the model's arithmetic, not proof of cause.`}
            right={
              <span className="flex items-center gap-6">
                {driverModels.length > 1 && (
                  <Segmented label="Model" options={driverModels.map((m) => ({ key: m, label: m === "ebm" ? "Boosting" : "Logistic" }))}
                    value={lm} onChange={(k) => studio.set({ lm: k })} />
                )}
                <span className="font-mono text-9.5 text-dim">
                  model {pct(drv!.predicted)} vs {pct(D[r].national_predicted)}
                </span>
              </span>
            }
          >
            <div className="flex flex-col gap-3">
              {drivers.map((d) => (
                <div key={d.key} className="grid grid-cols-[138px_minmax(0,1fr)] items-center gap-8" title={d.lever || undefined}>
                  <span className="text-10.5 truncate flex items-center gap-4">
                    {d.modifiable && <span className="w-5 h-5 rounded-full bg-accent flex-none" title="a health system can change this" />}
                    <span className={d.modifiable ? "" : "text-dim"}>{d.label}</span>
                  </span>
                  <span className="relative block h-11">
                    <span className="absolute inset-y-0 left-1/2 w-px bg-border2" />
                    <span
                      className="absolute inset-y-1 rounded-1 transition-all duration-500"
                      style={{
                        width: `${(Math.abs(d.v) / maxAbs) * 50}%`,
                        left: d.v >= 0 ? "50%" : `${50 - (Math.abs(d.v) / maxAbs) * 50}%`,
                        background: d.v >= 0 ? "var(--good)" : "var(--bad)",
                        opacity: d.modifiable ? 1 : 0.55,
                      }}
                    />
                  </span>
                </div>
              ))}
            </div>
            <div className="flex justify-between text-9.5 text-faint mt-5 pl-[146px]">
              <span>pulls below Ethiopia</span>
              <span>lifts above</span>
            </div>
          </Section>
        )}

        <Section
          help="map.region-behind"
          title={`Who is left behind: ${rungLabel}`}
          how={`${rungLabel} for women in each group, in this region. The dashed mark is the same group nationally. Faded bars rest on fewer than ${data.min_n} women: read them as a direction, not a number.`}
        >
          <div className="mb-8">
            <Segmented label="Group by" options={DIMENSIONS.map((d) => ({ key: d, label: d }))} value={dim} onChange={setDim} />
          </div>
          <div className="flex flex-col gap-4">
            {sub.map((s) => {
              const v = s[reachKey];
              const nv = subNat.find((x) => x.level === s.level)?.[reachKey];
              return (
                <div key={s.level} className="grid grid-cols-[112px_minmax(0,1fr)_44px] items-center gap-8">
                  <span className="text-10.5 truncate" title={s.level}>{s.level}</span>
                  <span className="relative block h-11 bg-panel3 rounded-full">
                    <span
                      className="absolute inset-y-0 left-0 rounded-full transition-all duration-500"
                      style={{ width: `${v * 100}%`, background: "var(--accent)", opacity: s.small ? 0.35 : 1 }}
                    />
                    {nv != null && (
                      <span className="absolute -inset-y-2 border-l border-dashed border-text opacity-60" style={{ left: `${nv * 100}%` }} />
                    )}
                  </span>
                  <span className="text-right font-mono text-10" title={`${s.n} women`}>
                    {pct(v)}
                    {s.small && <span className="text-faint">*</span>}
                  </span>
                </div>
              );
            })}
          </div>
          {sub.some((s) => s.small) && (
            <div className="text-9.5 text-faint mt-5">* fewer than {data.min_n} women in the group</div>
          )}
        </Section>

        <Section help="map.region-circumstances" title="The region's circumstances" how="How common each circumstance is among women in this region (dot) against Ethiopia (tick). Blue dots are things a health system can change.">
          <div className="flex flex-col gap-4">
            {data.profile_meta
              .slice()
              .sort((a, b) => Number(b.modifiable) - Number(a.modifiable))
              .map((m) => {
                const v = prof[m.key];
                const n = profNat[m.key];
                if (v == null) return null;
                return (
                  <div key={m.key} className="grid grid-cols-[150px_minmax(0,1fr)_36px] items-center gap-8">
                    <span className={`text-10.5 truncate ${m.modifiable ? "" : "text-dim"}`} title={m.label}>{m.label}</span>
                    <span className="relative block h-11">
                      <span className="absolute top-1/2 left-0 right-0 h-px bg-border2" />
                      {n != null && <span className="absolute top-0 bottom-0 w-px bg-text opacity-60" style={{ left: `${n * 100}%` }} />}
                      <span
                        className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-9 h-9 rounded-full border border-panel transition-all duration-500"
                        style={{ left: `${v * 100}%`, background: m.modifiable ? "var(--accent)" : "var(--dim)" }}
                      />
                    </span>
                    <span className="text-right font-mono text-10">{pct(v)}</span>
                  </div>
                );
              })}
          </div>
        </Section>

        {births != null && (
          <Section help="map.region-year" title="Women each year" how={data.population.method + ". " + data.population.source + "."}>
            <div className="grid grid-cols-3 gap-8">
              {[
                ["Births", births],
                ["Not reaching 8", births * (1 - c.reach8)],
                ...(cohort !== "entry" ? [["No ANC at all", births * c.never] as [string, number]] : []),
              ].map(([l, v]) => (
                <div key={l as string}>
                  <div className="text-9.5 uppercase tracking-label text-faint font-semibold">{l}</div>
                  <div className="font-mono text-14 font-semibold mt-2">{people(v as number)}</div>
                </div>
              ))}
            </div>
          </Section>
        )}

        <div className="px-14 py-10 text-9.5 text-faint leading-relaxed">
          Survey-weighted, Ethiopia DHS 2024–25; intervals are 95% from a cluster bootstrap within the region. The model
          split uses the full cohort. Associations, not causes.
        </div>
      </div>
    </aside>
  );
}
