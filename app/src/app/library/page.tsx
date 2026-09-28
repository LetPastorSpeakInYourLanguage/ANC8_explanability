"use client";

import Reports, { type Documents } from "@/components/Reports";
import { InlineError, PanelLoading, Screen } from "@/components/studio/ui";
import { useJSON } from "@/lib/data";
import { useStudio } from "@/lib/studio";

export default function LibraryPage() {
  const studio = useStudio();
  const docs = useJSON<Documents>("/documents.json");
  const doc = studio.params.get("doc") ?? undefined;
  return (
    <Screen>
      {docs.state === "error" && <InlineError message={docs.error} />}
      {docs.state === "loading" && <PanelLoading rows={8} />}
      {docs.state === "ready" && <Reports data={docs.data} initialDoc={doc} />}
    </Screen>
  );
}
