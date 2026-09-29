"use client";

import { useMemo } from "react";
import Predict from "@/components/predict/Predict";
import { InlineError, PanelLoading, Screen } from "@/components/studio/ui";
import { useJSON } from "@/lib/data";
import type { Bundle, Answers } from "@/lib/ebm";
import type { Insights, Schema, Example } from "@/lib/types";

export default function PredictPage() {
  const schema = useJSON<Schema>("/form_schema.json");
  const browser = useJSON<Bundle>("/browser_models.json");
  const insights = useJSON<Insights>("/insights.json");
  const examples = useJSON<Example[]>("/examples.json");

  // A real woman from the held-out set as the starting point: perturbing an actual
  // profile is more informative than perturbing an invented one.
  const start = useMemo<Answers>(() => {
    const ex = examples.data ?? [];
    const typical = ex.find((e) => e.label === "typical") ?? ex[0];
    if (typical) return typical.answers as Answers;
    const out: Answers = {};
    for (const [name, r] of Object.entries(insights.data?.ranges ?? {})) {
      out[name] = r.kind === "continuous" ? r.median : r.options[0];
    }
    return out;
  }, [examples.data, insights.data]);

  const err = schema.error ?? insights.error;
  return (
    <Screen>
      {err && <InlineError message={err} />}
      {(schema.state === "loading" || insights.state === "loading" || examples.state === "loading") && !err && (
        <PanelLoading rows={8} />
      )}
      {schema.state === "ready" && insights.state === "ready" && examples.state !== "loading" && (
        <Predict schema={schema.data} browser={browser.data} insights={insights.data} initial={start} />
      )}
    </Screen>
  );
}
