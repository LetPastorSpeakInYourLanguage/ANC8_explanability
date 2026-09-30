"use client";

import { useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, Tooltip, XAxis, YAxis } from "recharts";
import DotRows, { niceTicks } from "@/components/charts/DotRows";
import MatrixHeat from "@/components/charts/MatrixHeat";
import { AXIS, ChartBox, GRID, SeriesLegend, TipPanel, tip } from "@/components/charts/rc";
import { useRenderTheme } from "@/components/shell/theme-provider";
import { DataNote, InlineError, Note, Panel, PanelLoading, Screen, Segmented, StatTile, Tag } from "@/components/studio/ui";
import type { Analysis } from "@/lib/analysis";
import { useJSON } from "@/lib/data";
import {
  NETWORKS, OUTCOME_OF, RUNG_LABEL, RUNG_OF, num, signed,
  type ExploreData, type Outcome,
} from "@/lib/explore";
import { label } from "@/lib/labels";
import { MODELS_INDEX, SETS, SET_SHORT, setFile, type Explained, type ModelsIndex, type ModelsSet } from "@/lib/modelCards";
import { RUNGS, useStudio } from "@/lib/studio";

const OUTCOMES: Outcome[] = ["anc1plus", "anc4plus", "anc8plus"];

type Measure = "AP" | "AUROC" | "lift" | "Brier";
const MEASURES: { key: Measure; label: string; title: string }[] = [
  { key: "AP", label: "Avg precision", title: "Average precision on the held-out women (higher is better)" },
  { key: "lift", label: "Over chance", title: "Average precision minus the share who reach the rung" },
  { key: "AUROC", label: "AUC", title: "Area under the ROC curve (higher is better)" },
  { key: "Brier", label: "Brier", title: "Mean squared error of the probabilities (lower is better)" },
];

const CAL_COLOR: Record<string, string> = {
  XGBoost: "var(--cross)", "Explainable Boosting": "var(--good)", "Logistic regression": "var(--accent)", "Random Forest": "var(--warn)",
};

interface ModelRow {
  model: string;
  name: string;
  network: boolean;
  held: Partial<Record<"AP" | "AUROC" | "Brier", number>>;
  dev: number | null;
}

export default function ModelsPage() {
  const studio = useStudio();
  const theme = useRenderTheme();
  const ana = useJSON<Analysis>("/analysis.json");
  const exp = useJSON<ExploreData>("/data/explore.json");
  const explained = useJSON<Explained>("/data/explain.json");
  const lib = useJSON<ModelsIndex>(MODELS_INDEX);
  const [measure, setMeasure] = useState<Measure>("AP");
  const [ablModel, setAblModel] = useState("XGBoost");
  const [calFocus, setCalFocus] = useState<string | null>(null);

  const rung = studio.rung;
  const outcome = OUTCOME_OF[rung];

  // The model library on one predictor set: every model at every rung, all scored on
  // the same 1,375 held-out women.
  const sets = lib.data?.meta.sets.map((x) => x.key) ?? [];
  const setAsked = studio.params.get("set") ?? "";
  const set = SETS.includes(setAsked) ? setAsked : "s21";
  const setCards = useJSON<ModelsSet>(setFile(set));
  const models = useMemo(() => {
    const out: Record<Outcome, ModelRow[]> = { anc1plus: [], anc4plus: [], anc8plus: [] };
    const d = lib.data;
    if (!d) return out;
    for (const o of OUTCOMES) {
      for (const [k, f] of Object.entries(d.families)) {
        const c = f.set === set ? d.summary[k]?.[RUNG_OF[o]] : undefined;
        if (!c) continue;
        out[o].push({
          model: f.slug, name: f.name, network: NETWORKS.includes(f.name),
          held: { AP: c.ap, AUROC: c.auroc, Brier: c.brier }, dev: c.dev_ap,
        });
      }
    }
    return out;
  }, [lib.data, set]);

  const err = ana.error ?? exp.error ?? lib.error;
  if (err) return <Screen><InlineError message={err} /></Screen>;
  if (!ana.data || !lib.data) return <Screen><PanelLoading rows={8} /></Screen>;
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
  const setPicker = sets.length < 2 ? null : (
    <Segmented
      label="Predictors"
      options={lib.data.meta.sets.map((x) => ({ key: x.key, label: SET_SHORT[x.key] ?? x.label }))}
      value={set}
      onChange={(k) => studio.set({ set: k })}
    />
  );
  const setLabel = SET_SHORT[set] ?? set;

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

  const tunedRows = models[outcome].filter((m) => !m.network && m.dev != null && m.held.AP != null);
  const drop = tunedRows.length ? tunedRows.reduce((t, m) => t + (m.dev! - m.held.AP!), 0) / tunedRows.length : null;

  // what tuning bought, and which settings matter: the three models on the 21
  const L = lib.data;
  const fams = Object.values(L.families);
  const tuneBy = L.tuning?.[rung] ?? {};
  const tuning = Object.entries(tuneBy)
    .filter(([, t]) => t.defaults_ap != null && t.tuned_ap != null)
    .map(([model, t]) => ({ model, defaults_AP: t.defaults_ap!, tuned_AP: t.tuned_ap!, gain: t.tuned_ap! - t.defaults_ap! }));
  const abl = tuneBy[ablModel] ?? tuneBy[Object.keys(tuneBy)[0]];
  const ablName = tuneBy[ablModel] ? ablModel : Object.keys(tuneBy)[0] ?? ablModel;
  const CAL_MODELS = L.meta.models ?? [];

  const cal: Record<string, { predicted: number; observed: number; n: number }[]> = Object.fromEntries(
    CAL_MODELS.map((m) => [m, setCards.data?.cards[`${set}.${fams.find((f) => f.name === m)?.slug}`]?.[rung]?.calibration ?? []]),
  );
  const calModels = CAL_MODELS.filter((m) => cal[m]?.length);
  // decision curve: this set's best model on held-out women, against logistic regression
  const baseCards = CAL_MODELS
    .map((m) => ({ m, c: setCards.data?.cards[`${set}.${fams.find((f) => f.name === m)?.slug}`]?.[rung] }))
    .filter((x) => x.c?.decision);
  const bestBase = [...baseCards].sort((x, y) => (y.c!.ap) - (x.c!.ap))[0];
  const lrCard = baseCards.find((x) => x.m === "Logistic regression");
  const other = lrCard && bestBase && lrCard.m !== bestBase.m ? lrCard : undefined;
  const dca = bestBase
    ? bestBase.c!.decision!.t.map((t, i) => ({
        threshold: t, model: bestBase.c!.decision!.model[i], treat_all: bestBase.c!.decision!.all[i], treat_none: 0,
        other: other ? other.c!.decision!.model[i] : undefined,
      }))
    : [];
  const dcaName = bestBase?.m ?? "Model";
  const otherName = other?.m ?? "";
  const dcaMax = Math.max(0.01, ...dca.map((r) => Math.max(r.model, r.treat_all, r.other ?? 0)));
  const dcaTicks = niceTicks(0, dcaMax, 4);
  if (dcaTicks[dcaTicks.length - 1] < dcaMax) dcaTicks.push(+(2 * dcaTicks[dcaTicks.length - 1] - dcaTicks[dcaTicks.length - 2]).toFixed(10));

  const leanRows = explained.data?.sets[set]?.[rung] ?? [];
  const leanModels = explained.data?.models ?? [];

  return (
    <Screen>
      <div data-help="models.tiles" className="grid gap-10 grid-cols-1 sm:grid-cols-3">
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

      <Panel help="models.dev-held"
        title={`Every model, development against held-out · ${setLabel} · ${RUNG_LABEL[rung]}`}
        how="Rings: cross-validated accuracy on the 5,518 development women, which the tuning saw. Dots: accuracy on the 1,375 held-out women, which nothing saw until the end. A long line from ring to dot is optimism. The dashed line is chance."
        actions={<span className="flex flex-wrap gap-6">{setPicker}{rungPicker}</span>}
      >
        <DotRows
          rows={rows.map((m) => ({
            key: m.name,
            label: m.name,
            tag: m.network ? <Tag tone="warn">network</Tag> : undefined,
            values: { dev: m.dev, held: m.network ? null : m.held.AP, net: m.network ? m.held.AP : null },
            display: num(m.held.AP),
          }))}
          series={[
            { key: "dev", label: "Development (cross-validated)", color: "var(--dim)", hollow: true },
            { key: "held", label: "Held-out women", color: "var(--accent)" },
            ...(rows.some((m) => m.network) ? [{ key: "net", label: "Held-out, network", color: "var(--net)" }] : []),
          ]}
          reference={{ value: prev(outcome), label: "Chance" }}
          format={(v) => v.toFixed(2)}
          labelWidth={250}
        />
        {drop != null && (
          <div className="px-14 pb-12">
            <Note tone={drop > 0.03 ? "warn" : "accent"}>
              Across the {tunedRows.length} models on this set, held-out accuracy was{" "}
              {drop > 0
                ? `${num(drop)} below development on average: the held-out women are harder at this rung, so compare models on the dots, not the rings.`
                : `${num(-drop)} above development on average: no sign that tuning overfitted.`}
            </Note>
          </div>
        )}
        <DataNote>A test on an earlier EDHS round or a neighbouring country&apos;s survey would show whether this accuracy travels; one survey round cannot.</DataNote>
      </Panel>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Panel help="models.by-rung"
          title={`Model by rung · ${setLabel}`}
          how="Held-out scores for every model at every rung, on this predictor set. Each column is shaded on its own (rungs differ in how hard they are), so read a column from dark to light to see the ranking at that rung."
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
          <Panel help="models.tuning"
            title={`Does tuning pay? · ${RUNG_LABEL[rung]}`}
            how="Rings: the model with its library defaults. Dots: after tuning (development accuracy). Most of the gain is small; the models are close before and after."
          >
            <DotRows
              rows={[...tuning]
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
        <Panel help="models.settings"
          title={`Which settings matter · ${ablName}`}
          how="Each tuned setting was moved one step down and one step up while the others stayed fixed. The bar spans the change in development accuracy: left of zero means the tuned value was better. A short bar near zero is a setting the model does not care about. The tuned value is under each name."
          actions={
            <Segmented
              label="Model"
              options={Object.keys(tuneBy).map((m) => ({ key: m, label: m === "Explainable Boosting" ? "EBM" : m === "Logistic regression" ? "Logistic" : m }))}
              value={ablName}
              onChange={setAblModel}
            />
          }
        >
          {abl ? (
            <>
              <DotRows
                rows={abl.params.map((p) => ({
                  key: p.parameter,
                  label: p.parameter.replace(/_/g, " "),
                  sub: `tuned: ${fmtParam(Number.isNaN(Number(p.tuned)) ? p.tuned : Number(p.tuned))}`,
                  values: { worst: p.worst, best: p.best },
                  display: signed(p.worst),
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
                  Defaults {num(abl.defaults_ap)} → tuned {num(abl.tuned_ap)} ({signed((abl.tuned_ap ?? 0) - (abl.defaults_ap ?? 0))} average precision, development, the 21 predictors).
                </Note>
              </div>
            </>
          ) : (
            <PanelLoading rows={6} />
          )}
        </Panel>

        <Panel help="models.calibration"
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
        <Panel help="models.decision"
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
                          ...(d.other != null ? [{ label: otherName, value: num(d.other), color: "var(--cross)" }] : []),
                          { label: "Act on everyone", value: num(d.treat_all), color: "var(--faint)" },
                        ]}
                      />
                    ))}
                  />
                  <Line dataKey="treat_none" stroke="var(--border2)" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                  <Line dataKey="treat_all" stroke="var(--faint)" strokeDasharray="4 3" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                  {dca[0]?.other != null && (
                    <Line dataKey="other" stroke="var(--cross)" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                  )}
                  <Line dataKey="model" stroke="var(--accent)" strokeWidth={2.25} dot={false} isAnimationActive={false} />
                </LineChart>
              </ChartBox>
              <SeriesLegend
                items={[
                  { key: "m", label: dcaName, color: "var(--accent)" },
                  ...(dca[0]?.other != null ? [{ key: "x", label: otherName, color: "var(--cross)" }] : []),
                  { key: "all", label: "Act on everyone", color: "var(--faint)", dashed: true },
                  { key: "none", label: "Act on no one", color: "var(--border2)" },
                ]}
              />
            </>
          ) : (
            <PanelLoading rows={6} />
          )}
        </Panel>

        <Panel help="models.lean"
          title={`What the models lean on · ${setLabel} · ${RUNG_LABEL[rung]}`}
          how={`Each predictor's share of what each model uses, on the held-out women: ${leanModels.includes("Explainable Boosting") ? "logistic regression and explainable boosting split their own predictions" : "logistic regression splits its own predictions"} exactly; the tree models by SHAP. Rows are the predictors the models agree on most, best first. One shading for the whole grid.`}
        >
          {leanRows.length ? (
            <MatrixHeat
              theme={theme}
              rows={leanRows.map((r) => ({ key: r.predictor, label: label(r.predictor), values: r.shares }))}
              cols={leanModels.map((m) => ({ key: m, label: m === "Explainable Boosting" ? "EBM" : m === "Logistic regression" ? "Logistic" : m }))}
              format={(v) => `${(v * 100).toFixed(0)}%`}
              labelWidth={200}
              cellWidth={70}
            />
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
