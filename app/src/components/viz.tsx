"use client";

import { ReactNode, useId } from "react";
import TermLink from "@/components/TermLink";

/**
 * The small chart vocabulary the analysis views are built from.
 *
 * Deliberately plain SVG rather than a charting library: the shapes needed
 * here are bars, dumbbells, a scatter and a line, and a dependency that draws
 * all four would be larger than every artifact the app loads put together.
 */

export const POS = "#2f7d70";
export const NEG = "#b4552d";

export function pct(v: number | null | undefined, digits = 1) {
  return v == null ? "—" : `${(v * 100).toFixed(digits)}%`;
}

export function num(v: number | null | undefined, digits = 3) {
  return v == null ? "—" : v.toFixed(digits);
}

export function signed(v: number | null | undefined, digits = 3) {
  return v == null ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;
}

/** A titled block with an explanatory line, used for every panel. */
export function Panel({
  title,
  lede,
  children,
  aside,
  term,
}: {
  title: string;
  lede?: ReactNode;
  children: ReactNode;
  aside?: ReactNode;
  /** glossary id: adds a "?" linking to the plain-language explanation */
  term?: string;
}) {
  return (
    <section className="card p-4 sm:p-5">
      <div className="flex items-start justify-between gap-4">
        <h2 className="font-semibold">
          {title}
          {term && <TermLink id={term} label={title} />}
        </h2>
        {aside}
      </div>
      {lede && (
        <p className="label mt-2 leading-relaxed max-w-3xl">{lede}</p>
      )}
      <div className="mt-4">{children}</div>
    </section>
  );
}

/** A note the reader should not skip: a caveat, or a number that cuts against. */
export function Caveat({ children }: { children: ReactNode }) {
  return (
    <p
      className="label mt-4 pt-3 leading-relaxed"
      style={{ borderTop: "1px solid var(--line)" }}
    >
      {children}
    </p>
  );
}

/** One horizontal bar with a label and a value. */
export function BarRow({
  label,
  value,
  max,
  display,
  color = "var(--accent)",
  note,
  onClick,
  active,
}: {
  label: ReactNode;
  value: number;
  max: number;
  display?: string;
  color?: string;
  note?: ReactNode;
  onClick?: () => void;
  active?: boolean;
}) {
  const width = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  const body = (
    <>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm truncate">{label}</span>
        <span className="label tabular text-[0.72rem] shrink-0">
          {display ?? value.toFixed(3)}
        </span>
      </div>
      <div className="mt-1 h-2 rounded-full" style={{ background: "var(--line)" }}>
        <div
          className="h-2 rounded-full transition-all"
          style={{ width: `${width}%`, background: color }}
        />
      </div>
      {note && <div className="label text-[0.7rem] mt-1">{note}</div>}
    </>
  );
  return onClick ? (
    <button
      className="w-full text-left rounded px-1 -mx-1"
      style={{ background: active ? "var(--line)" : "transparent" }}
      onClick={onClick}
    >
      {body}
    </button>
  ) : (
    <div>{body}</div>
  );
}

/** A bar that can go either way from a centre line. */
export function DivergingRow({
  label,
  value,
  scale,
  display,
  note,
}: {
  label: ReactNode;
  value: number;
  scale: number;
  display?: string;
  note?: ReactNode;
}) {
  const half = scale > 0 ? Math.min(50, (Math.abs(value) / scale) * 50) : 0;
  const positive = value >= 0;
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm truncate">{label}</span>
        <span className="label tabular text-[0.72rem] shrink-0">
          {display ?? signed(value)}
        </span>
      </div>
      <div
        className="mt-1 h-2 rounded-full relative"
        style={{ background: "var(--line)" }}
      >
        <div
          className="h-2 absolute top-0"
          style={{
            left: positive ? "50%" : `${50 - half}%`,
            width: `${half}%`,
            background: positive ? POS : NEG,
            borderRadius: 999,
          }}
        />
        <div
          className="absolute top-[-2px] h-3 w-px"
          style={{ left: "50%", background: "var(--muted)" }}
        />
      </div>
      {note && <div className="label text-[0.7rem] mt-1">{note}</div>}
    </div>
  );
}

/** Two points on one line: the classic before/after comparison. */
export function Dumbbell({
  label,
  a,
  b,
  min,
  max,
  aLabel,
  bLabel,
  note,
}: {
  label: ReactNode;
  a: number;
  b: number;
  min: number;
  max: number;
  aLabel?: string;
  bLabel?: string;
  note?: ReactNode;
}) {
  const span = max - min || 1;
  const px = (v: number) => ((v - min) / span) * 100;
  const lo = Math.min(px(a), px(b));
  const hi = Math.max(px(a), px(b));
  return (
    <div className="py-1">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm truncate">{label}</span>
        <span className="label tabular text-[0.72rem] shrink-0">
          {a.toFixed(3)} → {b.toFixed(3)}
        </span>
      </div>
      <div className="mt-1.5 h-3 relative">
        <div
          className="absolute h-px top-1/2"
          style={{ left: `${lo}%`, width: `${hi - lo}%`, background: "var(--line)" }}
        />
        <div
          className="absolute h-2 w-2 rounded-full top-1/2 -translate-y-1/2 -translate-x-1/2"
          style={{ left: `${px(a)}%`, background: "var(--set21)" }}
          title={aLabel}
        />
        <div
          className="absolute h-2.5 w-2.5 rounded-full top-1/2 -translate-y-1/2 -translate-x-1/2"
          style={{ left: `${px(b)}%`, background: "var(--accent)" }}
          title={bLabel}
        />
      </div>
      {note && <div className="label text-[0.7rem]">{note}</div>}
    </div>
  );
}

/** A stacked proportion bar; segments must sum to roughly 1. */
export function StackedBar({
  segments,
  height = 18,
}: {
  segments: { value: number; color: string; title?: string; label?: string }[];
  height?: number;
}) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  return (
    <div className="flex w-full overflow-hidden rounded" style={{ height }}>
      {segments.map((s, i) => {
        const w = (s.value / total) * 100;
        if (w <= 0) return null;
        return (
          <div
            key={i}
            style={{ width: `${w}%`, background: s.color }}
            title={s.title}
            className="flex items-center justify-center"
          >
            {w > 11 && s.label && (
              <span className="text-[0.62rem] text-white tabular">{s.label}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}

/** A line chart over a shared x scale, for calibration and decision curves. */
export function LineChart({
  series,
  xLabel,
  yLabel,
  xDomain,
  yDomain,
  diagonal = false,
  height = 240,
  markers = false,
  zeroLine = false,
}: {
  series: { name: string; color: string; dashed?: boolean;
            points: { x: number; y: number }[] }[];
  xLabel: string;
  yLabel: string;
  xDomain?: [number, number];
  yDomain?: [number, number];
  diagonal?: boolean;
  height?: number;
  markers?: boolean;
  zeroLine?: boolean;
}) {
  const id = useId();
  const all = series.flatMap((s) => s.points);
  if (!all.length) return null;
  const [x0, x1] = xDomain ?? [
    Math.min(...all.map((p) => p.x)),
    Math.max(...all.map((p) => p.x)),
  ];
  const [y0, y1] = yDomain ?? [
    Math.min(...all.map((p) => p.y)),
    Math.max(...all.map((p) => p.y)),
  ];
  const W = 320;
  const H = 220;
  const pad = { l: 38, r: 8, t: 8, b: 30 };
  const sx = (x: number) =>
    pad.l + ((x - x0) / (x1 - x0 || 1)) * (W - pad.l - pad.r);
  const sy = (y: number) =>
    H - pad.b - ((y - y0) / (y1 - y0 || 1)) * (H - pad.t - pad.b);

  const ticks = (a: number, b: number) =>
    [0, 0.25, 0.5, 0.75, 1].map((f) => a + (b - a) * f);

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height }}
           role="img" aria-label={`${yLabel} against ${xLabel}`}>
        {ticks(y0, y1).map((t, i) => (
          <g key={`y${i}`}>
            <line x1={pad.l} x2={W - pad.r} y1={sy(t)} y2={sy(t)}
                  stroke="var(--line)" strokeWidth="0.5" />
            <text x={pad.l - 4} y={sy(t) + 3} textAnchor="end"
                  fontSize="7" fill="var(--muted)">
              {Math.abs(t) < 1 ? t.toFixed(2) : t.toFixed(1)}
            </text>
          </g>
        ))}
        {ticks(x0, x1).map((t, i) => (
          <text key={`x${i}`} x={sx(t)} y={H - pad.b + 11} textAnchor="middle"
                fontSize="7" fill="var(--muted)">
            {Math.abs(t) < 1 ? t.toFixed(2) : t.toFixed(1)}
          </text>
        ))}
        {zeroLine && y0 < 0 && y1 > 0 && (
          <line x1={pad.l} x2={W - pad.r} y1={sy(0)} y2={sy(0)}
                stroke="var(--muted)" strokeWidth="0.6" />
        )}
        {diagonal && (
          <line x1={sx(x0)} y1={sy(y0)} x2={sx(Math.min(x1, y1))}
                y2={sy(Math.min(x1, y1))} stroke="var(--muted)"
                strokeWidth="0.6" strokeDasharray="3 3" />
        )}
        {series.map((s) => (
          <g key={`${id}-${s.name}`}>
            <polyline
              points={s.points.map((p) => `${sx(p.x)},${sy(p.y)}`).join(" ")}
              fill="none"
              stroke={s.color}
              strokeWidth="1.6"
              strokeDasharray={s.dashed ? "4 3" : undefined}
              vectorEffect="non-scaling-stroke"
            />
            {markers &&
              s.points.map((p, i) => (
                <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r="1.8" fill={s.color} />
              ))}
          </g>
        ))}
        <text x={(W - pad.l) / 2 + pad.l} y={H - 2} textAnchor="middle"
              fontSize="7.5" fill="var(--muted)">
          {xLabel}
        </text>
        <text x={9} y={H / 2} textAnchor="middle" fontSize="7.5"
              fill="var(--muted)" transform={`rotate(-90 9 ${H / 2})`}>
          {yLabel}
        </text>
      </svg>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1">
        {series.map((s) => (
          <span key={s.name} className="label text-[0.7rem] flex items-center gap-1.5">
            <span className="inline-block w-3 h-px" style={{ background: s.color }} />
            {s.name}
          </span>
        ))}
      </div>
    </div>
  );
}

/** A compact table that stays readable on a phone. */
export function Table({
  head,
  rows,
  note,
}: {
  head: ReactNode[];
  rows: ReactNode[][];
  note?: ReactNode;
}) {
  return (
    <div>
      <div className="overflow-x-auto -mx-4 sm:mx-0 px-4 sm:px-0">
        <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {head.map((h, i) => (
                <th
                  key={i}
                  className="label text-left font-normal py-1.5 pr-3 whitespace-nowrap"
                  style={{ borderBottom: "1px solid var(--line)" }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                {r.map((c, j) => (
                  <td
                    key={j}
                    className={`py-1.5 pr-3 align-top ${j ? "tabular" : ""}`}
                    style={{ borderBottom: "1px solid var(--line)" }}
                  >
                    {c}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {note && <p className="label mt-2 leading-relaxed">{note}</p>}
    </div>
  );
}

/** A headline figure with its caption, for the top of a view. */
export function Stat({
  value,
  label,
  tone,
}: {
  value: string;
  label: ReactNode;
  tone?: "good" | "bad" | "plain";
}) {
  const color =
    tone === "good" ? POS : tone === "bad" ? NEG : "var(--fg)";
  return (
    <div>
      <div className="text-2xl font-semibold tabular" style={{ color }}>
        {value}
      </div>
      <div className="label mt-0.5 leading-snug">{label}</div>
    </div>
  );
}
