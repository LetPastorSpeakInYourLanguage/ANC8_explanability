"use client";

import Link from "next/link";
import { ArrowRight, Download } from "lucide-react";
import { Panel, Screen, SectionRule, StatTile } from "@/components/studio/ui";
import { MODELS_INDEX, type ModelsIndex } from "@/lib/modelCards";
import { useJSON } from "@/lib/data";
import { asset } from "@/lib/paths";
import { COHORTS, useStudio } from "@/lib/studio";

/**
 * The study on one page. It says what was done and points to the tool that shows each
 * finding, so nothing is explained twice: the tools carry the evidence, this page is
 * the map to them.
 */

interface Regions {
  cohorts: Record<string, { national: Record<string, number> }>;
}
interface War {
  did_check: Record<string, { did: number }>;
}
interface Scen {
  levers: { key: string; supported: boolean }[];
}

const TERMS: [string, string][] = [
  ["Rung", "One step of the ladder: ANC1+, ANC4+ or ANC8+ contacts."],
  ["Cohort", "Which women are counted: everyone, those who started ANC, or births in the last 24 months."],
  ["Held-out women", "1,375 women the models never saw until the final score."],
  ["Average precision", "How well a model ranks the women who reach the rung. Chance equals the share who reach it."],
  ["AUROC", "The chance that a woman who reached the rung is scored above one who did not. 0.5 is a coin toss."],
  ["Chance, prevalence", "The score of a model that knows nothing but the overall rate."],
  ["Calibration", "Whether a predicted 30% happens 30% of the time. A slope of 1 is honest."],
  ["PSU bootstrap", "Resampling whole survey clusters to get honest 95% intervals."],
  ["G-computation", "Re-scoring every woman as if a factor changed, then averaging. The planner's method."],
  ["SHAP", "A share of each prediction credited to each predictor."],
];

const DOCS: [string, string][] = [
  ["brief", "Brief"], ["findings", "Findings"], ["methods", "Methods"], ["data", "Data"],
  ["predictors", "Predictors"], ["horizons", "Horizons"], ["wartime", "Wartime"],
  ["limitations", "Limitations"], ["insights", "Insights"], ["glossary", "Glossary"],
  ["record", "Analysis record"], ["decisions", "Decisions"],
];

const p0 = (v: number) => `${Math.round(v * 100)}%`;

function Row({ text, to, go }: { text: React.ReactNode; to: string; go: string }) {
  const studio = useStudio();
  return (
    <Link
      href={studio.href(to)}
      className="group flex items-center gap-10 px-14 py-8 border-b border-border last:border-b-0 hover:bg-panel2 hover:no-underline text-text"
    >
      <span className="flex-1 min-w-0 text-11.5 leading-snug">{text}</span>
      <span className="text-10.5 text-accent whitespace-nowrap">{go}</span>
      <ArrowRight className="size-12 text-faint group-hover:text-accent flex-none" />
    </Link>
  );
}

export default function AboutPage() {
  const reg = useJSON<Regions>("/data/regions.json").data;
  const war = useJSON<War>("/data/war.json").data;
  const scen = useJSON<Scen>("/data/scenarios.json").data;
  const mod = useJSON<ModelsIndex>(MODELS_INDEX).data;

  const nat = reg?.cohorts.full.national;
  const recent = reg?.cohorts.recent.national;
  const supported = scen?.levers.filter((l) => l.supported).length;
  const aps8 = ["logistic-regression", "random-forest", "xgboost"]
    .map((s) => mod?.summary[`s21.${s}`]?.anc8?.ap).filter((v): v is number => v != null);
  const spread8 = aps8.length === 3 ? Math.max(...aps8) - Math.min(...aps8) : undefined;
  const n = (v: number | undefined, f: (x: number) => string) => (v == null ? "…" : f(v));

  return (
    <Screen>
      <div className="grid gap-10 grid-cols-2 xl:grid-cols-4">
        <StatTile label="Survey" value="EDHS 2024–25" sub="Ethiopia Demographic and Health Survey" />
        <StatTile label="Women" value={COHORTS[0].n.toLocaleString("en-US")} sub="most recent birth, contacts recorded" />
        <StatTile label="Cohorts" value="3" sub={COHORTS.map((c) => `${c.short} ${c.n.toLocaleString("en-US")}`).join(" · ")} />
        <StatTile label="Held-out" value={(mod?.meta.n_heldout ?? 1375).toLocaleString("en-US")} sub="scored once, survey-weighted" />
      </div>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-2">
        <Panel help="about.findings" title="Where to see each finding" how="Each line is a finding, and the tool that shows it. Numbers come from the studio's data files.">
          <Row to="/help" go="Help" text="New to the studio? Every tool explained in plain language, with screenshots." />
          <Row to="/explore/ladder" go="The ANC ladder"
            text={<><b className="font-mono">{n(nat?.continue_4_to_8, (v) => p0(1 - v))}</b> of women who reach four contacts stop before eight.</>} />
          <Row to="/explore/cohorts" go="Cohorts"
            text={<>The 24-month cohort reproduces the EDHS report: ANC4+ <b className="font-mono">{n(recent?.reach4, p0)}</b>.</>} />
          <Row to="/war" go="Conflict simulator"
            text={<>The Tigray war cut first contact by about <b className="font-mono">{n(war?.did_check.anc1.did, (v) => `${Math.round(v * 100)}`)}</b> points.</>} />
          <Row to="/planner" go="Scenario planner"
            text={<><b className="font-mono">{supported ?? "…"}</b> levers raise every rung; the others raise some rungs and not others.</>} />
          <Row to="/your-data?mode=register" go="First-visit screener" text="Twelve questions match the 21-predictor model." />
          <Row to="/models" go="Model analysis"
            text={<>The three models on the 21 finish within <b className="font-mono">{n(spread8, (v) => v.toFixed(2))}</b> average precision of each other at ANC8+.</>} />
        </Panel>

        <div className="flex flex-col gap-10 md:gap-14 min-w-0">
          <Panel help="about.limits" title="Limits" how="What this study cannot support, and where the tool that shows it lives.">
            <Row to="/planner" go="Scenario planner" text="Scenarios are associations, not causes." />
            <Row to="/models" go="Model analysis" text="One survey round: accuracy on another round is untested." />
            <Row to="/explore/cohorts" go="Cohorts" text="Contact counts are recalled, and older births are recalled less well." />
            <Row to="/war" go="Conflict simulator" text="Conflict elsewhere is assumed to act as it did in Tigray." />
            <Row to="/your-data?mode=register" go="First-visit screener" text="A score describes women like her, not her." />
          </Panel>

          <Panel help="about.reports" title="Full reports" how="The written study, for reviewers. Plain Markdown files.">
            <div className="p-14 flex flex-wrap gap-6">
              {DOCS.map(([k, t]) => (
                <a
                  key={k}
                  href={asset(`/docs/${k}.md`)}
                  download
                  className="inline-flex items-center gap-5 border border-border2 bg-panel h-22 px-8 rounded-2 text-10.5 text-dim hover:text-accent hover:no-underline"
                >
                  <Download className="size-10" />
                  {t}
                </a>
              ))}
            </div>
          </Panel>
        </div>
      </div>

      <div>
        <SectionRule label="Terms" />
        <div className="grid gap-x-14 sm:grid-cols-2 xl:grid-cols-3">
          {TERMS.map(([t, d]) => (
            <div key={t} className="py-6 border-b border-border">
              <div className="text-11 font-semibold">{t}</div>
              <div className="text-10.5 text-dim leading-snug">{d}</div>
            </div>
          ))}
        </div>
      </div>
    </Screen>
  );
}
