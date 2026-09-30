"use client";

import Link from "next/link";
import { ArrowRight, Flame, Map as MapIcon, SlidersHorizontal, Upload } from "lucide-react";
import Funnel from "@/components/charts/Funnel";
import { Panel, PanelLoading, Screen, StatTile, InlineError } from "@/components/studio/ui";
import { useJSON } from "@/lib/data";
import { useStudio } from "@/lib/studio";
import { useMemo } from "react";
import type { FeatureCollection } from "geojson";
import { useRouter } from "next/navigation";
import MiniMap, { useRegionPaths } from "@/components/map/MiniMap";
import { useRenderTheme } from "@/components/shell/theme-provider";
import { NO_DATA, classify, colorOf } from "@/lib/colors";
import { REGION_NAMES } from "@/lib/regions";
import type { RegionsData } from "@/lib/regionsData";
import { EARLY, leverWeight, type ScenarioData } from "@/lib/scenario";
import { simulate, summarise, type WarData } from "@/lib/war";

type Cascade = {
  reach1: number; reach4: number; reach8: number; never: number;
  start_lt4: number; four_lt8: number; continue_1_to_4: number; continue_4_to_8: number; n: number;
};

const pct = (v: number) => `${Math.round(v * 100)}%`;

const TOOLS = [
  { path: "/map", icon: MapIcon, title: "Map & regions",
    body: "Every region shaded by where it loses women. Click one for its analysis and what to work on." },
  { path: "/planner", icon: SlidersHorizontal, title: "Scenario planner",
    body: "Move a factor a health system can change and see ANC1+, ANC4+ and ANC8+ respond, region by region." },
  { path: "/war", icon: Flame, title: "Conflict simulator",
    body: "What the Tigray war did to antenatal care, and what the same shock would do elsewhere." },
  { path: "/your-data", icon: Upload, title: "Your data",
    body: "Load your own ANC records: see the trend, a forecast, and which women to follow up." },
];

export default function Overview() {
  const studio = useStudio();
  const policy = useJSON<{ cascade: Cascade }>("/policy.json");

  return (
    <Screen>
      {policy.state === "error" && <InlineError message={policy.error} />}
      {policy.state === "ready" && (
        <div data-help="overview.tiles" className="grid gap-10 grid-cols-2 lg:grid-cols-4">
          <StatTile label="Reach any ANC" value={pct(policy.data.cascade.reach1)} sub="at least one contact (ANC1+)" />
          <StatTile label="Reach four contacts" value={pct(policy.data.cascade.reach4)} sub="the earlier standard (ANC4+)" />
          <StatTile label="Reach eight contacts" value={pct(policy.data.cascade.reach8)}
                    sub="the WHO recommendation (ANC8+)" tone="bad" />
          <StatTile label="Lost between 4 and 8" value={pct(1 - policy.data.cascade.continue_4_to_8)}
                    sub="of women who reach four never reach eight" tone="warn" />
        </div>
      )}

      <ActOn />

      <div className="grid gap-10 md:gap-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Panel help="overview.ladder"
          title="The antenatal care ladder"
          how="Each bar is the share of all women with a recent pregnancy who reached that rung. Between the bars: of the women on the rung above, how many continued and how many were lost."
        >
          {policy.state === "ready" ? (
            <div className="p-14">
              <Funnel
                steps={[
                  { key: "all", label: "All women", value: 1 },
                  { key: "anc1", label: "ANC1+", value: policy.data.cascade.reach1 },
                  { key: "anc4", label: "ANC4+", value: policy.data.cascade.reach4 },
                  { key: "anc8", label: "ANC8+", value: policy.data.cascade.reach8 },
                ]}
              />
            </div>
          ) : (
            <PanelLoading rows={4} />
          )}
        </Panel>

        <Panel help="overview.tools" title="Planning tools">
          <div className="grid sm:grid-cols-2">
            {TOOLS.map((t, i) => {
              const Icon = t.icon;
              return (
                <Link
                  key={t.path}
                  href={studio.href(t.path)}
                  className={`group block px-14 py-12 border-border hover:bg-panel2 hover:no-underline text-text ${
                    i % 2 === 0 ? "sm:border-r" : ""
                  } ${i < 2 ? "border-b" : "border-b sm:border-b-0"} last:border-b-0`}
                >
                  <div className="flex items-center gap-7">
                    <Icon className="size-14 text-accent" />
                    <span className="text-12 font-semibold flex-1">{t.title}</span>
                    <ArrowRight className="size-12 text-faint group-hover:text-accent" />
                  </div>
                  <div className="text-11 text-dim mt-5 leading-relaxed">{t.body}</div>
                </Link>
              );
            })}
          </div>
        </Panel>
      </div>
      <Link href={studio.href("/about")} className="text-10.5 text-accent hover:underline self-start">
        About the study
      </Link>
    </Screen>
  );
}

const fmtN = (v: number) => (v >= 1e6 ? `${(v / 1e6).toFixed(1)} million` : v >= 1e4 ? `${Math.round(v / 1e3)} thousand` : Math.round(v).toLocaleString());

/**
 * Four things to act on, each computed from the studio's own data and each a link to
 * the screen that shows it: where the ladder loses most, where the most women never
 * start, the strongest lever the data support, and what a conflict would cost.
 */
function ActOn() {
  const studio = useStudio();
  const router = useRouter();
  const theme = useRenderTheme();
  const reg = useJSON<RegionsData>("/data/regions.json");
  const sc = useJSON<ScenarioData>("/data/scenarios.json");
  const war = useJSON<WarData>("/data/war.json");
  const geo = useJSON<FeatureCollection>("/geo/regions.geojson");
  const paths = useRegionPaths(geo.data);

  const items = useMemo(() => {
    if (!reg.data || !sc.data || !war.data) return null;
    const R = reg.data;
    const nat = R.cohorts.recent.national;
    const births = (r: string) => R.population.regions[r]?.births ?? 0;
    const never = REGION_NAMES.map((r) => ({ r, n: births(r) * R.cohorts.recent.regions[r].never }))
      .sort((a, b) => b.n - a.n)[0];
    const natIdx = sc.data.regions.length - 1;
    const levers = [...sc.data.levers.filter((l) => l.supported_at?.[sc.data!.primary ?? "logistic"]?.anc8 ?? l.supported).map((l) => l.key), EARLY]
      .map((k) => ({ k, v: leverWeight(sc.data!, k, natIdx).anc8?.v ?? 0 }))
      .sort((a, b) => b.v - a.v);
    const top = levers[0];
    const label = top.k === EARLY ? "an earlier first visit" : sc.data.levers.find((l) => l.key === top.k)!.label.toLowerCase();
    const second = levers.find((l) => l.k !== EARLY);
    const secondLabel = second ? sc.data.levers.find((l) => l.key === second.k)!.label.toLowerCase() : "";
    // a Tigray-like siege in Amhara, the region with the most births in the north
    const a = R.cohorts.recent.regions.Amhara;
    const base = { anc1: a.reach1, anc4: a.reach4, anc8: a.reach8 };
    const s = { startQ: 1, durationQ: 8, intensity: 1, pattern: "siege" as const, restored: true,
      tau: war.data.fit.tau, kappa: war.data.backtest.kappa_fit ?? 2, horizonQ: 24 };
    const lost = summarise(simulate(war.data, s, base), base, births("Amhara"), s).lost.anc1;
    return [
      { tone: "var(--warn)", head: `${Math.round((1 - nat.continue_4_to_8) * 100)}% of women who reach four contacts stop before eight`,
        body: "The biggest loss on the ladder is not starting ANC but staying in it: retention between the fourth and eighth contact.",
        href: "/explore/ladder" },
      { tone: "var(--bad)", head: `${never.r}: ${fmtN(never.n)} women a year receive no ANC at all`,
        body: "More women never start antenatal care here than in any other region. Open it on the map for what drives it.",
        href: `/map?region=${encodeURIComponent(never.r)}&metric=never` },
      { tone: "var(--good)", head: `${label[0].toUpperCase()}${label.slice(1)} for half the women it applies to: +${(top.v * 50).toFixed(1)} points of ANC8+`,
        body: `Of the levers the data support, ${label} moves ANC8+ most${second ? `; next is ${secondLabel}` : ""}. Association-based.`,
        href: `/planner?lv=${top.k}:50&rung=anc8` },
      { tone: "var(--cross)", head: `A two-year siege in Amhara: about ${fmtN(lost)} more women with no ANC`,
        body: "The conflict simulator, built from the Tigray war and checked on Amhara, over six years including recovery.",
        href: "/war?hit=Amhara&rung=anc1" },
    ];
  }, [reg.data, sc.data, war.data]);

  const fills = useMemo(() => {
    if (!reg.data) return {};
    const vals = REGION_NAMES.map((r) => reg.data!.cohorts.recent.regions[r]?.reach8 ?? null);
    const cls = classify(vals, "good", theme);
    return Object.fromEntries(REGION_NAMES.map((r, i) => [r, colorOf(vals[i], cls, theme)]));
  }, [reg.data, theme]);

  return (
    <div className="grid gap-10 md:gap-14 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
      <Panel help="overview.act-on" title="Four things to act on" how="Each is computed from the studio's data and opens the screen that shows it.">
        {items ? (
          <div className="grid sm:grid-cols-2">
            {items.map((it, i) => (
              <Link key={i} href={studio.href(it.href)}
                className={`group block px-14 py-12 border-border hover:bg-panel2 hover:no-underline text-text ${i % 2 === 0 ? "sm:border-r" : ""} ${i < 2 ? "border-b" : "border-b sm:border-b-0"} last:border-b-0`}>
                <div className="flex gap-8">
                  <div className="w-3 rounded-2 flex-none" style={{ background: it.tone }} />
                  <div className="min-w-0">
                    <div className="text-12 font-semibold leading-snug flex items-start gap-6">
                      <span className="flex-1">{it.head}</span>
                      <ArrowRight className="size-12 text-faint group-hover:text-accent flex-none mt-2" />
                    </div>
                    <div className="text-10.5 text-dim mt-4 leading-relaxed">{it.body}</div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <PanelLoading rows={4} />
        )}
      </Panel>
      <Panel help="overview.minimap" title="ANC8+ by region" how="The share of women reaching eight contacts (24-month cohort), five classes, darker is more. Click a region to open it on the map.">
        {paths.length ? (
          <div className="px-14 py-10">
            <MiniMap paths={paths} fills={fills} noData={NO_DATA[theme]} title="ANC8+ by region"
              onSelect={(r) => router.push(studio.href(`/map?region=${encodeURIComponent(r)}&metric=anc8`))} />
          </div>
        ) : (
          <PanelLoading rows={4} />
        )}
      </Panel>
    </div>
  );
}
