"""Write the six short notebooks that ship with release/notebooks/.

Called by build_release.py, and runnable on its own:

    python scripts/build_release_notebooks.py [destination]

The notebooks in the repository root are the working record: long, and they
re-run searches. These are the opposite. Each one reads the artifacts the
pipeline already produced, shows the result, and says what was decided and
why. A reader can execute all six end to end and see every number in the
study.

Where a cell would trigger real computation it is written but left inert,
marked with a comment. That keeps the notebook honest
about where the numbers came from without making it a trap to run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _lines(text):
    return text.splitlines(keepends=True)


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(text.strip())}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": _lines(text.strip("\n"))}


def notebook(cells):
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python",
                           "name": "python3"},
            "language_info": {"name": "python", "version": "3.13"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


# The setup cell every notebook opens with. Both layouts are supported: the
# repository, where results live under outputs/, and the release package,
# where they live under artifacts/.
SETUP = '''
import json, sys, warnings
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

HERE = Path.cwd()
ROOT = next(p for p in [HERE, *HERE.parents]
            if (p / "src").exists() or (p / "scripts").exists())
sys.path.insert(0, str(ROOT / "src"))

def art(*parts):
    """A result file, wherever this package puts it."""
    for base in (ROOT / "artifacts", ROOT / "outputs"):
        p = base.joinpath(*parts)
        if p.exists():
            return p
    raise FileNotFoundError("/".join(parts))

def data():
    """The derived analysis dataset."""
    for p in (ROOT / "data" / "ANC8_analysis_frozen_v2.parquet",
              ROOT / "data" / "ANC8_analysis_frozen_v2.pkl",
              ROOT / "outputs" / "enhanced" / "ANC8_analysis_frozen_v2.pkl"):
        if p.exists():
            return pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_pickle(p)
    raise FileNotFoundError("analysis dataset")

def figure(slug):
    """Show a figure the analysis already produced."""
    from IPython.display import Image, display
    for base in (ROOT / "figures", ROOT / "outputs" / "figures"):
        p = base / f"{slug}.png"
        if p.exists():
            return display(Image(str(p)))
    print(f"({slug} not built yet -- run scripts/make_figures.py)")

def wmean(x, w):
    x, w = np.asarray(x, float), np.asarray(w, float)
    return float((x * w).sum() / w.sum())

print("root:", ROOT)
'''


# =========================================================== notebook 1
def nb_cohort():
    c = []
    c.append(md("""
# 1. The cohort, the outcome, and the design that governs everything

The WHO recommends **eight antenatal contacts** during pregnancy. This study
asks what best predicts who attains them in Ethiopia, and treats that as one
rung of a ladder
rather than a single question: reaching care at all (ANC1+), reaching the
previous WHO minimum of four (ANC4+), and reaching eight (ANC8+).

This notebook establishes three things everything else depends on:

1. who is in the cohort and why;
2. that the three outcomes are a nested ladder, derived from one count;
3. that the survey design is respected -- weights, clusters and strata --
   because ignoring it would make every later interval too narrow.
"""))
    c.append(code(SETUP))

    c.append(md("""
## 1.1 The cohort

6,893 women with a recent live birth who could report the number of antenatal
contacts for that pregnancy. Women who could not report it are **excluded, not
imputed**: the outcome is the one thing that cannot be filled in from the
predictors without circularity.
"""))
    c.append(code('''
df = data()
w = (df.v005 / 1e6).to_numpy()
print(f"{len(df):,} women, {df.shape[1]} columns")
print(f"{df.v021.nunique()} sampling clusters in {df.v022.nunique()} strata")
'''))

    c.append(md("""
## 1.2 The ladder

All three outcomes are thresholds of the same contact count, so they are
nested by construction: a woman with eight contacts necessarily has four and
one. The pipeline asserts this rather than assuming it -- a failure would mean
the derivation is wrong, and every cross-rung comparison after it meaningless.
"""))
    c.append(code('''
for rung, k in [("anc1plus", 1), ("anc4plus", 4), ("anc8plus", 8)]:
    print(f"{rung:10s} threshold >= {k:2d}   weighted {wmean(df[rung], w) * 100:5.1f}%"
          f"   unweighted {df[rung].mean() * 100:5.1f}%")

nested = ((df.anc8plus <= df.anc4plus) & (df.anc4plus <= df.anc1plus)).all()
print(f"\\nnested for every woman: {bool(nested)}")
'''))

    c.append(md("""
Weighted and unweighted differ by several points, which is the first sign that
the design matters. The weighted numbers describe Ethiopia; the unweighted
ones describe the women who happened to be interviewed.

## 1.3 Where the women actually are on the ladder

The headline coverage numbers hide the more useful question: of the women who
start, how many continue?
"""))
    c.append(code('''
n = df.anc_contacts.fillna(0).to_numpy()
started, at4 = n >= 1, n >= 4

print(f"reach any contact      {wmean(n >= 1, w) * 100:5.1f}%")
print(f"reach four or more     {wmean(n >= 4, w) * 100:5.1f}%")
print(f"reach eight or more    {wmean(n >= 8, w) * 100:5.1f}%")
print()
print(f"of those who start,  {wmean(n[started] >= 4, w[started]) * 100:4.1f}% reach 4+"
      f"   ({100 - wmean(n[started] >= 4, w[started]) * 100:4.1f}% lost)")
print(f"of those at 4+,      {wmean(n[at4] >= 8, w[at4]) * 100:4.1f}% reach 8+"
      f"   ({100 - wmean(n[at4] >= 8, w[at4]) * 100:4.1f}% lost)")
'''))
    c.append(code('figure("fig01_cascade")'))

    c.append(md("""
**The largest single loss is between the fourth contact and the eighth**, not
at the door. Three quarters of women already reach antenatal care. This is the
finding that shapes the rest of the project, and it needs no model -- it is a
count.

## 1.4 The survey design

The DHS is a stratified, multi-stage cluster sample. Three consequences:

- **weights** (`v005`/1e6) so estimates describe the country;
- **clusters** (`v021`): women in one enumeration area resemble each other, so
  every split and every fold is grouped by cluster -- otherwise a model can
  memorise an area and the test score is optimistic;
- **strata** (`v022`): the held-out set samples clusters *within* stratum, so
  the design survives the split.

The split never looks at the outcome, which is what lets all three rungs share
one partition -- and that is what makes importance comparable across the
ladder later.
"""))
    c.append(code('''
from anc8 import design

train_psus, test_psus = design.make_psu_holdout(df)
dev = df[df.v021.isin(train_psus)]
held = df[df.v021.isin(test_psus)]

print(f"development {len(dev):,} women in {dev.v021.nunique()} clusters")
print(f"held-out    {len(held):,} women in {held.v021.nunique()} clusters")
print(f"clusters shared between them: {len(set(dev.v021) & set(held.v021))}")
print()
for rung in ("anc1plus", "anc4plus", "anc8plus"):
    print(f"{rung:10s} dev {wmean(dev[rung], dev.v005 / 1e6) * 100:5.1f}%"
          f"   held-out {wmean(held[rung], held.v005 / 1e6) * 100:5.1f}%")
'''))

    c.append(md("""
Same partition, same folds, all three rungs, and the same partition
restricted to their women for the ANC-entry cohort and the 24-month window.
Every result in the study is scored on these women.

## 1.5 What is already visible

Attainment is not spread evenly. The spread is the analysis in miniature.
"""))
    c.append(code('''
rows = []
for region, g in df.groupby("region", observed=True):
    i = df.index.get_indexer(g.index)
    rows.append((str(region), wmean(df.anc8plus.to_numpy()[i], w[i]) * 100, len(i)))
for name, pct, k in sorted(rows, key=lambda r: -r[1]):
    print(f"  {name:24s}{pct:5.1f}%   (n={k})")
'''))
    c.append(md("""
Sixty-six percent in Addis Ababa against under four in Somali: a seventeen-fold
difference inside one country. Notebook 6 shows that regions with nearly
identical coverage are failing for **opposite reasons**, which is the finding
with the clearest implication for how programmes should be targeted.
"""))

    c.append(md("""
## 1.6 The official indicator uses a narrower window

The cohort above is every woman whose most recent pregnancy has an ANC count.
The DHS-8 indicator (Guide to DHS Statistics, Table 9.2) counts only live
births and stillbirths in the **24 months** before interview. 28% of the
cohort gave birth 24-35 months earlier, with longer recall -- and in the
north, during the war.

Restricting to the official window reproduces the 2024-25 EDHS report's
regional table closely, which also checks the outcome, weights and region
coding.
"""))
    c.append(code('''
from anc8 import cohorts

edhs = {"Tigray": 57.1, "Afar": 46.2, "Amhara": 62.0, "Oromia": 48.4, "Somali": 12.7,
        "Benishangul-Gumuz": 57.2, "Central Ethiopia": 58.5, "Sidama": 41.5,
        "South West Ethiopia": 48.1, "South Ethiopia": 47.1, "Gambella": 49.2,
        "Harari": 46.5, "Addis Ababa": 94.8, "Dire Dawa": 69.1}
try:
    rec = cohorts.load("recent")
    print(f"recent cohort: {len(rec):,} women, "
          f"{int((rec.pregnancy_outcome == 'stillbirth').sum())} stillbirths")
    print(f"national ANC4+ {np.average(rec.anc4plus, weights=rec.v005) * 100:.1f}%  (EDHS: 53.0%)\\n")
    for r, g in rec.groupby("region", observed=True):
        ours = np.average(g.anc4plus, weights=g.v005) * 100
        print(f"  {str(r):22s} ours {ours:5.1f}   EDHS {edhs[str(r)]:5.1f}   {ours - edhs[str(r)]:+.1f}")
except Exception as exc:
    print("recent cohort needs data/birth_timing.parquet:", exc)
'''))
    c.append(md("""
The 24-month window is used as a sensitivity check on the predictor results.
The second prediction horizon -- the 5,001 women who started ANC -- is the
subject of notebook 5.
"""))
    return notebook(c)


# =========================================================== notebook 2
def nb_predictors():
    c = []
    c.append(md("""
# 2. Predictor value: how many predictors, and which

Which predictors carry the prediction of ANC8+, and of ANC1+ and ANC4+, and
how many are needed? This notebook follows the whole path: from the 6,648
columns of the survey to a candidate pool, then every predictor set the study
tried -- from one variable to the full pool, with the pre-specified
21-predictor set as one of them -- on the same women.

Every comparison holds the model fixed (logistic regression, each set at its
own best regularisation) and varies only the predictors. Sets are built on the
development women; the held-out women score each set once.
"""))
    c.append(code(SETUP + '''
def fvp(*parts):
    return art("feature_value", *parts)

RUNGS = ("anc1plus", "anc4plus", "anc8plus")
'''))

    c.append(md("""
## 2.1 From 6,648 columns to a candidate pool

Most columns cannot be predictors of antenatal care: they were not asked in
this round, describe life after the birth, or are observed for too few
women. The rest are scored on development women only and checked for timing.
"""))
    c.append(code('''
scr = pd.read_csv(art("enhanced", "candidate_screening.csv"))
reason = scr.exclusion_reason.fillna("")
print(f"{len(scr):,} columns in the Individual Recode\\n")
for name, m in [("not collected in this round", reason.str.startswith("not collected")),
                ("entirely missing in the cohort", reason.str.startswith("entirely missing")),
                ("measured at or after the delivery", reason.str.contains("at or after delivery")),
                ("observed for under half the cohort", reason.str.startswith("observed for only")),
                ("administrative", reason.str.contains("administrative"))]:
    print(f"  {name:40s}{int(m.sum()):>6,}")
cand = scr[scr.screen_status == "candidate"]
print(f"\\n  rankable candidates                     {len(cand):>6,}")
reg = pd.read_csv(art("enhanced", "predictor_register_v2.csv"))
new = reg[reg.provenance == "Newly admitted EDHS source variable"]
print(f"  admitted survey variables               {len(new):>6,}")
print(f"  full candidate pool (columns)           {len(reg):>6,}")
rest = cand[~cand.variable.isin(reg.final_variable)]
print(f"\\nnot admitted: {len(rest)}, median univariate AUC {rest.weighted_auc.median():.3f} (0.5 = no signal)")
'''))
    c.append(code('figure("fig14_screening")'))
    c.append(md("""
The strongest columns in the survey are **leaks**: they record the care
itself. "Visited a health facility in the last 12 months" is the clearest --
ANC contacts *are* facility visits. `src/anc8/features.py` lists every such
exclusion with its reason. The strongest legitimate predictor is the
continuous wealth score (univariate AUC 0.755).

The pool has 95 columns, which are 85 distinct variables once copies are
merged (`region` and `v024` are the same fourteen regions). The study selects
from **88**: the 85 plus three constructs only the 21-predictor set has.

## 2.2 The result: every set, on the held-out women
"""))
    c.append(code('''
for rung in RUNGS:
    try:
        h = pd.read_csv(fvp("full", rung, "why21_heldout.csv"))
        b = json.loads(Path(fvp("full", rung, "why21_bootstrap.json")).read_text())
    except FileNotFoundError:
        print(f"{rung}: run scripts/run_why21_heldout.py")
        continue
    print(f"\\n{rung}  (held-out prevalence {h.prevalence.iloc[0]:.3f})")
    for r in h.itertuples():
        k = b.get(r.set)
        vs = (f"  vs 21: {k['d_AP']:+.3f} [{k['d_AP_lo']:+.3f}, {k['d_AP_hi']:+.3f}]"
              if k else "  (reference)")
        print(f"  {r.set:28s} n={r.n_predictors:2d}  AP {r.AP:.3f}  AUROC {r.AUROC:.3f}{vs}")
'''))
    c.append(md("""
- **ANC8+:** 7 of the 21, the 8 selected from the pool, all 21 and the full
  pool land within 0.015 held-out AP; every interval includes zero. **7 to 8
  predictors are enough.**
- **ANC4+ and ANC1+:** the full pool beats the 21 with intervals excluding
  zero; every smaller set falls slightly short. Reaching care depends on many
  small factors.

## 2.3 The 21 on their own
"""))
    c.append(code('''
drop = {r: pd.read_csv(fvp("full", r, "drop_one_within_21.csv")).set_index("predictor").loss
        for r in RUNGS}
tab = pd.DataFrame(drop).sort_values("anc8plus", ascending=False)
print("AP lost when each member is dropped from the 21\\n")
print(tab.to_string(float_format=lambda v: f"{v:+.4f}"))
print("\\nmembers that add nothing:", {r: int((drop[r] <= 0).sum()) for r in RUNGS})
'''))
    c.append(code('figure("fig33_drop_within_21")\nfigure("fig34_why21")'))
    c.append(md("""
Region, pregnancy intention and wealth carry the 21 at every rung. The number
that add nothing grows up the ladder, to 14 of 21 for ANC8+; the greedy path
within the 21 peaks at 7 for ANC8+ and falls after that.

## 2.4 What the rest of the pool adds

A candidate counts only if it adds at least **0.005 AP on average and on at
least 4 of 5 splits**.
"""))
    c.append(code('''
for rung in RUNGS:
    add = pd.read_csv(fvp("full", rung, "add_one_to_21.csv"))
    top = ", ".join(add[add.clears_threshold].predictor.head(6))
    print(f"{rung:9s} {int(add.clears_threshold.sum())}/{len(add)} clear the bar alone   {top}")
'''))
    c.append(code('figure("fig26_add_one")\nfigure("fig27_diminishing_returns")'))
    c.append(md("""
## 2.5 Building from nothing: the tiers

Forward selection over all 88, stopping at the first step that fails the bar.
Tier 1 reaches 90% of the full pool's lift over prevalence; tier 2 is each
further step that still pays.
"""))
    c.append(code('''
for rung in RUNGS:
    d = pd.read_csv(fvp("full", rung, "forward_steps.csv"))
    print(f"\\n{rung}")
    for r in d.itertuples():
        flag = "  (at interview)" if isinstance(r.at_interview, str) and r.at_interview else ""
        print(f"  {r.tier:13s} {r.predictor:34s} AP {r.AP:.4f}  +{r.gain:.4f} "
              f"({r.seeds_positive}/5){flag}")
'''))
    c.append(code('figure("fig28_tier_ladders")\nfigure("fig29_selection_frequency")\nfigure("fig30_heldout_sets")'))
    c.append(md("""
The wealth score is chosen first in every run and region in every run;
pregnancy intention enters for ANC4+ and ANC8+ but not for reaching care.
Bootstrap re-selection keeps wealth (100%), pregnancy intention (90%) and
region (80%); most other places rotate.

## 2.6 How each predictor's value changes up the ladder

Each predictor's value relative to the 21 -- the AP lost when a member is
dropped, or gained when a non-member is added -- as a share of each rung's
ceiling (full-pool AP minus prevalence), so rungs can be compared.
"""))
    c.append(code('''
try:
    m = pd.read_csv(art("predictor_value", "full", "matrix.csv"))
    w = m.pivot(index="predictor", columns="rung", values="marginal_share") * 100
    w["shift"] = w.anc8plus - w.anc1plus
    top = w.loc[w[list(RUNGS)].max(axis=1).sort_values(ascending=False).head(15).index]
    print(top.sort_values("shift").to_string(float_format=lambda v: f"{v:+.1f}"))
except FileNotFoundError:
    print("run scripts/run_predictor_matrix.py")
'''))
    c.append(code('figure("fig35_predictor_rung_matrix")'))
    c.append(md("""
Region and the wealth measures become far more valuable for completing the
schedule; residence, education level and the gap since the previous pregnancy
matter only for reaching care. Notebook 4 shows the same shift with three
independent importance methods.
"""))
    return notebook(c)



# =========================================================== notebook 3
def nb_modelling():
    c = []
    c.append(md("""
# 3. Modelling, tuning, and what tuning actually bought

With the 21 predictors, XGBoost was **not** significantly better than
logistic regression on any metric. When the best of three cannot separate
itself from the simplest, the useful question is whether any algorithm would
do better. This notebook asks it on the full pool: ten model families tuned
with Optuna, an ordinal arm that respects the outcome's structure, and nested
calibration -- and then whether any of that mattered, and whether
preprocessing did.
"""))
    c.append(code(SETUP))

    c.append(md("""
## 3.1 The model zoo

Every family is tuned with Optuna's TPE sampler over the **same** PSU-grouped
folds, so the comparison is like for like.
"""))
    c.append(code('''
OUTCOME = "anc8plus"
dev = pd.read_csv(art("enhanced", OUTCOME, "development_oof_performance.csv"))
dev = dev.sort_values("AP", ascending=False)
print(f"  {'model':28s}{'AP':>8s}{'AUROC':>8s}{'Brier':>8s}{'slope':>8s}"
      f"{'trials':>8s}{'seconds':>9s}")
for r in dev.itertuples():
    print(f"  {r.model:28s}{r.AP:>8.4f}{r.AUROC:>8.4f}{r.Brier:>8.4f}"
          f"{r.Calibration_slope:>8.2f}{r.n_trials:>8.0f}{r.seconds:>9.0f}")
print(f"\\ntotal search time: {dev.seconds.sum() / 3600:.1f} hours")
'''))

    c.append(md("""
Look at the spread in the AP column. The best and worst differ by about 0.02,
after hours of search across ten quite different learning algorithms. That is
the first hint that the algorithm was never the binding constraint.

### Two arms that deserve explanation

**The Explainable Boosting Machine** is a generalised additive model: an
intercept plus one learned curve per predictor. Attribution from it is *exact*,
not a SHAP approximation, and the whole model fits in 27 KB of lookup tables --
which is why the web app can score it in the browser and respond to a slider
instantly.

**The cumulative-link ordinal arm** treats ANC8+ as what it is: a dichotomised
count. It fits P(count >= k) at several thresholds, constrains the pooled score
to be monotone in k, and reads off the threshold wanted. It is the
statistically correct object for a ladder question. It helped in development
and **did not survive the held-out set** -- 0.4022 AP against 0.4274 for plain
binary. It is reported because it is the right object, not because it won.

## 3.2 The chosen hyperparameters
"""))
    c.append(code('''
best = json.loads(Path(art("enhanced", OUTCOME, "best_hyperparameters.json")).read_text())
for model in list(best)[:6]:
    print(f"\\n{model}")
    for k, v in best[model].items():
        print(f"    {k:26s} {v}")
'''))

    c.append(md("""
## 3.3 Did the search buy anything?

This is the question most model comparisons skip. For each tuned parameter,
move it away from the value Optuna chose -- holding everything else at its
tuned setting -- and re-measure. A parameter whose perturbation barely moves
the score was not worth searching over.

Two reference points frame it: **library defaults**, meaning no tuning at all,
and the **Optuna optimum**, which the search paid for.
"""))
    c.append(code('''
try:
    abl = pd.read_csv(art("enhanced", OUTCOME, "hyperparameter_ablation.csv"))

    print("WHAT THE WHOLE SEARCH BOUGHT, PER MODEL\\n")
    for model in abl.model.unique():
        d = abl[(abl.model == model) & (abl.parameter == "(library defaults)")]
        t = abl[(abl.model == model) & (abl.parameter == "(tuned optimum)")]
        if len(d) and len(t):
            print(f"  {model:24s} defaults {d.AP.iloc[0]:.4f} -> tuned {t.AP.iloc[0]:.4f}"
                  f"   gain {t.AP.iloc[0] - d.AP.iloc[0]:+.4f}")

    real = abl[~abl.parameter.astype(str).str.startswith("(")]
    print("\\nWHICH PARAMETERS ACTUALLY MATTER\\n")
    for model in real.model.unique():
        sub = real[real.model == model].groupby("parameter").AP_vs_tuned.min().sort_values()
        print(f"  {model}")
        for name, v in sub.head(6).items():
            bar = "#" * min(36, int(abs(v) * 1000))
            print(f"    {name:24s}{v:+.4f}  {bar}")
        print()
except FileNotFoundError:
    print("run scripts/run_hyperparameter_ablation.py first")
'''))
    c.append(code('figure("fig16_hyperparameters")\nfigure("fig17_tuning_gain")'))

    c.append(md("""
### The number to read this against

Every model's **development** AP ran about **0.08 above its held-out AP**. That
gap is the signature of selecting among many models on the same folds, not of
one model generalising badly.

So a tuning gain smaller than 0.08 is not evidence that the tuned model
generalises better. It is within the noise of the selection process that
produced it. It is the reason the study's attention is on the predictors
rather than on the optimiser.
"""))
    c.append(code('''
held = pd.read_csv(art("enhanced", OUTCOME, "heldout_performance.csv"))
held = held[held.generation.astype(str).str.startswith("V2")].set_index("model")
d = dev.set_index("model")
common = [m for m in d.index if m in held.index]
print(f"  {'model':28s}{'development':>13s}{'held-out':>11s}{'drop':>9s}")
for m in common:
    print(f"  {m:28s}{d.loc[m, 'AP']:>13.4f}{held.loc[m, 'AP']:>11.4f}"
          f"{held.loc[m, 'AP'] - d.loc[m, 'AP']:>+9.4f}")
print(f"\\n  mean drop {np.mean([held.loc[m, 'AP'] - d.loc[m, 'AP'] for m in common]):+.4f}")
'''))
    c.append(code('figure("fig04_leaderboard_anc8plus")'))

    c.append(md("""
## 3.4 Did better preprocessing help?

Imputation and encoding variants, with the predictors, model, folds and
weights held fixed.
"""))
    c.append(code('''
pre = pd.read_csv(art("enhanced", "preprocessing_ablation.csv")).sort_values("AP", ascending=False)
for r in pre.itertuples():
    print(f"  {r.variant:52s} AP {r.AP:.4f}  ({r.AP_vs_original:+.4f})")
'''))
    c.append(md("""
The best variant buys about **+0.003 AP**, an order of magnitude less than the
choice of predictors.

## 3.5 Refitting, if you want to

These are written out rather than run, so this notebook stays a quick read.

```python
# !python scripts/run_pipeline.py --outcome anc8plus
# !python scripts/run_hyperparameter_ablation.py --outcome anc8plus
```

Logistic regression and LightGBM give identical predictions on any number of
CPU threads. XGBoost does not: at a fixed thread count it is deterministic,
but changing the count moved ANC8+ development AP between 0.506 and 0.518. So
a different machine will reproduce the logistic and LightGBM numbers closely
and the XGBoost ones only to about 0.01 AP -- which is also a reminder that
several of the gaps between models on the leaderboard are smaller than that.
"""))
    return notebook(c)


# =========================================================== notebook 4
def nb_evaluation():
    c = []
    c.append(md("""
# 4. Evaluation, evidence, and the ladder

Two questions, kept apart because they have different answers:

1. **On the held-out set, does the full-pool model beat the 21-predictor
   XGBoost?** This test set cannot tell.
2. **Does the full pool beat the 21 in general?** Yes, by repeated splitting,
   consistently and measurably.

Then the ladder: how what matters changes as the bar rises from reaching care
at all to completing the schedule.
"""))
    c.append(code(SETUP))

    c.append(md("""
## 4.1 Held-out performance

One held-out set of 1,375 women, never touched during development.
"""))
    c.append(code('''
OUTCOME = "anc8plus"
h = pd.read_csv(art("enhanced", OUTCOME, "heldout_performance.csv")).sort_values("AP", ascending=False)
print(f"  {'model':34s}{'AP':>8s}{'AUROC':>8s}{'Brier':>8s}{'slope':>8s}{'sens':>7s}{'spec':>7s}")
for r in h.itertuples():
    print(f"  {r.model[:32]:34s}{r.AP:>8.4f}{r.AUROC:>8.4f}{r.Brier:>8.4f}"
          f"{r.Calibration_slope:>8.2f}{r.Sensitivity:>7.2f}{r.Specificity:>7.2f}")
'''))

    c.append(md("""
Read the **calibration slope** column next to AUROC. A model can rank women
well and still produce probabilities that are too extreme; a slope well below 1
means exactly that, and a user reading those numbers as rates would be misled.
Discrimination and calibration are different properties and this table reports
both.
"""))
    c.append(code('figure("fig05_calibration")'))

    c.append(md("""
## 4.2 The comparison, and its uncertainty

Paired stratified-PSU bootstrap: resample clusters within strata, recompute
both models on the same resample, take the difference. Resampling *individuals*
would treat 1,375 correlated women as independent and produce an interval far
too narrow.
"""))
    c.append(code('''
ci = json.loads(Path(art("enhanced", OUTCOME, "paired_bootstrap_ci.json")).read_text())
print(f"{ci['champion']}  vs  {ci['baseline']}\\n")
for key, label in (("d_AP", "AP"), ("d_AUROC", "AUROC")):
    d = ci[key]
    verdict = "excludes zero" if ci.get(f"{key}_excludes_zero") else "INCLUDES ZERO"
    print(f"  {label:6s} {d['point']:+.4f}  [{d['lo']:+.4f}, {d['hi']:+.4f}]   {verdict}")
'''))
    c.append(code('figure("fig07_bootstrap")'))

    c.append(md("""
**The AP interval includes zero.** One held-out set of this size cannot resolve
a difference this small, and no amount of extra modelling will change that. It
is stated here rather than buried, because the alternative -- quoting only the
evidence that agreed -- is how this kind of analysis goes wrong.

## 4.3 The evidence that does carry the claim

Twenty independent stratum-preserving splits, each refit from scratch. This
answers a different question: not "how uncertain is this one test set" but
"does the full pool win generally".
"""))
    c.append(code('''
s = json.loads(Path(art("enhanced", OUTCOME, "stability_summary.json")).read_text())
print(f"model: {s['model']}, {s['n_seeds']} independent splits")
print(f"the {s['n_original_predictors']}-predictor set vs the {s['n_enhanced_predictors']}-column full pool\\n")
for k in ("AP", "AUROC"):
    d = s[k]
    print(f"  {k:6s} 21 {d['original_mean']:.4f} -> full pool {d['enhanced_mean']:.4f}")
    print(f"         gain {d['delta_mean']:+.4f} [{d['delta_lo']:+.4f}, {d['delta_hi']:+.4f}]"
          f"   full pool wins {d['seeds_enhanced_better']}/{s['n_seeds']}")
'''))
    c.append(code('figure("fig06_stability")'))

    c.append(md("""
Twenty out of twenty. That is the evidence the claim rests on, and both results
are reported wherever the claim appears.

## 4.4 Where the model works, and where it does not

A national AUROC of 0.78 can hide subgroups at chance.
"""))
    c.append(code('''
sub = pd.read_csv(art("enhanced", OUTCOME, "subgroup_performance.csv"))
sub = sub[sub.n >= 40].sort_values("V2_AUROC")
print(f"  {'subgroup':34s}{'n':>6s}{'21':>8s}{'pool':>8s}")
for r in sub.itertuples():
    flag = "   <-- at or below chance" if r.V2_AUROC < 0.55 else ""
    print(f"  {r.variable + ': ' + str(r.level):34s}{r.n:>6d}{r.V1_AUROC:>8.3f}"
          f"{r.V2_AUROC:>8.3f}{flag}")
'''))
    c.append(code('figure("fig11_subgroups")'))

    c.append(md("""
Several regional subgroups sit at or near chance. Sample sizes are small
(60-150 women), so these are indicative -- but they are the right thing to
check before deploying a national tool regionally. A model that works
nationally and not in the regions with the worst coverage is the wrong tool for
the places that need it most.

## 4.5 Is it worth using at all?

Decision-curve analysis: net benefit against the two default strategies of
treating everyone and treating no one.
"""))
    c.append(code('figure("fig10_decision_curve")'))

    c.append(md("""
## 4.6 The ladder

All three rungs share one split, one set of folds, one predictor pool. Any
difference between them is the outcome, not the data.

**The trap here is average precision.** AP is prevalence-dependent: a model
that ranks at random scores AP equal to the prevalence -- 0.776 on ANC1+ and
0.192 on ANC8+. Comparing raw AP across rungs would say the easy question is
the one a blind guess already wins.
"""))
    c.append(code('''
from anc8 import outcomes as oc

rows = []
for rung in ("anc1plus", "anc4plus", "anc8plus"):
    try:
        d = pd.read_csv(art("enhanced", rung, "heldout_performance.csv"))
    except FileNotFoundError:
        print(f"{rung}: not run yet")
        continue
    d = d[d.generation.astype(str).str.startswith("V2")].set_index("model")
    # the development champion -- choosing on held-out scores would be optimistic
    dev = pd.read_csv(art("enhanced", rung, "development_oof_performance.csv"))
    champ = next(m for m in dev.dropna(subset=["AP"]).sort_values("AP", ascending=False).model
                 if m in d.index)
    b = d.loc[champ].copy()
    b["model"] = champ
    prev = oc.OUTCOMES[rung]["weighted_prevalence"]
    rows.append({"rung": oc.OUTCOMES[rung]["label"], "best model": b.model,
                 "prevalence": prev, "AP": b.AP, "AP lift": b.AP - prev,
                 "AUROC": b.AUROC})
if rows:
    print(pd.DataFrame(rows).to_string(index=False, float_format=lambda v: f"{v:.4f}"))
'''))
    c.append(code('figure("fig18_ladder_performance")'))

    c.append(md("""
Raw AP exaggerates the gap between rungs, because its floor is the
prevalence. AUROC, which has no such floor, still agrees in direction: it
falls from about 0.83 for ANC1+ to about 0.76 for ANC8+. **Reaching care is
genuinely easier to predict than completing it.** Never compare raw AP
across rungs; compare AUROC or lift above the floor.

## 4.7 What changes as the bar rises

Importance is computed three independent ways -- exact additive contributions,
SHAP on the best booster, and drop-one loss -- and normalised to a share within
each rung. A shift has to appear in at least two of the three before it is
reported as a finding.
"""))
    c.append(code('''
try:
    pat = pd.read_csv(art("ladder", "ladder_patterns.csv"))
    for kind in pat.pattern.unique():
        sub = pat[pat.pattern == kind].sort_values("mean_share_shift",
                                                   key=abs, ascending=False)
        print(f"\\n{kind.upper()}\\n")
        for r in sub.head(10).itertuples():
            print(f"  {r.predictor:34s} {r.domain:18s} shift {r.mean_share_shift:+.4f}"
                  f"   ({r.methods_agreeing}/{r.methods_total} methods agree)")
except FileNotFoundError:
    print("run scripts/run_ladder_analysis.py once all three rungs exist")
'''))
    c.append(code('figure("fig19_ladder_importance")\nfigure("fig20_domain_rollup")'))

    c.append(md("""
**Access-limited** predictors matter most for reaching care at all and fade as
the threshold rises. **Engagement-limited** ones do the opposite: they barely
distinguish who gets through the door, and increasingly distinguish who
finishes. That distinction is the practical one, because the two call for
different programmes -- which notebook 6 makes concrete.
"""))
    return notebook(c)


# =========================================================== notebook 5
def nb_horizons():
    c = []
    c.append(md("""
# 5. Two prediction horizons: before ANC, and at ANC entry

Before a woman starts antenatal care, a prediction can use only who she is,
her household and where she lives. Once she has started, it can also use
when her first contact happened. This notebook repeats the predictor-value
study at that second horizon -- the 5,001 women who started ANC and know
their first-contact timing -- for ANC4+ and ANC8+ (every woman at this
horizon has ANC1+).

It uses the same development / held-out split, restricted to these women
(4,017 / 984).
"""))
    c.append(code(SETUP))
    c.append(code('''
from anc8 import cohorts
e = cohorts.load("entry")
print(f"{len(e):,} women, {(e.partition == 'held-out').sum()} held out")
print(f"first contact by 3 months (early ANC): {e.early_anc.mean() * 100:.1f}%")
for rung in ("anc4plus", "anc8plus"):
    ew = e.v005 / 1e6
    print(f"{rung}: {wmean(e[rung], ew) * 100:.1f}% (weighted)")
'''))
    c.append(md("""
## 5.1 Do the same predictors carry the prediction?
"""))
    c.append(code('''
try:
    t = pd.read_csv(art("horizons", "tiers_by_horizon.csv"))
    for (r, h), g in t.groupby(["outcome", "horizon"], sort=False):
        print(f"{r:9s} {h:11s}  " + ", ".join(g.sort_values("step").predictor))
except FileNotFoundError:
    print("run scripts/run_horizons.py")
'''))
    c.append(md("""
## 5.2 What early ANC adds
"""))
    c.append(code('''
try:
    d = pd.read_csv(art("horizons", "early_anc_development.csv"))
    b = json.loads(Path(art("horizons", "heldout_bootstrap.json")).read_text())
    for x in d.itertuples():
        k = b.get(f"{x.outcome} | {x.base} + early ANC vs {x.base}")
        print(f"{x.outcome:9s} + early ANC to {x.base:10s} development {x.AP_without:.3f} -> "
              f"{x.AP_with:.3f} ({x.gain:+.4f}, {x.seeds_positive}/5)"
              + (f"   held-out dAUROC {k['d_AUROC']:+.3f} [{k['d_AUROC_lo']:+.3f}, "
                 f"{k['d_AUROC_hi']:+.3f}]" if k else ""))
except FileNotFoundError:
    print("run scripts/run_horizons.py")
'''))
    c.append(code('figure("fig36_horizons")\nfigure("fig37_early_anc")'))
    c.append(md("""
## 5.3 Is a separate model for the entry horizon worth building?

The same predictor sets fitted on all women (before ANC) and on the ANC-entry
women, both scored on the same 984 held-out women who started ANC.
"""))
    c.append(code('''
try:
    x = pd.read_csv(art("horizons", "cross_horizon.csv"))
    print(x[["outcome", "set", "trained_on", "AP", "AUROC"]]
          .to_string(index=False, float_format=lambda v: f"{v:.3f}"))
except FileNotFoundError:
    print("run scripts/run_horizons.py")
'''))
    c.append(md("""
See `docs/HORIZONS.md` for what these results mean.
"""))
    return notebook(c)


# =========================================================== notebook 6
def nb_insights():
    c = []
    c.append(md("""
# 6. What this means for antenatal care in Ethiopia

Written for someone deciding where to put a budget rather than which model to
choose. Every claim here points at the artifact it came from.

One distinction runs through the whole notebook. The **cascade** results are
descriptive: they count where women are actually lost, and counting requires no
causal assumption. The **model** results are associational: they describe which
women attain care, not what would happen if a woman's circumstances changed.
The first kind is sturdier and is what the strongest recommendations rest on.
"""))
    c.append(code(SETUP))

    c.append(md("""
## 6.1 The binding constraint is not the door

Three quarters of Ethiopian women reach antenatal care. The system then loses
them -- and the largest single loss is between the fourth contact and the
eighth.
"""))
    c.append(code('''
df = data()
w = (df.v005 / 1e6).to_numpy()
n = df.anc_contacts.fillna(0).to_numpy()
started, at4 = n >= 1, n >= 4

print(f"  never reach care at all            {wmean(n < 1, w) * 100:5.1f}% of all women")
print(f"  start but stop before 4            {wmean(started & (n < 4), w) * 100:5.1f}%")
print(f"  reach 4 but stop before 8          {wmean(at4 & (n < 8), w) * 100:5.1f}%")
print(f"  reach 8+                           {wmean(n >= 8, w) * 100:5.1f}%")
print()
print(f"  of those who start,   {wmean(n[started] >= 4, w[started]) * 100:4.0f}% continue to 4+")
print(f"  of those at 4+,       {wmean(n[at4] >= 8, w[at4]) * 100:4.0f}% continue to 8+"
      f"   <-- the largest loss")
'''))

    c.append(md("""
## 6.2 The finding that should change how programmes are targeted

Regions with almost identical ANC8+ coverage are failing for **opposite
reasons**. A single national programme would be wrong for most of them.
"""))
    c.append(code('''
rows = []
for region, g in df.groupby("region", observed=True):
    i = df.index.get_indexer(g.index)
    ni, wi = n[i], w[i]
    st = ni >= 1
    f4 = ni >= 4
    rows.append({
        "region": str(region),
        "reach 8+": wmean(ni >= 8, wi),
        "never start": wmean(ni < 1, wi),
        "stop before 4": wmean(st & (ni < 4), wi),
        "reach 4, stop": wmean(f4 & (ni < 8), wi),
        "stay 1->4": wmean(ni[st] >= 4, wi[st]),
        "stay 4->8": wmean(ni[f4] >= 8, wi[f4]),
    })
casc = pd.DataFrame(rows).sort_values("reach 8+")
print((casc.set_index("region") * 100).to_string(float_format=lambda v: f"{v:5.1f}"))
'''))
    c.append(code('figure("fig02_regional_cascade")'))

    c.append(md("""
Read the table by looking for each region's **largest** loss:

**Somali has an access problem.** Two thirds of women never reach antenatal
care at all. Nothing that improves continuity of care helps them, because they
are not in contact with it. What Somali needs is outreach.

**Central Ethiopia has the opposite problem.** Eighty-six percent of women
reach care -- close to Addis Ababa. But of those who get to four contacts, only
about one in six goes on to eight, the lowest continuation rate in the country.
Building facilities there would solve a problem that is already solved. What
Central Ethiopia needs is retention.

**Sidama loses women early**, before the fourth contact.

A programme designed for Somali would waste its budget in Central Ethiopia, and
one designed for Central Ethiopia would not reach a single Somali woman who
needs it. Both look similar on the headline number.

**Addis Ababa shows the ceiling is reachable**: 95% retained through the first
transition, 70% through the second, under Ethiopian conditions.

## 6.3 Which regions beat their own circumstances?

A region with poor coverage and a poor, rural, low-education population is not
the same problem as a region with poor coverage and an advantaged one. Predict
attainment from **circumstance alone -- with region deliberately withheld** --
and compare to reality.
"""))
    c.append(code('''
try:
    reg = pd.read_csv(art("policy", "regional_performance.csv"))
    for rung in ("anc1plus", "anc4plus", "anc8plus"):
        sub = reg[reg.rung == rung].sort_values("gap", ascending=False)
        if not len(sub):
            continue
        print(f"\\n{rung}")
        print(f"  {'region':24s}{'actual':>9s}{'expected':>10s}{'gap':>9s}")
        for r in sub.itertuples():
            flag = ("  outperforming" if r.gap > 0.05 else
                    "  underperforming" if r.gap < -0.05 else "")
            print(f"  {str(r.region):24s}{r.actual * 100:>8.1f}%"
                  f"{r.expected_from_circumstances * 100:>9.1f}%{r.gap * 100:>+8.1f}{flag}")
except FileNotFoundError:
    print("run scripts/run_policy_analysis.py first")
'''))
    c.append(code('figure("fig21_regional_gap")'))

    c.append(md("""
**Afar is the standout.** It attains far more than its population profile
implies, at every rung. Whatever Afar is doing is worth finding out about from
the Ministry's own records -- this data cannot say what it is, only that
something is working there that the circumstances do not explain.

The mirror image is a region doing worse than its profile implies, which is
where a supply-side problem is most likely to be hiding.

A caution: region was withheld from the model, but predictors correlated with
region were not, so the "expected" column is not a clean counterfactual. Read
the ranking, not the decimal.

## 6.4 How much rests on things a health system can change?

Split the predictors into what a ministry can move -- distance, transport,
insurance, media reach, water and sanitation -- and what it cannot -- wealth,
education, age, parity, household structure. Same folds, same model.
"""))
    c.append(code('''
try:
    dec = pd.read_csv(art("policy", "modifiable_vs_fixed.csv"))
    print(f"  {'rung':10s}{'everything':>13s}{'service factors':>18s}{'circumstance':>15s}")
    for r in dec.itertuples():
        print(f"  {r.rung:10s}{r.all_predictors:>13.3f}{r.modifiable_only:>18.3f}"
              f"{r.fixed_only:>15.3f}")
except FileNotFoundError:
    print("run scripts/run_policy_analysis.py first")
'''))
    c.append(code('figure("fig22_modifiable")'))

    c.append(md("""
Service factors carry more of the signal for **reaching care at all** than for
**completing the schedule**. That is consistent with the cascade: getting
through the door is partly a supply problem, and the losses further along are
driven by things this survey measures as circumstance.

It is a decomposition of predictive signal, not of causal effect. It says where
to look, not what to do.

## 6.5 Who is left behind once they are already in the system

The cleanest equity comparison in the data: among women who have **already
reached four contacts** -- so, women the system has demonstrably reached and
who have demonstrably engaged -- who goes on to eight?
"""))
    c.append(code('''
sub = df[at4]
nn, ww = n[at4], w[at4]
for var in ("wealth_quintile", "residence", "maternal_education"):
    if var not in sub:
        continue
    print(f"\\n{var}")
    for lev, g in sub.groupby(var, observed=True):
        i = sub.index.get_indexer(g.index)
        if len(i) < 25:
            continue
        print(f"  {str(lev):26s}{wmean(nn[i] >= 8, ww[i]) * 100:5.1f}%   (n={len(i)})")
'''))
    c.append(code('figure("fig03_continuation_equity")'))

    c.append(md("""
A woman in the richest fifth who reaches four contacts is about **two and a
half times** as likely to complete the schedule as an equally-engaged woman in
the poorest fifth. Both have already shown they will attend. The difference is
what it costs them to keep attending -- transport paid eight times instead of
four, days of work lost, childcare.

That points at the practical barriers to *repeat* visits rather than at whether
women value antenatal care. They have already demonstrated that they do. It is
also a narrower and cheaper problem than generalised demand creation.

## 6.6 If a programme can only reach a fraction of women, who?
"""))
    c.append(code('''
try:
    b = pd.read_csv(art("policy", "risk_bands.csv"))
    print(f"  {'predicted risk':16s}{'women':>8s}{'share':>9s}{'actual 8+':>12s}")
    for r in b.itertuples():
        print(f"  {r.band:16s}{r.n:>8d}{r.population_share * 100:>8.1f}%"
              f"{r.actual_rate * 100:>11.1f}%")
except FileNotFoundError:
    print("run scripts/run_policy_analysis.py first")
'''))
    c.append(code('figure("fig23_risk_bands")'))

    c.append(md("""
The band just below the operating threshold is the group a capacity-limited
programme can realistically move: women whose predicted attainment is low but
not hopeless. The lowest band is large and hard to shift; the highest needs no
help.

The model ranks women correctly about 78% of the time, which is useful for
directing attention across a population and far too blunt for a decision about
an individual woman.

## 6.7 What to take away

1. **Stop treating ANC8 coverage as one national problem.** Target by where in
   the cascade each region loses women, not by its headline coverage.
2. **Somali, Oromia and Afar need outreach** -- a third or more of women never
   make contact at all.
3. **Central Ethiopia, Tigray, South Ethiopia and Sidama need retention.**
   Continuation from four contacts to eight is where the national number will
   move.
4. **The cost of repeat attendance looks like a binding constraint** for poorer
   women who have already engaged.
5. **Addis Ababa's continuation rates show the ceiling is reachable** within
   Ethiopia -- 95% and 70% at the two transitions.
6. **Find out what Afar is doing.** It outperforms its population profile at
   every rung, and this data cannot say why.

And two cautions worth repeating. These are patterns, not causes. And the
predictions are moderately accurate, not precise -- see `docs/LIMITATIONS.md`,
which states what this analysis cannot support rather than leaving it to be
discovered.
"""))

    c.append(md("""
## 6.8 What the war did to antenatal care in Tigray

The cohort reaches back to births in mid-2021, so many Tigrayan women in it
were pregnant during the war (Nov 2020 - Nov 2022). No pre-war pregnancy is
in the survey, so the comparison is wartime against post-war. Exposure is assigned
by the calendar window of the pregnancy, with dates and sources in
`docs/conflict_windows.csv`.

The estimate is a difference-in-differences. Tigray's change from wartime to
post-war pregnancies, minus the **within-region** change in peaceful regions
over the same calendar periods. The peaceful regions absorb the national
trend and the extra recall error of older births.
"""))
    c.append(code('''
try:
    dd = pd.read_csv(art("wartime", "tigray_difference_in_differences.csv"))
    main = dd[(dd.window_shift_months == 0) & (dd.controls == "peaceful regions")]
    print(f"Tigray: {int(main.tigray_during_n.iloc[0])} wartime, "
          f"{int(main.tigray_after_n.iloc[0])} post-war pregnancies\\n")
    for r in main.itertuples():
        print(f"  {r.measure:11s} {r.tigray_during * 100:5.1f}% -> {r.tigray_after * 100:5.1f}%"
              f"   elsewhere {r.control_change_within_region * 100:+5.1f} pts"
              f"   DiD {r.did * 100:+5.1f} [{r.lo * 100:+.1f}, {r.hi * 100:+.1f}]")
    rob = dd[dd.measure == "anc4plus"]
    print(f"\\nANC4+ effect across window shifts and control groups: "
          f"{rob['did'].min() * 100:+.1f} to {rob['did'].max() * 100:+.1f} pts")
except FileNotFoundError:
    print("run scripts/run_wartime_analysis.py first")
'''))
    c.append(code('figure("fig31_tigray_did")\nfigure("fig32_regional_gap_cohort")'))
    c.append(md("""
Tigray against every region, over the same two calendar periods:
"""))
    c.append(code('''
try:
    rp = pd.read_csv(art("wartime", "region_by_war_period.csv"))
    w = rp.pivot(index="region", columns="period", values="anc4plus")
    w["change"] = w["after"] - w["during"]
    print((w.sort_values("change", ascending=False) * 100)
          .to_string(float_format=lambda v: f"{v:5.1f}"))
except FileNotFoundError:
    print("run scripts/run_wartime_analysis.py first")
'''))
    c.append(code('figure("fig38_tigray_regions_by_period")'))
    c.append(md("""
**The war's damage was at the door.** About one wartime pregnancy in five in
Tigray received no antenatal care at all, against one in thirteen after the
ceasefire. Recovery brought women back to four contacts but not to eight. So
post-war Tigray now does better than its circumstances imply at reaching care,
and still falls short on completing it -- a retention problem, like Central
Ethiopia.

Women displaced or killed are not in the survey, and some areas were too
insecure to survey, so this almost certainly understates the wartime damage.
"""))
    return notebook(c)


NOTEBOOKS = {
    "01_cohort_and_outcome.ipynb": nb_cohort,
    "02_predictor_value.ipynb": nb_predictors,
    "03_modelling_and_tuning.ipynb": nb_modelling,
    "04_evaluation_and_the_ladder.ipynb": nb_evaluation,
    "05_prediction_horizons.ipynb": nb_horizons,
    "06_insights_and_policy.ipynb": nb_insights,
}

INDEX = """# Notebooks

Six, in order. Each reads the artifacts the pipeline produced; the expensive
stages are written out as comments.

| | | |
|---|---|---|
| 1 | `01_cohort_and_outcome.ipynb` | who is in the cohort, the nested outcome ladder, and the survey design that governs every later interval |
| 2 | `02_predictor_value.ipynb` | from 6,648 columns to a pool, every predictor set on held-out women, the drop study, and value across the ladder |
| 3 | `03_modelling_and_tuning.ipynb` | ten model families, the search, and the uncomfortable question of what tuning actually bought |
| 4 | `04_evaluation_and_the_ladder.ipynb` | held-out performance, two kinds of evidence, subgroups, and how importance shifts up the ladder |
| 5 | `05_prediction_horizons.ipynb` | before ANC starts vs at ANC entry, and what early ANC adds |
| 6 | `06_insights_and_policy.ipynb` | what it means for antenatal care in Ethiopia, including the Tigray war |

Start at 1 if you want the argument. Start at 6 if you want the findings.

Run them with `jupyter lab` from the package root, or non-interactively:

```bash
python scripts/execute_nb.py notebooks/01_cohort_and_outcome.ipynb
```
"""


def build(dest: Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    for name, fn in NOTEBOOKS.items():
        (dest / name).write_text(json.dumps(fn(), indent=1), encoding="utf-8")
    (dest / "README.md").write_text(INDEX, encoding="utf-8")
    return len(NOTEBOOKS)


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "release" / "notebooks"
    print(f"{build(out)} notebooks -> {out}")
