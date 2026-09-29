"use client";

import { CartesianGrid, Line, LineChart, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";
import { AXIS, ChartBox, GRID, TipPanel, tip } from "@/components/charts/rc";
import { Panel, StatTile } from "@/components/studio/ui";
import type { Card } from "@/lib/modelCards";

const pct = (v: number) => `${Math.round(v * 100)}%`;

type P = { predicted: number; observed: number; n: number };

/** Predicted tenths against what happened. */
export function Calibration({ card, name }: { card: Card; name: string }) {
  const pts = [...card.calibration].sort((a, b) => a.predicted - b.predicted);
  const hi = Math.max(0.05, ...pts.map((p) => Math.max(p.predicted, p.observed)));
  const top = Math.min(1, Math.ceil(hi * 10) / 10);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => +(t * top).toFixed(4));
  return (
    <Panel
      title="Honest probabilities?"
      how="Held-out women in ten equal groups by predicted chance. Each dot: the group's average prediction against the share who reached the rung. On the diagonal, a predicted 30% means 30%. Above it the model is too cautious; below it, too confident."
    >
      <ChartBox height={240} className="pt-10 pr-14">
        <LineChart data={pts} margin={{ left: -4, right: 6, top: 6, bottom: 0 }}>
          <CartesianGrid {...GRID} />
          <XAxis {...AXIS} type="number" dataKey="predicted" domain={[0, top]} ticks={ticks} tickFormatter={pct} />
          <YAxis {...AXIS} type="number" domain={[0, top]} ticks={ticks} tickFormatter={pct} width={44} />
          <ReferenceLine segment={[{ x: 0, y: 0 }, { x: top, y: top }]} stroke="var(--faint)" strokeDasharray="4 3" />
          <Tooltip
            content={tip<P>((d) => (
              <TipPanel
                title={name}
                rows={[
                  { label: "Predicted", value: pct(d.predicted) },
                  { label: "Observed", value: pct(d.observed) },
                  { label: "Women", value: d.n },
                ]}
              />
            ))}
          />
          <Line dataKey="observed" stroke="var(--accent)" strokeWidth={1.75} dot={{ r: 2.5, strokeWidth: 0, fill: "var(--accent)" }} isAnimationActive={false} />
        </LineChart>
      </ChartBox>
    </Panel>
  );
}

const box = "flex flex-col items-center justify-center px-8 py-10 text-center";
const head = "px-8 py-6 text-9.5 uppercase tracking-label text-faint font-semibold";

/** The weighted 2x2 at the operating threshold, and its four rates. */
export function Decisions({ card }: { card: Card }) {
  const o = card.operating;
  return (
    <Panel
      title="At the working threshold"
      how="The threshold was set on the development women, then applied once to the held-out women. Each box is a share of all women. Sensitivity: of those who reach the rung, how many were called. Specificity: of those who do not, how many were called. PPV and NPV: how often a yes, or a no, was right."
    >
      {o ? (
        <div className="p-14 flex flex-col gap-10">
          <div className="grid grid-cols-[64px_1fr_1fr] border border-border rounded-2">
            <div />
            <div className={`${head} text-center border-l border-border`}>Reached</div>
            <div className={`${head} text-center border-l border-border`}>Did not</div>
            <div className={`${head} border-t border-border flex items-center`}>Yes</div>
            <div className={`${box} border-l border-t border-border bg-goodbg`}>
              <span className="font-mono text-17 font-semibold">{pct(o.tp)}</span>
              <span className="text-9.5 text-dim">right</span>
            </div>
            <div className={`${box} border-l border-t border-border bg-warnbg`}>
              <span className="font-mono text-17 font-semibold">{pct(o.fp)}</span>
              <span className="text-9.5 text-dim">false alarm</span>
            </div>
            <div className={`${head} border-t border-border flex items-center`}>No</div>
            <div className={`${box} border-l border-t border-border bg-warnbg`}>
              <span className="font-mono text-17 font-semibold">{pct(o.fn)}</span>
              <span className="text-9.5 text-dim">missed</span>
            </div>
            <div className={`${box} border-l border-t border-border bg-goodbg`}>
              <span className="font-mono text-17 font-semibold">{pct(o.tn)}</span>
              <span className="text-9.5 text-dim">right</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-8">
            <StatTile label="Sensitivity" value={pct(o.sensitivity)} />
            <StatTile label="Specificity" value={pct(o.specificity)} />
            <StatTile label="PPV" value={pct(o.ppv)} />
            <StatTile label="NPV" value={pct(o.npv)} />
          </div>
        </div>
      ) : (
        <p className="px-14 py-12 text-11 text-dim">No working threshold was set for this model.</p>
      )}
    </Panel>
  );
}
