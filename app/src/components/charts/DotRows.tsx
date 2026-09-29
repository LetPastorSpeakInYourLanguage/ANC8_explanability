"use client";

import type { ReactNode } from "react";

/**
 * One row per thing, several dots per row on a shared axis: the house's answer to
 * the dumbbell, the dot plot and the interval chart at once. Two series make a
 * dumbbell (development vs held-out), three make a ladder (ANC1+, ANC4+, ANC8+),
 * one series with lo/hi makes an interval chart. Rows can be clicked.
 */

export interface DotSeries {
  key: string;
  label: string;
  color: string;
  /** drawn as a ring rather than a filled dot */
  hollow?: boolean;
}

export interface DotRow {
  key: string;
  label: ReactNode;
  title?: string;
  sub?: ReactNode;
  values: Record<string, number | null | undefined>;
  /** an interval per series */
  lo?: Record<string, number | null | undefined>;
  hi?: Record<string, number | null | undefined>;
  /** muted: a small cell, or a row that is only context */
  muted?: boolean;
  /** a tag after the label */
  tag?: ReactNode;
  /** the value printed at the right; defaults to the last series */
  display?: ReactNode;
}

export default function DotRows({
  rows,
  series,
  domain,
  format,
  reference,
  connect = true,
  active,
  onSelect,
  labelWidth = 150,
  valueWidth = 54,
  ticks,
  showLegend = true,
}: {
  rows: DotRow[];
  series: DotSeries[];
  domain?: [number, number];
  format: (v: number) => string;
  reference?: { value: number; label: string } | null;
  /** join a row's dots with a line (a dumbbell) */
  connect?: boolean;
  active?: string;
  onSelect?: (key: string) => void;
  labelWidth?: number;
  valueWidth?: number;
  ticks?: number[];
  showLegend?: boolean;
}) {
  const all: number[] = [];
  for (const r of rows)
    for (const s of series) {
      for (const v of [r.values[s.key], r.lo?.[s.key], r.hi?.[s.key]]) if (v != null && Number.isFinite(v)) all.push(v);
    }
  if (reference) all.push(reference.value);
  let [min, max] = domain ?? [Math.min(...all), Math.max(...all)];
  if (!domain) {
    const pad = (max - min) * 0.06 || 0.01;
    min -= pad;
    max += pad;
  }
  const x = (v: number) => `${((v - min) / (max - min || 1)) * 100}%`;
  const tickVals = ticks ?? niceTicks(min, max, 4);
  // the label column gives way on a phone so the axis keeps most of the row
  const cols = `min(${labelWidth}px, 36%) minmax(0,1fr) ${valueWidth}px`;

  return (
    <div className="px-10 py-8">
      {showLegend && series.length > 1 && (
        <div className="flex flex-wrap gap-x-12 gap-y-3 px-6 pb-6">
          {series.map((s) => (
            <span key={s.key} className="flex items-center gap-5 text-10 text-dim">
              <Dot color={s.color} hollow={s.hollow} />
              {s.label}
            </span>
          ))}
          {reference && (
            <span className="flex items-center gap-5 text-10 text-dim">
              <span className="inline-block h-10 border-l border-dashed border-text opacity-60" />
              {reference.label}
            </span>
          )}
        </div>
      )}
      <div className="flex flex-col">
        {rows.map((r) => {
          const on = active === r.key;
          const vals = series.map((s) => r.values[s.key]).filter((v): v is number => v != null && Number.isFinite(v));
          const last = [...series].reverse().find((s) => r.values[s.key] != null);
          const Tag = onSelect ? "button" : "div";
          return (
            <Tag
              key={r.key}
              type={onSelect ? "button" : undefined}
              onClick={onSelect ? () => onSelect(r.key) : undefined}
              aria-pressed={onSelect ? on : undefined}
              className={`grid items-center gap-8 w-full rounded-2 px-6 py-3 text-left ${
                onSelect ? "hover:bg-panel2" : ""
              } ${on ? "bg-sel" : ""} ${r.muted ? "opacity-55" : ""}`}
              style={{ gridTemplateColumns: cols }}
            >
              <span className="min-w-0" title={r.title}>
                <span className="flex items-center gap-5 min-w-0">
                  <span className={`truncate text-10.5 ${on ? "font-semibold" : ""}`}>{r.label}</span>
                  {r.tag}
                </span>
                {r.sub && <span className="block text-9.5 text-faint truncate leading-tight">{r.sub}</span>}
              </span>
              <span className="relative block h-16 w-full">
                <span className="absolute inset-x-0 top-1/2 h-px bg-panel3" />
                {tickVals.map((t) => (
                  <span key={t} className="absolute inset-y-2 w-px bg-border opacity-70" style={{ left: x(t) }} />
                ))}
                {reference && (
                  <span
                    className="absolute -inset-y-1 border-l border-dashed border-text opacity-50"
                    style={{ left: x(reference.value) }}
                  />
                )}
                {connect && vals.length > 1 && (
                  <span
                    className="absolute top-1/2 h-2 -mt-1 bg-border2 rounded-full transition-all duration-500"
                    style={{ left: x(Math.min(...vals)), width: `calc(${x(Math.max(...vals))} - ${x(Math.min(...vals))})` }}
                  />
                )}
                {series.map((s) => {
                  const lo = r.lo?.[s.key];
                  const hi = r.hi?.[s.key];
                  if (lo == null || hi == null) return null;
                  return (
                    <span
                      key={`i-${s.key}`}
                      className="absolute top-1/2 h-2 -mt-1 rounded-full opacity-45 transition-all duration-500"
                      style={{ left: x(lo), width: `calc(${x(hi)} - ${x(lo)})`, background: s.color }}
                    />
                  );
                })}
                {series.map((s) => {
                  const v = r.values[s.key];
                  if (v == null || !Number.isFinite(v)) return null;
                  return (
                    <span
                      key={s.key}
                      title={`${s.label}: ${format(v)}`}
                      className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 transition-all duration-500"
                      style={{ left: x(v) }}
                    >
                      <Dot color={s.color} hollow={s.hollow} />
                    </span>
                  );
                })}
              </span>
              <span className="text-right font-mono text-10.5 font-medium truncate">
                {r.display ?? (last && r.values[last.key] != null ? format(r.values[last.key]!) : "–")}
              </span>
            </Tag>
          );
        })}
      </div>
      <div className="grid gap-8 px-6 pt-2" style={{ gridTemplateColumns: cols }}>
        <span />
        <span className="relative block h-12">
          {tickVals.map((t) => (
            <span
              key={t}
              className="absolute -translate-x-1/2 font-mono text-9.5 text-faint whitespace-nowrap max-sm:even:hidden"
              style={{ left: x(t) }}
            >
              {format(t)}
            </span>
          ))}
        </span>
        <span />
      </div>
    </div>
  );
}

function Dot({ color, hollow }: { color: string; hollow?: boolean }) {
  return (
    <span
      className="block size-9 rounded-full border-2"
      style={{ borderColor: color, background: hollow ? "var(--panel)" : color }}
    />
  );
}

/** A few round tick values between min and max. */
export function niceTicks(min: number, max: number, count: number): number[] {
  const span = max - min;
  if (!(span > 0)) return [min];
  const raw = span / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => span / s <= count + 1) ?? raw;
  const out: number[] = [];
  for (let t = Math.ceil(min / step) * step; t <= max + 1e-12; t += step) out.push(+t.toFixed(10));
  return out;
}
