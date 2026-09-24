"use client";

import { useMemo, useState } from "react";
import type { Analysis, ModelAblation } from "@/lib/analysis";
import {
  BarRow, Caveat, DivergingRow, Dumbbell, LineChart, Panel, Stat, Table,
  num, pct, signed,
} from "./viz";

/**
 * Models and tuning: the leaderboard, what the search cost, and what it bought.
 *
 * The uncomfortable number is given the most space, because it is the one a
 * reader most needs: every model's development score ran about 0.08 AP above
 * its held-out score, which is larger than anything tuning achieved. A view
 * that showed only the winning configuration would imply the search mattered
 * more than it did.
 */


/** Model names carry their predictor set internally ("V1 XGBoost"); show the set. */
function modelName(m: string) {
  return m.startsWith("V1 ") ? `${m.slice(3)} (21 predictors)` : m;
}

function rungLabel(rung: string) {
  return rung.replace("plus", "+").toUpperCase();
}

function Leaderboard({ a, rung }: { a: Analysis; rung: string }) {
  const [sortBy, setSortBy] = useState<"dev_AP" | "held_AP" | "optimism">("dev_AP");
  const board = a.leaderboard[rung] ?? [];
  const optimism = a.optimism?.[rung];
  const prevalence = a.outcomes[rung]?.weighted_prevalence;

  const rows = useMemo(() => {
    const v = [...board];
    v.sort((x, y) => {
      const xa = x[sortBy];
      const ya = y[sortBy];
      if (xa == null) return 1;
      if (ya == null) return -1;
      return sortBy === "optimism" ? ya - xa : ya - xa;
    });
    return v;
  }, [board, sortBy]);

  const withBoth = board.filter((r) => r.dev_AP != null && r.held_AP != null);
  const lo = Math.min(...withBoth.flatMap((r) => [r.dev_AP!, r.held_AP!]));
  const hi = Math.max(...withBoth.flatMap((r) => [r.dev_AP!, r.held_AP!]));
  const totalHours =
    board.reduce((s, r) => s + (r.seconds ?? 0), 0) / 3600;

  return (
    <Panel
      title={`Every model that was tried — ${rungLabel(rung)}`}
      term="overfitting"
      lede={
        <>
          Ten families plus ensembles and calibrated variants, each tuned with
          Optuna over the same cluster-grouped folds, so the comparison is like
          for like. Total search time for this rung:{" "}
          <strong>{totalHours.toFixed(1)} hours</strong>.
          {prevalence != null && (
            <>
              {" "}
              Average precision has a floor at the prevalence,{" "}
              {pct(prevalence)} — a model that ranked at random would score
              that.
            </>
          )}
        </>
      }
      aside={
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
          className="text-xs"
          style={{ width: "auto", padding: "0.3rem 0.45rem" }}
          aria-label="sort by"
        >
          <option value="dev_AP">sort by development AP</option>
          <option value="held_AP">sort by held-out AP</option>
          <option value="optimism">sort by optimism</option>
        </select>
      }
    >
      {withBoth.length > 1 && (
        <>
          <div className="flex gap-4 mb-3">
            <span className="label text-[0.7rem] flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full"
                    style={{ background: "var(--set21)" }} />
              development (out-of-fold)
            </span>
            <span className="label text-[0.7rem] flex items-center gap-1.5">
              <span className="inline-block w-2.5 h-2.5 rounded-full"
                    style={{ background: "var(--accent)" }} />
              held-out
            </span>
          </div>
          <div className="space-y-1 mb-5">
            {rows
              .filter((r) => r.dev_AP != null && r.held_AP != null)
              .map((r) => (
                <Dumbbell
                  key={r.model}
                  label={modelName(r.model)}
                  a={r.dev_AP!}
                  b={r.held_AP!}
                  min={lo}
                  max={hi}
                  aLabel="development"
                  bLabel="held-out"
                />
              ))}
          </div>
        </>
      )}

      {optimism && (
        <div
          className="p-3 rounded-lg mb-5"
          style={{ background: "var(--bg)", border: "1px solid var(--line)" }}
        >
          <Stat
            value={signed(-optimism.mean_drop)}
            label={
              <>
                mean AP lost from development to held-out, across{" "}
                {optimism.n_models} models. Every arm moves the same way, which
                is the signature of selecting among many models on the same
                folds — not of one model generalising badly.
              </>
            }
            tone="bad"
          />
        </div>
      )}

      <Table
        head={["model", "dev AP", "held AP", "AUROC", "Brier", "slope",
               "trials", "search"]}
        rows={rows.map((r) => [
          <span key="m" className="whitespace-nowrap">
            {modelName(r.model)}
          </span>,
          num(r.dev_AP),
          num(r.held_AP),
          num(r.held_AUROC ?? r.dev_AUROC),
          num(r.held_Brier ?? r.dev_Brier),
          num(r.held_slope ?? r.dev_slope, 2),
          r.n_trials ?? "—",
          r.seconds != null ? `${(r.seconds / 60).toFixed(0)} min` : "—",
        ])}
        note="Calibration slope belongs next to AUROC: a model can rank women
              well and still produce probabilities that are far too extreme, and
              a slope well below 1 means exactly that."
      />
    </Panel>
  );
}

function Calibration({ a, rung }: { a: Analysis; rung: string }) {
  const curves = a.calibration[rung];
  if (!curves) return null;
  const preferred = [
    "Explainable Boosting", "XGBoost", "Logistic regression",
    "V1 XGBoost", "V1 Logistic regression",
  ].filter((m) => curves[m]);
  const [chosen, setChosen] = useState<string[]>(preferred.slice(0, 3));
  const colors = ["var(--accent)", "#4b8f88", "#7aaea2", "var(--set21)", "#c2703d"];
  const all = Object.keys(curves);

  const series = chosen.map((m, i) => ({
    name: modelName(m),
    color: colors[i % colors.length],
    dashed: m.startsWith("V1"),
    points: curves[m].map((p) => ({ x: p.predicted, y: p.observed })),
  }));

  return (
    <Panel
      title="Do the probabilities mean what they say?"
      term="calibration"
      lede="Held-out women sorted into ten equal groups by predicted probability.
            The dashed diagonal is perfect: a group predicted 30% in which 30%
            attained. Above the line the model is under-confident, below it
            over-confident."
    >
      <div className="grid gap-5 sm:grid-cols-[1fr_200px]">
        <LineChart
          series={series}
          xLabel="predicted probability"
          yLabel="observed attainment"
          xDomain={[0, Math.max(...series.flatMap((s) => s.points.map((p) => p.x)), 0.5)]}
          yDomain={[0, 1]}
          diagonal
          markers
        />
        <div>
          <p className="label text-[0.72rem] mb-2">show</p>
          <div className="space-y-1 max-h-64 overflow-y-auto pr-1">
            {all.map((m) => (
              <label key={m} className="flex items-start gap-2 text-[0.78rem]">
                <input
                  type="checkbox"
                  checked={chosen.includes(m)}
                  onChange={() =>
                    setChosen((c) =>
                      c.includes(m) ? c.filter((x) => x !== m) : [...c, m]
                    )
                  }
                  style={{ width: "auto", marginTop: 2 }}
                />
                <span className="leading-snug">{modelName(m)}</span>
              </label>
            ))}
          </div>
        </div>
      </div>
    </Panel>
  );
}

function DecisionCurve({ a, rung }: { a: Analysis; rung: string }) {
  const dc = a.decision_curve[rung];
  if (!dc?.length) return null;
  const name = dc[0].model_name ?? "full-pool model";
  const series = [
    { name, color: "var(--accent)", points: dc.map((r) => ({ x: r.threshold, y: r.model })) },
    { name: "treat everyone", color: "var(--muted)",
      points: dc.map((r) => ({ x: r.threshold, y: r.treat_all })) },
    { name: "treat no one", color: "var(--line)",
      points: dc.map((r) => ({ x: r.threshold, y: r.treat_none })) },
  ];
  if (dc[0].v1_xgboost != null) {
    series.push({
      name: "21-predictor XGBoost", color: "var(--set21)",
      points: dc.map((r) => ({ x: r.threshold, y: r.v1_xgboost! })),
    });
  }
  return (
    <Panel
      title="Is using the model better than the obvious alternatives?"
      term="net-benefit"
      lede="Net benefit across the thresholds a programme might plausibly use.
            The model is worth using only where its line sits above both
            defaults — treating everyone, and treating no one."
    >
      <LineChart
        series={series}
        xLabel="threshold probability"
        yLabel="net benefit"
        height={250}
        zeroLine
      />
    </Panel>
  );
}

function AblationPanel({ a, rung }: { a: Analysis; rung: string }) {
  const abl = a.ablation[rung];
  const models = abl ? Object.keys(abl) : [];
  const [model, setModel] = useState(models[0] ?? "");
  if (!abl || !models.length) {
    return (
      <Panel
        title="What did the tuning actually buy?"
      term="tuning"
        lede="The hyperparameter ablation has not been run for this rung yet. It
              re-measures each tuned parameter moved off its chosen value, and
              compares the tuned model against library defaults."
      >
        <p className="label">
          Run <code>scripts/run_hyperparameter_ablation.py --outcome {rung}</code>.
        </p>
      </Panel>
    );
  }
  const d: ModelAblation = abl[model] ?? abl[models[0]];
  const worst = Math.max(...d.parameters.map((p) => Math.abs(p.worst_AP_drop)), 0.001);
  const optimism = a.optimism?.[rung]?.mean_drop;

  return (
    <Panel
      title="What did the tuning actually buy?"
      term="tuning"
      lede="Each parameter moved away from the value Optuna chose, with every
            other parameter held at its tuned setting, and the out-of-fold score
            re-measured. A parameter whose perturbation barely moves the score
            was not worth searching over."
      aside={
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="text-xs"
          style={{ width: "auto", padding: "0.3rem 0.45rem" }}
          aria-label="model"
        >
          {models.map((m) => (
            <option key={m} value={m}>{modelName(m)}</option>
          ))}
        </select>
      }
    >
      <div className="grid grid-cols-3 gap-4 mb-5">
        <Stat value={num(d.defaults_AP)} label="library defaults, no tuning" />
        <Stat value={num(d.tuned_AP)} label="the Optuna optimum" />
        <Stat
          value={signed(d.gain)}
          label="what the whole search bought"
          tone={d.gain != null && d.gain > 0.01 ? "good" : "plain"}
        />
      </div>

      <p className="label mb-2">
        Worst AP drop caused by moving each parameter off its tuned value
      </p>
      <div className="space-y-2">
        {d.parameters.slice(0, 10).map((p) => (
          <BarRow
            key={p.parameter}
            label={p.parameter}
            value={Math.abs(p.worst_AP_drop)}
            max={worst}
            display={signed(p.worst_AP_drop, 4)}
            color={Math.abs(p.worst_AP_drop) > 0.005 ? "var(--accent)" : "var(--line)"}
            note={`${p.n_perturbations} perturbations tried`}
          />
        ))}
      </div>

      {optimism != null && (
        <Caveat>
          Read all of this against one number: development scores on this rung
          ran <strong>{optimism.toFixed(3)} AP</strong> above held-out scores. A
          tuning gain smaller than that gap is not evidence that the tuned model
          generalises better — it is within the noise of the selection process
          that produced it. The gains in this project came from the predictors,
          not from the optimiser.
        </Caveat>
      )}
    </Panel>
  );
}

function TuningGain({ a }: { a: Analysis }) {
  if (!a.tuning_gain?.length) return null;
  const scale = Math.max(...a.tuning_gain.map((g) => Math.abs(g.gain)), 0.005);
  return (
    <Panel
      title="Tuning gain over library defaults, everywhere it was measured"
      term="tuning"
      lede="Across models and rungs. Positive means the search found something
            the defaults did not."
    >
      <div className="space-y-2.5">
        {a.tuning_gain.map((g) => (
          <DivergingRow
            key={`${g.rung}-${g.model}`}
            label={`${g.model} · ${rungLabel(g.rung)}`}
            value={g.gain}
            scale={scale}
            display={signed(g.gain, 4)}
            note={`defaults ${num(g.defaults_AP)} → tuned ${num(g.tuned_AP)}`}
          />
        ))}
      </div>
    </Panel>
  );
}

function Hyperparameters({ a, rung }: { a: Analysis; rung: string }) {
  const hp = a.hyperparameters[rung];
  const models = hp ? Object.keys(hp) : [];
  const [open, setOpen] = useState<string | null>(models[0] ?? null);
  if (!hp || !models.length) return null;
  return (
    <Panel
      title="The configurations the search settled on"
      lede="Reported in full, because a comparison whose hyperparameters are not
            stated cannot be reproduced or disputed."
    >
      <div className="space-y-1">
        {models.map((m) => {
          const isOpen = open === m;
          return (
            <div key={m}>
              <button
                className="w-full text-left py-1.5 flex items-center justify-between"
                style={{ borderBottom: "1px solid var(--line)" }}
                onClick={() => setOpen(isOpen ? null : m)}
              >
                <span className="text-sm">{modelName(m)}</span>
                <span className="label text-[0.7rem]">
                  {Object.keys(hp[m]).length} parameters {isOpen ? "−" : "+"}
                </span>
              </button>
              {isOpen && (
                <div className="py-2 grid gap-x-6 gap-y-1 sm:grid-cols-2">
                  {Object.entries(hp[m]).map(([k, v]) => (
                    <div key={k} className="flex justify-between gap-3 text-[0.78rem]">
                      <span className="label">{k}</span>
                      <span className="tabular">{String(v)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

export default function Models({ analysis }: { analysis: Analysis }) {
  const rungs = analysis.rungs.length ? analysis.rungs : ["anc8plus"];
  const [rung, setRung] = useState(
    rungs.includes("anc8plus") ? "anc8plus" : rungs[0]
  );

  return (
    <div className="space-y-6">
      {rungs.length > 1 && (
        <div className="flex items-center gap-2">
          <span className="label">Outcome</span>
          <div className="flex gap-1">
            {rungs.map((r) => (
              <button
                key={r}
                onClick={() => setRung(r)}
                className="px-2.5 py-1 text-xs rounded"
                style={{
                  border: "1px solid var(--line)",
                  background: r === rung ? "var(--accent)" : "transparent",
                  color: r === rung ? "#fff" : "var(--muted)",
                }}
              >
                {rungLabel(r)}
              </button>
            ))}
          </div>
        </div>
      )}

      <Leaderboard a={analysis} rung={rung} />
      <AblationPanel a={analysis} rung={rung} />
      <TuningGain a={analysis} />
      <Calibration a={analysis} rung={rung} />
      <DecisionCurve a={analysis} rung={rung} />
      <Hyperparameters a={analysis} rung={rung} />
    </div>
  );
}
