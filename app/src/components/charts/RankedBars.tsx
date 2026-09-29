"use client";

/**
 * The house ranked bars (lab_resource_v2 DashboardRankedBars), with each bar in its
 * map class colour so the list and the map read as one picture. A dashed tick marks
 * the national value where there is one.
 */

export interface RankedRow {
  key: string;
  label: string;
  value: number | null;
  display: string;
  color: string;
  sub?: string;
}

export default function RankedBars({
  rows,
  active,
  onSelect,
  reference,
  referenceLabel = "Ethiopia",
  signed = false,
  labelWidth = 112,
  valueWidth = 58,
}: {
  rows: RankedRow[];
  active?: string;
  onSelect?: (key: string) => void;
  reference?: number | null;
  referenceLabel?: string;
  /** values can be negative: bars grow from a centre line */
  signed?: boolean;
  labelWidth?: number;
  valueWidth?: number;
}) {
  const vals = rows.map((r) => r.value ?? 0);
  const max = Math.max(1e-9, ...vals.map((v) => Math.abs(v)), Math.abs(reference ?? 0));
  return (
    <div className="px-10 py-8 flex flex-col gap-1">
      {rows.map((r) => {
        const on = active === r.key;
        const v = r.value ?? 0;
        const w = (Math.abs(v) / max) * (signed ? 50 : 100);
        return (
          <button
            key={r.key}
            type="button"
            onClick={() => onSelect?.(r.key)}
            aria-pressed={on}
            className={`grid items-center gap-8 w-full rounded-2 px-6 py-3 text-left hover:bg-panel2 ${
              on ? "bg-sel" : ""
            }`}
            style={{ gridTemplateColumns: `min(${labelWidth}px, 40%) minmax(0,1fr) ${valueWidth}px` }}
          >
            <span className="min-w-0" title={r.sub ? `${r.label} · ${r.sub}` : r.label}>
              <span className={`block truncate text-10.5 ${on ? "font-semibold" : ""}`}>{r.label}</span>
              {r.sub && <span className="block truncate text-9.5 text-faint">{r.sub}</span>}
            </span>
            <span className="relative block h-9 w-full rounded-full bg-panel3 overflow-hidden">
              {r.value != null && (
                <span
                  className="absolute inset-y-0 rounded-full transition-all duration-500"
                  style={{
                    background: r.color,
                    width: `${w}%`,
                    left: signed ? (v >= 0 ? "50%" : `${50 - w}%`) : 0,
                  }}
                />
              )}
              {signed && <span className="absolute inset-y-0 left-1/2 w-px bg-border2" />}
              {!signed && reference != null && (
                <span
                  className="absolute -inset-y-2 border-l border-dashed border-text opacity-60"
                  style={{ left: `${(reference / max) * 100}%` }}
                  title={`${referenceLabel}`}
                />
              )}
            </span>
            <span className="text-right font-mono text-10.5 font-medium">{r.display}</span>
          </button>
        );
      })}
    </div>
  );
}
