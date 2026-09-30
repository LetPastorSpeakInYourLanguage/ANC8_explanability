"""Build the study's reproduction folder: the models the studio uses, from the survey file.

    python scripts/build_reproduction.py            # writes reproduction/

reproduction/ is the study's hand-over for researchers who hold the EDHS 2024-25
Individual Recode. Its notebooks, run in order, rebuild from ETIR8AFL.DTA: the
cohort and the outcome ladder, the 21 predictors, the analysis frame, the split,
logistic regression, random forest and XGBoost on the 21 at ANC1+, ANC4+ and ANC8+
(each tuned over the grid notebook 2 prespecified), their evaluation, their
explanations and the planner's levers and regional drivers.

Everything else the study tried -- the candidate pool, other predictor sets, other
model families, recalibration, ensembles, networks -- is rebuilt by
reproduction_full/ (scripts/build_reproduction_full.py) and recorded in
research_record/ (scripts/build_research_record.py).

Nothing is hand-written twice: notebook 1 is the study's own (shared with the full
build), the package and stage scripts are synced from src/anc8 and scripts/, and the
study's results go to reference/ for every notebook to check itself against.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import build_reproduction_full as full  # noqa: E402  (notebook 1, the helpers, the folder texts)
from build_reproduction_full import code, md, write_nb  # noqa: E402

OUT = ROOT / "reproduction"

SCRIPTS = ["run_notebooks.py", "train_core.py", "fit_library_models.py", "run_hyperparameter_ablation.py",
           "run_explainability.py", "run_model_cards.py", "run_scenarios.py", "run_regional_eda.py",
           "build_form_schema.py"]

REQUIREMENTS = """\
# The analysis environment the study ran in. Newer versions will very likely work,
# but the check cells compare against the study's numbers, and XGBoost can differ in
# the last digits across versions.
numpy==2.5.0
pandas==3.0.3
scipy==1.18.0
scikit-learn==1.9.0
xgboost==3.3.0
shap==0.52.0
joblib==1.5.3
matplotlib==3.11.0
pyarrow==25.0.1
python-docx==1.1.2
nbformat==5.10.4
nbclient==0.10.2
jupyter==1.1.1
"""

SETUP = '''
# Settings for this notebook
QUICK = False   # True: fewer resamples for the intervals (a check that everything runs)

import sys, json, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
here = Path.cwd()
sys.path.insert(0, str(here.parent / "src" if here.name.startswith("notebooks") else here / "src"))
from anc8 import repro
P = repro.setup(quick=QUICK)
QUICK = P.quick

import numpy as np
import pandas as pd
from anc8 import library as lib
'''

MODELS = ["Logistic regression", "Random Forest", "XGBoost"]


# ======================================================================== notebooks
def nb00():
    return [md('''
# 00 · Start here

These notebooks rebuild the study's models from the EDHS 2024-25 Individual Recode: who is in
the cohort, how the three outcomes and the 21 predictors were made, how the women were split,
how each model was tuned and checked, what each model leans on, and the planner's levers. Run
them in order; each reads only what the earlier ones wrote and ends by checking its results
against the study's (in `reference/`).

The study predicts whether a woman reaches **one or more** (ANC1+), **four or more** (ANC4+)
and **eight or more** (ANC8+) antenatal care contacts, from what is known before her care
starts. Three models, **logistic regression, random forest and XGBoost**, are fitted on the
**21 predictors** at each of the three rungs: nine models. Each is tuned over the small grid
of settings the study fixed in advance.

## Before you start

1. **The data.** Obtain `ETIR8AFL.DTA` (Ethiopia DHS 2024-25, Individual Recode, Stata) from
   The DHS Program and put it in `data/`. It is licensed to you and must not be shared;
   nothing in this folder contains survey rows, and everything the notebooks write stays in
   `outputs/`, `results/` and `quick/`, which are never committed.
2. **The environment.** Python 3.12 or 3.13, then `pip install -r requirements.txt`.
3. **The order.** The table below; about half an hour in all on an 8-core laptop.

| Notebook | Does | Time |
|---|---|---|
| 01 | the cohort, the outcome ladder and the 21 predictors, from the survey file | 2 min |
| 02 | the analysis frame: the three rungs, birth timing, the women who started care | 2 min |
| 03 | the held-out split and the development folds | under 1 min |
| 04 | logistic regression, tuned at each rung | under 1 min |
| 05 | random forest, tuned at each rung | 10 min |
| 06 | XGBoost, tuned at each rung | 3 min |
| 07 | evaluation on the held-out women | 10 min |
| 08 | explanations: what each model leans on | 2 min |
| 09 | the planner's levers and why regions differ | 5 min |

To run them all without opening Jupyter, from this folder:

```
python scripts/run_notebooks.py            # all of them, in order
python scripts/run_notebooks.py --from 05  # resume after a stop
python scripts/run_notebooks.py --quick    # a fast check with fewer resamples
```

Executed copies, with every table, figure and check, land in `executed/`.

## What else the study tried

The study also screened every column of the survey into a candidate pool, compared four
predictor sets, fitted eleven model families and two neural networks, recalibrated and combined
them. None of that is needed for these models; `reproduction_full/` rebuilds all of it, and
`research_record/` records its results.

## Folders

```
data/            put ETIR8AFL.DTA here
notebooks/       00-09
src/anc8/        the analysis package every notebook uses
scripts/         the stage scripts some notebooks run
reference/       the study's results, for the checks
outputs/         what the notebooks write (analysis frames, tables, figures)
results/         the nine models' predictions and settings
```
'''), code('''
# Is the environment the one the study used, and is the survey file in place?
import importlib, sys
from pathlib import Path

here = Path.cwd()
project = here.parent if here.name.startswith("notebooks") else here
want = {}
for line in (project / "requirements.txt").read_text().splitlines():
    if "==" in line and not line.startswith("#"):
        name, v = line.split("==")
        want[name.strip()] = v.strip()

MODULE = {"scikit-learn": "sklearn", "python-docx": "docx"}
print(f"python {sys.version.split()[0]}")
for name, v in want.items():
    try:
        m = importlib.import_module(MODULE.get(name, name))
        got = getattr(m, "__version__", "?")
        print(f"  {name:14s} {got:10s} {'' if got == v else f'(the study used {v})'}")
    except ImportError:
        print(f"  {name:14s} MISSING    (pip install -r requirements.txt)")

dta = [p for p in (project / "data").glob("*") if p.name.lower() == "etir8afl.dta"]
print("\\nsurvey file:", dta[0] if dta else "NOT FOUND: put ETIR8AFL.DTA in data/")
''')]


def nb01():
    cells = full.nb01()
    cells[1] = code(SETUP + '''
from anc8 import cohorts
PROJECT = P.project
print("survey file:", cohorts.IR_FILE)
''')
    return cells


def nb02():
    return [md('''
# 02 · The analysis frame

Notebook 01 built the 21 predictors for every woman. The later notebooks need a few more
things from the survey file, joined to the same women:

- **the outcome ladder.** ANC1+, ANC4+ and ANC8+ from the same contact count (`m14_1`), so the
  three rungs are cuts through one number and a woman who reaches eight has reached four and one;
- **the survey's own columns** that the maps and the planner describe women by (travel time to a
  health post, listening to the radio, and so on). They describe regions; the models use only
  the 21;
- **the timing of each woman's most recent birth**, for her age at that birth (the one change
  made to the 21: current age is replaced by age at the birth, which is what the pregnancy saw)
  and for the 24-month window the national report uses;
- **the women who started care and when**, for the planner's earlier-first-visit lever.

**Reads:** `data/ETIR8AFL.DTA`, `outputs/ANC8_analysis_frozen.pkl`
**Writes:** `outputs/enhanced/ANC8_analysis_frozen_v2.pkl`, `birth_timing.parquet`, `anc_entry.csv`
'''), code(SETUP + '''
from anc8 import cohorts, features
OUT = P.outputs / "enhanced"
OUT.mkdir(parents=True, exist_ok=True)
ir = pd.read_stata(cohorts.IR_FILE, convert_categoricals=False)
first = pd.read_pickle(P.outputs / "ANC8_analysis_frozen.pkl")
first = first[first.anc8plus.notna()].copy()
print(f"{len(first):,} women with a resolved contact count")
'''), code('''
frame, numeric, categorical = features.assemble(first, ir)
frame.to_pickle(OUT / "ANC8_analysis_frozen_v2.pkl")
print(f"analysis frame: {frame.shape[0]:,} women x {frame.shape[1]} columns")
w = frame.v005 / 1e6
for r in lib.RUNGS:
    print(f"  {r}: {np.average(frame[r], weights=w):.1%} of women (survey-weighted)")
timing = cohorts.birth_timing()
print("birth timing for", len(timing), "women")
'''), md('''
## The women who started antenatal care, and when

The survey records the timing of the first contact in weeks (`m13a_1` from 100) or months
(from 200). A first contact at 12 weeks or earlier, or in the first three months, is
**early**; later is not; "don't know" (998) and women with no contact are left out. These are
the ANC-entry cohort, on the same split as everyone else.
'''), code('''
t = ir[["caseid", "m13a_1"]].copy()
t["caseid"] = t.caseid.astype(str)
weeks, months = t.m13a_1.between(100, 199), t.m13a_1.between(200, 299)
t["early_anc"] = np.nan
t.loc[weeks, "early_anc"] = (t.m13a_1[weeks] - 100 <= 12).astype(float)
t.loc[months, "early_anc"] = (t.m13a_1[months] - 200 <= 3).astype(float)
cohort = cohorts.load("full")[["caseid", "partition"]]
entry = cohort.merge(t[t.early_anc.notna()], on="caseid", how="inner")
entry = entry.rename(columns={"partition": "entry_partition"})[["caseid", "early_anc", "entry_partition"]]
entry.to_csv(OUT / "anc_entry.csv", index=False)
print(f"{len(entry):,} women started care with a known timing; {entry.early_anc.mean():.0%} of them early (unweighted)")
'''), md('''
## Checks against the study
'''), code('''
ref = repro.reference("fingerprints.json")
repro.check("the analysis frame is identical to the study's (content fingerprint)",
            repro.fingerprint(frame) == ref["analysis_frame"], repro.fingerprint(frame))
e = cohorts.entry_table().sort_values("caseid").reset_index(drop=True)
repro.check("the ANC-entry cohort is the study's (content fingerprint)", repro.fingerprint(e) == ref["anc_entry"], f"{len(e):,} women")
repro.report()
''')]


def nb03():
    cells = full.nb03()
    cells[0] = md('''
# 03 · The held-out women and the development folds

Every number the study reports for a model comes from women the model never saw. A fifth of
the survey's **clusters** (the villages and neighbourhoods the survey visited) are set aside
before anything is fitted: 1,375 women. The rest, 5,518 women, are the **development** set,
split again into five folds for tuning.

Why clusters and not women: women in one cluster share a health post, a road and a season of
fieldwork. Splitting them between development and held-out would let a model learn the
cluster and look better than it is. The folds keep clusters whole for the same reason, and
keep each survey stratum (region by urban/rural) spread across the folds.

The split is drawn once, from a fixed seed, and every model at every rung uses exactly these
women and these folds.
''')
    cells[1] = code(SETUP + '''
from anc8 import cohorts, design
dev, held = lib.partitions()   # also checks the split and folds against the study's digests
folds = design.make_psu_stratum_folds(dev)
print(f"development: {len(dev):,} women in {dev.v021.nunique()} clusters")
print(f"held-out:    {len(held):,} women in {held.v021.nunique()} clusters")
repro.check("no cluster is on both sides", not (set(dev.v021) & set(held.v021)))
''')
    return cells


def tuning_nb(num: str, model: str, blurb: str, pre: str) -> list:
    return [md(f'''
# {num} · {model}

{blurb}

**Preparation.** {pre}

**Tuning.** The study fixed a small grid of settings in advance (the grid below). Every
setting is fitted on four of the five development folds and scored on the fifth, in turn, and
the settings are ranked by **survey-weighted average precision, out of fold**. Inside each
fold the survey weights are rescaled to average one, so their size does not interact with the
model's regularisation. The best setting is refitted on all 5,518 development women, and the
held-out women are scored **once**. The operating threshold (for sensitivity and specificity)
is chosen on the development predictions only.

The model is tuned separately at each rung: three fits, each saved to
`results/s21/<rung>/{model}.npz` with its out-of-fold and held-out predictions and the setting
it chose. A fit already saved is skipped, so the notebook can be stopped and resumed.
'''), code(SETUP + f'''
MODEL = "{model}"
FOLD_JOBS = 5   # folds fitted in parallel; lower it on a machine with few cores
'''), code('''
grid = lib.GRIDS[MODEL]
print(pd.DataFrame([{"setting": k, "values": ", ".join("none" if v is None else str(v) for v in vals)}
                    for k, vals in grid.items()]).to_string(index=False))
print(f"\\n{len(lib.grid_settings(MODEL))} settings, each scored at every rung")
'''), code('''
for r in lib.RUNGS:
    job = lib.Job("grid", "s21", r, MODEL, MODEL)
    if lib.is_done(P.results, job):
        print(f"{job.id}: already done")
        continue
    lib.run(job, P.results, fold_jobs=FOLD_JOBS)
'''), md('''
## What the grid chose, and the check against the study
'''), code('''
for r in lib.RUNGS:
    meta = lib.load_cell(P.results, "s21", r, MODEL)["meta"]
    print(f"{r}: {meta['params']}  (development AP {meta['dev_metrics']['AP']:.3f}, held-out AP {meta['held_metrics']['AP']:.3f})")
repro.compare_cells(P.results, [MODEL])
repro.report()
''')]


def nb07():
    return [md('''
# 07 · Evaluation on the held-out women

Everything here is measured on the 1,375 held-out women, with their survey weights, and every
interval comes from resampling **whole clusters within their strata** (500 times), so it
reflects the survey's design.

For each model and rung: average precision against chance (the share reaching the rung),
AUROC, the Brier score, calibration (slope and intercept), the share of the women one is
looking for who sit in the top fifth of the ranking, sensitivity and specificity at the
threshold chosen on the development women, AUROC within regions, wealth, education and
residence groups, the difference from the best model and from logistic regression with its
paired interval, and the net benefit across risk thresholds (decision curve).

Two further checks: every model is refitted from its saved setting and must reproduce its
saved predictions exactly, and the tuning is examined: what the grid gained over the model's
default settings, and how much each setting matters.
'''), code(SETUP + f'''
MODELS = {MODELS!r}
'''), code('''
repro.run_script("fit_library_models.py", "--root", P.results)
repro.run_script("run_hyperparameter_ablation.py", "--root", P.results)
repro.run_script("run_explainability.py")   # the cards show what each model leans on (notebook 08)
repro.run_script("run_model_cards.py", "--library", P.results, *(["--quick"] if QUICK else []))
'''), md('''
## The three models at the three rungs
'''), code('''
cards = json.load(open(P.outputs / "model_cards" / "model_cards.json"))
rows = []
for key, by in cards["cards"].items():
    fam = cards["families"][key]
    for rung, c in by.items():
        rows.append({"rung": rung, "model": fam["name"], "AP": c["ap"], "AP 95%": f"{c['ap_ci'][0]:.3f}-{c['ap_ci'][1]:.3f}",
                     "chance": c["prevalence"], "AUROC": c["auroc"], "slope": c["slope"], "top 20% hold": c["top20"]})
cardtab = pd.DataFrame(rows).sort_values(["rung", "AP"], ascending=[True, False])
print(cardtab.round(3).to_string(index=False))
'''), code('''
import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 3, figsize=(12, 3.4))
for ax, rung in zip(axes, ["anc1", "anc4", "anc8"]):
    t = cardtab[cardtab.rung == rung].set_index("model")
    ax.bar(t.index, t.AP, color=["#4c78a8", "#72b7b2", "#f58518"])
    ax.axhline(t.chance.iloc[0], color="grey", lw=0.8, ls="--")
    ax.set_title(rung.upper() + "+"); ax.set_ylim(0, 1); ax.tick_params(axis="x", labelrotation=20)
axes[0].set_ylabel("held-out average precision (dashed: chance)")
plt.tight_layout(); plt.show()
'''), md('''
## What tuning bought
'''), code('''
for rung in lib.RUNGS:
    a = pd.read_csv(P.outputs / "library" / "tuning" / f"ablation_s21_{rung}.csv")
    g = a[a.parameter.isin(["(library defaults)", "(tuned optimum)"])].pivot_table(index="model", columns="parameter", values="AP")
    g["gain"] = g["(tuned optimum)"] - g["(library defaults)"]
    print(rung); print(g.round(4).to_string(), "\\n")
repro.compare_cells(P.results, MODELS)
repro.report()
''')]


def nb08():
    return [md('''
# 08 · What each model leans on

Each fitted model is explained on the held-out women, with their survey weights:

- **Logistic regression** is additive: its log-odds is a sum over predictors, so a woman's
  contribution from a predictor is its coefficients times her values, measured from the
  weighted average woman. The split is exact.
- **Random forest and XGBoost** are explained by **TreeSHAP**, the exact Shapley attribution for
  a tree ensemble (probability units for the forest, log-odds for XGBoost).

A predictor's importance is its weighted mean absolute contribution; its **share** is that over
the model's total, which makes the models comparable even though their units differ. The
agreement table lists each predictor's share under every model and how many models put it in
their top five; the concordance table is the rank correlation between models.

**Writes:** `outputs/explain/importance.csv`, `effects.json`, `agreement.csv`, `concordance.csv`
'''), code(SETUP), code('''
# notebook 07 already computed them for the model cards
if not (P.outputs / "explain" / "importance.csv").exists():
    repro.run_script("run_explainability.py")
'''), code(f'''
agree = pd.read_csv(P.outputs / "explain" / "agreement.csv")
models = {MODELS!r}
for rung in lib.RUNGS:
    print(rung, "· the ten predictors the models agree on most")
    print(agree[agree.rung == rung].head(10)[["predictor", *models, "mean_rank", "top5_models"]].round(3).to_string(index=False), "\\n")
print(pd.read_csv(P.outputs / "explain" / "concordance.csv").round(2).to_string(index=False))
'''), code('''
# The direction: each model's average contribution from the wealth quintile, by quintile, at ANC8+
# (log-odds for logistic regression and XGBoost, probability for the random forest)
eff = json.load(open(P.outputs / "explain" / "effects.json"))
order = ["Poorest", "Poorer", "Middle", "Richer", "Richest"]
table = pd.DataFrame({m: {r["level"]: r["effect"] for r in eff["s21"]["anc8plus"][m]["wealth_quintile"]} for m in models})
print(table.reindex(order).round(3).to_string())
repro.compare_table(pd.read_csv(P.outputs / "explain" / "importance.csv"), "explain_importance.csv",
                    keys=["set", "rung", "model", "predictor"], value="share", label="every predictor's share, per model")
repro.report()
''')]


def nb09():
    return [md('''
# 09 · The planner's levers, and why regions differ

**Levers.** A lever is something a health system can change, written as an edit to each
woman's record among the 21 predictors: a health centre or hospital within an hour, health
insurance, weekly radio health messages (one more weekly media source for a woman who does not
yet listen weekly), every pregnancy wanted, women taking part in decisions on their own
healthcare. Every woman is re-scored by logistic regression with the lever applied, and the
average change in her predicted chance, by region, is the lever's weight (g-computation).
Women already in the better state are unchanged. All combinations of the levers are scored, so
any mix of coverages combines exactly. One more lever, an earlier first visit, uses a model
fitted on the women who started care. Intervals resample whole clusters with the model held
fixed. These are associations: what the model expects if circumstances changed, not what a
programme would cause.

**Why a region differs.** Logistic regression is additive, so the gap between a region's
average predicted log-odds and the country's splits exactly across the 21 predictors, then
sums to planning concepts (access, insurance, wealth, education, and so on).
'''), code(SETUP), code('''
repro.run_script("run_scenarios.py", "--models", "logistic", *(["--quick"] if QUICK else []))
repro.run_script("run_regional_eda.py", "--models", "logistic")
'''), code('''
s = json.load(open(P.outputs / "scenarios" / "scenarios.json"))
keys = [l["key"] for l in s["levers"]] + ["all together"]
nat = {r: s["by_model"]["logistic"]["rungs"][r]["gain"][-1] for r in ("anc1", "anc4", "anc8")}
print("Change in the share reaching each rung if every eligible woman is reached (points, Ethiopia):")
print(pd.DataFrame({r: [v * 100 for v in g] for r, g in nat.items()}, index=keys).round(2).to_string())
drv = pd.read_csv(P.outputs / "regional" / "drivers_concepts_by_region.csv")
print("\\nWhy Somali's ANC8+ differs from Ethiopia's (log-odds, by concept):")
print(drv[(drv.model == "logistic") & (drv.rung == "anc8") & (drv.region == "Somali")].sort_values("contribution")[["label", "contribution"]].round(3).to_string(index=False))
ref = repro.reference("levers_national.json")["logistic"]
gap = max(abs(a - b) for r in ref for a, b in zip(ref[r], nat[r]))
repro.check("the national lever effects are the study's", gap < 1e-9, f"largest difference {gap:.1e}")
repro.report()
''')]


# ------------------------------------------------------------------ reference files
def write_reference(out: Path):
    """The study's results, as the notebooks' checks read them (aggregates only)."""
    from anc8 import cohorts, library as lib
    from anc8.repro import fingerprint as fp

    core = ROOT / "outputs" / "core"
    ref = out / "reference"
    ref.mkdir(parents=True, exist_ok=True)
    entry = cohorts.entry_table().sort_values("caseid")
    json.dump({
        "analysis_frame_21": fp(pd.read_pickle(ROOT / "outputs" / "ANC8_analysis_frozen.pkl")),
        "analysis_frame": fp(pd.read_pickle(ROOT / "outputs" / "enhanced" / "ANC8_analysis_frozen_v2.pkl")),
        "anc_entry": fp(entry.reset_index(drop=True)),
        "partition": {"development": lib.DEV_DIGEST, "held_out": lib.HELD_DIGEST, "folds": lib.FOLD_DIGEST},
    }, open(ref / "fingerprints.json", "w"), indent=2)
    shutil.copy2(ROOT / "outputs" / "notebook3_explainability_handoff" / "predictor_architecture.json",
                 ref / "predictor_architecture.json")

    rows = []
    for job in lib.grid_jobs():
        meta = lib.load_cell(core, job.set, job.rung, job.model)["meta"]
        rows.append({"set": job.set, "rung": job.rung, "model": job.model, "n_predictors": meta["n_predictors"],
                     "dev_AP": meta["dev_metrics"].get("AP_seed_mean", meta["dev_metrics"]["AP"]),
                     "held_AP": meta["held_metrics"]["AP"], "held_AUROC": meta["held_metrics"]["AUROC"],
                     "params": json.dumps(meta["params"])})
    pd.DataFrame(rows).to_csv(ref / "expected_results.csv", index=False)

    imp = pd.read_csv(ROOT / "outputs" / "explain" / "importance.csv")
    imp[(imp.set == "s21") & imp.model.isin(MODELS)].to_csv(ref / "explain_importance.csv", index=False)
    s = json.load(open(ROOT / "outputs" / "scenarios" / "scenarios.json"))
    json.dump({"logistic": {r: b["gain"][-1] for r, b in s["by_model"]["logistic"]["rungs"].items()}},
              open(ref / "levers_national.json", "w"), indent=2)


def main():
    # executed/ holds the notebooks as run on the study's machine: kept across rebuilds
    for sub in ("notebooks", "src", "scripts", "reference", "data"):
        shutil.rmtree(OUT / sub, ignore_errors=True)
    OUT.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "src" / "anc8", OUT / "src" / "anc8", ignore=shutil.ignore_patterns("__pycache__"))
    (OUT / "scripts").mkdir()
    for s in SCRIPTS:
        shutil.copy2(ROOT / "scripts" / s, OUT / "scripts" / s)
    (OUT / "data").mkdir()
    (OUT / "data" / "README.md").write_text(full.DATA_README, encoding="utf-8")
    (OUT / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")
    (OUT / ".gitignore").write_text(full.GITIGNORE, encoding="utf-8")
    (OUT / "README.md").write_text(README, encoding="utf-8")
    write_reference(OUT)

    nbs = {
        "00_start_here": nb00(), "01_cohort_outcomes_and_the_21": nb01(), "02_analysis_frame": nb02(),
        "03_split_and_folds": nb03(),
        "04_logistic_regression": tuning_nb("04", "Logistic regression",
            "A weighted sum of the predictors, turned into a chance: the plain baseline every other model must beat. "
            "It is regularised (L2), and the one setting tuned is how strongly.",
            "Numbers: median fill for missing values, then scaled to mean 0 and standard deviation 1. "
            "Categories: the most frequent level fills a missing value, then one column per level (one-hot)."),
        "05_random_forest": tuning_nb("05", "Random Forest",
            "Hundreds of decision trees, each grown on a bootstrap sample of women and a random share of the "
            "predictors at every split, averaged. It needs no scaling and finds interactions by itself.",
            "Numbers: median fill. Categories: the most frequent level fills a missing value, then each level becomes "
            "an integer code the trees split on."),
        "06_xgboost": tuning_nb("06", "XGBoost",
            "Gradient boosting: small trees added one at a time, each correcting the last. It is fitted on one "
            "thread everywhere, because its row and column sampling depends on the thread count, and a result that "
            "followed the machine could not be reproduced.",
            "Numbers: median fill. Categories: the most frequent level fills a missing value, then integer codes."),
        "07_evaluation": nb07(), "08_explainability": nb08(), "09_levers_and_drivers": nb09(),
    }
    for name, cells in nbs.items():
        write_nb(OUT / "notebooks" / f"{name}.ipynb", cells)
    print(f"wrote {OUT}: {len(nbs)} notebooks")


README = """# Reproducing the study's models

**What this adds to the 21-predictor analysis of notebooks 1 and 2:** it rebuilds that analysis's logistic regression, random forest and XGBoost from ETIR8AFL.DTA alone, tuned over the same prespecified grids, and extends them from ANC8+ to all three rungs (ANC1+, ANC4+ and ANC8+, with age at the birth in place of current age), adding exact logistic-regression and TreeSHAP explanations, g-computation planning levers and exact regional decompositions, every step checked against the study's own results.

Notebooks that rebuild, from the Ethiopia DHS 2024-25 Individual Recode, the models the
study's planning studio runs on: the cohort and the ANC1+, ANC4+ and ANC8+ outcomes, the 21
predictors, the split, logistic regression, random forest and XGBoost at each rung (tuned over
the grid the study fixed in advance), their evaluation, their explanations and the planner's
levers. About half an hour in all.

**Start with `notebooks/00_start_here.ipynb`.** It lists what to install, where the survey
file goes and the run order. To run everything from the command line:
`python scripts/run_notebooks.py` (executed copies go to `executed/`).

## How the notebooks check themselves

Each notebook ends with checks against the study's own results in `reference/`: the content
fingerprints of the analysis frames, the digests of the split, and every model's setting and
development and held-out average precision, its explanations and the levers' effects. A run on
the study's software versions reproduces them exactly.

## Everything else the study tried

`reproduction_full/` rebuilds the whole model library (other predictor sets, eleven model
families, recalibration, ensembles, networks), and `research_record/` records what all of it
found. Neither is needed for these models.

## Layout

```
notebooks/        00-09
src/anc8/         the analysis package (every step is a documented function)
scripts/          the stage scripts some notebooks run, and run_notebooks.py
reference/        the study's results, for the checks
executed/         the notebooks as run from the survey file on the study's machine (every check passed)
data/             put ETIR8AFL.DTA here (not included; see data/README.md)
requirements.txt  the software versions the study used
```
"""


if __name__ == "__main__":
    main()
