"""Build research_record/: everything the model library found, as aggregate results.

    python scripts/build_research_record.py            # 500 resamples (about 15 minutes)
    python scripts/build_research_record.py --quick    # 50 resamples

The study's models are three models on the 21 predictors (reproduction/). On the
way there the study built a much larger library -- eleven model families and two
networks on four predictor sets at three rungs, each model recalibrated two ways,
and combined into ensembles -- and ran the studies that decided what to keep: the
predictor-value study, the duplicate analysis, the parsimonious searches, the
tuning checks. This writes all of it down, so none of that work is lost and any of
it can be taken up again (reproduction_full/ rebuilds it from the survey file).

Only aggregates leave the machine: per-model metrics with intervals, paired
differences, predictor lists and step tables. No woman's record or prediction is
written (the DHS licence).

Writes research_record/:
  README.md                 what is here, what it found, and what is left to try
  tables/library_cells.csv  every cell the library planned: done or not, and its metrics
  tables/calibration.csv    each model against its isotonic and Platt recalibrations
  tables/ensembles.csv      each ensemble against the best single model
  tables/predictor_sets.csv each model on the four predictor sets, against the 21
  tables/catboost.csv       the CatBoost runs, finished and not
  tables/networks.csv       the two networks against the best tree model
  tables/tuning/            the grid against the longer search; one-step setting checks
  tables/predictor_value/   the predictor-value study, per rung (tiers, steps, held-out)
  tables/duplicates/        the near-duplicate analysis
  tables/parsimonious/      the parsimonious searches' lists
  record.ipynb              the figures, drawn from the tables alone (executed)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import design, library as lib  # noqa: E402

LIB = ROOT / "outputs" / "library"
CORE = ROOT / "outputs" / "core"
OUT = ROOT / "research_record"
T = OUT / "tables"
SEED = 2026
VARIANTS = {"isotonic calibrated": "isotonic", "platt calibrated": "platt"}


def variant_of(model: str, kind: str) -> tuple[str, str, str]:
    """(family, variant, lineup) of a cell."""
    lineup = ""
    if "/" in model:
        lineup, model = model.split("/", 1)
    for tag, v in VARIANTS.items():
        if model.endswith(f"({tag})"):
            return model[: -len(tag) - 3], v, lineup
    if kind in ("stack", "cumlink"):
        return model, "ensemble", lineup
    if kind == "net":
        return model, "network", lineup
    if kind == "grid":
        return model, "grid (the study's models)", lineup
    return model, "tuned", lineup


def planned() -> list[tuple[str, lib.Job, Path]]:
    """Every cell the library planned, with where it lives."""
    out = [(r, j, LIB) for j in lib.jobs(lib.ALL_SETS) for r, _ in j.cells]
    out += [(j.rung, j, LIB) for ln in lib.LINEUPS for j in lib.lineup_jobs(ln)]
    out += [(j.rung, j, CORE) for j in lib.grid_jobs()]
    return out


def boot_metrics(y, w, p, boots):
    ap = np.empty(len(boots))
    au = np.empty(len(boots))
    for i, ix in enumerate(boots):
        ap[i] = average_precision_score(y[ix], p[ix], sample_weight=w[ix])
        au[i] = roc_auc_score(y[ix], p[ix], sample_weight=w[ix])
    return ap, au


def ci(a):
    return float(np.nanpercentile(a, 2.5)), float(np.nanpercentile(a, 97.5))


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--quick", action="store_true")
    args = ap_.parse_args()
    n_boot = 50 if args.quick else 500

    # FUTURE_WORK.md is written by hand and kept; the tables are rebuilt
    shutil.rmtree(T, ignore_errors=True)
    T.mkdir(parents=True)

    dev, held = lib.partitions()
    boots = list(design.stratified_psu_bootstrap(held.v022.to_numpy(), held.v021.to_numpy(), n_boot, SEED))
    w = (held.v005 / 1e6).to_numpy()

    rows, draws = [], {}
    for rung, job, root in planned():
        _, model = rung, [m for r, m in job.cells if r == rung][0]
        fam, var, lineup = variant_of(model, job.kind)
        row = {"set": job.set, "rung": rung, "cell": model, "family": fam, "variant": var, "lineup": lineup,
               "kind": job.kind, "device": job.device}
        path = lib.cell_path(root, job.set, rung, model)
        if not path.exists():
            failed = lib.failed_path(root, job).exists()
            rows.append({**row, "status": "failed" if failed else "not run"})
            continue
        cell = lib.load_cell(root, job.set, rung, model)
        m = cell["meta"]
        y = held[rung].astype(int).to_numpy()
        bap, bau = boot_metrics(y, w, cell["held"], boots)
        draws[(job.set, rung, model if root == LIB else f"grid/{model}")] = bap
        hm, dm = m["held_metrics"], m["dev_metrics"]
        rows.append({**row, "status": "done", "n_predictors": m.get("n_predictors"),
                     "dev_AP": dm.get("AP_seed_mean", dm["AP"]), "held_AP": hm["AP"],
                     "held_AP_lo": ci(bap)[0], "held_AP_hi": ci(bap)[1],
                     "held_AUROC": hm["AUROC"], "held_AUROC_lo": ci(bau)[0], "held_AUROC_hi": ci(bau)[1],
                     "Brier": hm.get("Brier"), "calibration_slope": hm.get("Calibration_slope"),
                     "CITL": hm.get("CITL"), "ICI": hm.get("ICI"), "prevalence": float(np.average(y, weights=w)),
                     "trials": m.get("n_trials") or m.get("n_settings"), "seconds": m.get("seconds"),
                     "params": json.dumps(m.get("params")) if m.get("params") else ""})
        print(f"  {job.set}/{rung}/{model}: {hm['AP']:.3f}", flush=True)
    cells = pd.DataFrame(rows)
    cells.to_csv(T / "library_cells.csv", index=False)
    done = cells[cells.status == "done"]

    def paired(a_key, b_key):
        d = draws[a_key] - draws[b_key]
        return float(np.nanmean(d)), *ci(d)

    # ---- recalibration: each tuned model against its two recalibrations
    cal = []
    for (s, r, fam), g in done[done.variant.isin(["tuned", "isotonic", "platt"])].groupby(["set", "rung", "family"]):
        base = g[g.variant == "tuned"]
        if base.empty:
            continue
        b = base.iloc[0]
        for _, c in g[g.variant != "tuned"].iterrows():
            d, lo, hi = paired((s, r, c.cell), (s, r, b.cell))
            cal.append({"set": s, "rung": r, "family": fam, "method": c.variant,
                        "AP_tuned": b.held_AP, "AP_recalibrated": c.held_AP, "AP_difference": d, "AP_difference_lo": lo,
                        "AP_difference_hi": hi, "slope_tuned": b.calibration_slope, "slope_recalibrated": c.calibration_slope,
                        "ICI_tuned": b.ICI, "ICI_recalibrated": c.ICI, "Brier_tuned": b.Brier, "Brier_recalibrated": c.Brier})
    pd.DataFrame(cal).to_csv(T / "calibration.csv", index=False)

    # ---- ensembles: against the single tuned model a user would pick (best development AP)
    ens = []
    tuned = done[(done.variant == "tuned")]
    for _, e in done[done.variant == "ensemble"].iterrows():
        pool = tuned[(tuned.set == e.set) & (tuned.rung == e.rung)]
        if e.lineup:
            pool = pool[pool.family.isin(lib.LINEUPS[e.lineup])]
        if pool.empty:
            continue
        pick = pool.sort_values("dev_AP", ascending=False).iloc[0]
        d, lo, hi = paired((e.set, e.rung, e.cell), (e.set, e.rung, pick.cell))
        ens.append({"set": e.set, "rung": e.rung, "ensemble": e.family, "lineup": e.lineup or "every family",
                    "AP_ensemble": e.held_AP, "best_single": pick.family, "AP_best_single": pick.held_AP,
                    "AP_difference": d, "AP_difference_lo": lo, "AP_difference_hi": hi,
                    "slope_ensemble": e.calibration_slope, "ICI_ensemble": e.ICI})
    pd.DataFrame(ens).to_csv(T / "ensembles.csv", index=False)

    # ---- predictor sets: each tuned model on each set, against the same model on the 21
    ps = []
    for (fam, r), g in tuned.groupby(["family", "rung"]):
        ref = g[g.set == "s21"]
        for _, c in g.iterrows():
            row = {"family": fam, "rung": r, "set": c.set, "set_label": lib.SET_LABEL[c.set],
                   "n_predictors": c.n_predictors, "AP": c.held_AP, "AP_lo": c.held_AP_lo, "AP_hi": c.held_AP_hi}
            if not ref.empty and c.set != "s21":
                d, lo, hi = paired((c.set, r, c.cell), ("s21", r, ref.iloc[0].cell))
                row.update({"AP_minus_21": d, "AP_minus_21_lo": lo, "AP_minus_21_hi": hi})
            ps.append(row)
    pd.DataFrame(ps).to_csv(T / "predictor_sets.csv", index=False)

    # ---- every tuned model against logistic regression on the same set and rung
    vl = []
    for _, c in tuned.iterrows():
        lr = tuned[(tuned.set == c.set) & (tuned.rung == c.rung) & (tuned.family == "Logistic regression")]
        if lr.empty or c.family == "Logistic regression":
            continue
        d, lo, hi = paired((c.set, c.rung, c.cell), (c.set, c.rung, lr.iloc[0].cell))
        vl.append({"set": c.set, "rung": c.rung, "family": c.family, "AP": c.held_AP, "AP_logistic": lr.iloc[0].held_AP,
                   "AP_difference": d, "AP_difference_lo": lo, "AP_difference_hi": hi})
    vl = pd.DataFrame(vl)
    vl.to_csv(T / "versus_logistic.csv", index=False)

    # ---- CatBoost and the networks
    cells[cells.family == "CatBoost"].to_csv(T / "catboost.csv", index=False)
    net = []
    for _, n in done[done.variant == "network"].iterrows():
        trees = tuned[(tuned.set == n.set) & (tuned.rung == n.rung)].sort_values("held_AP", ascending=False)
        best = trees.iloc[0]
        d, lo, hi = paired((n.set, n.rung, n.cell), (n.set, n.rung, best.cell))
        net.append({"set": n.set, "rung": n.rung, "network": n.family, "AP": n.held_AP, "AUROC": n.held_AUROC,
                    "best_tuned_model": best.family, "AP_best_tuned": best.held_AP,
                    "AP_difference": d, "AP_difference_lo": lo, "AP_difference_hi": hi})
    pd.DataFrame(net).to_csv(T / "networks.csv", index=False)

    # ---- the studies behind the choices (aggregate tables, copied as they are)
    copies = {
        "tuning": [LIB / "tuning" / f for f in ("grid_vs_search.csv",)] + sorted((LIB / "tuning").glob("ablation_*.csv")),
        "duplicates": sorted((ROOT / "outputs" / "enhanced" / "redundancy").glob("*")),
    }
    for r in lib.RUNGS:
        fv = ROOT / "outputs" / "feature_value" / "full" / r
        copies[f"predictor_value/{r}"] = [fv / f for f in (
            "summary.json", "forward_steps.csv", "original21_placement.csv", "selection_frequency.csv",
            "add_one_to_21.csv", "drop_one_within_21.csv", "remove_one_from_all.csv", "heldout.csv",
            "heldout_bootstrap.json", "lightgbm_check.csv") if (fv / f).exists()]
        copies.setdefault("parsimonious", []).append(ROOT / "outputs" / "enhanced" / r / "parsimonious_spec.json")
    for sub, files in copies.items():
        (T / sub).mkdir(parents=True, exist_ok=True)
        for f in files:
            if f.exists():
                name = f"{f.parent.name}_{f.name}" if sub == "parsimonious" else f.name
                shutil.copy2(f, T / sub / name)

    write_figures_notebook()
    (OUT / "README.md").write_text(readme(cells, pd.DataFrame(cal), pd.DataFrame(ens), pd.DataFrame(ps),
                                          pd.DataFrame(net), vl, n_boot), encoding="utf-8")
    print(f"wrote {OUT}")


FIGURES = [
    ("""# The research record, in figures

Every figure below is drawn from the tables in `tables/` alone; no survey data are needed.
Intervals are 95%, from resampling whole survey clusters of the held-out women.""", None),
    (None, """import pandas as pd, numpy as np, matplotlib.pyplot as plt
T = "tables/"
cells = pd.read_csv(T + "library_cells.csv")
tuned = cells[(cells.status == "done") & (cells.variant == "tuned")]
RUNGS = ["anc1plus", "anc4plus", "anc8plus"]
SETS = {"pool": "Full pool", "s21": "The 21", "short": "Short set", "pars": "Parsimonious"}"""),
    ("""## Every tuned model on every set, held-out average precision""", None),
    (None, """fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for ax, r in zip(axes, RUNGS):
    t = tuned[tuned.rung == r].pivot_table(index="family", columns="set", values="held_AP")[list(SETS)]
    im = ax.imshow(t.values, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(SETS)), SETS.values(), rotation=30); ax.set_yticks(range(len(t)), t.index)
    for i in range(t.shape[0]):
        for j in range(t.shape[1]):
            v = t.values[i, j]
            if np.isfinite(v): ax.text(j, i, f"{v:.3f}", ha="center", va="center", fontsize=8)
    ax.set_title(r.upper().replace("PLUS", "+"))
plt.tight_layout(); plt.show()"""),
    ("""## More predictors against the 21 (paired difference, each model)""", None),
    (None, """ps = pd.read_csv(T + "predictor_sets.csv").dropna(subset=["AP_minus_21"])
fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
for ax, r in zip(axes, RUNGS):
    g = ps[ps.rung == r]
    for k, (s, lab) in enumerate([(s, l) for s, l in SETS.items() if s != "s21"]):
        h = g[g.set == s]
        x = k + np.linspace(-0.3, 0.3, len(h))
        ax.errorbar(x, h.AP_minus_21, yerr=[h.AP_minus_21 - h.AP_minus_21_lo, h.AP_minus_21_hi - h.AP_minus_21], fmt="o", ms=3, lw=0.8)
    ax.axhline(0, color="grey", lw=0.8); ax.set_xticks(range(3), [l for s, l in SETS.items() if s != "s21"])
    ax.set_title(r.upper().replace("PLUS", "+"))
axes[0].set_ylabel("AP minus the same model on the 21")
plt.tight_layout(); plt.show()"""),
    ("""## Recalibration: what isotonic and Platt did""", None),
    (None, """cal = pd.read_csv(T + "calibration.csv")
fig, axes = plt.subplots(1, 2, figsize=(13, 4))
for m, c in (("isotonic", "tab:red"), ("platt", "tab:blue")):
    h = cal[cal.method == m]
    axes[0].hist(h.AP_difference, bins=30, alpha=0.6, label=m, color=c)
    axes[1].scatter(h.slope_tuned, h.slope_recalibrated, s=10, alpha=0.6, label=m, color=c)
axes[0].axvline(0, color="grey"); axes[0].set_xlabel("held-out AP, recalibrated minus tuned"); axes[0].legend()
axes[1].plot([0, 2], [0, 2], color="grey", lw=0.8); axes[1].axhline(1, color="grey", ls=":"); axes[1].axvline(1, color="grey", ls=":")
axes[1].set_xlabel("calibration slope, tuned"); axes[1].set_ylabel("calibration slope, recalibrated"); axes[1].legend()
plt.tight_layout(); plt.show()"""),
    ("""## Ensembles and networks against the best single model""", None),
    (None, """ens = pd.read_csv(T + "ensembles.csv"); net = pd.read_csv(T + "networks.csv")
rows = [(f"{e.ensemble} ({e.lineup})", e) for e in ens.itertuples()] + [(n.network, n) for n in net.itertuples()]
lab = sorted({k for k, _ in rows})
fig, ax = plt.subplots(figsize=(10, 4))
for i, k in enumerate(lab):
    vals = [r for kk, r in rows if kk == k]
    x = i + np.linspace(-0.3, 0.3, len(vals))
    ax.errorbar(x, [v.AP_difference for v in vals], yerr=[[v.AP_difference - v.AP_difference_lo for v in vals], [v.AP_difference_hi - v.AP_difference for v in vals]], fmt="o", ms=3, lw=0.8)
ax.axhline(0, color="grey"); ax.set_xticks(range(len(lab)), lab, rotation=20, ha="right")
ax.set_ylabel("held-out AP minus the best single model"); plt.tight_layout(); plt.show()"""),
    ("""## Tuning: notebook 2's grids against the longer search""", None),
    (None, """g = pd.read_csv(T + "tuning/grid_vs_search.csv")
print(g[["rung", "model", "grid_settings", "search_trials", "grid_held_AP", "search_held_AP", "held_AP_difference"]].round(4).to_string(index=False))"""),
    ("""## CatBoost: what finished""", None),
    (None, """cb = pd.read_csv(T + "catboost.csv")
print(cb.groupby(["set", "variant"]).status.value_counts().unstack(fill_value=0).to_string())
print()
print(cb[cb.status == "done"][["set", "rung", "variant", "held_AP", "held_AP_lo", "held_AP_hi"]].round(3).to_string(index=False))"""),
]


def write_figures_notebook():
    import nbformat as nbf
    from nbclient import NotebookClient
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(m) if m else nbf.v4.new_code_cell(c) for m, c in FIGURES]
    for i, c in enumerate(nb.cells):
        c.id = f"cell-{i:03d}"
    nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}
    NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(OUT)}}).execute()
    nbf.write(nb, str(OUT / "record.ipynb"))


def readme(cells, cal, ens, ps, net, vl, n_boot) -> str:
    done = cells[cells.status == "done"]
    n_plan, n_done = len(cells), len(done)
    tuned = done[done.variant == "tuned"]
    fams = sorted(tuned.family.unique())
    grid = done[done.variant.str.startswith("grid")]

    def rng(s):
        return f"{s.min():+.3f} to {s.max():+.3f}"

    iso = cal[cal.method == "isotonic"]
    platt = cal[cal.method == "platt"]
    iso_worse = int((iso.AP_difference_hi < 0).sum())
    stack = ens[ens.ensemble == "Stacked ensemble"]
    cum = ens[ens.ensemble == "Cumulative-link ensemble"]
    sets = ps.dropna(subset=["AP_minus_21"])
    by_set = sets.groupby(["set_label", "rung"]).AP_minus_21.median().unstack().round(3)
    cat = cells[cells.family == "CatBoost"]
    cat_done = cat[cat.status == "done"]
    best8 = tuned[tuned.rung == "anc8plus"].sort_values("held_AP", ascending=False).head(5)
    beats_lr = vl[vl.AP_difference_lo > 0]
    loses_lr = vl[vl.AP_difference_hi < 0]
    stack_up = int((stack.AP_difference_lo > 0).sum())
    cum_down = int((cum.AP_difference_hi < 0).sum())
    xg = cal[(cal.set == "pool") & (cal.rung == "anc8plus") & (cal.family == "XGBoost") & (cal.method == "platt")]
    xg_slope = (f"XGBoost at ANC8+ on the full pool: slope {xg.slope_tuned.iloc[0]:.2f} before, "
                f"{xg.slope_recalibrated.iloc[0]:.2f} after") if len(xg) else ""

    lines = [
        "# The research record: everything the model library found",
        "",
        "The study's models are three, logistic regression, random forest and XGBoost on the 21",
        "predictors at each rung (`reproduction/` rebuilds them). To get there the study built a much",
        "larger model library and ran the studies that decided what to keep. This folder records all",
        "of it as aggregate results, so the work can be cited, checked and taken up again.",
        "`reproduction_full/` rebuilds every number here from the survey file.",
        "",
        "No woman's record or prediction is in this folder: only metrics, intervals, paired",
        f"differences, predictor lists and step tables. Intervals come from {n_boot} resamples of whole",
        "survey clusters within strata of the 1,375 held-out women; differences are paired (the same",
        "resamples for both models).",
        "",
        "## What was built",
        "",
        f"- **{n_done} of {n_plan} planned models** finished: {len(fams)} model families",
        f"  ({', '.join(fams)}), each tuned by an Optuna search on four predictor sets (the full pool",
        "  of 86 duplicate-free candidates, the 21, the short set and the parsimonious set) at ANC1+,",
        "  ANC4+ and ANC8+; each recalibrated two ways (isotonic and Platt); stacked and",
        "  cumulative-link ensembles over every family and over the three- and four-model lineups; and",
        "  two neural networks (a ladder transformer and a contact-sequence encoder-decoder).",
        f"- **The study's own nine models** (three models on the 21, notebook 2's grids): held-out AP",
        f"  {', '.join(f'{r.rung} {r.family} {r.held_AP:.3f}' for r in grid.sort_values(['rung', 'family']).itertuples())}.",
        "",
        "Everything is in `tables/library_cells.csv`, one row per planned model, with its status.",
        "",
        "## What it found",
        "",
        "**The models are close.** At ANC8+ the five best tuned models on any set:",
        "",
        "| Set | Model | Held-out AP (95% interval) |",
        "|---|---|---|",
        *[f"| {lib.SET_LABEL[r.set]} | {r.family} | {r.held_AP:.3f} ({r.held_AP_lo:.3f}-{r.held_AP_hi:.3f}) |"
          for r in best8.itertuples()],
        "",
        "Their intervals overlap widely. Against logistic regression on the same set and rung",
        f"(`tables/versus_logistic.csv`, paired), {len(beats_lr)} of {len(vl)} tuned models were reliably better",
        f"(interval above zero) and {len(loses_lr)} reliably worse.",
        "",
        "**More predictors buy little.** Median difference from the same model on the 21, held-out AP",
        "(`tables/predictor_sets.csv`, with each model's paired interval):",
        "",
        by_set.to_markdown() if hasattr(by_set, "to_markdown") else by_set.to_string(),
        "",
        "The full pool adds about 0.01-0.02 at ANC1+ and ANC4+ and close to nothing at ANC8+; the",
        "short and parsimonious sets hold most of the 21's accuracy with far fewer questions.",
        "",
        "**Recalibration.** Platt scaling cannot change the ranking, so its AP difference is zero; it",
        f"corrects over- or under-confidence (calibration slope, `tables/calibration.csv`). Isotonic",
        f"scaling changed AP by {rng(iso.AP_difference)}, and was reliably worse (interval below zero)",
        f"in {iso_worse} of {len(iso)} models: its steps tie women the model had ranked apart, and with",
        "5,518 development women the steps are fitted on too few. Platt is the one worth keeping where",
        f"a model is overconfident ({xg_slope}).",
        "",
        f"**Ensembles.** The stacked ensemble changed AP by {rng(stack.AP_difference)} against the single",
        f"model a user would have picked (the best on development); its gain was reliably above zero in",
        f"{stack_up} of {len(stack)} cases. The cumulative-link ensemble (the best model refitted at several",
        f"contact thresholds and pooled) changed AP by {rng(cum.AP_difference)}, reliably worse in {cum_down} of",
        f"{len(cum)}: pooling thresholds, and the isotonic map back to a chance, cost more than",
        "neighbouring thresholds lent (`tables/ensembles.csv`).",
        "",
        f"**Networks.** Against the best tuned model on the same set and rung, the networks changed AP",
        f"by {rng(net.AP_difference)}, never above it (`tables/networks.csv`): competitive at best, at far",
        "higher cost.",
        "",
        "**Tuning.** Notebook 2's prespecified grids (4, 48 and 64 settings) matched the longer Optuna",
        "searches on held-out women (`tables/tuning/grid_vs_search.csv`); the searches' higher",
        "development scores were the search fitting its own folds.",
        "",
        "**How the sets were chosen.** `tables/predictor_value/` holds the predictor-value study per",
        "rung (forward selection over repeated splits, the tiers, what each of the 21 adds and costs,",
        "the held-out check); `tables/duplicates/` the near-duplicate analysis that took the pool from",
        "95 to 86; `tables/parsimonious/` the parsimonious searches' lists.",
        "",
        "## Left to do: possible advantages for later work",
        "",
        f"- **CatBoost.** {len(cat_done)} of {len(cat)} planned CatBoost models finished (the tuned models",
        "  on the full pool and the 21, run on a Colab GPU); its recalibrations and the short and",
        "  parsimonious sets did not. On the cells that finished it sits with the other boosted trees",
        "  (`tables/catboost.csv`). Its native handling of categories, most of the 21, is the reason to",
        "  finish it: it may use them better than one-hot or integer codes do.",
        "- **Platt recalibration for the tree models** where the slope is far from 1 (XGBoost at ANC8+),",
        "  if the models are used to give chances, not only to rank.",
        "- **The networks with more data.** They predict all three rungs together, or contact by",
        "  contact; pooled survey rounds could give them the size they need.",
        "- **A second survey round** to check that the accuracy travels, for every model here.",
        "",
        "## Files",
        "",
        "```",
        "tables/library_cells.csv    every planned model: status, metrics with intervals, settings",
        "tables/calibration.csv      each model against its isotonic and Platt recalibrations",
        "tables/ensembles.csv        each ensemble against the best single model",
        "tables/predictor_sets.csv   each model on the four sets, against the 21",
        "tables/networks.csv         the networks against the best tuned model",
        "tables/versus_logistic.csv  every tuned model against logistic regression, paired",
        "tables/catboost.csv         the CatBoost runs",
        "tables/tuning/              grid against search; one-step setting checks",
        "tables/predictor_value/     the predictor-value study, per rung",
        "tables/duplicates/          the near-duplicate analysis",
        "tables/parsimonious/        the parsimonious searches",
        "record.ipynb                the figures, from these tables alone",
        "```",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
