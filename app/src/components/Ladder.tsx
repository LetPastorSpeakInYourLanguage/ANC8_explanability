"use client";

import { label, DOMAIN_COLORS } from "@/lib/labels";
import type { Insights } from "@/lib/types";
import type { Analysis, MatrixRow } from "@/lib/analysis";
import { Caveat, Panel, Table, num, pct } from "./viz";

/**
 * The ladder view: how predictor importance shifts from "reached antenatal
 * care at all" to "completed the full eight-contact schedule".
 *
 * The question the three-rung analysis exists to answer.
 * Predictors are labelled access-limited (they matter more for first contact)
 * or engagement-limited (they matter more for completing the schedule), and
 * only patterns that at least two independent importance methods agree on are
 * shown at all.
 */

const RUNGS = ["anc1plus", "anc4plus", "anc8plus"];

/**
 * The cross-rung performance comparison, which can be shown from the
 * leaderboards alone -- before the importance analysis that needs all three
 * rungs has run. It carries the single most misreadable number in the project,
 * so it is worth showing early rather than waiting.
 */
function RungPerformance({ analysis }: { analysis: Analysis }) {
  const rows = RUNGS.filter((r) => analysis.leaderboard?.[r]?.length).map((r) => {
    // The development champion: ranking by held-out score would make the
    // comparison optimistic, because the held-out women would pick the model.
    const board = analysis.leaderboard[r]
      .filter((m) => m.held_AP != null && m.dev_AP != null)
      .sort((a, b) => (b.dev_AP ?? 0) - (a.dev_AP ?? 0));
    const best = board[0];
    const prev = analysis.outcomes?.[r]?.weighted_prevalence ?? null;
    return { rung: r, best, prev };
  }).filter((x) => x.best && x.prev != null);

  if (rows.length < 2) return null;

  return (
    <Panel
      title="The same model, measured at each rung"
      term="auroc"
      lede="All three rungs share one split, one set of folds and one predictor
            set, so any difference between them is the outcome and not the data."
    >
      <Table
        head={["rung", "model (dev champion)", "attain it", "AP", "AP lift", "AUROC"]}
        rows={rows.map(({ rung, best, prev }) => [
          rung.replace("plus", "+").toUpperCase(),
          best!.model,
          pct(prev),
          <span key="ap" style={{ color: "var(--muted)" }}>
            {num(best!.held_AP)}
          </span>,
          `+${num((best!.held_AP ?? 0) - (prev ?? 0))}`,
          num(best!.held_AUROC),
        ])}
      />
      <Caveat>
        Average precision cannot be compared between rungs. Its floor is the
        attainment rate, so a model with no signal at all would
        &ldquo;score&rdquo; about four times higher on ANC1+ than on ANC8+. Read
        the AUROC column instead: it still falls from reaching care to completing
        it, so completing care is genuinely harder to predict, just not by as
        much as raw AP suggests.
      </Caveat>
    </Panel>
  );
}

/**
 * Each predictor's value relative to the 21-predictor set, at every rung, on
 * one scale: the AP it adds (or, for a member of the 21, loses when dropped)
 * as a share of that rung's ceiling above prevalence.
 */
function PredictorMatrix({ rows }: { rows: MatrixRow[] }) {
  const byPred = new Map<string, Record<string, MatrixRow>>();
  rows.forEach((r) => {
    const m = byPred.get(r.predictor) ?? {};
    m[r.rung] = r;
    byPred.set(r.predictor, m);
  });
  const val = (m: Record<string, MatrixRow>, r: string) => m[r]?.marginal_share ?? null;
  const ranked = Array.from(byPred.entries())
    .map(([p, m]) => ({ p, m, top: Math.max(...RUNGS.map((r) => val(m, r) ?? -1)) }))
    .sort((a, b) => b.top - a.top)
    .slice(0, 20);
  const cell = (v: number | null, tier: string | null | undefined) => {
    if (v == null) return "—";
    const t = tier === "tier 1" ? " T1" : tier === "tier 2" ? " T2" : "";
    const strong = v >= 0.03;
    return (
      <span className="tabular" style={{ color: v <= 0 ? "var(--muted)" : undefined,
                                         fontWeight: strong ? 600 : 400 }}>
        {(v * 100).toFixed(1)}%{t}
      </span>
    );
  };
  return (
    <Panel
      title="Each predictor's value, from reaching care to completing it"
      term="add-one"
      lede="For members of the 21, the AP lost when dropped from it; for the rest,
            the AP gained when added to it. Shown as a share of each rung's
            ceiling (full-pool AP minus prevalence), so rungs can be compared.
            T1 / T2 = selected in tier 1 / tier 2 at that rung."
    >
      <Table
        head={["predictor", "in the 21", "ANC1+", "ANC4+", "ANC8+", "shift ANC1+ → ANC8+"]}
        rows={ranked.map(({ p, m }) => {
          const a = val(m, "anc1plus");
          const b = val(m, "anc8plus");
          return [
            label(p),
            m.anc8plus?.in_21 || m.anc1plus?.in_21 ? "yes" : "",
            cell(a, m.anc1plus?.tier),
            cell(val(m, "anc4plus"), m.anc4plus?.tier),
            cell(b, m.anc8plus?.tier),
            a != null && b != null ? `${((b - a) * 100).toFixed(1)} pts` : "—",
          ];
        })}
      />
      <Caveat>
        A predictor that duplicates another shows little value here, because
        the other carries its signal; the importance methods above count
        duplicates once and are the better guide to what a model uses.
      </Caveat>
    </Panel>
  );
}

export default function Ladder({
  data,
  analysis,
}: {
  data: Insights;
  analysis?: Analysis;
}) {
  if (!data.ladder_patterns?.length) {
    return (
      <div className="space-y-6">
        {analysis && <RungPerformance analysis={analysis} />}
        <div className="card p-5">
          <h2 className="font-semibold">
            How importance shifts along the ladder
          </h2>
          <p className="label mt-2 leading-relaxed max-w-2xl">
            This panel compares what predicts reaching antenatal care at all
            against what predicts completing the full schedule, with importance
            computed three independent ways and only patterns that at least two
            of them agree on reported. It appears once all three rungs have been
            modelled and the cross-outcome analysis has run.
          </p>
          {analysis && (
            <p className="label mt-3">
              Rungs evaluated so far:{" "}
              {RUNGS.filter((r) => analysis.leaderboard?.[r]?.length)
                .map((r) => r.replace("plus", "+").toUpperCase())
                .join(", ") || "none"}
              .
            </p>
          )}
        </div>
      </div>
    );
  }

  const access = data.ladder_patterns.filter((p) => p.pattern === "access-limited");
  const engagement = data.ladder_patterns.filter(
    (p) => p.pattern === "engagement-limited"
  );
  const perf = data.ladder_performance ?? [];
  const roll = data.domain_rollup ?? {};

  const maxShift = Math.max(
    ...data.ladder_patterns.map((p) => Math.abs(p.mean_share_shift)),
    0.001
  );

  const PatternList = ({
    items,
    title,
    blurb,
    accent,
  }: {
    items: typeof access;
    title: string;
    blurb: string;
    accent: string;
  }) => (
    <div className="card p-4">
      <h3 className="font-semibold text-sm" style={{ color: accent }}>
        {title}
      </h3>
      <p className="label mt-1 mb-4 leading-relaxed">{blurb}</p>
      {items.length === 0 && (
        <p className="label">No predictor showed this pattern consistently.</p>
      )}
      {items.slice(0, 12).map((p) => (
        <div key={p.predictor} className="mb-2.5">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-[0.82rem]">{label(p.predictor)}</span>
            <span className="label tabular text-[0.7rem]">
              {p.methods_agreeing}/{p.methods_total} methods
            </span>
          </div>
          <div
            className="mt-1 h-1.5 rounded-full"
            style={{ background: "var(--line)" }}
          >
            <div
              className="h-1.5 rounded-full"
              style={{
                width: `${(Math.abs(p.mean_share_shift) / maxShift) * 100}%`,
                background: DOMAIN_COLORS[p.domain] ?? accent,
              }}
            />
          </div>
          <p className="label text-[0.68rem] mt-0.5">{p.domain}</p>
        </div>
      ))}
    </div>
  );

  return (
    <div className="space-y-6">
      <section className="card p-4 sm:p-5">
        <h2 className="font-semibold">
          Does reaching care need the same things as completing the schedule?
        </h2>
        <p className="label mt-2 leading-relaxed max-w-3xl">
          ANC1+, ANC4+ and ANC8+ are the same women, the same predictors and the
          same folds — three rungs of one ladder. Comparing what each rung
          depends on separates a problem of <strong>access</strong> from a
          problem of <strong>sustained engagement</strong>, which call for
          different responses.
        </p>

        {perf.length > 0 && (
          <div className="mt-5 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="label text-left">
                  <th className="pb-2 pr-4 font-normal">Rung</th>
                  <th className="pb-2 pr-4 font-normal">Attain it</th>
                  <th className="pb-2 pr-4 font-normal">AUROC</th>
                  <th className="pb-2 pr-4 font-normal">AP</th>
                  <th className="pb-2 font-normal">AP lift</th>
                </tr>
              </thead>
              <tbody className="tabular">
                {perf.map((r) => (
                  <tr key={r.outcome} style={{ borderTop: "1px solid var(--line)" }}>
                    <td className="py-2 pr-4">{r.rung}</td>
                    <td className="py-2 pr-4">
                      {(r.weighted_prevalence * 100).toFixed(1)}%
                    </td>
                    <td className="py-2 pr-4">{r.AUROC.toFixed(3)}</td>
                    <td className="py-2 pr-4" style={{ color: "var(--muted)" }}>
                      {r.AP.toFixed(3)}
                    </td>
                    <td className="py-2">
                      +{r.AP_lift_over_prevalence.toFixed(3)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="label mt-2 leading-relaxed">
              Average Precision cannot be compared between rungs — its floor is
              the attainment rate, so a model with no signal would &ldquo;score&rdquo;
              four times higher on ANC1+ than on ANC8+. Read AUROC, or AP lift
              above that floor.
            </p>
          </div>
        )}
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        <PatternList
          items={access}
          title="Matters more for reaching care at all"
          blurb="Importance falls as the threshold rises — these shape whether a woman gets through the door."
          accent="var(--warn)"
        />
        <PatternList
          items={engagement}
          title="Matters more for completing the schedule"
          blurb="Importance rises as the threshold rises — these shape whether she keeps coming back."
          accent="var(--accent)"
        />
      </div>

      {Object.keys(roll).length > 0 && (
        <section className="card p-4 sm:p-5">
          <h3 className="font-semibold text-sm">By domain</h3>
          <p className="label mt-1 mb-4 leading-relaxed">
            Share of total importance at each rung. Individual predictors
            reorder noisily; domains are where a real shift shows up.
          </p>
          {Object.entries(roll)
            .sort((a, b) => (b[1][RUNGS[2]] ?? 0) - (a[1][RUNGS[2]] ?? 0))
            .map(([domain, shares]) => (
              <div key={domain} className="mb-3">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[0.82rem]">{domain}</span>
                  <span className="label tabular text-[0.7rem]">
                    {RUNGS.map((r) =>
                      shares[r] != null ? (shares[r] * 100).toFixed(0) + "%" : "—"
                    ).join("  →  ")}
                  </span>
                </div>
                <div className="flex gap-1 mt-1">
                  {RUNGS.map((r) => (
                    <div
                      key={r}
                      className="h-2 rounded-full flex-1"
                      style={{ background: "var(--line)" }}
                    >
                      <div
                        className="h-2 rounded-full"
                        style={{
                          width: `${Math.min(100, (shares[r] ?? 0) * 300)}%`,
                          background: DOMAIN_COLORS[domain] ?? DOMAIN_COLORS.Other,
                        }}
                      />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          <p className="label mt-3">ANC1+ → ANC4+ → ANC8+</p>
        </section>
      )}
      {analysis?.predictor_matrix && <PredictorMatrix rows={analysis.predictor_matrix} />}
    </div>
  );
}
