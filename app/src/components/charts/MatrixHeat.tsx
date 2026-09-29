"use client";

import type { ReactNode } from "react";
import { classify, colorOf, inkOn } from "@/lib/colors";
import type { Scale } from "@/lib/metrics";

/**
 * A generic heatmap: rows x columns of numbers, five house classes. `perColumn`
 * classes each column on its own (columns measure different things); otherwise the
 * whole grid shares one scale, so any two cells can be compared. Empty cells are
 * drawn as blanks, never as zero.
 */

export interface MatrixCol {
  key: string;
  label: ReactNode;
  title?: string;
  scale?: Scale;
}

export interface MatrixRow {
  key: string;
  label: ReactNode;
  title?: string;
  sub?: ReactNode;
  values: Record<string, number | null | undefined>;
}

export default function MatrixHeat({
  rows,
  cols,
  format,
  theme,
  scale = "good",
  perColumn = false,
  quantile = true,
  active,
  activeCol,
  onRow,
  onCol,
  onCell,
  labelWidth = 170,
  cellWidth = 64,
}: {
  rows: MatrixRow[];
  cols: MatrixCol[];
  format: (v: number, col: string) => string;
  theme: "light" | "dark";
  scale?: Scale;
  perColumn?: boolean;
  quantile?: boolean;
  active?: string;
  activeCol?: string;
  onRow?: (key: string) => void;
  onCol?: (key: string) => void;
  onCell?: (row: string, col: string) => void;
  labelWidth?: number;
  cellWidth?: number;
}) {
  const global = classify(rows.flatMap((r) => cols.map((c) => r.values[c.key] ?? null)), scale, theme, quantile);
  const classes = Object.fromEntries(
    cols.map((c) => [
      c.key,
      perColumn ? classify(rows.map((r) => r.values[c.key] ?? null), c.scale ?? scale, theme, quantile) : global,
    ]),
  );

  return (
    <div className="overflow-x-auto px-10 py-8">
      <table className="border-collapse w-full" style={{ minWidth: labelWidth + cols.length * cellWidth }}>
        <thead>
          <tr>
            <th style={{ width: labelWidth }} />
            {cols.map((c) => (
              <th key={c.key} className="px-1 pb-4 align-bottom" style={{ minWidth: cellWidth }}>
                {onCol ? (
                  <button
                    type="button"
                    onClick={() => onCol(c.key)}
                    title={c.title}
                    className={`w-full rounded-2 px-2 py-3 text-9.5 font-semibold leading-tight ${
                      activeCol === c.key ? "bg-sel text-text" : "text-dim hover:bg-panel2"
                    }`}
                  >
                    {c.label}
                  </button>
                ) : (
                  <div className="text-9.5 font-semibold text-dim leading-tight text-center" title={c.title}>
                    {c.label}
                  </div>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const on = active === r.key;
            return (
              <tr key={r.key}>
                <td className={`text-10.5 pr-8 py-1 ${on ? "font-semibold" : ""}`} title={r.title}>
                  {onRow ? (
                    <button type="button" onClick={() => onRow(r.key)} className="hover:text-accent text-left w-full truncate block">
                      {r.label}
                    </button>
                  ) : (
                    <span className="truncate block">{r.label}</span>
                  )}
                  {r.sub && <span className="block text-9.5 text-faint truncate">{r.sub}</span>}
                </td>
                {cols.map((c) => {
                  const v = r.values[c.key];
                  const has = v != null && Number.isFinite(v);
                  const fill = has ? colorOf(v, classes[c.key], theme) : "transparent";
                  const sel = on && activeCol === c.key;
                  const body = has ? format(v, c.key) : "";
                  return (
                    <td key={c.key} className="p-1">
                      <div
                        role={onCell ? "button" : undefined}
                        tabIndex={onCell && has ? 0 : undefined}
                        onClick={onCell && has ? () => onCell(r.key, c.key) : undefined}
                        onKeyDown={onCell && has ? (e) => e.key === "Enter" && onCell(r.key, c.key) : undefined}
                        title={has ? `${typeof r.label === "string" ? r.label : r.key} · ${typeof c.label === "string" ? c.label : c.key}: ${body}` : "no estimate"}
                        className={`h-22 rounded-1 font-mono text-9.5 font-medium flex items-center justify-center transition-colors duration-500 ${
                          has ? "" : "border border-dashed border-border"
                        } ${onCell && has ? "cursor-pointer" : ""} ${on ? "ring-1 ring-text/40" : ""}`}
                        style={{
                          background: fill,
                          color: has ? inkOn(fill, theme) : undefined,
                          outline: sel ? "2px solid var(--text)" : undefined,
                          outlineOffset: 1,
                        }}
                      >
                        {body}
                      </div>
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
