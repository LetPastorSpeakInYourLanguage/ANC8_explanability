"use client";

import { useEffect, useMemo, useState } from "react";
import Brief from "@/components/Brief";
import Reports, { type Documents } from "@/components/Reports";
import Journey, { type JourneyData } from "@/components/Journey";
import Findings from "@/components/Findings";
import InsightsView from "@/components/Insights";
import Ladder from "@/components/Ladder";
import Models from "@/components/Models";
import Evidence from "@/components/Evidence";
import FeatureValueView from "@/components/FeatureValue";
import HorizonsView from "@/components/Horizons";
import WartimeView from "@/components/Wartime";
import WhatIf from "@/components/WhatIf";
import Predict from "@/components/Predict";
import type { Bundle, Answers } from "@/lib/ebm";
import type { Insights, Schema, Example } from "@/lib/types";
import type { Analysis, Policy } from "@/lib/analysis";
import { asset } from "@/lib/paths";

type Tab =
  | "brief" | "findings" | "predictors" | "ladder" | "horizons" | "wartime" | "whatif"
  | "predict" | "evidence" | "record" | "reports";

const TABS: { id: Tab; title: string; blurb: string }[] = [
  { id: "brief", title: "Brief", blurb: "The policy brief for the Ministry of Health" },
  { id: "findings", title: "Findings", blurb: "Where women are lost along the antenatal care cascade" },
  { id: "predictors", title: "Predictors", blurb: "Which predictors carry the prediction: 2, 8, 21 or the full pool" },
  { id: "ladder", title: "The ladder", blurb: "How predictor value changes from ANC1+ to ANC4+ to ANC8+" },
  { id: "horizons", title: "Horizons", blurb: "Before ANC starts vs at ANC entry" },
  { id: "wartime", title: "Tigray war", blurb: "Antenatal care during and after the war, against other regions" },
  { id: "whatif", title: "What if", blurb: "Move a factor, watch the prediction respond" },
  { id: "predict", title: "Predict", blurb: "Score one woman across every model" },
  { id: "evidence", title: "Evidence", blurb: "Models, tuning, uncertainty, and how much to believe" },
  { id: "record", title: "Analysis record", blurb: "Every analysis, and what every term and chart means" },
  { id: "reports", title: "Reports", blurb: "Every document and figure, in full" },
];

const TAB_IDS = new Set(TABS.map((t) => t.id));

/** "#reports/predictors" -> ["reports", "predictors"]; unknown -> brief. */
function readHash(): [Tab, string | undefined] {
  if (typeof window === "undefined") return ["brief", undefined];
  const [t, d] = window.location.hash.replace(/^#/, "").split("/");
  return [TAB_IDS.has(t as Tab) ? (t as Tab) : "brief", d || undefined];
}

async function loadJSON<T>(path: string, fallback: T | null = null): Promise<T | null> {
  try {
    const r = await fetch(asset(path));
    if (!r.ok) return fallback;
    return (await r.json()) as T;
  } catch {
    return fallback;
  }
}

export default function Page() {
  const [tab, setTabState] = useState<Tab>("brief");
  const [doc, setDoc] = useState<string | undefined>(undefined);
  const [documents, setDocuments] = useState<Documents | null>(null);
  const [journey, setJourney] = useState<JourneyData | null>(null);

  // The address bar follows the view, so a tab or a report can be bookmarked
  // or sent to someone.
  const navigate = (t: string, d?: string) => {
    const next = (TAB_IDS.has(t as Tab) ? t : "brief") as Tab;
    setTabState(next);
    setDoc(d);
    const hash = d ? `#${next}/${d}` : `#${next}`;
    if (window.location.hash !== hash) window.history.pushState(null, "", hash);
    // A jump to one term or figure scrolls to it instead (see Journey).
    if (!d || !/^(term|fig)-/.test(d)) window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const setTab = (t: Tab) => navigate(t);

  useEffect(() => {
    const apply = () => {
      const [t, d] = readHash();
      setTabState(t);
      setDoc(d);
    };
    apply();
    // Plain links such as href="#record/term-ap" (used for the "?" next to
    // technical terms) change the hash without going through navigate().
    const onHash = () => { apply(); window.scrollTo({ top: 0 }); };
    window.addEventListener("popstate", apply);
    window.addEventListener("hashchange", onHash);
    return () => {
      window.removeEventListener("popstate", apply);
      window.removeEventListener("hashchange", onHash);
    };
  }, []);
  const [insights, setInsights] = useState<Insights | null>(null);
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [schema, setSchema] = useState<Schema | null>(null);
  const [examples, setExamples] = useState<Example[]>([]);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetch(asset("/insights.json")).then((r) => r.json()),
      fetch(asset("/ebm_bundle.json")).then((r) => r.json()),
      loadJSON<Schema>("/form_schema.json"),
      loadJSON<Example[]>("/examples.json", []),
      loadJSON<Analysis>("/analysis.json"),
      loadJSON<Policy>("/policy.json"),
      loadJSON<Documents>("/documents.json"),
      loadJSON<JourneyData>("/journey.json"),
    ])
      .then(([i, b, s, e, a, p, docs, j]) => {
        setDocuments(docs);
        setJourney(j);
        setInsights(i);
        setBundle(b);
        setSchema(s);
        setExamples(e ?? []);
        setAnalysis(a);
        setPolicy(p);
      })
      .catch((e) => setError(String(e)));
  }, []);

  // A real woman from the held-out set as the what-if starting point: it is
  // more informative to perturb an actual profile than an invented one.
  const startingPoint = useMemo<Answers>(() => {
    const typical = examples.find((e) => e.label === "typical") ?? examples[0];
    if (typical) return typical.answers as Answers;
    if (!insights) return {};
    const out: Answers = {};
    for (const [name, r] of Object.entries(insights.ranges)) {
      out[name] = r.kind === "continuous" ? r.median : r.options[0];
    }
    return out;
  }, [examples, insights]);

  if (error) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-12">
        <p style={{ color: "var(--warn)" }}>Could not load the model: {error}</p>
      </main>
    );
  }

  if (!insights || !bundle) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-12">
        <p className="label">Loading…</p>
      </main>
    );
  }

  const prevalence = insights.outcomes?.anc8plus?.weighted_prevalence;
  const visible = TABS.filter((t) => {
    if (t.id === "findings") return !!policy;
    if (t.id === "reports") return !!documents;
    if (t.id === "record") return !!journey;
    if (t.id === "brief") return !!policy || !!analysis;
    if (t.id === "evidence") return !!analysis;
    if (t.id === "predictors") return !!analysis?.feature_value;
    if (t.id === "horizons") return !!analysis?.horizons;
    if (t.id === "wartime") return !!policy?.wartime;
    if (t.id === "predict") return !!schema;
    return true;
  });
  const active = visible.some((t) => t.id === tab) ? tab : visible[0].id;

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:py-10">
      <header className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">
          Antenatal care attainment in Ethiopia
        </h1>
        <p className="label mt-2 max-w-3xl leading-relaxed">
          What predicts whether a woman reaches antenatal care, and whether she
          completes the eight contacts the WHO recommends. Built on the 2024–25
          Ethiopia DHS.
          {prevalence != null && (
            <>
              {" "}
              Nationally {(prevalence * 100).toFixed(1)}% of women attain ANC8+,
              which is the number any prediction should be read against.
            </>
          )}
        </p>
      </header>

      <nav
        className="flex gap-1 overflow-x-auto mb-6 pb-px"
        style={{ borderBottom: "1px solid var(--line)" }}
      >
        {visible.map((t) => {
          const on = active === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className="px-3 py-2 text-sm whitespace-nowrap"
              style={{
                borderBottom: on ? "2px solid var(--accent)" : "2px solid transparent",
                color: on ? "var(--fg)" : "var(--muted)",
                fontWeight: on ? 600 : 400,
              }}
              title={t.blurb}
            >
              {t.title}
            </button>
          );
        })}
      </nav>

      {active === "brief" && (
        <Brief policy={policy} analysis={analysis} onNavigate={navigate} />
      )}
      {active === "record" && journey && (
        <Journey data={journey} docs={documents} sub={doc} onNavigate={navigate} />
      )}
      {active === "findings" && policy && <Findings policy={policy} />}
      {active === "predictors" && analysis?.feature_value && (
        <div className="space-y-6">
          <FeatureValueView data={analysis.feature_value} />
          <InsightsView data={insights} analysis={analysis ?? undefined} />
        </div>
      )}
      {active === "ladder" && (
        <Ladder data={insights} analysis={analysis ?? undefined} />
      )}
      {active === "horizons" && analysis?.horizons && (
        <HorizonsView data={analysis.horizons} />
      )}
      {active === "wartime" && policy?.wartime && <WartimeView data={policy.wartime} />}
      {active === "whatif" && (
        <WhatIf bundle={bundle} insights={insights} initial={startingPoint} />
      )}
      {active === "evidence" && analysis && (
        <div className="space-y-6">
          <Models analysis={analysis} />
          <Evidence analysis={analysis} />
        </div>
      )}
      {active === "predict" && schema && <Predict schema={schema} />}
      {active === "reports" && documents && (
        <Reports data={documents} initialDoc={doc} />
      )}

      <footer className="mt-10 pt-5" style={{ borderTop: "1px solid var(--line)" }}>
        <p className="label leading-relaxed max-w-3xl">
          A research and educational tool, not clinical advice, and not
          validated for decisions about individuals. Everything here describes
          associations in one survey round in one country. A predicted
          probability is a rate among women with similar recorded
          characteristics — not a statement about what will happen to any
          particular person.
        </p>
      </footer>
    </main>
  );
}
