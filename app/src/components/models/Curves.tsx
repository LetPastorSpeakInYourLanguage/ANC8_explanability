"use client";

import { useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";
import { AXIS, ChartBox, GRID, SeriesLegend, TipPanel, tip } from "@/components/charts/rc";
import { Panel, Segmented } from "@/components/studio/ui";
import type { Card } from "@/lib/modelCards";

type Kind = "gains" | "roc" | "pr";
const KINDS: { key: Kind; label: string }[] = [
  { key: "gains", label: "Finding women" },
  { key: "roc", label: "ROC" },
  { key: "pr", label: "Precision–recall" },
];

interface Row {
  x: number;
  model: number | null;
  vs: number | null;
  chance: number;
  perfect?: number;
}

const pct = (v: number) => `${Math.round(v * 100)}%`;
const TICKS = [0, 0.25, 0.5, 0.75, 1];

function rowsOf(kind: Kind, card: Card, vs: Card | null): Row[] {
  if (kind === "gains") {
    const n = card.gains.length;
    return card.gains.map((g, i) => {
      const x = i / (n - 1);
      return { x, model: g, vs: vs ? vs.gains[i] : null, chance: x, perfect: Math.min(x / card.target_share, 1) };
    });
  }
  const pick = (c: Card) => (kind === "roc" ? c.roc : c.pr);
  const [xs, ys] = pick(card);
  const v = vs ? pick(vs)[1] : null;
  return xs.map((x, i) => ({
    x,
    model: ys[i],
    vs: v ? v[i] : null,
    chance: kind === "roc" ? x : card.prevalence,
  }));
}

/** Three views of the same question: how much better than chance does the ranking do. */
export default function Curves({ card, vs, name, vsName }: { card: Card; vs: Card | null; name: string; vsName: string | null }) {
  const [kind, setKind] = useState<Kind>("gains");
  const [focus, setFocus] = useState<string | null>(null);
  const data = useMemo(() => rowsOf(kind, card, vs), [kind, card, vs]);
  const who = card.target === "miss" ? "miss the rung" : "reach the rung";
  const axes = {
    gains: { x: "Women followed up, best-ranked first" },
    roc: { x: "False alarms" },
    pr: { x: "Recall" },
  }[kind];
  const chanceLabel = kind === "pr" ? "Chance (prevalence)" : "Chance";
  const items = [
    { key: "model", label: name, color: "var(--accent)" },
    ...(vs && vsName ? [{ key: "vs", label: vsName, color: "var(--cross)" }] : []),
    { key: "chance", label: chanceLabel, color: "var(--faint)", dashed: true },
    ...(kind === "gains" ? [{ key: "perfect", label: "Perfect ranking", color: "var(--border2)", dashed: true }] : []),
  ];
  const dim = (k: string) => (focus && focus !== k ? 0.15 : 1);
  return (
    <Panel help="analysis.curves"
      title="Against chance"
      how={
        kind === "gains"
          ? `Rank women by the model's score and follow up the best-ranked first. The line shows what share of all women who ${who} you find. The dashed diagonal is picking at random; the faint dashed line is a perfect ranking.`
          : kind === "roc"
            ? "How many true cases are caught (hits) for each share of false alarms. The diagonal is a coin toss."
            : "Of the women flagged, how many were right (precision) at each level of recall. The flat dashed line is what random flagging gives: the share who reach the rung."
      }
      actions={<Segmented label="Curve" options={KINDS} value={kind} onChange={setKind} />}
    >
      <ChartBox height={280} className="pt-10 pr-14">
        <LineChart data={data} margin={{ left: -4, right: 6, top: 6, bottom: 16 }}>
          <CartesianGrid {...GRID} />
          <XAxis {...AXIS} type="number" dataKey="x" domain={[0, 1]} ticks={TICKS} tickFormatter={pct}
            label={{ value: axes.x, position: "insideBottom", offset: -10, fontSize: 10, fill: "var(--dim)" }} />
          <YAxis {...AXIS} type="number" domain={[0, 1]} ticks={TICKS} tickFormatter={pct} width={44} />
          {kind === "gains" && <ReferenceLine x={0.2} stroke="var(--border2)" strokeDasharray="2 3" />}
          <Tooltip
            content={tip<Row>((d) => (
              <TipPanel
                title={kind === "gains" ? `Top ${pct(d.x)} of women` : pct(d.x)}
                rows={[
                  { label: name, value: d.model == null ? "–" : pct(d.model), color: "var(--accent)" },
                  ...(d.vs != null && vsName ? [{ label: vsName, value: pct(d.vs), color: "var(--cross)" }] : []),
                  { label: chanceLabel, value: pct(d.chance) },
                ]}
              />
            ))}
          />
          <Line dataKey="chance" stroke="var(--faint)" strokeDasharray="4 3" strokeOpacity={dim("chance")} dot={false} isAnimationActive={false} />
          {kind === "gains" && (
            <Line dataKey="perfect" stroke="var(--border2)" strokeDasharray="1 3" strokeOpacity={dim("perfect")} dot={false} isAnimationActive={false} />
          )}
          {vs && <Line dataKey="vs" stroke="var(--cross)" strokeWidth={1.75} strokeOpacity={dim("vs")} dot={false} isAnimationActive={false} />}
          <Line dataKey="model" stroke="var(--accent)" strokeWidth={2.25} strokeOpacity={dim("model")} dot={false} isAnimationActive={false} />
        </LineChart>
      </ChartBox>
      <SeriesLegend items={items} focus={focus} onFocus={setFocus} />
    </Panel>
  );
}
