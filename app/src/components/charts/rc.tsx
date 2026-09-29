"use client";

import type { ReactNode } from "react";
import { ResponsiveContainer } from "recharts";

/**
 * Recharts in the house style (the shadcn chart pattern, retuned): flush, hairline
 * grid, IBM Plex Mono tick labels in the faint ink, no shadows, a flat tooltip panel.
 * Colours are the house CSS variables, so every chart follows the theme with no
 * re-render. Spread AXIS and GRID into the Recharts parts:
 *
 *   <XAxis {...AXIS} dataKey="k" />   <CartesianGrid {...GRID} />
 */

const TICK = { fontSize: 10, fontFamily: "var(--font-family-mono)", fill: "var(--faint)" };

export const AXIS = {
  tick: TICK,
  axisLine: { stroke: "var(--border2)" },
  tickLine: { stroke: "var(--border2)" },
  tickSize: 4,
} as const;

export const GRID = { stroke: "var(--border)", strokeDasharray: "2 3" } as const;

export const AXIS_LABEL = { fontSize: 10, fill: "var(--dim)", fontFamily: "var(--font-family-sans)" } as const;

/** A fixed-height box that the chart fills; the width follows the panel. */
export function ChartBox({ height = 240, children, className = "" }: {
  height?: number;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`w-full min-w-0 ${className}`} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 600, height }}>
        {children as React.ReactElement}
      </ResponsiveContainer>
    </div>
  );
}

export interface TipRow {
  label: ReactNode;
  value: ReactNode;
  color?: string;
}

/** The flat tooltip panel. Use as <Tooltip content={tip((p) => ...)} />. */
export function TipPanel({ title, rows }: { title?: ReactNode; rows: TipRow[] }) {
  return (
    <div className="bg-panel border border-border2 rounded-3 px-10 py-7 text-10.5 min-w-[140px]">
      {title != null && <div className="font-semibold mb-3">{title}</div>}
      {rows.map((r, i) => (
        <div key={i} className="flex items-center gap-8 leading-relaxed">
          {r.color && <span className="inline-block size-8 rounded-1 flex-none" style={{ background: r.color }} />}
          <span className="text-dim flex-1">{r.label}</span>
          <span className="font-mono font-medium">{r.value}</span>
        </div>
      ))}
    </div>
  );
}

// Recharts hands the tooltip content its own props; only these fields are used.
export interface TipProps<T> {
  active?: boolean;
  label?: string | number;
  payload?: { payload: T; name?: string; value?: number; color?: string; dataKey?: string }[];
}

/** Adapts a renderer of the hovered datum into Recharts' tooltip content. */
export function tip<T>(render: (d: T, p: TipProps<T>) => ReactNode) {
  return function Content(raw: unknown): ReactNode {
    const props = raw as TipProps<T>;
    if (!props.active || !props.payload?.length) return null;
    return render(props.payload[0].payload, props);
  };
}

/** Series chips: a legend that is also a focus control. */
export function SeriesLegend({ items, focus, onFocus }: {
  items: { key: string; label: string; color: string; dashed?: boolean }[];
  focus?: string | null;
  onFocus?: (k: string | null) => void;
}) {
  return (
    <div className="flex flex-wrap gap-x-12 gap-y-4 px-14 pb-10">
      {items.map((it) => {
        const dim = focus && focus !== it.key;
        return (
          <button
            key={it.key}
            type="button"
            onMouseEnter={() => onFocus?.(it.key)}
            onMouseLeave={() => onFocus?.(null)}
            onFocus={() => onFocus?.(it.key)}
            onBlur={() => onFocus?.(null)}
            className={`flex items-center gap-5 text-10 ${dim ? "opacity-40" : ""} ${onFocus ? "" : "cursor-default"}`}
          >
            <span
              className="inline-block w-14 h-0 border-t-2"
              style={{ borderColor: it.color, borderTopStyle: it.dashed ? "dashed" : "solid" }}
            />
            <span className="text-dim">{it.label}</span>
          </button>
        );
      })}
    </div>
  );
}
