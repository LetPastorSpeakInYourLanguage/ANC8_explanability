"use client";

import type { Classes } from "@/lib/colors";
import { NO_DATA } from "@/lib/colors";
import { formatValue, type Metric } from "@/lib/metrics";

/** The map legend: what darker means in words, then the five classes with ranges. */
export default function Legend({
  metric,
  classes,
  theme,
  compact = false,
}: {
  metric: Metric;
  classes: Classes;
  theme: "light" | "dark";
  compact?: boolean;
}) {
  const edges = [classes.min, ...classes.breaks, classes.max];
  const labels =
    metric.scale === "diverging"
      ? ["much worse", "worse", "as expected", "better", "much better"]
      : classes.colors.map((_, i) => `${formatValue(metric, edges[i])}–${formatValue(metric, edges[i + 1])}`);
  return (
    <div className={`bg-panel border border-border2 rounded-3 ${compact ? "px-8 py-6" : "px-10 py-8"} max-w-[340px]`}>
      <div className="text-11 font-semibold leading-snug">{metric.label}</div>
      {!compact && (
        <div className="text-10 text-dim mt-2 leading-snug">
          {/* on the dark palette "more" is brighter, not darker */}
          {theme === "dark" ? metric.legend.replace(/^Darker:/, "Brighter:") : metric.legend}
        </div>
      )}
      <div className="flex mt-6 gap-1">
        {classes.colors.map((c, i) => (
          <div key={c} className="flex-1 min-w-0">
            <div className="h-9 rounded-1" style={{ background: c }} />
            <div className="text-8.5 font-mono text-faint mt-2 leading-tight truncate" title={labels[i]}>
              {labels[i]}
            </div>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-5 mt-5 text-9.5 text-faint">
        <span className="inline-block w-9 h-9 rounded-1" style={{ background: NO_DATA[theme] }} />
        no estimate
        <span className="inline-block w-9 h-9 rounded-1 ml-8 border border-dashed border-border2" />
        contested area
      </div>
    </div>
  );
}
