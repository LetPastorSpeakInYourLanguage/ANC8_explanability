"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useTheme } from "./theme-provider";

/**
 * The guided tour for a demonstration: in presentation mode a small panel walks
 * through the studio, one screen per step, each opened in the state that tells its
 * story. The arrow keys step forward and back, Escape leaves. The words are short on
 * purpose: they are prompts for the presenter, not a script to read.
 */

const STEPS: { path: string; title: string; say: string }[] = [
  { path: "/", title: "The ladder",
    say: "78% of women start antenatal care, 52% reach four contacts and 19% reach the eight the WHO recommends. The biggest loss is between four and eight." },
  { path: "/map?metric=anc8", title: "Where",
    say: "Every region shaded by ANC8+. Press play to move the map from ANC1+ to ANC8+, and see the country empty out." },
  { path: "/map?region=Somali&metric=never", title: "One region",
    say: "Click a region: its ladder with intervals, where it loses women, who is left behind, and which of its gaps a health system can work on." },
  { path: "/explore/ladder", title: "One distribution",
    say: "The three rungs are cuts through one contact count. Women bunch at three or four contacts, and at eight." },
  { path: "/explore/predictors?rung=anc8", title: "How many predictors",
    say: "From 6,648 survey columns to the few that carry the prediction: most of the accuracy arrives with the first two." },
  { path: "/explore/models?rung=anc8", title: "Every model, honestly",
    say: "Development against held-out women for every model in the library. The ranking is on women no model saw." },
  { path: "/planner?lv=insurance:60,intention:50,early:40&rung=anc8", title: "What if",
    say: "Move the levers the data support and see each region respond, with each lever's weight. A budget is spent where it buys most women." },
  { path: "/war?hit=Amhara&rung=anc1", title: "If conflict returns",
    say: "Built from the Tigray war, checked on Amhara. Choose regions, duration and intensity; press play to watch it arrive and fade." },
  { path: "/your-data", title: "Your own data",
    say: "Load a DHIS2 export: the trend, a forecast tested on the same series, and the planner's levers on top. Nothing leaves the laptop." },
  { path: "/your-data?mode=register", title: "At the first visit",
    say: "Twelve questions a midwife can ask give almost the accuracy of the full model: a ranked list of women to follow up." },
  { path: "/help", title: "Help for every tool",
    say: "Every panel's (i) says how to read it, and Read more opens a plain-language guide with screenshots. The Help button on each screen opens that screen's guide." },
];

export default function Tour() {
  const { present, togglePresent } = useTheme();
  const router = useRouter();
  const pathname = usePathname();
  const [i, setI] = useState(0);

  const go = useCallback(
    (k: number) => {
      const n = Math.max(0, Math.min(STEPS.length - 1, k));
      setI(n);
      router.push(STEPS[n].path, { scroll: true });
    },
    [router],
  );

  useEffect(() => {
    if (!present) return;
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "SELECT" || t.tagName === "TEXTAREA")) return;
      if (e.key === "ArrowRight" || e.key === "PageDown") { e.preventDefault(); go(i + 1); }
      else if (e.key === "ArrowLeft" || e.key === "PageUp") { e.preventDefault(); go(i - 1); }
      else if (e.key === "Escape") togglePresent();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [present, i, go, togglePresent]);

  if (!present) return null;
  const s = STEPS[i];
  const here = pathname === s.path.split("?")[0];
  return (
    <div role="dialog" aria-label="Guided tour"
      className="fixed right-14 bottom-36 z-[1200] w-[min(360px,calc(100vw-28px))] bg-panel border border-accent rounded-3">
      <div className="flex items-center gap-8 px-12 py-7 border-b border-border">
        <span className="text-9.5 font-semibold uppercase tracking-label text-accent flex-1">
          Tour · {i + 1} of {STEPS.length}
        </span>
        <button type="button" onClick={togglePresent} className="text-faint hover:text-text" aria-label="Leave the tour" title="Leave (Esc)">
          <X className="size-13" />
        </button>
      </div>
      <div className="px-12 py-10">
        <div className="text-13 font-semibold">{s.title}</div>
        <div className="text-11 text-dim leading-relaxed mt-4">{s.say}</div>
        {!here && (
          <button type="button" onClick={() => go(i)} className="text-10.5 text-accent hover:underline mt-6">Open this screen</button>
        )}
      </div>
      <div className="flex items-center gap-8 px-12 py-8 border-t border-border">
        <button type="button" onClick={() => go(i - 1)} disabled={i === 0}
          className="h-24 px-8 rounded-2 border border-border2 bg-panel2 text-10.5 flex items-center gap-3 disabled:opacity-40">
          <ChevronLeft className="size-12" /> Back
        </button>
        <div className="flex-1 flex justify-center gap-3">
          {STEPS.map((_, k) => (
            <button key={k} type="button" onClick={() => go(k)} aria-label={`Step ${k + 1}`}
              className={`size-6 rounded-full ${k === i ? "bg-accent" : "bg-border2"}`} />
          ))}
        </div>
        <button type="button" onClick={() => go(i + 1)} disabled={i === STEPS.length - 1}
          className="h-24 px-8 rounded-2 border border-accent bg-accent text-white text-10.5 flex items-center gap-3 disabled:opacity-40">
          Next <ChevronRight className="size-12" />
        </button>
      </div>
    </div>
  );
}
