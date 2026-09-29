"use client";

import DotRows from "@/components/charts/DotRows";
import { Panel, StatTile, Tag } from "@/components/studio/ui";
import type { Card, Family, SpaceRow } from "@/lib/modelCards";
import { signed } from "@/lib/explore";

const fmtVal = (v: string | number | undefined | null) => {
  if (v == null) return "none";
  if (typeof v === "string") return v;
  const a = Math.abs(v);
  if (a !== 0 && (a < 0.01 || a >= 10000)) return v.toExponential(1);
  return Number.isInteger(v) ? String(v) : String(+v.toPrecision(3));
};

/** Where the chosen value sits inside the range the search was allowed to try. */
function place(r: SpaceRow): number | null {
  if (r.kind === "cat" || typeof r.chosen !== "number" || r.low == null || r.high == null) return null;
  const f = (v: number) => (r.log ? Math.log(v) : v);
  const t = (f(r.chosen) - f(r.low)) / (f(r.high) - f(r.low) || 1);
  return Math.min(1, Math.max(0, t));
}

function SpaceTable({ rows }: { rows: SpaceRow[] }) {
  return (
    <div className="px-14 py-8 flex flex-col">
      {rows.map((r) => {
        const t = place(r);
        return (
          <div key={r.param} className="grid items-center gap-10 py-4 border-b border-border last:border-b-0 grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_64px]">
            <span className="text-10.5 truncate" title={r.param}>{r.param.replace(/_/g, " ")}</span>
            {t != null ? (
              <span className="flex items-center gap-6 min-w-0">
                <span className="font-mono text-9.5 text-faint">{fmtVal(r.low)}</span>
                <span className="relative block h-12 flex-1">
                  <span className="absolute inset-x-0 top-1/2 h-2 -mt-1 rounded-full bg-panel3" />
                  <span
                    className="absolute top-1/2 size-9 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent border-2 border-panel"
                    style={{ left: `${t * 100}%` }}
                  />
                </span>
                <span className="font-mono text-9.5 text-faint">{fmtVal(r.high)}{r.log ? " log" : ""}</span>
              </span>
            ) : (
              <span className="flex flex-wrap gap-3">
                {(r.choices ?? []).map((c) => (
                  <Tag key={String(c)} tone={String(c) === String(r.chosen) ? "accent" : "neutral"}>{fmtVal(c)}</Tag>
                ))}
              </span>
            )}
            <span className="text-right font-mono text-10.5 font-medium">{fmtVal(r.chosen)}</span>
          </div>
        );
      })}
    </div>
  );
}

/** How the model was built: the search and what it bought, or a line on how it came to be. */
export default function Tuning({ card, fam }: { card: Card; fam: Family }) {
  const t = card.tuning;
  return (
    <Panel help="analysis.tuning"
      title="How it was built"
      how="Tuned models were searched with Optuna: each trial picks settings, fits five folds of the development women and scores average precision out of fold. Each bar is the range the search was allowed to try, with the winning value marked."
    >
      <div className="px-14 py-10 flex flex-col gap-4 border-b border-border">
        <p className="text-11.5">{fam.what}</p>
        <p className="text-10.5 text-dim">{fam.pre}</p>
      </div>
      {t.tuned && (
        <>
          <div className="px-14 py-10 flex flex-wrap gap-6 border-b border-border">
            {t.trials != null && <Tag>{t.trials} trials</Tag>}
            <Tag>5 folds by cluster</Tag>
            <Tag>weighted average precision</Tag>
            {t.seconds != null && <Tag>{t.seconds >= 120 ? `${Math.round(t.seconds / 60)} min` : `${Math.round(t.seconds)} s`}</Tag>}
          </div>
          {t.space && <SpaceTable rows={t.space} />}
          {t.defaults_ap != null && t.tuned_ap != null && (
            <div className="border-t border-border">
              <DotRows
                rows={[{
                  key: "gain",
                  label: "What tuning bought",
                  values: { d: t.defaults_ap, t: t.tuned_ap },
                  display: signed(t.tuned_ap - t.defaults_ap),
                }]}
                series={[
                  { key: "d", label: "Library defaults", color: "var(--dim)", hollow: true },
                  { key: "t", label: "Tuned", color: "var(--accent)" },
                ]}
                format={(v) => v.toFixed(3)}
                labelWidth={130}
              />
            </div>
          )}
          {t.ablation && t.ablation.length > 0 && (
            <div className="border-t border-border">
              <DotRows
                rows={t.ablation.map((a) => ({
                  key: a.param,
                  label: a.param.replace(/_/g, " "),
                  values: { w: a.worst, b: a.best },
                  display: signed(a.worst),
                }))}
                series={[
                  { key: "w", label: "Worse neighbour", color: "var(--bad)" },
                  { key: "b", label: "Better neighbour", color: "var(--good)" },
                ]}
                reference={{ value: 0, label: "Tuned value" }}
                format={(v) => signed(v, 3)}
                labelWidth={130}
              />
            </div>
          )}
        </>
      )}
      {!t.tuned && t.how && <p className="px-14 py-10 text-11 text-dim">{t.how}</p>}
      {t.network && (
        <div className="px-14 pb-12 grid grid-cols-2 sm:grid-cols-4 gap-8">
          <StatTile label="Epochs, at most" value={t.network.epochs} sub={`stops after ${t.network.patience} without gain`} />
          <StatTile label="Batch" value={t.network.batch} />
          <StatTile label="Learning rate" value={fmtVal(t.network.lr)} />
          <StatTile label="Seeds" value={t.network.seeds.length} sub={t.network.seeds.join(", ")} />
        </div>
      )}
    </Panel>
  );
}
