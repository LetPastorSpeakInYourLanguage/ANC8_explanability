"use client";

import type { Wartime } from "@/lib/analysis";
import { Caveat, DivergingRow, Dumbbell, Panel, Table, pct, signed } from "./viz";

/**
 * Antenatal care for pregnancies that overlapped the Tigray war.
 *
 * Exposure is assigned by the calendar window of each pregnancy, and the
 * estimate is a difference-in-differences: the change in Tigray from wartime
 * to post-war pregnancies, minus the within-region change in peaceful regions
 * over the same calendar periods. The peaceful regions absorb the national
 * trend and the extra recall error of older births.
 */

const NAMES: Record<string, string> = {
  anc1plus: "Any antenatal care (ANC1+)",
  anc4plus: "Four or more contacts (ANC4+)",
  anc8plus: "Eight or more contacts (ANC8+)",
  never: "Never received any antenatal care",
  start_lt4: "Started, stopped before 4",
  four_lt8: "Reached 4, stopped before 8",
};

/** Tigray against every region over the same two calendar periods. */
function Regions({ data }: { data: Wartime }) {
  const rows = data.by_war_period ?? [];
  if (!rows.length) return null;
  const regions = Array.from(new Set(rows.map((r) => r.region)));
  const get = (reg: string, per: string) => rows.find((r) => r.region === reg && r.period === per);
  const change = (reg: string) => (get(reg, "after")?.anc4plus ?? 0) - (get(reg, "during")?.anc4plus ?? 0);
  const ordered = [...regions].sort((a, b) => change(b) - change(a));
  return (
    <div className="mt-6">
      <h3 className="text-sm font-medium mb-1">Tigray against every region, same periods</h3>
      <p className="label mb-2 leading-relaxed">
        Pregnancies with at least three months inside the war window against
        those conceived after the ceasefire, in every region. Sorted by the
        change in ANC4+.
      </p>
      <Table
        head={["region", "n (wartime / post-war)", "no ANC", "ANC4+", "ANC8+", "ANC4+ change"]}
        rows={ordered.map((reg) => {
          const d = get(reg, "during");
          const a = get(reg, "after");
          const name = reg === "Tigray" ? <strong key="n">{reg}</strong> : reg;
          return [
            name,
            `${d?.n ?? "—"} / ${a?.n ?? "—"}`,
            `${pct(d?.never, 0)} → ${pct(a?.never, 0)}`,
            `${pct(d?.anc4plus, 0)} → ${pct(a?.anc4plus, 0)}`,
            `${pct(d?.anc8plus, 0)} → ${pct(a?.anc8plus, 0)}`,
            signed(change(reg) * 100, 1),
          ];
        })}
      />
    </div>
  );
}

export default function WartimeView({ data }: { data: Wartime }) {
  const main = (data.did ?? []).filter(
    (d) => d.window_shift_months === 0 && d.controls === "peaceful regions"
  );
  if (!main.length) return null;
  const by = Object.fromEntries(main.map((d) => [d.measure, d]));
  const order = ["anc1plus", "anc4plus", "anc8plus", "never", "start_lt4", "four_lt8"]
    .filter((m) => by[m]);
  const scale = Math.max(...order.map((m) => Math.max(Math.abs(by[m].lo), Math.abs(by[m].hi))));
  const robust = (data.did ?? []).filter((d) => d.measure === "anc4plus");
  const rmin = Math.min(...robust.map((d) => d.did));
  const rmax = Math.max(...robust.map((d) => d.did));
  const gaps = (data.regional_gap ?? []).filter((g) => g.region === "Tigray");
  const gap = (cohort: string, o: string) => gaps.find((g) => g.cohort === cohort && g.outcome === o);
  const n1 = main[0].tigray_during_n;
  const n2 = main[0].tigray_after_n;

  return (
    <Panel
      title="Births during the conflict: what the Tigray war did to antenatal care"
      term="did"
      lede={
        <>
          Tigrayan women whose pregnancy ran at least three months inside the war
          (Nov 2020 – Nov 2022, n={n1}) against those who conceived after the
          ceasefire (n={n2}). Peaceful regions over the same calendar periods
          supply the comparison, so the national trend and the fading memory of
          older births are taken out.
        </>
      }
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="text-sm font-medium mb-2">Tigray, before and after the ceasefire</h3>
          <div className="space-y-1">
            {order.map((m) => (
              <Dumbbell
                key={m}
                label={NAMES[m]}
                a={by[m].tigray_during}
                b={by[m].tigray_after}
                min={0}
                max={1}
                aLabel="wartime pregnancy"
                bLabel="post-war pregnancy"
              />
            ))}
          </div>
          <p className="label mt-2 text-[0.7rem]">
            left point wartime, right point post-war; values are shares of women
          </p>
        </div>
        <div>
          <h3 className="text-sm font-medium mb-2">
            Change beyond the change elsewhere (percentage points, 95% interval)
          </h3>
          <div className="space-y-2.5">
            {order.map((m) => (
              <DivergingRow
                key={m}
                label={NAMES[m]}
                value={by[m].did}
                scale={scale}
                display={`${signed(by[m].did * 100, 1)} [${signed(by[m].lo * 100, 1)}, ${signed(by[m].hi * 100, 1)}]`}
              />
            ))}
          </div>
        </div>
      </div>

      <div
        className="mt-5 p-3 rounded-lg text-sm leading-relaxed"
        style={{ background: "var(--bg)", border: "1px solid var(--line)" }}
      >
        During the war, <strong>{pct(by.never?.tigray_during, 0)}</strong> of pregnant
        women in Tigray never received any antenatal care. After the ceasefire it
        was <strong>{pct(by.never?.tigray_after, 0)}</strong>. The damage was at the
        door: women cut off from care entirely. Completing the full eight
        contacts barely moved either way ({signed((by.anc8plus?.did ?? 0) * 100, 1)} points,
        an interval that includes zero), so recovery restored access without
        yet restoring the full schedule.
        {robust.length > 1 && (
          <> Moving the war window three months either way, or changing the
          comparison regions, keeps the ANC4+ effect between{" "}
          {signed(rmin * 100, 0)} and {signed(rmax * 100, 0)} points.</>
        )}
      </div>

      <Regions data={data} />

      {gaps.length > 0 && (
        <div className="mt-5">
          <h3 className="text-sm font-medium mb-1">
            Post-war Tigray against its own circumstances
          </h3>
          <p className="label mb-2 leading-relaxed">
            Attainment predicted from wealth, education and household factors
            with region withheld, compared with what happened.
          </p>
          <Table
            head={["", "all births", "post-war pregnancies only", "last 24 months (sensitivity)"]}
            rows={["anc1plus", "anc4plus", "anc8plus"].map((o) => [
              NAMES[o],
              gap("full", o) ? signed(gap("full", o)!.gap * 100, 1) : "—",
              gap("post-war pregnancies", o) ? signed(gap("post-war pregnancies", o)!.gap * 100, 1) : "—",
              gap("recent", o) ? signed(gap("recent", o)!.gap * 100, 1) : "—",
            ])}
            note="Points above (+) or below (-) what the region's population profile implies.
                  After the war Tigray does better than expected at getting women to care,
                  and still falls short on completing it."
          />
        </div>
      )}

      <Caveat>
        This describes women who were interviewed. Women displaced out of the
        region or who died are not in the survey, and some enumeration areas
        were excluded for security reasons -- plausibly the worst-affected, so the
        wartime shortfall is more likely understated than overstated. Wealth and
        distance mattered as much during the war as after it (no detectable
        change in either effect), though with about 580 Tigrayan women the test
        can only rule out large changes. The 2021 incursion into Afar and Amhara
        affected too few births in this survey window to analyse. The survey
        records antenatal care only for births from about mid-2021, so no
        pre-war Tigrayan pregnancy is observed: the comparison is wartime
        against post-war.
      </Caveat>
    </Panel>
  );
}
