"use client";

import Link from "next/link";
import { ArrowRight, Flame, Map as MapIcon, SlidersHorizontal, Upload } from "lucide-react";
import Funnel from "@/components/charts/Funnel";
import { Panel, PanelLoading, Screen, StatTile, InlineError } from "@/components/studio/ui";
import { useJSON } from "@/lib/data";
import { useStudio } from "@/lib/studio";

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
        <div className="grid gap-10 grid-cols-2 lg:grid-cols-4">
          <StatTile label="Reach any ANC" value={pct(policy.data.cascade.reach1)} sub="at least one contact (ANC1+)" />
          <StatTile label="Reach four contacts" value={pct(policy.data.cascade.reach4)} sub="the earlier standard (ANC4+)" />
          <StatTile label="Reach eight contacts" value={pct(policy.data.cascade.reach8)}
                    sub="the WHO recommendation (ANC8+)" tone="bad" />
          <StatTile label="Lost between 4 and 8" value={pct(1 - policy.data.cascade.continue_4_to_8)}
                    sub="of women who reach four never reach eight" tone="warn" />
        </div>
      )}

      <div className="grid gap-10 md:gap-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Panel
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

        <Panel title="Planning tools">
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
    </Screen>
  );
}
