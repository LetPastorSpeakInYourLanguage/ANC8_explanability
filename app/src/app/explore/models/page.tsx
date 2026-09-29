"use client";

import { useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";
import DotRows, { niceTicks } from "@/components/charts/DotRows";
import MatrixHeat from "@/components/charts/MatrixHeat";
import { AXIS, ChartBox, GRID, SeriesLegend, TipPanel, tip } from "@/components/charts/rc";
import { useRenderTheme } from "@/components/shell/theme-provider";
import { InlineError, Note, Panel, PanelLoading, Screen, Segmented, StatTile, Tag } from "@/components/studio/ui";
import type { Analysis, LeaderboardRow } from "@/lib/analysis";
import { useJSON } from "@/lib/data";
import {
  NETWORKS, OUTCOME_OF, RUNG_LABEL, RUNG_OF, modelName, num, poolOf, setName, signed,
  type ExploreData, type Outcome,
} from "@/lib/explore";
import { cohortRungs } from "@/lib/regionsData";
import { COHORTS, RUNGS, useStudio } from "@/lib/studio";

const OUTCOMES: Outcome[] = ["anc1plus", "anc4plus", "anc8plus"];
const nz = (v: number | null | undefined) => (v == null || v === 0 ? null : v);

type Measure = "AP" | "AUROC" | "lift" | "Brier";
const MEASURES: { key: Measure; label: string; title: string }[] = [
  { key: "AP", label: "Avg precision", title: "Average precision on the held-out women (higher is better)" },
  { key: "lift", label: "Over chance", title: "Average precision minus the share who reach the rung" },
  { key: "AUROC", label: "AUC", title: "Area under the ROC curve (higher is better)" },
  { key: "Brier", label: "Brier", title: "Mean squared error of the probabilities (lower is better)" },
];

const CAL_MODELS = ["XGBoost", "Explainable Boosting", "Logistic regression", "MLP"];
const CAL_COLOR: Record<string, string> = {
  XGBoost: "var(--cross)", "Explainable Boosting": "var(--good)", "Logistic regression": "var(--accent)", MLP: "var(--warn)",
};

interface ModelRow {
  model: string;
  name: string;
  pool: "95" | "21";
  network: boolean;
  held: Partial<Record<"AP" | "AUROC" | "Brier", number>>;
  dev: number | null;
}

export default function ModelsPage() {
  const studio = useStudio();
  const theme = useRenderTheme();
  const ana = useJSON<Analysis>("/analysis.json");
  const exp = useJSON<ExploreData>("/data/explore.json");
  const [measure, setMeasure] = useState<Measure>("AP");
  const [ablModel, setAblModel] = useState("XGBoost");
  const [calFocus, setCalFocus] = useState<string | null>(null);

  const rung = studio.rung;
  const outcome = OUTCOME_OF[rung];

  // Every model at every rung: the tree and linear models from the leaderboard plus
  // the two networks, all scored on the same 1,375 held-out women.
  const models = useMemo(() => {
    const out: Record<Outcome, ModelRow[]> = { anc1plus: [], anc4plus: [], anc8plus: [] };
    if (!ana.data) return out;
    for (const o of OUTCOMES) {
      out[o] = (ana.data.leaderboard[o] ?? []).map((r: LeaderboardRow) => ({
        model: r.model,
        name: modelName(r.model),
        pool: poolOf(r.generation),
        network: false,
        held: { AP: r.held_AP ?? undefined, AUROC: r.held_AUROC ?? undefined, Brier: r.held_Brier ?? undefined },
        dev: nz(r.dev_AP),
      }));
      for (const n of NETWORKS) {
        const h = exp.data?.networks?.heldout.find((r) => r.rung === o && r.model === n);
        const d = exp.data?.networks?.development.find((r) => r.rung === o && r.model === n);
        if (h) out[o].push({ model: n, name: n, pool: "95", network: true, held: { AP: h.AP, AUROC: h.AUROC, Brier: h.Brier }, dev: d?.AP ?? null });
      }
    }
    return out;
  }, [ana.data, exp.data]);

  const err = ana.error ?? exp.error;
  if (err) return <Screen><InlineError message={err} /></Screen>;
  if (!ana.data) return <Screen><PanelLoading rows={8} /></Screen>;
  const a = ana.data;
  const prev = (o: Outcome) => a.outcomes[o].weighted_prevalence;

  const best = (o: Outcome) => [...models[o]].sort((x, y) => (y.held.AP ?? 0) - (x.held.AP ?? 0))[0];
  const rows = [...models[outcome]].sort((x, y) => (y.held.AP ?? 0) - (x.held.AP ?? 0));

  const rungPicker = (
    <Segmented
      label="Rung"
      options={RUNGS.map((r) => ({ key: r.key, label: r.label }))}
      value={rung}
      onChange={(k) => studio.set({ rung: k })}
    />
  );

  // model x rung grid
  const names = [...new Set(OUTCOMES.flatMap((o) => models[o].map((m) => m.name)))];
  const gridVal = (m: ModelRow | undefined, o: Outcome) => {
    if (!m) return null;
    if (measure === "lift") return m.held.AP != null ? m.held.AP - prev(o) : null;
    return m.held[measure] ?? null;
  };
  const gridRows = names
    .map((n) => ({
      key: n,
      label: n,
      values: Object.fromEntries(OUTCOMES.map((o) => [o, gridVal(models[o].find((m) => m.name === n), o)])),
    }))
    .sort((x, y) => (y.values[outcome] ?? -9) * (measure === "Brier" ? -1 : 1) - (x.values[outcome] ?? -9) * (measure === "Brier" ? -1 : 1));

  // model x predictor set, for the current cohort
  const cohort = cohortRungs(studio.cohort).includes(rung) ? studio.cohort : "full";
  const fvh = a.feature_value?.[cohort]?.[outcome]?.heldout ?? [];
  const sets = ["tier 1", "tier 1+2", "original 21", "all 88"].filter((s) => fvh.some((r) => r.set === s));
  const fams = [...new Set(fvh.map((r) => r.model))];

  const tuning = (a.tuning_gain ?? []).filter((r) => r.rung === outcome);
  const abl = a.ablation?.[outcome]?.[ablModel];
  const hp = a.hyperparameters?.[outcome]?.[ablModel] ?? {};

  const cal = a.calibration?.[outcome] ?? {};
  const calModels = CAL_MODELS.filter((m) => cal[m]?.length);
  const dca = a.decision_curve?.[outcome] ?? [];
  const dcaName = dca[0]?.model_name ?? "Model";
  const dcaMax = Math.max(0.01, ...dca.map((r) => Math.max(r.model, r.treat_all, r.v1_xgboost ?? 0)));
  const dcaTicks = niceTicks(0, dcaMax, 4);
  if (dcaTicks[dcaTicks.length - 1] < dcaMax) dcaTicks.push(+(2 * dcaTicks[dcaTicks.length - 1] - dcaTicks[dcaTicks.length - 2]).toFixed(10));

  const nets = exp.data?.networks;
  const paired = nets?.paired.filter((r) => r.rung === outcome) ?? [];

  return (
    <Screen>
      <div className="grid gap-10 grid-cols-1 sm:grid-cols-3">
        {OUTCOMES.map((o) => {
          const b = best(o);
          return (
            <StatTile
              key={o}
              label={`Best on held-out women · ${RUNG_LABEL[o]}`}
              value={num(b?.held.AP, 3)}
              sub={`${b?.name} · average precision; chance is ${num(prev(o), 2)}`}
              active={o === outcome}
              onClick={() => studio.set({ rung: RUNG_OF[o] })}
            />
          );
        })}
      </div>

      <Panel
        title={`Every model, development against held-out · ${RUNG_LABEL[rung]}`}
        how="Rings: cross-validated accuracy on the 5,518 development women, which the tuning saw. Dots: accuracy on the 1,375 held-out women, which nothing saw until the end. A long line from ring to dot is optimism. Networks are drawn in orange. The dashed line is chance."
        actions={rungPicker}
      >
        <DotRows
          rows={rows.map((m) => ({
            key: m.name,
            label: m.name,
            tag: m.network ? <Tag tone="warn">network</Tag> : m.pool === "21" ? <Tag tone="cross">21</Tag> : undefined,
            values: { dev: m.dev, held: m.network ? null : m.held.AP, net: m.network ? m.held.AP : null },
            display: num(m.held.AP),
          }))}
          series={[
            { key: "dev", label: "Development (cross-validated)", color: "var(--dim)", hollow: true },
            { key: "held", label: "Held-out women", color: "var(--accent)" },
            { key: "net", label: "Held-out, network", color: "var(--net)" },
          ]}
          reference={{ value: prev(outcome), label: "Chance" }}
          format={(v) => v.toFixed(2)}
          labelWidth={250}
        />
        {a.optimism?.[outcome] && (
          <div className="px-14 pb-12">
            <Note tone={a.optimism[outcome].mean_drop > 0.03 ? "warn" : "accent"}>
              Across the {a.optimism[outcome].n_models} tuned models, held-out accuracy was{" "}
              {a.optimism[outcome].mean_drop > 0
                ? `${num(a.optimism[outcome].mean_drop)} below development on average: the held-out women are harder at this rung, so compare models on the dots, not the rings.`
                : `${num(-a.optimism[outcome].mean_drop)} above development on average: no sign that tuning overfitted.`}
            </Note>
          </div>
        )}
      </Panel>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Panel
          title="Model by rung"
          how="Held-out scores for every model at every rung. Each column is shaded on its own (rungs differ in how hard they are), so read a column from dark to light to see the ranking at that rung. Blank: the model was not run at that rung."
          actions={<Segmented label="Measure" options={MEASURES} value={measure} onChange={setMeasure} />}
        >
          <MatrixHeat
            theme={theme}
            perColumn
            scale={measure === "Brier" ? "bad" : "good"}
            rows={gridRows}
            cols={OUTCOMES.map((o) => ({ key: o, label: RUNG_LABEL[o], scale: measure === "Brier" ? "bad" : "good" }))}
            format={(v) => (measure === "lift" ? signed(v, 3) : v.toFixed(3))}
            activeCol={outcome}
            onCol={(k) => studio.set({ rung: RUNG_OF[k as Outcome] })}
            labelWidth={250}
            cellWidth={72}
          />
        </Panel>

        <div className="flex flex-col gap-10 md:gap-14 min-w-0">
          <Panel
            title={`Model by predictor count · ${RUNG_LABEL[rung]}`}
            how={`Held-out average precision for four model families, each trained on predictor sets of different sizes (${COHORTS.find((c) => c.key === cohort)!.label.toLowerCase()}). One shading for the whole grid, so any two cells compare. A small set that holds its colour is the cheaper tool.`}
          >
            {fvh.length ? (
              <MatrixHeat
                theme={theme}
                rows={fams.map((f) => ({
                  key: f,
                  label: f,
                  values: Object.fromEntries(sets.map((s) => [s, fvh.find((r) => r.model === f && r.set === s)?.AP ?? null])),
                }))}
                cols={sets.map((s) => ({ key: s, label: setName(s, fvh.find((r) => r.set === s)?.n_predictors) }))}
                format={(v) => v.toFixed(3)}
                labelWidth={120}
                cellWidth={70}
              />
            ) : (
              <PanelLoading rows={4} />
            )}
          </Panel>

          <Panel
            title={`Does tuning pay? · ${RUNG_LABEL[rung]}`}
            how="Rings: the model with its library defaults. Dots: after tuning (development accuracy). Most of the gain is small; the models are close before and after."
          >
            <DotRows
              rows={tuning
                .sort((x, y) => y.gain - x.gain)
                .map((r) => ({
                  key: r.model,
                  label: r.model,
                  values: { d: r.defaults_AP, t: r.tuned_AP },
                  display: signed(r.gain),
                }))}
              series={[
                { key: "d", label: "Defaults", color: "var(--dim)", hollow: true },
                { key: "t", label: "Tuned", color: "var(--accent)" },
              ]}
              format={(v) => v.toFixed(3)}
              labelWidth={170}
            />
          </Panel>
        </div>
      </div>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-2">
        <Panel
          title={`Which settings matter · ${ablModel}`}
          how="Each tuned setting was moved one step down and one step up while the others stayed fixed. The bar spans the change in development accuracy: left of zero means the tuned value was better. A short bar near zero is a setting the model does not care about. The tuned value is under each name."
          actions={
            <Segmented
              label="Model"
              options={Object.keys(a.ablation?.[outcome] ?? {}).map((m) => ({ key: m, label: m === "Explainable Boosting" ? "EBM" : m === "Logistic regression" ? "Logistic" : m }))}
              value={ablModel}
              onChange={setAblModel}
            />
          }
        >
          {abl ? (
            <>
              <DotRows
                rows={abl.parameters.map((p) => ({
                  key: p.parameter,
                  label: p.parameter.replace(/_/g, " "),
                  sub: hp[p.parameter] != null ? `tuned: ${fmtParam(hp[p.parameter])}` : undefined,
                  values: { worst: p.worst_AP_drop, best: p.best_AP_gain },
                  display: signed(p.worst_AP_drop),
                }))}
                series={[
                  { key: "worst", label: "Worse of the two neighbours", color: "var(--bad)" },
                  { key: "best", label: "Better of the two", color: "var(--good)" },
                ]}
                reference={{ value: 0, label: "Tuned value" }}
                format={(v) => signed(v, 3)}
                labelWidth={180}
              />
              <div className="px-14 pb-12">
                <Note tone="accent">
                  Defaults {num(abl.defaults_AP)} → tuned {num(abl.tuned_AP)} ({signed(abl.gain)} average precision, development).
                </Note>
              </div>
            </>
          ) : (
            <PanelLoading rows={6} />
          )}
        </Panel>

        <Panel
          title={`Are the probabilities honest? · ${RUNG_LABEL[rung]}`}
          how="Held-out women grouped into tenths by predicted probability. Each point is a group's average prediction against the share who actually reached the rung. On the diagonal, a predicted 30% means 30%. Above it the model is too cautious; below it, too confident."
        >
          {calModels.length ? (
            <>
              <ChartBox height={270} className="pt-10 pr-14">
                <LineChart margin={{ left: -4, right: 6, top: 6, bottom: 0 }}>
                  <CartesianGrid {...GRID} />
                  <XAxis {...AXIS} type="number" dataKey="predicted" domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tickFormatter={(v) => `${v * 100}%`} />
                  <YAxis {...AXIS} type="number" dataKey="observed" domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tickFormatter={(v) => `${v * 100}%`} width={44} />
                  <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="var(--faint)" strokeDasharray="4 3" />
                  <Tooltip
                    content={tip<{ predicted: number; observed: number; n: number }>((d, p) => (
                      <TipPanel
                        title={String(p.payload?.[0]?.name ?? "")}
                        rows={[
                          { label: "Predicted", value: `${(d.predicted * 100).toFixed(0)}%` },
                          { label: "Observed", value: `${(d.observed * 100).toFixed(0)}%` },
                          { label: "Women", value: d.n },
                        ]}
                      />
                    ))}
                  />
                  {calModels.map((m) => (
                    <Line
                      key={m}
                      name={m}
                      data={[...cal[m]].sort((x, y) => x.predicted - y.predicted)}
                      dataKey="observed"
                      stroke={CAL_COLOR[m]}
                      strokeWidth={calFocus === m ? 3 : 1.75}
                      strokeOpacity={calFocus && calFocus !== m ? 0.15 : 1}
                      dot={{ r: 2.5, strokeWidth: 0, fill: CAL_COLOR[m] }}
                      isAnimationActive={false}
                    />
                  ))}
                </LineChart>
              </ChartBox>
              <SeriesLegend
                items={calModels.map((m) => ({ key: m, label: m, color: CAL_COLOR[m] }))}
                focus={calFocus}
                onFocus={setCalFocus}
              />
            </>
          ) : (
            <PanelLoading rows={6} />
          )}
        </Panel>
      </div>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-2">
        <Panel
          title={`Is the model worth acting on? · ${RUNG_LABEL[rung]}`}
          how="Decision curve. Along the bottom: how sure you want to be before acting on a woman (the risk at which follow-up is worth its cost). Up the side: the net benefit, true positives gained minus false positives weighted by that threshold. A model helps wherever its line sits above both 'act on everyone' and 'act on no one'."
        >
          {dca.length ? (
            <>
              <ChartBox height={250} className="pt-10 pr-14">
                <LineChart data={dca} margin={{ left: -4, right: 6, top: 6, bottom: 0 }}>
                  <CartesianGrid {...GRID} />
                  <XAxis {...AXIS} type="number" dataKey="threshold" domain={[0, 0.8]} ticks={[0, 0.2, 0.4, 0.6, 0.8]} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
                  <YAxis {...AXIS} domain={[-0.02, dcaTicks[dcaTicks.length - 1]]} ticks={dcaTicks} allowDataOverflow tickFormatter={(v) => v.toFixed(2)} width={44} />
                  <Tooltip
                    content={tip<(typeof dca)[number]>((d) => (
                      <TipPanel
                        title={`Act at ${Math.round(d.threshold * 100)}% risk`}
                        rows={[
                          { label: dcaName, value: num(d.model), color: "var(--accent)" },
                          ...(d.v1_xgboost != null ? [{ label: "XGBoost · 21 predictors", value: num(d.v1_xgboost), color: "var(--cross)" }] : []),
                          { label: "Act on everyone", value: num(d.treat_all), color: "var(--faint)" },
                        ]}
                      />
                    ))}
                  />
                  <Line dataKey="treat_none" stroke="var(--border2)" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                  <Line dataKey="treat_all" stroke="var(--faint)" strokeDasharray="4 3" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                  {dca[0]?.v1_xgboost != null && (
                    <Line dataKey="v1_xgboost" stroke="var(--cross)" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                  )}
                  <Line dataKey="model" stroke="var(--accent)" strokeWidth={2.25} dot={false} isAnimationActive={false} />
                </LineChart>
              </ChartBox>
              <SeriesLegend
                items={[
                  { key: "m", label: dcaName, color: "var(--accent)" },
                  ...(dca[0]?.v1_xgboost != null ? [{ key: "x", label: "XGBoost · 21 predictors", color: "var(--cross)" }] : []),
                  { key: "all", label: "Act on everyone", color: "var(--faint)", dashed: true },
                  { key: "none", label: "Act on no one", color: "var(--border2)" },
                ]}
              />
            </>
          ) : (
            <PanelLoading rows={6} />
          )}
        </Panel>

        <Panel
          title={`Networks against the trees · ${RUNG_LABEL[rung]}`}
          how="The difference in held-out average precision between each network and a reference model, measured on the same women and resampled 1,000 times. The bar is the 95% interval: a bar that crosses zero is a tie. Right of zero, the network is better."
        >
          {paired.length ? (
            <>
              <DotRows
                rows={paired.map((r) => ({
                  key: `${r.network}|${r.reference}`,
                  label: `vs ${r.reference}`,
                  sub: r.network,
                  values: { d: r.d_AP },
                  lo: { d: r.d_AP_lo },
                  hi: { d: r.d_AP_hi },
                  display: signed(r.d_AP),
                }))}
                series={[{ key: "d", label: "Difference", color: "var(--net)" }]}
                reference={{ value: 0, label: "No difference" }}
                format={(v) => signed(v, 2)}
                labelWidth={220}
                showLegend={false}
              />
              {nets?.ladder_violations && (
                <div className="grid grid-cols-3 border-t border-border">
                  {Object.entries(nets.ladder_violations).map(([k, v]) => (
                    <div key={k} className="px-12 py-9 border-r border-border last:border-r-0 min-w-0">
                      <div className={`font-mono text-15 font-semibold ${v > 0 ? "text-bad" : "text-good"}`}>{(v * 100).toFixed(1)}%</div>
                      <div className="text-9.5 text-dim leading-snug">{k}</div>
                    </div>
                  ))}
                </div>
              )}
              <div className="px-14 py-10">
                <Note tone="accent">
                  The row of numbers: held-out women whose predictions break the ladder (a higher chance of ANC8+ than of ANC4+). Three
                  separate tree models can do this; both networks predict the rungs jointly and never do.
                </Note>
              </div>
            </>
          ) : (
            <PanelLoading rows={6} />
          )}
        </Panel>
      </div>
    </Screen>
  );
}

function fmtParam(v: unknown): string {
  if (typeof v === "number") return Math.abs(v) >= 100 || Number.isInteger(v) ? String(v) : v.toPrecision(3);
  return String(v);
}
