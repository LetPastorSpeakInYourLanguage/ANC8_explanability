"use client";

import { classify, colorOf, inkOn } from "@/lib/colors";
import { formatValue, type Metric } from "@/lib/metrics";
import type { RegionsData } from "@/lib/regionsData";
import type { Cohort } from "@/lib/studio";

/**
 * Regions down, metrics across: every region's whole profile on one screen. Each
 * column has its own five classes, so a column shows who is high and low on that
 * measure; comparing colours across columns is not meaningful and the header says
 * which way is bad. Clicking a cell selects the region and puts that metric on the
 * map; clicking a header only changes the map.
 */
export default function Heatmap({
  data,
  cohort,
  regions,
  metrics,
  activeMetric,
  activeRegion,
  onCell,
  onHeader,
  theme,
}: {
  data: RegionsData;
  cohort: Cohort;
  regions: string[];
  metrics: Metric[];
  activeMetric: string;
  activeRegion: string;
  onCell: (region: string, metric: string) => void;
  onHeader: (metric: string) => void;
  theme: "light" | "dark";
}) {
  const cols = metrics.map((m) => {
    const vals = regions.map((r) => m.value(data, cohort, r));
    return { m, vals, classes: classify(vals, m.scale, theme), national: m.value(data, cohort, null) };
  });

  return (
    <div className="overflow-x-auto">
      <table className="border-collapse w-full" style={{ minWidth: 150 + metrics.length * 62 }}>
        <thead>
          <tr>
            <th className="sticky left-0 bg-panel z-10 w-[150px]" />
            {cols.map(({ m }) => (
              <th key={m.key} className="px-1 pb-4 align-bottom">
                <button
                  type="button"
                  onClick={() => onHeader(m.key)}
                  title={`${m.label}. ${m.legend}`}
                  className={`w-full h-52 flex flex-col items-center justify-end gap-2 rounded-2 px-2 pb-3 ${
                    m.key === activeMetric ? "bg-sel" : "hover:bg-panel2"
                  }`}
                >
                  <span className="text-9.5 font-semibold text-dim leading-tight text-center">{m.short}</span>
                  <span
                    className={`text-8.5 font-mono ${
                      m.scale === "good" ? "text-good" : m.scale === "bad" ? "text-bad" : "text-cross"
                    }`}
                  >
                    {m.scale === "good" ? "▲ better" : m.scale === "bad" ? "▲ worse" : "± gap"}
                  </span>
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr className="border-b border-border2">
            <td className="sticky left-0 bg-panel z-10 text-10.5 font-semibold pr-8 py-3 whitespace-nowrap">Ethiopia</td>
            {cols.map(({ m, national }) => (
              <td key={m.key} className="text-center font-mono text-10 text-dim py-3">
                {formatValue(m, national)}
              </td>
            ))}
          </tr>
          {regions.map((r, ri) => {
            const on = r === activeRegion;
            return (
              <tr key={r}>
                <td
                  className={`sticky left-0 z-10 text-10.5 pr-8 py-1 whitespace-nowrap ${on ? "bg-sel font-semibold" : "bg-panel"}`}
                >
                  <button type="button" onClick={() => onCell(r, activeMetric)} className="hover:text-accent text-left">
                    {r}
                  </button>
                </td>
                {cols.map(({ m, vals, classes }) => {
                  const v = vals[ri];
                  const fill = colorOf(v, classes, theme);
                  const activeCell = on && m.key === activeMetric;
                  return (
                    <td key={m.key} className="p-1">
                      <button
                        type="button"
                        onClick={() => onCell(r, m.key)}
                        title={`${r}: ${m.label} ${formatValue(m, v)}`}
                        className={`w-full h-24 rounded-1 font-mono text-9.5 font-medium transition-colors duration-500 ${
                          activeCell ? "outline-2 outline-offset-1 outline-text" : ""
                        }`}
                        style={{ background: fill, color: inkOn(fill, theme), outlineStyle: activeCell ? "solid" : undefined }}
                      >
                        {formatValue(m, v)}
                      </button>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
