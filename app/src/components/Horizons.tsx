"use client";

import type { Horizons } from "@/lib/analysis";
import { label } from "@/lib/labels";
import { Caveat, Panel, Table, num, signed } from "./viz";

/**
 * The two prediction horizons.
 *
 * Before ANC starts, a prediction can use only what is known about the woman
 * and her household. At ANC entry it can also use when the first contact
 * happened. The same questions are asked at both: which predictors carry the
 * prediction, and what the timing of the first contact adds on top. ANC entry
 * covers ANC4+ and ANC8+ only, because every woman in it has ANC1+.
 */

const RUNG: Record<string, string> = { anc4plus: "ANC4+", anc8plus: "ANC8+" };
const SET: Record<string, string> = {
  "21": "21-predictor set", "tier set": "selected set", "full pool": "full pool",
};

function interval(b?: { d_AP: number; d_AP_lo: number; d_AP_hi: number;
                        d_AUROC: number; d_AUROC_lo: number; d_AUROC_hi: number },
                  key: "AP" | "AUROC" = "AP") {
  if (!b) return "—";
  const k = `d_${key}` as const;
  return `${signed(b[k])} [${signed(b[`${k}_lo` as const])}, ${signed(b[`${k}_hi` as const])}]`;
}

export default function HorizonsView({ data }: { data: Horizons }) {
  const boot = data.bootstrap ?? {};
  const rungs = ["anc4plus", "anc8plus"].filter(
    (r) => (data.early_anc ?? []).some((x) => x.outcome === r));

  return (
    <div className="space-y-6">
      <Panel
        title="Two horizons: before ANC starts, and at ANC entry"
        term="horizon"
        lede="Before ANC, a prediction can use only who the woman is and where she
              lives. Once she has started, it can also use whether her first contact
              came early (by 12 weeks or 3 months). The same predictor-value study
              is run at both horizons, on the same development and held-out split."
      >
        {data.tiers && (
          <Table
            head={["outcome", "horizon", "tier 1", "tier 2", "21-predictor set", "full pool"]}
            rows={rungs.flatMap((r) => ["before ANC", "ANC entry"].map((h) => {
              const t = (data.tiers ?? []).filter((x) => x.outcome === r && x.horizon === h)
                .sort((a, b) => a.step - b.step);
              if (!t.length) return [RUNG[r], h, "—", "—", "—", "—"];
              return [
                RUNG[r], h,
                t.filter((x) => x.tier === "tier 1").map((x) => label(x.predictor)).join(", "),
                t.filter((x) => x.tier === "tier 2").map((x) => label(x.predictor)).join(", ") || "—",
                num(t[0].set21_AP),
                num(t[0].all_pool_AP),
              ];
            }))}
            note="Forward selection at each horizon, in order; development AP. At ANC entry
                  the pool also contains early ANC."
          />
        )}
      </Panel>

      {data.early_anc && (
        <Panel
          title="What knowing the first contact was early adds"
          term="heldout"
          lede="Early ANC added to the 21, to the selected set and to the full pool:
                on development folds, then once on the 984 held-out women who
                started ANC."
        >
          <Table
            head={["outcome", "added to", "development AP", "gain (splits)",
                   "held-out ΔAP [95%]", "held-out ΔAUROC [95%]"]}
            rows={(data.early_anc ?? []).map((x) => [
              RUNG[x.outcome] ?? x.outcome,
              SET[x.base] ?? x.base,
              `${num(x.AP_without)} → ${num(x.AP_with)}`,
              `${signed(x.gain, 4)} (${x.seeds_positive}/5)`,
              interval(boot[`${x.outcome} | ${x.base} + early ANC vs ${x.base}`]),
              interval(boot[`${x.outcome} | ${x.base} + early ANC vs ${x.base}`], "AUROC"),
            ])}
          />
        </Panel>
      )}

      {data.cross && (
        <Panel
          title="Is a separate model for the entry horizon worth building?"
          term="paired"
          lede="The same predictor sets fitted on all women (before ANC) and on the
                women who started ANC, both scored on the same held-out women who
                started ANC. Neither uses early ANC."
        >
          <Table
            head={["outcome", "set", "fitted before ANC: AP / AUROC",
                   "fitted at entry: AP / AUROC", "ΔAUROC [95%]"]}
            rows={rungs.flatMap((r) => ["21", "full pool"].map((s) => {
              const rows = (data.cross ?? []).filter((x) => x.outcome === r && x.set === s);
              const f = rows.find((x) => x.trained_on === "full-cohort development");
              const e = rows.find((x) => x.trained_on === "ANC-entry development");
              return [
                RUNG[r], SET[s] ?? s,
                f ? `${num(f.AP)} / ${num(f.AUROC)}` : "—",
                e ? `${num(e.AP)} / ${num(e.AUROC)}` : "—",
                interval(boot[`${r} | ${s}: entry-trained vs full-cohort-trained`], "AUROC"),
              ];
            }))}
          />
          <Caveat>
            984 held-out women, of whom about a quarter reach ANC8+. Intervals
            that include zero mean the held-out set cannot tell the two apart.
          </Caveat>
        </Panel>
      )}
    </div>
  );
}
