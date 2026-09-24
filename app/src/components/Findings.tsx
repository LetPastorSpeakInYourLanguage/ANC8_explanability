"use client";

import { useMemo, useState } from "react";
import type { Policy, RegionalCascadeRow } from "@/lib/analysis";
import {
  BarRow, Caveat, DivergingRow, Panel, StackedBar, Stat, Table, pct, num,
} from "./viz";

/**
 * What the data says about antenatal care in Ethiopia.
 *
 * Deliberately the first view. The cascade results here are descriptive —
 * they count where women are actually lost — which makes them the sturdiest
 * thing in the project and the part with the clearest implication for anyone
 * deciding where to put a budget. The model-based panels come later and are
 * labelled as associational where they appear.
 */

const SEG = {
  never: "#b4552d",
  start_lt4: "#d9944e",
  four_lt8: "#7aaea2",
  reach8: "#1f5757",
};

const LOSS_ADVICE: Record<string, string> = {
  "never starting":
    "an access problem — outreach, not continuity of care",
  "stopping before the 4th contact":
    "women are lost in early pregnancy",
  "stopping between the 4th and 8th":
    "a retention problem — these women already attend",
};

function Cascade({ c }: { c: NonNullable<Policy["cascade"]> }) {
  return (
    <Panel
      title="The problem is not getting women through the door"
      term="cascade"
      lede={
        <>
          Every number here is a count, survey-weighted to describe Ethiopia
          rather than the {c.n.toLocaleString()} women interviewed. No model is
          involved, so nothing here depends on a modelling assumption.
        </>
      }
    >
      <div className="grid grid-cols-3 gap-4 mb-5">
        <Stat value={pct(c.reach1)} label="reach antenatal care at least once" />
        <Stat value={pct(c.reach4)} label="reach four or more contacts" />
        <Stat value={pct(c.reach8)} label="reach the eight the WHO recommends" />
      </div>

      <div className="space-y-4">
        <div>
          <div className="flex justify-between label text-[0.72rem] mb-1">
            <span>of the women who start, how many reach four?</span>
            <span className="tabular">
              {pct(c.continue_1_to_4, 0)} continue · {pct(1 - c.continue_1_to_4, 0)} lost
            </span>
          </div>
          <StackedBar
            segments={[
              { value: c.continue_1_to_4, color: SEG.four_lt8, label: "continue" },
              { value: 1 - c.continue_1_to_4, color: "var(--line)" },
            ]}
          />
        </div>
        <div>
          <div className="flex justify-between label text-[0.72rem] mb-1">
            <span>of the women at four, how many reach eight?</span>
            <span className="tabular">
              {pct(c.continue_4_to_8, 0)} continue · {pct(1 - c.continue_4_to_8, 0)} lost
            </span>
          </div>
          <StackedBar
            segments={[
              { value: c.continue_4_to_8, color: SEG.reach8, label: "continue" },
              { value: 1 - c.continue_4_to_8, color: "var(--line)" },
            ]}
          />
        </div>
      </div>

      <Caveat>
        Three quarters of Ethiopian women already reach antenatal care. The
        single largest loss in the whole cascade is between the fourth contact
        and the eighth — not women failing to find the health system, but the
        health system failing to hold on to women who have already found it.
      </Caveat>
    </Panel>
  );
}

function Regional({ rows }: { rows: RegionalCascadeRow[] }) {
  const [sort, setSort] = useState<"reach8" | "never" | "four_lt8">("reach8");
  const sorted = useMemo(
    () => [...rows].sort((a, b) => (a[sort] ?? 0) - (b[sort] ?? 0)),
    [rows, sort]
  );

  // Regions with similar coverage but different bottlenecks are the point of
  // the panel, so surface a concrete pair rather than leaving it to be noticed.
  const contrast = useMemo(() => {
    const low = rows.filter((r) => r.reach8 < 0.13);
    const access = low.filter((r) => r.biggest_loss === "never starting")
      .sort((a, b) => b.biggest_loss_share - a.biggest_loss_share)[0];
    const retain = low
      .filter((r) => r.biggest_loss === "stopping between the 4th and 8th")
      .sort((a, b) => b.biggest_loss_share - a.biggest_loss_share)[0];
    return access && retain ? { access, retain } : null;
  }, [rows]);

  return (
    <Panel
      title="Regions with the same coverage are failing for opposite reasons"
      lede="Each bar is one region's whole population of recent mothers, split by
            how far up the ladder they reached. Read where the bar is widest:
            that is where that region loses women."
      aside={
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as typeof sort)}
          className="text-xs"
          style={{ width: "auto", padding: "0.3rem 0.45rem" }}
          aria-label="sort regions by"
        >
          <option value="reach8">sort by ANC8+ coverage</option>
          <option value="never">sort by never starting</option>
          <option value="four_lt8">sort by lost between 4 and 8</option>
        </select>
      }
    >
      {contrast && (
        <div
          className="mb-5 p-3 rounded-lg text-sm leading-relaxed"
          style={{ background: "var(--bg)", border: "1px solid var(--line)" }}
        >
          <strong>{contrast.access.region}</strong> reaches{" "}
          {pct(contrast.access.reach8)} and{" "}
          <strong>{contrast.retain.region}</strong> reaches{" "}
          {pct(contrast.retain.reach8)} — nearly the same. But{" "}
          {pct(contrast.access.never, 0)} of women in {contrast.access.region}{" "}
          never reach care at all, while in {contrast.retain.region} only{" "}
          {pct(contrast.retain.never, 0)} never start and{" "}
          {pct(contrast.retain.four_lt8, 0)} are lost between the fourth contact
          and the eighth. A programme built for one cannot help the other.
        </div>
      )}

      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-3">
        {[
          ["never start", SEG.never],
          ["start, stop before 4", SEG.start_lt4],
          ["reach 4, stop before 8", SEG.four_lt8],
          ["reach 8+", SEG.reach8],
        ].map(([l, c]) => (
          <span key={l} className="label text-[0.7rem] flex items-center gap-1.5">
            <span className="inline-block w-3 h-2.5 rounded-sm" style={{ background: c }} />
            {l}
          </span>
        ))}
      </div>

      <div className="space-y-2.5">
        {sorted.map((r) => (
          <div key={r.region}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-sm">{r.region}</span>
              <span className="label tabular text-[0.72rem]">
                {pct(r.reach8)} reach 8+ · n={r.n}
              </span>
            </div>
            <div className="mt-1">
              <StackedBar
                segments={[
                  { value: r.never, color: SEG.never,
                    title: `never start: ${pct(r.never)}`,
                    label: (r.never * 100).toFixed(0) },
                  { value: r.start_lt4, color: SEG.start_lt4,
                    title: `start, stop before 4: ${pct(r.start_lt4)}`,
                    label: (r.start_lt4 * 100).toFixed(0) },
                  { value: r.four_lt8, color: SEG.four_lt8,
                    title: `reach 4, stop before 8: ${pct(r.four_lt8)}`,
                    label: (r.four_lt8 * 100).toFixed(0) },
                  { value: r.reach8, color: SEG.reach8,
                    title: `reach 8+: ${pct(r.reach8)}`,
                    label: (r.reach8 * 100).toFixed(0) },
                ]}
              />
            </div>
            <div className="label text-[0.7rem] mt-1">
              biggest loss: {r.biggest_loss} —{" "}
              {LOSS_ADVICE[r.biggest_loss] ?? ""}
            </div>
          </div>
        ))}
      </div>

      <Caveat>
        Retention is what moves the national number, and it is reachable: the
        best-performing region keeps{" "}
        {pct(Math.max(...rows.map((r) => r.continue_1_to_4 ?? 0)), 0)} of
        starters through to four contacts and{" "}
        {pct(Math.max(...rows.map((r) => r.continue_4_to_8 ?? 0)), 0)} from four
        to eight — under Ethiopian conditions, not an imported benchmark.
      </Caveat>
    </Panel>
  );
}

function Equity({ eq }: { eq: NonNullable<Policy["continuation_equity"]> }) {
  const NAMES: Record<string, string> = {
    wealth_quintile: "Household wealth",
    residence: "Where she lives",
    maternal_education: "Her education",
  };
  return (
    <Panel
      title="Who is left behind once they are already in the system"
      term="continuation"
      lede="Every woman counted here has already attended four times, so this is
            not about whether women value antenatal care. They have demonstrated
            that they do. It is about what it costs them to keep attending."
    >
      <div className="grid gap-5 sm:grid-cols-3">
        {Object.entries(eq).map(([variable, levels]) => {
          const max = Math.max(...levels.map((l) => l.continue_4_to_8));
          return (
            <div key={variable}>
              <h3 className="text-sm font-medium mb-2">
                {NAMES[variable] ?? variable}
              </h3>
              <div className="space-y-2">
                {levels.map((l) => (
                  <BarRow
                    key={l.level}
                    label={l.level}
                    value={l.continue_4_to_8}
                    max={max}
                    display={pct(l.continue_4_to_8, 0)}
                    note={`n=${l.n}`}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
      <Caveat>
        The gap between the top and bottom of these tables is the cost of repeat
        attendance — transport paid eight times rather than four, days of work
        lost, childcare. That is a narrower and cheaper problem than generalised
        demand creation, and it applies to women the system has already reached.
      </Caveat>
    </Panel>
  );
}

function RegionalGap({ rows }: { rows: NonNullable<Policy["regional_gap"]> }) {
  const [rung, setRung] = useState("anc8plus");
  const available = useMemo(
    () => Array.from(new Set(rows.map((r) => r.rung))),
    [rows]
  );
  const sub = useMemo(
    () => rows.filter((r) => r.rung === rung).sort((a, b) => b.gap - a.gap),
    [rows, rung]
  );
  const scale = Math.max(...sub.map((r) => Math.abs(r.gap)), 0.01);

  return (
    <Panel
      title="Which regions beat their own circumstances"
      term="regional-gap"
      lede="Attainment predicted from wealth, education, household and access
            factors only — with region itself deliberately withheld from the
            model — then compared with what actually happened. A positive gap
            means the region does better than its population profile implies."
      aside={
        <select
          value={rung}
          onChange={(e) => setRung(e.target.value)}
          className="text-xs"
          style={{ width: "auto", padding: "0.3rem 0.45rem" }}
          aria-label="which rung"
        >
          {available.map((r) => (
            <option key={r} value={r}>
              {r.replace("plus", "+").toUpperCase()}
            </option>
          ))}
        </select>
      }
    >
      <div className="space-y-2.5">
        {sub.map((r) => (
          <DivergingRow
            key={r.region}
            label={r.region}
            value={r.gap}
            scale={scale}
            display={`${r.gap >= 0 ? "+" : ""}${(r.gap * 100).toFixed(1)} pts`}
            note={`actual ${pct(r.actual)} · expected ${pct(
              r.expected_from_circumstances
            )}`}
          />
        ))}
      </div>
      <Caveat>
        Region was withheld from the model, but predictors correlated with
        region were not, so the expected column is not a clean counterfactual.
        Read the ranking rather than the decimal. A region well above the line
        is doing something its circumstances do not explain — which is a
        question for the Ministry&apos;s own facility records, not for this
        survey.
      </Caveat>
    </Panel>
  );
}

function Modifiable({ rows }: { rows: NonNullable<Policy["modifiable"]> }) {
  return (
    <Panel
      title="How much rests on things a health system can change"
      lede="The same model and folds, run three times on three predictor sets:
            everything; only service factors a ministry can move (distance,
            transport, insurance, media reach, water and sanitation); and only
            fixed circumstance (wealth, education, age, parity, household)."
    >
      <Table
        head={["rung", "everything", "service factors only", "circumstance only"]}
        rows={rows.map((r) => [
          r.rung,
          num(r.all_predictors),
          num(r.modifiable_only),
          num(r.fixed_only),
        ])}
        note="Survey-weighted AUROC, development out-of-fold. Service factors
              carry proportionally more of the signal for reaching care at all
              than for completing the schedule — consistent with the cascade,
              where getting through the door is partly a supply problem and the
              later losses are not."
      />
      <Caveat>
        This decomposes predictive signal, not causal effect. It says where to
        look, not what to do.
      </Caveat>
    </Panel>
  );
}

function RiskBands({ rows }: { rows: NonNullable<Policy["risk_bands"]> }) {
  const max = Math.max(...rows.map((r) => r.actual_rate));
  return (
    <Panel
      title="If a programme can only reach a fraction of women, which fraction?"
      term="operating-threshold"
      lede="Held-out women grouped by the probability the model gave them, against
            what actually happened to them."
    >
      <div className="space-y-2.5">
        {rows.map((r) => (
          <BarRow
            key={r.band}
            label={`predicted ${r.band}`}
            value={r.actual_rate}
            max={max}
            display={`${pct(r.actual_rate, 0)} actually reached 8+`}
            note={`${pct(r.population_share, 0)} of all women · n=${r.n}`}
          />
        ))}
      </div>
      <Caveat>
        The band just below the operating threshold is the group a
        capacity-limited programme can realistically move: predicted low, but
        not hopeless. The bottom band is large and hard to shift; the top needs
        no help. The model ranks women correctly about 78% of the time, which is
        useful across a population and far too blunt for any individual woman.
      </Caveat>
    </Panel>
  );
}

export default function Findings({ policy }: { policy: Policy }) {
  return (
    <div className="space-y-6">
      {policy.cascade && <Cascade c={policy.cascade} />}
      {policy.regional_cascade && <Regional rows={policy.regional_cascade} />}
      {policy.continuation_equity && <Equity eq={policy.continuation_equity} />}
      {policy.regional_gap && <RegionalGap rows={policy.regional_gap} />}
      {policy.modifiable && <Modifiable rows={policy.modifiable} />}
      {policy.risk_bands && <RiskBands rows={policy.risk_bands} />}

      <section className="card p-4 sm:p-5">
        <h2 className="font-semibold">What this suggests, concretely</h2>
        <ol className="mt-3 space-y-2 text-sm leading-relaxed list-decimal pl-5">
          <li>
            Stop treating ANC8 coverage as one national problem. Target by where
            in the cascade each region loses women, not by its headline number.
          </li>
          <li>
            Regions where a third or more of women never make contact need
            outreach. Nothing that improves continuity reaches them.
          </li>
          <li>
            Regions where women arrive and are lost partway need retention.
            Continuation from four contacts to eight is where the national
            number will move.
          </li>
          <li>
            The cost of repeat attendance looks like a binding constraint for
            poorer women who have already engaged — a narrower problem than
            demand creation.
          </li>
          <li>
            The ceiling is reachable within Ethiopia. One region already
            achieves it.
          </li>
        </ol>
        <Caveat>
          These are patterns, not causes. The cascade results count where women
          are lost, which needs no causal assumption; the model-based panels
          describe which women attain care, not what would happen if a
          woman&apos;s circumstances changed. The survey holds no facility data
          at all, so it can say where the problem is and not why.
        </Caveat>
      </section>
    </div>
  );
}
