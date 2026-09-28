"use client";

/**
 * The ANC ladder as a funnel: one bar per rung, sized by the share of women who reach
 * it, with the share who continue from one rung to the next between them. The loss
 * at each step is drawn as the gap, in the house "bad" tone, so the eye lands on
 * where women are lost rather than on who arrives.
 */

export interface FunnelStep {
  key: string;
  label: string;
  value: number; // share of all women, 0..1
}

const pct = (v: number) => `${Math.round(v * 100)}%`;

export default function Funnel({
  steps,
  active,
  onSelect,
  compact = false,
}: {
  steps: FunnelStep[];
  active?: string;
  onSelect?: (key: string) => void;
  compact?: boolean;
}) {
  return (
    <div className={`flex flex-col ${compact ? "gap-4" : "gap-6"}`}>
      {steps.map((s, i) => {
        const prev = i === 0 ? 1 : steps[i - 1].value;
        const cont = prev > 0 ? s.value / prev : 0;
        const on = active === s.key;
        return (
          <div key={s.key}>
            {i > 0 && (
              <div className="flex items-center gap-8 pl-[92px] py-2 text-9.5 font-mono text-faint">
                <span className="text-good">{pct(cont)} continue</span>
                <span aria-hidden="true">·</span>
                <span className="text-bad">{pct(1 - cont)} lost</span>
              </div>
            )}
            <button
              type="button"
              disabled={!onSelect}
              onClick={() => onSelect?.(s.key)}
              aria-pressed={on}
              className={`grid grid-cols-[84px_minmax(0,1fr)] items-center gap-8 w-full text-left rounded-2 px-4 py-3 ${
                onSelect ? "hover:bg-panel2" : "cursor-default"
              } ${on ? "bg-sel" : ""}`}
            >
              <span className="text-11 font-medium">{s.label}</span>
              <span className="relative block h-22 bg-panel3 rounded-2 overflow-hidden">
                {/* the share lost before this rung, relative to the rung above */}
                <span
                  className="absolute inset-y-0 left-0 bg-badbg"
                  style={{ width: `${prev * 100}%` }}
                  aria-hidden="true"
                />
                <span
                  className="absolute inset-y-0 left-0 rounded-2 transition-all duration-500"
                  style={{ width: `${s.value * 100}%`, background: "var(--accent)" }}
                />
                {/* a short bar cannot hold its label, so the label sits just past its end */}
                <span
                  className={`absolute inset-y-0 flex items-center font-mono text-11 font-semibold ${
                    s.value >= 0.16 ? "left-6 text-white" : "text-text"
                  }`}
                  style={s.value >= 0.16 ? undefined : { left: `calc(${s.value * 100}% + 6px)` }}
                >
                  {pct(s.value)}
                </span>
              </span>
            </button>
          </div>
        );
      })}
    </div>
  );
}
