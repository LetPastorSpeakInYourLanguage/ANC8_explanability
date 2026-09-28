"use client";

import { useRouter } from "next/navigation";
import Journey, { type JourneyData } from "@/components/Journey";
import type { Documents } from "@/components/Reports";
import { InlineError, PanelLoading, Screen } from "@/components/studio/ui";
import { useJSON } from "@/lib/data";
import { useStudio } from "@/lib/studio";

/** The analysis record and the glossary are one component with three views; the
 *  route picks the view, and ?sub= carries a term or figure to jump to. */
export default function JourneyScreen({ defaultSub }: { defaultSub: string }) {
  const studio = useStudio();
  const router = useRouter();
  const journey = useJSON<JourneyData>("/journey.json");
  const docs = useJSON<Documents>("/documents.json");
  const sub = studio.params.get("sub") ?? defaultSub;

  const navigate = (tab: string, target?: string) => {
    if (tab === "reports") {
      router.push(studio.href(`/library?doc=${encodeURIComponent(target ?? "")}`));
      return;
    }
    const view = target ?? "timeline";
    const base = view === "timeline" ? "/library/record" : "/library/glossary";
    router.push(`${base}?sub=${encodeURIComponent(view)}`, { scroll: !/^(term|fig)-/.test(view) });
  };

  return (
    <Screen>
      {journey.state === "error" && <InlineError message={journey.error} />}
      {journey.state === "loading" && <PanelLoading rows={8} />}
      {journey.state === "ready" && (
        <Journey data={journey.data} docs={docs.data} sub={sub} onNavigate={navigate} />
      )}
    </Screen>
  );
}
