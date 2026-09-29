"""Write the small JSON files the studio's visual screens read.

    python scripts/export_viz_data.py

Reads result tables only (outputs/regional, outputs/wartime, ...), never the
per-woman data, so everything it writes is an aggregate and can be committed and
deployed. Each block is written only when its analysis has run; a missing input is
reported, not faked.

  app/public/data/regions.json   map, region panels, region x metric heatmap
  app/public/data/explore.json   the Explore screens' extras: contact-count
                                 distributions, the EDHS report table, the networks
  app/public/data/war.json       the conflict simulator's model, evidence and backtest
  app/public/data/scenarios.json the planner's levers: g-computation over 128 combinations
  app/public/data/series.json    ANC by quarter and half-year of birth, and the screener
  app/public/samples/*.csv       sample files for "Your data" (survey-derived and synthetic)
  app/public/data/lab.json       the Model lab: attention, drop-off curves, composite profiles
  app/public/data/nets.json      the two networks' weights, for the browser forward pass
  app/public/data/models/        the Model analysis screen: index.json (scores for every
                                 model), and <set>.json (full cards, one predictor set each)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8.concepts import CONCEPTS, concept_of  # noqa: E402
from anc8.reference import EDHS_ANC4_BY_REGION, EDHS_ANC4_NATIONAL  # noqa: E402

OUT = ROOT / "app" / "public" / "data"
REGIONAL = ROOT / "outputs" / "regional"
WARTIME = ROOT / "outputs" / "wartime"
DEEP = ROOT / "outputs" / "deep"
WAR = ROOT / "outputs" / "war"
SCEN = ROOT / "outputs" / "scenarios"
TS = ROOT / "outputs" / "timeseries"
SCREEN = ROOT / "outputs" / "screener"

RUNG_OF = {"anc1plus": "anc1", "anc4plus": "anc4", "anc8plus": "anc8"}


def r4(v):
    """Round for the wire; JSON has no NaN, so missing becomes null."""
    if v is None:
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    try:
        f = float(v)
    except (TypeError, ValueError):
        return v
    return None if not np.isfinite(f) else round(f, 4)


def clean(obj):
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    return r4(obj) if not isinstance(obj, str) else obj


CASCADE_KEYS = ["reach1", "reach4", "reach8", "never", "start_lt4", "four_lt8",
                "continue_1_to_4", "continue_4_to_8"]


def regions_block() -> dict | None:
    need = ["cascade_by_region.csv", "subgroups_by_region.csv", "profile_by_region.csv",
            "drivers_concepts_by_region.csv", "population.json"]
    missing = [n for n in need if not (REGIONAL / n).exists()]
    if missing:
        print(f"  regions: skipped, run scripts/run_regional_eda.py first ({missing})")
        return None

    casc = pd.read_csv(REGIONAL / "cascade_by_region.csv")
    cohorts = {}
    for cohort, g in casc.groupby("cohort"):
        block = {}
        for r in g.itertuples(index=False):
            d = r._asdict()
            entry = {"n": d["n"], "clusters": d["n_clusters"], "loss": d["biggest_loss_key"],
                     "action": d["action"]}
            for k in CASCADE_KEYS:
                entry[k] = d[k]
                entry[f"{k}_ci"] = [d[f"{k}_lo"], d[f"{k}_hi"]]
            block[d["region"]] = entry
        cohorts[cohort] = {"national": block.pop("Ethiopia"), "regions": block}

    sub = pd.read_csv(REGIONAL / "subgroups_by_region.csv").sort_values(["dimension", "order"])
    subgroups: dict = {}
    for (cohort, region, dim), g in sub.groupby(["cohort", "region", "dimension"], sort=False):
        subgroups.setdefault(cohort, {}).setdefault(region, {})[dim] = [
            {"level": x.level, "n": x.n, "small": bool(x.small), "reach1": x.reach1,
             "reach4": x.reach4, "reach8": x.reach8, "never": x.never,
             "continue_4_to_8": x.continue_4_to_8}
            for x in g.itertuples(index=False)]

    prof = pd.read_csv(REGIONAL / "profile_by_region.csv")
    profile_meta = (prof[["key", "label", "modifiable"]].drop_duplicates("key")
                    .to_dict("records"))
    profile: dict = {}
    for x in prof.itertuples(index=False):
        profile.setdefault(x.cohort, {}).setdefault(x.region, {})[x.key] = x.value

    drv = pd.read_csv(REGIONAL / "drivers_concepts_by_region.csv")
    drivers: dict = {}
    for rung, g in drv.groupby("rung"):
        drivers[rung] = {
            "national_predicted": float(g.national_predicted.iloc[0]),
            "regions": {
                region: {
                    "predicted": float(gg.region_predicted.iloc[0]),
                    "concepts": {x.concept: x.contribution for x in gg.itertuples(index=False)},
                }
                for region, gg in g.groupby("region")
            },
        }

    gap: dict = {}
    gp = WARTIME / "regional_gap_by_cohort.csv"
    if gp.exists():
        for x in pd.read_csv(gp).itertuples(index=False):
            gap.setdefault(x.cohort, {}).setdefault(RUNG_OF[x.outcome], {})[x.region] = {
                "actual": x.actual, "expected": x.expected, "gap": x.gap, "n": x.n}

    pop = json.loads((REGIONAL / "population.json").read_text(encoding="utf-8"))

    return {
        "source": "Ethiopia DHS 2024-25, survey-weighted; 95% intervals from a stratified "
                  "PSU bootstrap within each region",
        "population": pop,
        "concepts": [{k: c[k] for k in ("key", "label", "modifiable", "lever")} for c in CONCEPTS],
        "cohorts": cohorts,
        "subgroups": subgroups,
        "profile_meta": profile_meta,
        "profile": profile,
        "drivers": drivers,
        "gap": gap,
        "min_n": json.loads((REGIONAL / "summary.json").read_text())["min_n"],
    }


def explore_block() -> dict:
    """What the Explore screens need beyond analysis.json and regions.json."""
    out: dict = {"edhs_anc4": {"national": EDHS_ANC4_NATIONAL / 100,
                               "regions": {r: v / 100 for r, v in EDHS_ANC4_BY_REGION.items()},
                               "source": "EDHS 2024-25 key indicators report, women with a "
                                         "live birth in the two years before the survey"}}

    f = REGIONAL / "contacts_by_region.csv"
    if f.exists():
        c = pd.read_csv(f).sort_values("contacts")
        out["contacts"] = {
            cohort: {region: {"share": g.share.tolist(), "n": int(g.n.sum())}
                     for region, g in gc.groupby("region")}
            for cohort, gc in c.groupby("cohort")}
        out["contact_cap"] = int(c.contacts.max())
    else:
        print("  explore: no contact distribution, run scripts/run_regional_eda.py")

    f = DEEP / "heldout_performance.csv"
    if f.exists():
        perf = pd.read_csv(f)
        perf["rung"] = perf.rung.map({"ANC1+": "anc1plus", "ANC4+": "anc4plus", "ANC8+": "anc8plus"})
        summ = json.loads((DEEP / "summary.json").read_text())
        oof = pd.read_csv(DEEP / "oof_summary.csv")
        oof["rung"] = oof.rung.map({"ANC1+": "anc1plus", "ANC4+": "anc4plus", "ANC8+": "anc8plus"})
        boot = pd.read_csv(DEEP / "heldout_paired_bootstrap.csv")
        boot["rung"] = boot.rung.map({"ANC1+": "anc1plus", "ANC4+": "anc4plus", "ANC8+": "anc8plus"})
        out["networks"] = {
            "heldout": perf.to_dict("records"),
            "development": oof.to_dict("records"),
            "paired": boot[~boot.reference.str.startswith("Development champion")].to_dict("records"),
            "ladder_violations": summ.get("ladder_violations_heldout", {}),
            "seeds": summ.get("seeds"),
        }
    else:
        print("  explore: no network results, run scripts/run_deep_models.py")
    return out


def war_block() -> dict | None:
    f = WAR / "war_model.json"
    if not f.exists():
        print("  war: skipped, run scripts/run_war_model.py first")
        return None
    m = json.loads(f.read_text(encoding="utf-8"))
    rung = {"anc1plus": "anc1", "anc4plus": "anc4", "anc8plus": "anc8"}
    obs = pd.read_csv(WAR / "observed_by_half.csv")
    series = {r: g.drop(columns="region").to_dict("records") for r, g in obs.groupby("region")}
    win = pd.read_csv(ROOT / "docs" / "conflict_windows.csv")
    fit = m["fit"]
    return {
        "method": ("Weighted logistic regression on Tigray and the regions without major conflict, "
                   "with region and half-year-of-birth fixed effects; a pregnancy's exposure is the "
                   "average disruption over its nine months. Association-based: it transfers the "
                   "Tigray disruption to other regions on the odds scale."),
        "fit": {
            "n": fit["n"], "n_tigray": fit["n_tigray"], "regions": fit["regions"],
            "tau": fit["tau_months"], "tau_supported": fit["tau_supported"],
            "shock": {rung[k]: {"log_odds": v["log_odds"], "lo": v["interval"][0], "hi": v["interval"][1]}
                      for k, v in fit["shock"].items()},
            "profile": [{"tau": t["tau"], "delta_ll": t["delta_ll"],
                         **{rung[k]: v for k, v in t["shock"].items()}} for t in fit["tau_profile"]],
        },
        "draws": [{rung[k]: d[k] for k in rung} for d in m["draws"]],
        "fitted_tigray": m["fitted_tigray"],
        "did_check": {rung[k]: v for k, v in m["did_check"].items()},
        "backtest": m["backtest_amhara"],
        "observed": series,
        "windows": win.to_dict("records"),
        "bootstrap_resamples": m["bootstrap_resamples"],
    }


def scenarios_block() -> dict | None:
    f = SCEN / "scenarios.json"
    if not f.exists():
        print("  scenarios: skipped, run scripts/run_scenarios.py first")
        return None
    m = json.loads(f.read_text(encoding="utf-8"))
    rungs = ("anc1", "anc4", "anc8")
    # A lever is offered by default only where the data back it: the model expects
    # every rung to rise when it is applied. The others are shown, with their numbers,
    # as levers the data do not support.
    for i, lv in enumerate(m["levers"]):
        ebm = [m["rungs"][r]["gain"][-1][i] for r in rungs]
        lr = [m["rungs"][r]["logistic_check"][-1][i] for r in rungs if m["rungs"][r]["logistic_check"]]
        lv["supported"] = all(g > 0 for g in ebm)
        lv["models_agree"] = all((a > 0) == (b > 0) for a, b in zip(ebm, lr))
    return {
        "method": ("g-computation: every woman re-scored by the explainable boosting model with the "
                   "lever applied; association-based, not a causal estimate"),
        **m,
    }


def series_block() -> dict | None:
    if not (TS / "national_quarterly.csv").exists():
        print("  series: skipped, run scripts/run_time_series.py first")
        return None
    nat = pd.read_csv(TS / "national_quarterly.csv")
    reg = pd.read_csv(TS / "regional_half_year.csv")
    out = {
        "national_quarterly": nat.to_dict("records"),
        "regional_half_year": {r: g.drop(columns="region").to_dict("records") for r, g in reg.groupby("region")},
        "caveats": json.loads((TS / "summary.json").read_text())["caveats"],
    }
    if (SCREEN / "screener.json").exists():
        out["screener"] = json.loads((SCREEN / "screener.json").read_text(encoding="utf-8"))
    # the sample files, served as they are
    samples = ROOT / "app" / "public" / "samples"
    samples.mkdir(parents=True, exist_ok=True)
    for src, name in ((TS / "sample_survey_quarterly.csv", "survey_regions_quarterly.csv"),
                      (TS / "sample_synthetic_monthly.csv", "synthetic_woreda_monthly.csv"),
                      (SCREEN / "sample_register.csv", "synthetic_register.csv")):
        if src.exists():
            (samples / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return out


def lab_block() -> dict | None:
    need = ["attention_concepts.csv", "dropoff_curves.csv", "contact_distribution_heldout.csv",
            "weights.json", "profiles.json"]
    missing = [n for n in need if not (DEEP / n).exists()]
    if missing:
        print(f"  lab: skipped ({missing}); run run_deep_models.py and build_lab_profiles.py")
        return None
    att = pd.read_csv(DEEP / "attention_concepts.csv")
    concepts = [c["key"] for c in CONCEPTS]
    ladder = {r: g.set_index("concept").attention.reindex(concepts).fillna(0).tolist()
              for r, g in att[att.model == "ladder"].groupby("region")}
    seq = {}
    for r, g in att[att.model == "sequence"].groupby("region"):
        piv = g.pivot_table(index="step", columns="concept", values="attention").reindex(columns=concepts).fillna(0)
        seq[r] = piv.sort_index().to_numpy().tolist()
    drop = pd.read_csv(DEEP / "dropoff_curves.csv")
    weights = json.loads((DEEP / "weights.json").read_text(encoding="utf-8"))
    prep = weights["ladder"]["prep"]
    tokens = prep["numeric"] + prep["categorical"]
    # the networks' weights go out as their own file, loaded only by the lab
    (OUT / "nets.json").write_text(json.dumps(weights, separators=(",", ":")), encoding="utf-8")
    print(f"  wrote app/public/data/nets.json  ({(OUT / 'nets.json').stat().st_size / 1024:.0f} KB)")
    return {
        "concepts": [{"key": c["key"], "label": c["label"], "modifiable": c["modifiable"]} for c in CONCEPTS],
        "token_concept": [concepts.index(concept_of(t)) if concept_of(t) in concepts else -1 for t in tokens],
        "tokens": tokens,
        "attention": {"ladder": ladder, "sequence": seq},
        "dropoff": {r: g[["contact", "predicted", "observed"]].to_dict("records") for r, g in drop.groupby("region")},
        "distribution": pd.read_csv(DEEP / "contact_distribution_heldout.csv").to_dict("records"),
        "profiles": json.loads((DEEP / "profiles.json").read_text(encoding="utf-8")),
    }


def sig(obj, digits=5):
    """Round to significant figures: search-space values run from 1e-5 to 1e3, so
    fixed decimals would flatten the small ones to zero."""
    if isinstance(obj, dict):
        return {k: sig(v, digits) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sig(v, digits) for v in obj]
    if isinstance(obj, (bool, np.bool_)) or obj is None or isinstance(obj, str):
        return obj
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    f = float(obj)
    return float(f"{f:.{digits}g}") if np.isfinite(f) else None


def models_block() -> dict | None:
    f = ROOT / "outputs" / "model_cards" / "model_cards.json"
    if not f.exists():
        print("  models: skipped, run scripts/run_model_cards.py first")
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def write(name: str, data, rounder=None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps((rounder or clean)(data), separators=(",", ":")), encoding="utf-8")
    print(f"  wrote app/public/data/{name}  ({p.stat().st_size / 1024:.0f} KB)")


def main():
    print("studio data")
    reg = regions_block()
    if reg:
        write("regions.json", reg)
    write("explore.json", explore_block())
    lab = lab_block()
    if lab:
        write("lab.json", lab)
    se = series_block()
    if se:
        write("series.json", se)
    sc = scenarios_block()
    if sc:
        write("scenarios.json", sc)
    war = war_block()
    if war:
        write("war.json", war)
    mc = models_block()
    if mc:
        # A small index for the rankings and heatmaps, and the full cards one predictor
        # set per file, fetched only when that set is on screen.
        keep = ("ap", "ap_ci", "auroc", "auroc_ci", "brier", "slope", "lift", "prevalence",
                "dev_ap", "rank", "of", "n_predictors")
        summary = {k: {r: {f: c[f] for f in keep} for r, c in by.items()} for k, by in mc["cards"].items()}
        write("models/index.json", {"meta": mc["meta"], "families": mc["families"], "summary": summary,
                                    "cross": mc["cross"]}, rounder=sig)
        for st in [x["key"] for x in mc["meta"]["sets"]]:
            write(f"models/{st}.json", {"cards": {k: by for k, by in mc["cards"].items()
                                                  if mc["families"][k]["set"] == st}}, rounder=sig)
        (OUT / "models.json").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
