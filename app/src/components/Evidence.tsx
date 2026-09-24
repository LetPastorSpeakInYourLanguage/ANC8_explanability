"use client";

import { useState } from "react";
import type { Analysis } from "@/lib/analysis";
import { label } from "@/lib/labels";
import {
  Caveat, DivergingRow, Dumbbell, Panel, Stat, Table,
  num, pct, signed, NEG, POS,
} from "./viz";

/**
 * How much of this should be believed.
 *
 * Two questions with different answers, kept apart: whether the full
 * candidate pool beats the 21-predictor set on one held-out set (it cannot be
 * resolved there), and whether it wins in general (it does, on repeated
 * splitting). Showing only the second would be shopping for the evidence
 * that agreed.
 */

function rungLabel(rung: string) {
  return rung.replace("plus", "+").toUpperCase();
}

function Bootstrap({ a, rung }: { a: Analysis; rung: string }) {
  const ci = a.bootstrap[rung];
  if (!ci) return null;
  const spans = !ci.d_AP_excludes_zero;
  return (
    <Panel
      title="On the held-out set, how uncertain is the comparison?"
      term="bootstrap"
      lede={
        <>
          {ci.champion} against {ci.baseline}, on the same 1,375 women.
          Confidence intervals come from resampling <em>clusters</em> within
          strata, not individuals — treating correlated women as independent
          would produce an interval far too narrow to be honest.
        </>
      }
    >
      <div className="grid gap-5 sm:grid-cols-2">
        {([["d_AP", "average precision"], ["d_AUROC", "AUROC"]] as const).map(
          ([key, name]) => {
            const d = ci[key];
            const excludes = ci[`${key}_excludes_zero` as const];
            const span = Math.max(Math.abs(d.lo), Math.abs(d.hi)) * 1.15;
            const toPct = (v: number) => 50 + (v / (span * 2)) * 100;
            return (
              <div key={key}>
                <div className="flex items-baseline justify-between">
                  <span className="text-sm">{name}</span>
                  <span className="tabular text-sm">
                    {signed(d.point)}
                  </span>
                </div>
                <div className="mt-2 h-6 relative">
                  <div
                    className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full"
                    style={{
                      left: `${toPct(d.lo)}%`,
                      width: `${toPct(d.hi) - toPct(d.lo)}%`,
                      background: excludes ? POS : "var(--line)",
                    }}
                  />
                  <div
                    className="absolute top-1/2 h-3 w-3 rounded-full -translate-y-1/2 -translate-x-1/2"
                    style={{ left: `${toPct(d.point)}%`, background: "var(--accent)" }}
                  />
                  <div
                    className="absolute top-0 bottom-0 w-px"
                    style={{ left: "50%", background: NEG }}
                  />
                </div>
                <p className="label text-[0.72rem] mt-1 tabular">
                  95% interval [{signed(d.lo)}, {signed(d.hi)}] ·{" "}
                  {excludes ? "excludes zero" : "includes zero"}
                </p>
              </div>
            );
          }
        )}
      </div>
      {spans && (
        <Caveat>
          The AP interval includes zero. One held-out set of this size cannot
          resolve a difference this small, and no amount of extra modelling
          changes that. This is stated here rather than buried, because the
          alternative — quoting only the evidence that agreed — is how this kind
          of analysis goes wrong. The claim rests on the repeated splitting
          below.
        </Caveat>
      )}
    </Panel>
  );
}

function Stability({ a, rung }: { a: Analysis; rung: string }) {
  const s = a.stability[rung];
  if (!s) return null;
  return (
    <Panel
      title="Does the full candidate pool beat the 21 in general?"
      term="repeated"
      lede={
        <>
          A different question from the one above, with a different answer.
          {" "}
          {s.n_seeds} independent cluster-grouped splits, each refit from
          scratch: the {s.n_original_predictors}-predictor set against the{" "}
          {s.n_enhanced_predictors}-column full pool, using {s.model}.
        </>
      }
    >
      <div className="grid grid-cols-3 gap-4 mb-5">
        <Stat
          value={`${s.AP.seeds_enhanced_better}/${s.n_seeds}`}
          label="splits where the full pool wins on AP"
          tone={s.AP.seeds_enhanced_better === s.n_seeds ? "good" : "plain"}
        />
        <Stat value={signed(s.AP.delta_mean, 4)} label="mean AP gain" />
        <Stat
          value={`[${signed(s.AP.delta_lo, 3)}, ${signed(s.AP.delta_hi, 3)}]`}
          label="range across splits"
        />
      </div>
      <Table
        head={["metric", "21-predictor set", "full pool", "gain", "wins"]}
        rows={(["AP", "AUROC"] as const).map((k) => [
          k,
          num(s[k].original_mean, 4),
          num(s[k].enhanced_mean, 4),
          signed(s[k].delta_mean, 4),
          `${s[k].seeds_enhanced_better}/${s.n_seeds}`,
        ])}
      />
      <Caveat>
        This is the stronger evidence and the one the claim rests on. It is
        not the same thing as a significant result on a held-out set, and the
        two should not be conflated: anyone reading &ldquo;the full pool is
        better&rdquo; should know which of them it means.
      </Caveat>
    </Panel>
  );
}

function Subgroups({ a, rung }: { a: Analysis; rung: string }) {
  const rows = a.subgroups[rung];
  const [variable, setVariable] = useState<string>("all");
  if (!rows?.length) return null;
  const variables = Array.from(new Set(rows.map((r) => r.variable)));
  const shown = rows
    .filter((r) => (variable === "all" ? true : r.variable === variable))
    .filter((r) => r.n >= 40)
    .sort((x, y) => x.V2_AUROC - y.V2_AUROC);
  const lo = Math.min(...shown.flatMap((r) => [r.V1_AUROC, r.V2_AUROC]), 0.45);
  const hi = Math.max(...shown.flatMap((r) => [r.V1_AUROC, r.V2_AUROC]), 0.9);
  const atChance = shown.filter((r) => r.V2_AUROC < 0.55);

  return (
    <Panel
      title="Where the model works, and where it does not"
      term="auroc"
      lede="A national AUROC of about 0.78 can hide subgroups sitting at chance.
            Points are the 21-predictor model and the full-pool model, within
            each subgroup."
      aside={
        <select
          value={variable}
          onChange={(e) => setVariable(e.target.value)}
          className="text-xs"
          style={{ width: "auto", padding: "0.3rem 0.45rem" }}
          aria-label="subgroup variable"
        >
          <option value="all">all subgroups</option>
          {variables.map((v) => (
            <option key={v} value={v}>{v.replace(/_/g, " ")}</option>
          ))}
        </select>
      }
    >
      <div className="flex gap-4 mb-3">
        <span className="label text-[0.7rem] flex items-center gap-1.5">
          <span className="inline-block w-2 h-2 rounded-full"
                style={{ background: "var(--set21)" }} />
          21-predictor set
        </span>
        <span className="label text-[0.7rem] flex items-center gap-1.5">
          <span className="inline-block w-2.5 h-2.5 rounded-full"
                style={{ background: "var(--accent)" }} />
          full pool
        </span>
      </div>
      <div className="space-y-1">
        {shown.map((r) => (
          <Dumbbell
            key={`${r.variable}-${r.level}`}
            label={
              <>
                {r.level}
                <span className="label ml-1.5 text-[0.68rem]">
                  {r.variable.replace(/_/g, " ")}
                </span>
              </>
            }
            a={r.V1_AUROC}
            b={r.V2_AUROC}
            min={lo}
            max={hi}
            note={`n=${r.n} · ${pct(r.weighted_prevalence, 0)} attain`}
          />
        ))}
      </div>
      {atChance.length > 0 && (
        <Caveat>
          {atChance.length} subgroup{atChance.length > 1 ? "s sit" : " sits"} at
          or near chance ({atChance.map((r) => r.level).join(", ")}). Sample
          sizes are small, so these are indicative rather than precise — but a
          model that works nationally and not in the regions with the worst
          coverage is the wrong tool for the places that need it most.
        </Caveat>
      )}
    </Panel>
  );
}

function Preprocessing({ a }: { a: Analysis }) {
  const rows = a.preprocessing;
  if (!rows?.length) return null;
  return (
    <Panel
      title="Did better preprocessing help?"
      term="ablation"
      lede="Imputation and encoding variants, with the predictors, model, folds and
            weights held fixed."
    >
      <div className="space-y-2.5">
        {[...rows]
          .sort((x, y) => y.AP_vs_original - x.AP_vs_original)
          .map((r) => (
            <DivergingRow
              key={r.variant}
              label={r.variant}
              value={r.AP_vs_original}
              scale={Math.max(...rows.map((p) => Math.abs(p.AP_vs_original)), 0.005)}
              display={signed(r.AP_vs_original, 4)}
              note={"AP " + num(r.AP)}
            />
          ))}
      </div>
      <Caveat>
        The best variant buys about +0.003 AP, an order of magnitude less than
        the choice of predictors. Reported because a list of only the wins
        would misrepresent where the gains came from.
      </Caveat>
    </Panel>
  );
}

function Screening({ a }: { a: Analysis }) {
  const s = a.screening;
  if (!s) return null;
  const admitted = s.top.filter((r) => r.screen_status?.includes("candidate"));
  const excluded = s.top.filter((r) => !r.screen_status?.includes("candidate"));
  return (
    <Panel
      title={`All ${s.n_columns.toLocaleString()} survey columns, screened`}
      term="screening"
      lede="Every column of the Individual Recode tested against the outcome on
            the development fold only, then checked by hand for timing,
            availability at prediction time, and sparsity."
    >
      <div className="flex flex-wrap gap-x-6 gap-y-2 mb-5">
        {Object.entries(s.counts).map(([k, v]) => (
          <Stat key={k} value={v.toLocaleString()} label={k} />
        ))}
      </div>

      <Table
        head={["variable", "what it is", "univariate AUC", "admitted?"]}
        rows={s.top.slice(0, 18).map((r) => [
          <span key="v" className="whitespace-nowrap">{r.variable}</span>,
          <span key="l" className="label">{r.label}</span>,
          num(r.weighted_auc),
          r.screen_status?.includes("candidate") ? (
            <span style={{ color: POS }}>yes</span>
          ) : (
            <span style={{ color: NEG }} title={r.exclusion_reason ?? ""}>
              no — {r.exclusion_reason ?? r.screen_status}
            </span>
          ),
        ])}
      />

      <Caveat>
        {excluded.length > 0 && (
          <>
            The excluded rows are the important ones. Several DHS variables
            predict the outcome superbly and are unusable, because they are
            recorded during or after the pregnancy being predicted — a model
            using them would score beautifully and mean nothing.{" "}
          </>
        )}
        {admitted.length} of the strongest candidates passed those checks.
      </Caveat>
    </Panel>
  );
}

function Redundancy({ a }: { a: Analysis }) {
  const r = a.redundancy;
  if (!r?.summary) return null;
  const s = r.summary;
  const moved = (r.grouped ?? []).filter(
    (g) => g.n_members > 1 && g.rank_grouped !== g.rank_as_single_columns
  );
  return (
    <Panel
      title="A defect we found in our own predictor set"
      term="duplicate"
      lede="Screening on univariate strength cannot notice that a variable
            appears twice. The survey ships raw coded columns, this project
            derived relabelled versions, and both ended up in the set."
    >
      <div className="grid grid-cols-3 gap-4 mb-5">
        <Stat value={String(s.n_predictors)} label="columns in the full pool" />
        <Stat
          value={String(s.n_after_deduplication)}
          label="genuinely distinct variables"
        />
        <Stat
          value={signed(-s.AP_cost_of_deduplication, 4)}
          label="AP change from removing the copies"
          tone={s.AP_cost_of_deduplication >= -0.002 ? "good" : "bad"}
        />
      </div>

      {r.pairs && r.pairs.length > 0 && (
        <Table
          head={["one name", "the other", "association", ""]}
          rows={r.pairs.slice(0, 10).map((p) => [
            label(p.a),
            label(p.b),
            num(p.association),
            p.exact_recoding ? (
              <span style={{ color: NEG }}>the same variable</span>
            ) : (
              <span className="label">near-duplicate</span>
            ),
          ])}
        />
      )}

      {moved.length > 0 && (
        <>
          <p className="label mt-5 mb-2">
            What happens to the importance ranking once the copies are added
            back together
          </p>
          <Table
            head={["variable", "grouped", "single column", "rank", "was"]}
            rows={moved.slice(0, 10).map((g) => [
              label(g.group),
              num(g.grouped_importance, 4),
              num(g.largest_single_member, 4),
              g.rank_grouped,
              <span key="w" className="label">{g.rank_as_single_columns}</span>,
            ])}
          />
        </>
      )}

      <Caveat>
        Prediction barely notices. Interpretation notices a great deal:
        per-column importance splits a duplicated variable&apos;s weight between
        its copies, so a &ldquo;top predictors&rdquo; table built without
        checking ranks it below things that matter less. Read importance at the
        group level.
      </Caveat>
    </Panel>
  );
}

export default function Evidence({ analysis }: { analysis: Analysis }) {
  const rungs = analysis.rungs.length ? analysis.rungs : ["anc8plus"];
  const [rung, setRung] = useState(
    rungs.includes("anc8plus") ? "anc8plus" : rungs[0]
  );
  const hasMany = rungs.length > 1;

  return (
    <div className="space-y-6">
      {hasMany && (
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

      <Bootstrap a={analysis} rung={rung} />
      <Stability a={analysis} rung={rung} />
      <Subgroups a={analysis} rung={rung} />
      <Redundancy a={analysis} />
      <Preprocessing a={analysis} />
      <Screening a={analysis} />

      <section className="card p-4 sm:p-5">
        <h2 className="font-semibold">What this analysis cannot support</h2>
        <ul className="mt-3 space-y-2 text-sm leading-relaxed list-disc pl-5">
          <li>
            <strong>Nothing here is causal.</strong> The models describe which
            women attained care, not what would happen if a woman&apos;s
            circumstances changed.
          </li>
          <li>
            <strong>No external validation.</strong> One survey round, one
            country. No later round to test on, no other data source, no
            prospective evaluation.
          </li>
          <li>
            <strong>The outcome is recalled.</strong> The contact count comes
            from the woman&apos;s memory at interview, possibly years later, and
            recall error is unlikely to be random.
          </li>
          <li>
            <strong>An equity problem the model does not solve.</strong> The
            woman&apos;s first language is among the strongest predictors and is
            roughly three-quarters concentrated by region, so it largely stands
            in for geography and ethnicity. Dropping it costs about 0.003 AP. It
            is kept and flagged rather than quietly removed, because the
            decision belongs to whoever deploys this.
          </li>
          <li>
            <strong>No facility data at all.</strong> Nothing about what
            happened at any contact — quality, waiting time, cost, staff. So the
            analysis can say where in the cascade women are lost and not why.
          </li>
        </ul>
      </section>
    </div>
  );
}
