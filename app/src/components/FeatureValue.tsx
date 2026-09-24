"use client";

import { useMemo, useState } from "react";
import type { FeatureValue, FeatureValueEntry } from "@/lib/analysis";
import { label } from "@/lib/labels";
import {
  BarRow, Caveat, DivergingRow, LineChart, Panel, Stat, Table, num, signed,
} from "./viz";

/**
 * Predictor value: which predictors carry the prediction, and why 21.
 *
 * Every comparison holds the model fixed (logistic regression, each set at
 * its own best regularisation) and varies only the predictors, on development
 * folds; the held-out table at the end is the one look at unseen women.
 *
 * A variable counts only if it changes AP by at least 0.005 AND does so on at
 * least 4 of 5 split seeds -- consistently, not on average.
 */

const COHORT_NAME: Record<string, string> = {
  full: "before ANC (6,893 women)",
  entry: "at ANC entry (5,001 women)",
  recent: "last 24 months (sensitivity)",
};
const COHORT_ORDER = ["full", "entry", "recent"];

const SET_NAME: Record<string, string> = {
  "tier 1": "tier 1",
  "tier 1+2": "tier 1+2",
  "original 21": "21-predictor set",
  "21 + early ANC": "21 + early ANC",
  "all 88": "full pool",
};

function rungLabel(r: string) {
  return r.replace("plus", "+").toUpperCase();
}

function Picker({
  value, options, onChange, render,
}: {
  value: string; options: string[]; onChange: (v: string) => void;
  render: (v: string) => string;
}) {
  return (
    <div className="flex gap-1 flex-wrap">
      {options.map((o) => (
        <button
          key={o}
          onClick={() => onChange(o)}
          className="px-2.5 py-1 text-xs rounded"
          style={{
            border: "1px solid var(--line)",
            background: o === value ? "var(--accent)" : "transparent",
            color: o === value ? "#fff" : "var(--muted)",
          }}
        >
          {render(o)}
        </button>
      ))}
    </div>
  );
}

function Headline({ e }: { e: FeatureValueEntry }) {
  const a = e.summary.anchors;
  const s0 = e.summary.stage0;
  const tiers = e.summary.tier1.length + e.summary.tier2.length;
  const nPool = e.summary.n_candidates ?? 88;
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <Stat value={num(a.original21)} label="the 21-predictor set (development AP)" />
      <Stat value={num(a.all88)} label={`the full pool of ${nPool}`} />
      <Stat
        value={s0 ? `${s0.n_non_contributors} of 21` : "—"}
        label="members of the 21 that add nothing when dropped"
        tone="plain"
      />
      <Stat
        value={tiers ? String(tiers) : "—"}
        label="variables selected from the pool (tier 1 + 2)"
        tone="good"
      />
      <div className="col-span-2 sm:col-span-4 label leading-relaxed">
        Prevalence, the score of a model with no information, is{" "}
        {num(a.prevalence)}. Read every AP against it.
      </div>
    </div>
  );
}

function WhyTwentyOne({ e }: { e: FeatureValueEntry }) {
  const drop = e.drop_within_21 ?? [];
  const path = e.path_within_21 ?? [];
  const s0 = e.summary.stage0;
  const a = e.summary.anchors;
  if (!drop.length && !path.length) return null;
  const scale = Math.max(...drop.map((d) => Math.abs(d.loss)), 0.002);
  const ceiling = a.all88 - a.prevalence;
  const share = (ap: number) => ((ap - a.prevalence) / ceiling) * 100;
  const steps = (e.steps ?? []).filter((s) => s.tier === "tier 1" || s.tier === "tier 2");
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {drop.length > 0 && (
        <div>
          <h3 className="text-sm font-medium mb-1">Each of the 21, dropped from the 21</h3>
          <p className="label mb-3 leading-relaxed">
            AP lost when one member is removed. A bar to the left means the set
            does as well or better without it.
          </p>
          <div className="space-y-2">
            {[...drop].sort((x, y) => y.loss - x.loss).map((r) => (
              <DivergingRow
                key={r.predictor}
                label={label(r.predictor)}
                value={r.loss}
                scale={scale}
                display={`${signed(r.loss, 4)} · ${r.seeds_positive}/5`}
              />
            ))}
          </div>
        </div>
      )}
      {path.length > 0 && (
        <div>
          <h3 className="text-sm font-medium mb-1">How many are needed</h3>
          <p className="label mb-2 leading-relaxed">
            Share of the full pool&apos;s lift over prevalence, as predictors are
            added best first: within the 21, and selected from the whole pool.
          </p>
          <LineChart
            series={[
              {
                name: "best k of the 21",
                color: "var(--set21)",
                points: path.map((p) => ({ x: p.step, y: share(p.AP) })),
              },
              ...(steps.length ? [{
                name: "selected from the pool",
                color: "var(--accent)",
                points: steps.map((s, i) => ({ x: i + 1, y: share(s.AP) })),
              }] : []),
              {
                name: "all 21",
                color: "var(--set21)",
                dashed: true,
                points: [{ x: 1, y: share(a.original21) }, { x: 21, y: share(a.original21) }],
              },
            ]}
            xLabel="predictors"
            yLabel="% of the full pool's lift"
            height={230}
            markers
          />
          {s0 && (
            <p className="label mt-3 leading-relaxed">
              The path within the 21 peaks at <strong>{s0.best_k_within_21}</strong>{" "}
              predictors ({num(s0.best_AP_within_21)}) against {num(a.original21)} for
              all 21. Dropping every non-contributor at once gives{" "}
              {num(s0.AP_21_minus_non_contributors)} with{" "}
              {21 - s0.n_non_contributors}.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function AddOne({ e }: { e: FeatureValueEntry }) {
  const rows = e.add_one ?? [];
  if (!rows.length) return null;
  const top = rows.slice(0, 14);
  const max = Math.max(...top.map((r) => Math.abs(r.gain)), 0.005);
  const rest = rows.slice(14);
  const nearZero = rest.filter((r) => Math.abs(r.gain) < 0.002).length;
  return (
    <div>
      <h3 className="text-sm font-medium mb-1">
        Each other candidate, added alone to the 21
      </h3>
      <p className="label mb-3 leading-relaxed">
        Coloured bars clear the threshold. The list is sorted; the long tail
        below it is where most candidates live.
      </p>
      <div className="space-y-2">
        {top.map((r) => (
          <BarRow
            key={r.predictor}
            label={label(r.predictor)}
            value={Math.max(0, r.gain)}
            max={max}
            display={`${signed(r.gain, 4)} · ${r.seeds_positive}/5`}
            color={r.clears_threshold ? "var(--accent)" : "var(--line)"}
            note={r.at_interview ? `measured at interview: ${r.at_interview}` : undefined}
          />
        ))}
      </div>
      {rest.length > 0 && (
        <p className="label mt-3">
          The other {rest.length} add between {signed(Math.min(...rest.map((r) => r.gain)), 4)}{" "}
          and {signed(Math.max(...rest.map((r) => r.gain)), 4)}; {nearZero} of them
          change AP by less than 0.002.
        </p>
      )}
    </div>
  );
}

function Cumulative({ e }: { e: FeatureValueEntry }) {
  const c = e.cumulative ?? [];
  if (c.length < 3) return null;
  const base = c[0].AP;
  return (
    <div>
      <h3 className="text-sm font-medium mb-1">Stacking every candidate onto the 21</h3>
      <p className="label mb-2 leading-relaxed">
        Added best first. The curve climbs for a handful of variables and then
        runs flat, or falls, for the rest.
      </p>
      <LineChart
        series={[{
          name: "development AP",
          color: "var(--accent)",
          points: c.map((r) => ({ x: r.n_added, y: r.AP })),
        }, {
          name: "the 21 alone",
          color: "var(--set21)",
          dashed: true,
          points: [{ x: 0, y: base }, { x: c[c.length - 1].n_added, y: base }],
        }]}
        xLabel="candidates added"
        yLabel="AP"
        height={210}
      />
    </div>
  );
}

function Tiers({ e }: { e: FeatureValueEntry }) {
  const steps = e.steps ?? [];
  if (!steps.length) return null;
  const freq = new Map((e.frequency ?? []).map((f) => [f.predictor, f.selected_share]));
  const colour: Record<string, string> = {
    "tier 1": "var(--accent)", "tier 2": "#7aaea2", "not selected": "var(--muted)",
  };
  return (
    <div>
      <h3 className="text-sm font-medium mb-1">
        Built from nothing: the variables that earn a place
      </h3>
      <p className="label mb-3 leading-relaxed">
        At each step the variable that adds most is kept, if it adds at least
        0.005 on 4 of 5 splits. Tier 1 reaches 90% of what the full pool
        achieves; tier 2 is each further step that still pays. The last row is
        the first that did not.
      </p>
      <Table
        head={["", "variable", "AP", "adds", "splits", "picked again", "in the 21?"]}
        rows={steps.map((s) => [
          <span key="t" className="text-[0.7rem] whitespace-nowrap"
                style={{ color: colour[s.tier] ?? "var(--muted)" }}>
            {s.tier}
          </span>,
          <span key="v">
            {label(s.predictor)}
            {s.at_interview && (
              <span className="label ml-1 text-[0.65rem]" title={s.at_interview}>
                · at interview
              </span>
            )}
          </span>,
          num(s.AP),
          signed(s.gain, 4),
          `${s.seeds_positive}/5`,
          freq.size ? (freq.has(s.predictor) ? `${Math.round((freq.get(s.predictor) ?? 0) * 100)}%` : "0%") : "—",
          s.in_original_21 ? "yes" : "",
        ])}
        note={freq.size ? "\"Picked again\" is how often the same variable was selected when the whole procedure was re-run on bootstrap resamples; under 70% means its place is not reliable." : undefined}
      />
    </div>
  );
}

const FAMILIES = ["Logistic regression", "Random Forest", "XGBoost"];

function HeldOut({ e }: { e: FeatureValueEntry }) {
  const all = e.heldout ?? [];
  if (!all.length) return null;
  const boot = e.heldout_bootstrap ?? {};
  const order = ["tier 1", "tier 1+2", "original 21", "21 + early ANC", "all 88"];
  // The set comparison uses logistic regression and LightGBM; random forest
  // and XGBoost were fitted on the 21 only and get their own table below.
  const h = all.filter((r) => r.model === "Logistic regression" || r.model === "LightGBM");
  const rows = [...h].sort((a, b) =>
    a.model.localeCompare(b.model) || order.indexOf(a.set) - order.indexOf(b.set));
  const fam = FAMILIES
    .map((m) => all.find((r) => r.model === m && r.set === "original 21"))
    .filter((r): r is NonNullable<typeof r> => !!r);
  return (
    <div className="space-y-6">
    <div>
      <h3 className="text-sm font-medium mb-1">One look at the held-out women</h3>
      <p className="label mb-3 leading-relaxed">
        Each set fitted on the development women and scored once on women it
        never saw. This is where optimism from selecting on the same folds shows.
      </p>
      <Table
        head={["model", "set", "predictors", "AP", "AUROC", "vs the 21 (95% interval)"]}
        rows={rows.map((r) => {
          const b = boot[`${r.model} | ${r.set} vs original 21`];
          return [
            r.model === "Logistic regression" ? "logistic" : r.model,
            SET_NAME[r.set] ?? r.set,
            r.n_predictors,
            num(r.AP),
            num(r.AUROC),
            b ? `${signed(b.d_AP)} [${signed(b.d_AP_lo)}, ${signed(b.d_AP_hi)}]` : "—",
          ];
        })}
      />
    </div>
    {fam.length > 1 && (
      <div>
        <h3 className="text-sm font-medium mb-1">The 21 under three model families</h3>
        <p className="label mb-3 leading-relaxed">
          The same 21 predictors with logistic regression, random forest and
          XGBoost, each fitted on the development women (the two tree models
          tuned on development folds) and scored once on the held-out women.
          {e.best_21_model && <> Best of the three: <strong>{e.best_21_model}</strong>.</>}
        </p>
        <Table
          head={["", "model", "AP", "AUROC", "calibration slope", "AP vs logistic (95% interval)"]}
          rows={fam.map((r) => {
            const b = boot[`${r.model} | original 21 vs original 21`];
            return [
              r.model === e.best_21_model ? <span key="s" style={{ color: "var(--accent)" }}>★</span> : "",
              r.model,
              num(r.AP),
              num(r.AUROC),
              num(r.Calibration_slope, 2),
              r.model === "Logistic regression" ? "reference"
                : b ? `${signed(b.d_AP)} [${signed(b.d_AP_lo)}, ${signed(b.d_AP_hi)}]` : "—",
            ];
          })}
          note="An interval containing 0 means the held-out women cannot tell that model from logistic regression on the same 21 predictors."
        />
      </div>
    )}
    </div>
  );
}

export default function FeatureValueView({ data }: { data: FeatureValue }) {
  const cohorts = useMemo(
    () => COHORT_ORDER.filter((c) => data[c]).concat(
      Object.keys(data).filter((c) => !COHORT_ORDER.includes(c))),
    [data]
  );
  const [cohort, setCohort] = useState(cohorts.includes("full") ? "full" : cohorts[0]);
  const rungs = useMemo(
    () => ["anc1plus", "anc4plus", "anc8plus"].filter((r) => data[cohort]?.[r]),
    [data, cohort]
  );
  const [rung, setRung] = useState("anc8plus");
  const active = rungs.includes(rung) ? rung : rungs[rungs.length - 1];
  const e = active ? data[cohort]?.[active] : undefined;
  if (!e) return null;

  return (
    <Panel
      title="Predictor value: 2, 8, 21 or the full pool?"
      term="bar"
      lede="Which predictors carry the prediction of ANC1+, ANC4+ and ANC8+, and
            whether the 21-predictor set is the right size. Same model, same
            folds; only the predictors change. A variable counts only if it moves
            AP by at least 0.005 on 4 of 5 split seeds."
    >
      <div className="flex flex-wrap gap-4 mb-5">
        <Picker value={cohort} options={cohorts} onChange={setCohort}
                render={(c) => COHORT_NAME[c] ?? c} />
        <Picker value={active} options={rungs} onChange={setRung} render={rungLabel} />
      </div>
      <div className="space-y-7">
        <Headline e={e} />
        <WhyTwentyOne e={e} />
        <div className="grid gap-6 lg:grid-cols-2">
          <AddOne e={e} />
          <Cumulative e={e} />
        </div>
        <Tiers e={e} />
        <HeldOut e={e} />
      </div>
      <Caveat>
        A set chosen by searching the development folds always looks better on
        them than on new women, so the held-out table is the fair comparison.
        Dropping a predictor that duplicates another understates it, and a
        variable can belong in a model for reasons prediction cannot see, such
        as equity monitoring. &ldquo;Adds nothing to prediction&rdquo; is not
        &ldquo;should be deleted&rdquo;.
      </Caveat>
    </Panel>
  );
}
