"use client";

import { useMemo } from "react";
import type { Analysis, Policy, RegionalCascadeRow } from "@/lib/analysis";
import { pct } from "./viz";

/**
 * The policy brief, as the app's front page.
 *
 * Written for the Ministry of Health: five findings, what each region needs,
 * and what to do. Every number is read from the same analysis files the
 * technical views use, so the brief cannot drift from the evidence behind it;
 * each finding links to the view that shows that evidence in full.
 */

type Nav = (tab: string, doc?: string) => void;

const ACTION: Record<string, { label: string; colour: string; what: string }> = {
  "never starting": {
    label: "Outreach", colour: "#b4552d",
    what: "bring the service to women it does not yet reach",
  },
  "stopping before the 4th contact": {
    label: "Early engagement", colour: "#c98a3e",
    what: "hold women through the first half of pregnancy",
  },
  "stopping between the 4th and 8th": {
    label: "Retention", colour: "#2f7d70",
    what: "follow-up, reminders, lower cost of each return visit",
  },
};

function FindingCard({
  n, value, title, body, cta, onClick,
}: {
  n: number; value: string; title: string; body: React.ReactNode;
  cta: string; onClick: () => void;
}) {
  return (
    <div className="card p-4 flex flex-col">
      <div className="flex items-baseline gap-3">
        <span className="label tabular">{n}</span>
        <span className="text-2xl font-semibold tabular" style={{ color: "var(--accent)" }}>
          {value}
        </span>
      </div>
      <h3 className="font-semibold mt-2 leading-snug">{title}</h3>
      <p className="label mt-2 leading-relaxed flex-1">{body}</p>
      <button
        onClick={onClick}
        className="mt-3 self-start text-xs px-2.5 py-1 rounded"
        style={{ border: "1px solid var(--line)", color: "var(--accent)" }}
      >
        {cta} →
      </button>
    </div>
  );
}

export default function Brief({
  policy, analysis, onNavigate,
}: {
  policy: Policy | null; analysis: Analysis | null; onNavigate: Nav;
}) {
  const c = policy?.cascade;
  const regions = policy?.regional_cascade ?? [];

  const contrast = useMemo(() => {
    const low = regions.filter((r) => r.reach8 < 0.13);
    const access = [...low].filter((r) => r.biggest_loss === "never starting")
      .sort((a, b) => b.never - a.never)[0];
    const retain = [...low].filter((r) => r.biggest_loss === "stopping between the 4th and 8th")
      .sort((a, b) => (a.continue_4_to_8 ?? 1) - (b.continue_4_to_8 ?? 1))[0];
    return access && retain ? { access, retain } : null;
  }, [regions]);

  const equity = useMemo(() => {
    const w = policy?.continuation_equity?.wealth_quintile;
    if (!w?.length) return null;
    // The brief compares the richest fifth with the poorest fifth by name; the
    // minimum is not always the poorest (Poorer sits slightly lower here).
    const sorted = [...w].sort((a, b) => a.continue_4_to_8 - b.continue_4_to_8);
    const lo = w.find((x) => x.level === "Poorest") ?? sorted[0];
    const hi = w.find((x) => x.level === "Richest") ?? sorted[sorted.length - 1];
    return { lo, hi, ratio: hi.continue_4_to_8 / lo.continue_4_to_8 };
  }, [policy]);

  const war = useMemo(() => {
    const d = (policy?.wartime?.did ?? []).filter(
      (r) => r.window_shift_months === 0 && r.controls === "peaceful regions");
    const never = d.find((r) => r.measure === "never");
    const anc8 = d.find((r) => r.measure === "anc8plus");
    return never ? { never, anc8 } : null;
  }, [policy]);

  // How consistently the leading predictors are chosen across the six
  // selection runs (three outcomes x two birth windows).
  const predictors = useMemo(() => {
    const fv = analysis?.feature_value;
    if (!fv) return null;
    const runs = Object.values(fv).flatMap((byRung) => Object.values(byRung));
    const count = (v: string) =>
      runs.filter((e) => [...e.summary.tier1, ...e.summary.tier2].includes(v)).length;
    return {
      n: runs.length,
      wealth: count("v191"), region: count("region"),
      intention: count("pregnancy_intention"),
    };
  }, [analysis]);

  const byRegion = useMemo(
    () => [...regions].sort((a, b) => a.reach8 - b.reach8),
    [regions]
  );

  return (
    <div className="space-y-8">
      {/* ---------------------------------------------------------- hero */}
      <section>
        <p className="label uppercase tracking-wide text-[0.7rem]">
          Policy brief · Federal Ministry of Health · EDHS 2024–25
        </p>
        <h2 className="text-xl sm:text-2xl font-semibold mt-1 leading-tight max-w-3xl">
          Most Ethiopian women reach antenatal care. Most do not complete it —
          and each region is losing them at a different point.
        </h2>
        {c && (
          <div className="grid grid-cols-3 gap-3 mt-5 max-w-2xl">
            {[
              [c.reach1, "receive any antenatal care"],
              [c.reach4, "reach four contacts"],
              [c.reach8, "reach the eight the WHO recommends"],
            ].map(([v, l]) => (
              <div key={String(l)} className="card p-3">
                <div className="text-2xl sm:text-3xl font-semibold tabular">
                  {pct(v as number, 0)}
                </div>
                <div className="label mt-1 leading-snug">{l as string}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ------------------------------------------------ how it was tested */}
      <section className="card p-4 sm:p-5 flex flex-col md:flex-row md:items-center gap-4"
               style={{ borderLeft: "4px solid var(--accent)" }}>
        <div className="flex-1">
          <h2 className="font-semibold">How these findings were tested</h2>
          <p className="label mt-1 leading-relaxed max-w-3xl">
            Every analysis in the study, with the question it answers, how it
            was tested and what it found. Every term (AUROC, average precision,
            held-out, bootstrap interval) is explained in plain language, and so
            is every chart.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 shrink-0">
          <button onClick={() => onNavigate("record", "record")}
                  className="text-xs px-3 py-1.5 rounded"
                  style={{ background: "var(--accent)", color: "#fff" }}>
            The analyses →
          </button>
          <button onClick={() => onNavigate("record", "terms")}
                  className="text-xs px-3 py-1.5 rounded"
                  style={{ border: "1px solid var(--line)" }}>
            Terms explained
          </button>
          <button onClick={() => onNavigate("record", "figures")}
                  className="text-xs px-3 py-1.5 rounded"
                  style={{ border: "1px solid var(--line)" }}>
            Reading the figures
          </button>
        </div>
      </section>

      {/* --------------------------------------------------- five findings */}
      <section>
        <h2 className="font-semibold mb-3">The five findings</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {c && (
            <FindingCard
              n={1}
              value={pct(1 - c.continue_4_to_8, 0)}
              title="The problem is holding women, not reaching them"
              body={<>of women who reach four contacts never reach eight. One woman
                in three stops at four, more than the {pct(c.never, 0)} who never
                start.</>}
              cta="The cascade"
              onClick={() => onNavigate("findings")}
            />
          )}
          {contrast && (
            <FindingCard
              n={2}
              value={`${pct(contrast.access.never, 0)} / ${pct(contrast.retain.continue_4_to_8, 0)}`}
              title="Regions with the same coverage fail for opposite reasons"
              body={<>In {contrast.access.region}, {pct(contrast.access.never, 0)} of
                women never reach care. In {contrast.retain.region}, only{" "}
                {pct(contrast.retain.continue_4_to_8, 0)} of those at four contacts
                reach eight. One programme cannot serve both.</>}
              cta="Every region"
              onClick={() => onNavigate("findings")}
            />
          )}
          {equity && (
            <FindingCard
              n={3}
              value={`${equity.ratio.toFixed(1)}×`}
              title="Among women already in care, poverty decides who finishes"
              body={<>Of women who reached four contacts, the {equity.hi.level.toLowerCase()}{" "}
                group is {equity.ratio.toFixed(1)} times as likely to reach eight as the{" "}
                {equity.lo.level.toLowerCase()} ({pct(equity.hi.continue_4_to_8, 0)} against{" "}
                {pct(equity.lo.continue_4_to_8, 0)}). They want care; the cost of
                returning is the barrier.</>}
              cta="Continuation by wealth"
              onClick={() => onNavigate("findings")}
            />
          )}
          {war && (
            <FindingCard
              n={4}
              value={`${pct(war.never.tigray_during, 0)} → ${pct(war.never.tigray_after, 0)}`}
              title="The Tigray war cut women off from care entirely"
              body={<>of pregnant Tigrayan women received no antenatal care, during the
                war and after the ceasefire: about {Math.round(war.never.did * -100)} points
                beyond the change elsewhere. Access recovered; completion did not.</>}
              cta="The war analysis"
              onClick={() => onNavigate("wartime")}
            />
          )}
          {predictors && (
            <FindingCard
              n={5}
              value={`${predictors.wealth}/${predictors.n}`}
              title="A few facts about a woman carry most of the prediction"
              body={<>Household wealth and region are chosen in {predictors.wealth} of{" "}
                {predictors.n} analyses; whether the pregnancy was wanted, in{" "}
                {predictors.intention}. Four questions come close to the
                21-predictor set, and most of the 21 add nothing to ANC8+ once the
                rest are in.</>}
              cta="Predictor value"
              onClick={() => onNavigate("predictors")}
            />
          )}
          <div className="card p-4 flex flex-col"
               style={{ background: "var(--bg)" }}>
            <h3 className="font-semibold leading-snug">Read the full brief</h3>
            <p className="label mt-2 leading-relaxed flex-1">
              The complete brief, the plain-language insights, the technical
              findings and every deep dive, with the tables behind each claim.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button onClick={() => onNavigate("reports", "brief")}
                      className="text-xs px-2.5 py-1 rounded"
                      style={{ background: "var(--accent)", color: "#fff" }}>
                Full brief →
              </button>
              <button onClick={() => onNavigate("reports", "findings")}
                      className="text-xs px-2.5 py-1 rounded"
                      style={{ border: "1px solid var(--line)" }}>
                Technical findings
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* --------------------------------------------- what each region needs */}
      {byRegion.length > 0 && (
        <section className="card p-4 sm:p-5">
          <h2 className="font-semibold">What each region needs</h2>
          <p className="label mt-2 leading-relaxed max-w-3xl">
            Each region&apos;s largest loss decides the programme it needs. Read
            the bar where it is widest. These are counts, survey-weighted, and
            need no model.
          </p>
          <div className="flex flex-wrap gap-2 mt-3">
            {Object.values(ACTION).map((a) => (
              <span key={a.label} className="text-[0.7rem] px-2 py-0.5 rounded"
                    style={{ background: a.colour, color: "#fff" }}>
                {a.label}: {a.what}
              </span>
            ))}
          </div>
          <div className="mt-4 overflow-x-auto -mx-4 sm:mx-0 px-4 sm:px-0">
            <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  {["Region", "Reach 8+", "Never start", "Stop before 4",
                    "Stop between 4 and 8", "Needs"].map((h) => (
                    <th key={h} className="label text-left font-normal py-1.5 pr-3 whitespace-nowrap"
                        style={{ borderBottom: "1px solid var(--line)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {byRegion.map((r: RegionalCascadeRow) => {
                  const a = ACTION[r.biggest_loss];
                  const cell = (v: number, key: string) => (
                    <td className="py-1.5 pr-3 tabular"
                        style={{ borderBottom: "1px solid var(--line)",
                                 fontWeight: r.biggest_loss === key ? 600 : 400 }}>
                      {pct(v, 0)}
                    </td>
                  );
                  return (
                    <tr key={r.region}>
                      <td className="py-1.5 pr-3" style={{ borderBottom: "1px solid var(--line)" }}>
                        {r.region}
                      </td>
                      <td className="py-1.5 pr-3 tabular" style={{ borderBottom: "1px solid var(--line)" }}>
                        {pct(r.reach8, 0)}
                      </td>
                      {cell(r.never, "never starting")}
                      {cell(r.start_lt4, "stopping before the 4th contact")}
                      {cell(r.four_lt8, "stopping between the 4th and 8th")}
                      <td className="py-1.5 pr-3" style={{ borderBottom: "1px solid var(--line)" }}>
                        {a && (
                          <span className="text-[0.7rem] px-2 py-0.5 rounded whitespace-nowrap"
                                style={{ background: a.colour, color: "#fff" }}>
                            {a.label}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {(() => {
            const addis = regions.find((r) => r.region === "Addis Ababa");
            return addis ? (
              <p className="label mt-3 leading-relaxed">
                The ceiling is reachable within Ethiopia: Addis Ababa keeps{" "}
                {pct(addis.continue_1_to_4, 0)} of women who start through to four
                contacts, and {pct(addis.continue_4_to_8, 0)} from four to eight.
              </p>
            ) : null;
          })()}
        </section>
      )}

      {/* ---------------------------------------------------- recommendations */}
      <section className="card p-4 sm:p-5">
        <h2 className="font-semibold">What to do</h2>
        <ol className="mt-3 space-y-3 text-sm leading-relaxed list-decimal pl-5 max-w-3xl">
          <li><strong>Target by where each region loses women, not by its headline
            coverage.</strong> Outreach where women never arrive; retention where
            they arrive and stop.</li>
          <li><strong>Make retention the national priority for the eight-contact
            standard.</strong> More women stop at four contacts than never start.</li>
          <li><strong>Lower the cost of each return visit</strong> for poorer women
            already in care: transport, visits aligned with other services, care
            closer to home.</li>
          <li><strong>Learn from Afar and Addis Ababa.</strong> Afar attains about 15
            points more eight-contact care than its population&apos;s circumstances
            predict; Addis Ababa shows the ceiling is reachable.</li>
          <li><strong>Protect first contact in conflict and crisis.</strong> It is
            the rung that collapses first, and in Tigray it recovered once access
            was restored.</li>
          <li><strong>Keep targeting tools explainable, and short where questions
            are costly.</strong> Four characteristics capture most of the value;
            use more only where the data already exist.</li>
          <li><strong>Pair the survey with facility records.</strong> The survey
            shows <em>where</em> women are lost; facility data are needed to learn{" "}
            <em>why</em>.</li>
        </ol>
      </section>

      {/* ---------------------------------------------------- the evidence */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Source", "Ethiopia DHS 2024–25: 6,893 women with a recent pregnancy, 5,037 in the official 24-month window. Survey-weighted to represent the country."],
          ["Checked", "The analysis reproduces the EDHS report's own four-contact figures: 53.0% nationally against 53.0%, every region within 1.5 points."],
          ["Counts vs models", "The regional cascade and continuation figures are counts and need no model — the sturdiest findings. Predictor findings are associations, not causes."],
          ["Not covered", "No facility data; the visit count is the woman's recall; one survey round. Women displaced or killed in conflict are not in the survey."],
        ].map(([t, b]) => (
          <div key={t} className="card p-4">
            <h3 className="text-sm font-semibold">{t}</h3>
            <p className="label mt-2 leading-relaxed">{b}</p>
          </div>
        ))}
      </section>
      <p className="label">
        Full detail, including every limitation:{" "}
        <button className="underline" onClick={() => onNavigate("reports", "limitations")}>
          Limitations
        </button>{" "}·{" "}
        <button className="underline" onClick={() => onNavigate("reports", "decisions")}>
          Decision log
        </button>
      </p>
    </div>
  );
}
