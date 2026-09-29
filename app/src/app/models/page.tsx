"use client";

import Link from "next/link";
import { useMemo } from "react";
import DotRows from "@/components/charts/DotRows";
import MatrixHeat from "@/components/charts/MatrixHeat";
import RankedBars from "@/components/charts/RankedBars";
import { Calibration, Decisions } from "@/components/models/Calibration";
import Curves from "@/components/models/Curves";
import Tuning from "@/components/models/Tuning";
import { useRenderTheme } from "@/components/shell/theme-provider";
import { Select } from "@/components/ui/select";
import {
  DataNote, InlineError, Note, Panel, PanelLoading, Picker, Screen, Segmented, StatTile, Tag,
} from "@/components/studio/ui";
import { useJSON } from "@/lib/data";
import { RUNG_LABEL, num, signed } from "@/lib/explore";
import { label } from "@/lib/labels";
import {
  GROUPS, MODELS_INDEX, SETS, SET_SHORT, bestAt, setFile, type Card, type ModelsIndex, type ModelsSet,
} from "@/lib/modelCards";
import { RUNGS, useStudio, type Rung } from "@/lib/studio";

const pct = (v: number, d = 0) => `${(v * 100).toFixed(d)}%`;
const DIMS = [
  { key: "region", label: "Region" },
  { key: "wealth", label: "Wealth" },
  { key: "education", label: "Education" },
  { key: "residence", label: "Residence" },
] as const;

export default function ModelAnalysisPage() {
  const studio = useStudio();
  const theme = useRenderTheme();
  // The index ranks every model; the full cards come one predictor set at a time.
  const setParam = studio.params.get("set") ?? "pool";
  const index = useJSON<ModelsIndex>(MODELS_INDEX);
  const setData = useJSON<ModelsSet>(setFile(setParam));

  const rung = studio.rung;
  const dim = (studio.params.get("dim") ?? "region") as (typeof DIMS)[number]["key"];

  const err = index.error ?? setData.error;
  const d = index.data;
  const S = setData.data;

  // Models are asked for by family (the slug), so switching the predictor set keeps
  // the same model in view.
  const view = useMemo(() => {
    if (!d) return null;
    const sets = d.meta.sets.map((x) => x.key);
    const setAsked = studio.params.get("set") ?? "";
    const set = sets.includes(setAsked) && SETS.includes(setAsked) ? setAsked : "pool";
    const slug = (studio.params.get("model") ?? "").replace(/^[a-z0-9]+\./, "");
    const asked = slug ? `${set}.${slug}` : "";
    const best = bestAt(d, rung, set);
    const key = d.summary[asked]?.[rung] ? asked : best;
    const vsSlug = studio.params.get("vs") ?? "";
    const vsAsked = vsSlug ? `${set}.${vsSlug}` : "";
    const vsKey = vsAsked && vsAsked !== key && d.summary[vsAsked]?.[rung] ? vsAsked : "";
    return { set, asked, best, key, vsKey };
  }, [d, studio.params, rung]);

  if (err) return <Screen><InlineError message={err} /></Screen>;
  if (!d || !view || !S?.cards[view.key]?.[rung]) return <Screen><PanelLoading rows={8} /></Screen>;

  const { set, key, vsKey, best, asked } = view;
  const fam = d.families[key];
  const card = S.cards[key][rung]!;
  const vs: Card | null = vsKey ? S.cards[vsKey]?.[rung] ?? null : null;
  const vsName = vsKey ? d.families[vsKey].name : null;
  const rl = RUNG_LABEL[rung];

  const inSet = Object.keys(d.families).filter((k) => d.families[k].set === set);
  const available = inSet.filter((k) => d.summary[k]?.[rung]);
  const byGroup = GROUPS.map((g) => ({
    g,
    items: available.filter((k) => d.families[k].group === g).sort((a, b) => d.summary[b][rung]!.ap - d.summary[a][rung]!.ap),
  })).filter((x) => x.items.length);

  const pick = (k: string) => studio.set({ model: d.families[k].slug });
  const who = card.target === "miss" ? `miss ${rl}` : `reach ${rl}`;
  const slopeTone = card.slope < 0.8 || card.slope > 1.25 ? "warn" : "good";

  // every model at this rung, against chance
  const ranked = available.map((k) => ({ k, c: d.summary[k][rung]! })).sort((a, b) => b.c.ap - a.c.ap);

  const sub = card.subgroups[dim];
  const own = Object.entries(d.summary[key]).map(([r, c]) => ({ r: r as Rung, c: c! }));

  const paired = [card.vs_best, card.vs_logistic].filter((p): p is NonNullable<typeof p> => !!p);
  const pairedRows = paired.flatMap((p) => [
    { key: `${p.key}-ap`, label: `Avg precision · vs ${p.vs}`, v: p.ap, lo: p.ap_ci[0], hi: p.ap_ci[1] },
    { key: `${p.key}-au`, label: `AUROC · vs ${p.vs}`, v: p.auroc, lo: p.auroc_ci[0], hi: p.auroc_ci[1] },
  ]);

  // Importance shares: the study's own explainable boosting and XGBoost fits on the pool,
  // limited to the predictors this model uses.
  const shares = card.shares?.rows ?? [];
  const shareKey = card.shares?.kind ?? null;

  return (
    <Screen>
      <div data-help="analysis.picker" className="flex flex-wrap items-center gap-10">
        <Select
          aria-label="Model"
          value={key}
          onChange={(e) => pick(e.target.value)}
          className="w-auto min-w-[260px] h-25 text-11.5 font-medium"
        >
          {byGroup.map(({ g, items }) => (
            <optgroup key={g} label={g}>
              {items.map((k) => (
                <option key={k} value={k}>{d.families[k].name}</option>
              ))}
            </optgroup>
          ))}
        </Select>
        <Segmented label="Predictors" options={d.meta.sets.map((x) => ({ key: x.key, label: SET_SHORT[x.key] ?? x.label }))} value={set} onChange={(k) => studio.set({ set: k })} />
        <Segmented label="Rung" options={RUNGS.map((r) => ({ key: r.key, label: r.label }))} value={rung} onChange={(k) => studio.set({ rung: k })} />
        <label className="flex items-center gap-6 text-10.5 text-dim">
          Compare
          <Select
            aria-label="Compare with"
            value={vsKey}
            onChange={(e) => studio.set({ vs: e.target.value ? d.families[e.target.value].slug : "" })}
            className="w-auto min-w-[180px] h-22 text-10.5"
          >
            <option value="">nothing</option>
            {available.filter((k) => k !== key).map((k) => (
              <option key={k} value={k}>{d.families[k].name}</option>
            ))}
          </Select>
        </label>
        <span className="flex gap-4 ml-auto">
          {best === key && <Tag tone="good">best at {rl}</Tag>}
          <Tag tone="neutral">{fam.group}</Tag>
          <Tag tone="cross">{card.n_predictors} predictors</Tag>
        </span>
      </div>
      {asked && asked !== key && (
        <Note tone="accent">{d.families[asked]?.name ?? asked.replace(/^[a-z0-9]+\./, "")} is not in the library for this set at {rl}. Showing {fam.name}.</Note>
      )}

      <div data-help="analysis.tiles" className="grid gap-10 grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="Average precision"
          value={num(card.ap, 3)}
          tone="accent"
          sub={<>chance {num(card.prevalence, 3)} · <span className="font-mono">×{card.ratio.toFixed(1)}</span> · 95% {num(card.ap_ci[0], 2)}–{num(card.ap_ci[1], 2)}</>}
        />
        <StatTile
          label="AUROC"
          value={num(card.auroc, 3)}
          tone="accent"
          sub={<>chance 0.500 · 95% {num(card.auroc_ci[0], 2)}–{num(card.auroc_ci[1], 2)}</>}
        />
        <StatTile
          label={`Top 20% hold`}
          value={pct(card.top20)}
          tone="good"
          sub={`of women who ${who} · chance 20%`}
        />
        <StatTile
          label="Calibration slope"
          value={num(card.slope, 2)}
          tone={slopeTone}
          sub={card.slope < 0.9 ? "1 is honest · too confident" : card.slope > 1.1 ? "1 is honest · too cautious" : "1 is honest · close"}
        />
      </div>

      <div className="grid gap-10 md:gap-14 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <Curves card={card} vs={vs} name={fam.name} vsName={vsName} />
        <div className="flex flex-col gap-10 md:gap-14 min-w-0">
          <Calibration card={card} name={fam.name} />
        </div>
      </div>

      <div className="grid gap-10 md:gap-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
        <Decisions card={card} />
        <Tuning card={card} fam={fam} />
      </div>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-2">
        <Panel help="analysis.where-works"
          title={`Where it works · AUROC`}
          how="Held-out AUROC inside each group, against the model's overall AUROC (dashed). Groups with fewer than 25 women, or with only one outcome, are left out. Small groups are noisy."
          actions={<Picker label="Group by" options={DIMS.map((x) => ({ key: x.key, label: x.label }))} value={dim} onChange={(k) => studio.set({ dim: k })} />}
        >
          <DotRows
            rows={sub.map((c) => ({ key: c.level, label: c.level, sub: `${c.n} women`, values: { a: c.auroc }, muted: c.n < 60 }))}
            series={[{ key: "a", label: "AUROC", color: "var(--accent)" }]}
            reference={{ value: card.auroc, label: "Overall" }}
            format={(v) => v.toFixed(2)}
            labelWidth={150}
          />
          <DataNote>Faded rows have under 60 women. More held-out women per group would tighten every dot.</DataNote>
        </Panel>

        <Panel help="analysis.dev-held"
          title="Development against held-out"
          how="Rings: cross-validated accuracy on the development women, which tuning saw. Dots: the held-out women, which nothing saw until the end. A long line from ring to dot is optimism."
        >
          <DotRows
            rows={own.map(({ r, c }) => ({
              key: r,
              label: RUNG_LABEL[r],
              sub: `rank ${c.rank} of ${c.of}`,
              values: { dev: c.dev_ap, held: c.ap },
              display: c.dev_ap == null ? num(c.ap) : signed(c.ap - c.dev_ap),
            }))}
            series={[
              { key: "dev", label: "Development", color: "var(--dim)", hollow: true },
              { key: "held", label: "Held-out", color: "var(--accent)" },
            ]}
            active={rung}
            onSelect={(r) => studio.set({ rung: r as Rung })}
            format={(v) => v.toFixed(2)}
            labelWidth={100}
          />
        </Panel>
      </div>

      <div className="grid gap-10 md:gap-14 xl:grid-cols-2">
        <Panel help="analysis.vs-chance"
          title={`All models against chance · ${rl}`}
          how="Held-out average precision with its 95% interval from resampling whole clusters. The dashed line is chance: the share who reach the rung. Click a model to look at it."
        >
          <DotRows
            rows={ranked.map(({ k, c }) => ({
              key: k,
              label: d.families[k].name,
              values: { ap: c.ap },
              lo: { ap: c.ap_ci[0] },
              hi: { ap: c.ap_ci[1] },
              display: num(c.ap),
            }))}
            series={[{ key: "ap", label: "Average precision", color: "var(--accent)" }]}
            reference={{ value: card.prevalence, label: "Chance" }}
            active={key}
            onSelect={pick}
            format={(v) => v.toFixed(2)}
            labelWidth={230}
          />
        </Panel>

        <div className="flex flex-col gap-10 md:gap-14 min-w-0">
          <Panel help="analysis.differences"
            title="Differences, with intervals"
            how="Held-out average precision and AUROC of this model minus another, with the 95% interval from the same resamples. An interval that crosses zero means the two cannot be told apart."
          >
            {pairedRows.length ? (
              <DotRows
                rows={pairedRows.map((r) => ({
                  key: r.key, label: r.label, values: { v: r.v }, lo: { v: r.lo }, hi: { v: r.hi }, display: signed(r.v, 3),
                }))}
                series={[{ key: "v", label: "Difference", color: "var(--accent)" }]}
                reference={{ value: 0, label: "No difference" }}
                format={(v) => signed(v, 2)}
                labelWidth={210}
              />
            ) : (
              <p className="px-14 py-12 text-11 text-dim">This is the model everything else is compared with.</p>
            )}
          </Panel>

          <Panel help="analysis.grid"
            title={`Every model, every rung · ${SET_SHORT[set] ?? set}`}
            how="Held-out average precision on this predictor set. Each column is shaded on its own, since rungs differ in difficulty. Click a row to look at that model."
          >
            <MatrixHeat
              theme={theme}
              perColumn
              rows={inSet
                .sort((a, b) => (d.summary[b]?.[rung]?.ap ?? -1) - (d.summary[a]?.[rung]?.ap ?? -1))
                .map((k) => ({
                  key: k,
                  label: d.families[k].name,
                  values: Object.fromEntries(RUNGS.map((r) => [r.key, d.summary[k]?.[r.key]?.ap ?? null])),
                }))}
              cols={RUNGS.map((r) => ({ key: r.key, label: r.label }))}
              format={(v) => v.toFixed(3)}
              active={key}
              activeCol={rung}
              onRow={pick}
              onCol={(k) => studio.set({ rung: k as Rung })}
              labelWidth={210}
              cellWidth={64}
            />
          </Panel>
        </div>
      </div>

      <Panel help="analysis.learned"
        title="What it learned from"
        how="The women, the outcome and the predictors behind these numbers. The share of importance is the model's own, where it has one."
      >
        <div className="p-14 grid gap-10 grid-cols-2 xl:grid-cols-4">
          <StatTile label="Development women" value={d.meta.n_development.toLocaleString("en-US")} sub="tuned and cross-validated here" />
          <StatTile label="Held-out women" value={d.meta.n_heldout.toLocaleString("en-US")} sub="scored once, at the end" />
          <StatTile label={`Reach ${rl}`} value={pct(card.prevalence)} sub="weighted share; the chance level" />
          <StatTile label="Predictors" value={card.n_predictors} sub={d.meta.sets.find((x) => x.key === set)?.label ?? set} />
        </div>
        {shares.length > 0 && shareKey && (
          <div className="border-t border-border">
            <RankedBars
              rows={shares.map((r) => ({
                key: r.predictor,
                label: label(r.predictor),
                value: r.share,
                display: pct(r.share, 1),
                color: "var(--accent)",
              }))}
              referenceLabel=""
              labelWidth={190}
            />
            <DataNote>Share of total importance on held-out women{shareKey === "shap" ? " (SHAP)" : shareKey === "logistic" ? " (its exact log-odds, by predictor)" : " (the model's own terms, exact)"}.</DataNote>
          </div>
        )}
        <div className="border-t border-border px-14 py-10 flex flex-wrap gap-x-16 gap-y-4 text-10.5">
          <Link className="text-accent hover:underline" href={studio.href("/explore/ladder")}>The ANC ladder</Link>
          <Link className="text-accent hover:underline" href={studio.href("/explore/predictors")}>Predictor selection</Link>
          <Link className="text-accent hover:underline" href={studio.href("/explore/cohorts")}>Cohorts</Link>
          <Link className="text-accent hover:underline" href={studio.href("/explore/models")}>Models compared</Link>
        </div>
        <DataNote>A test on an earlier survey round would show whether this accuracy travels.</DataNote>
      </Panel>
    </Screen>
  );
}
