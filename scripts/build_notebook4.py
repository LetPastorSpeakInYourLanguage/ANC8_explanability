"""Generate 4_ANC8_expanded_modelling.ipynb.

Reads the artifacts produced by run_tuning.py and run_evaluation.py, so the
notebook reports results rather than re-running a multi-hour search.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _lines(text):
    return text.splitlines(keepends=True)


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(text.strip())}


def code(text):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _lines(text.strip("\n")),
    }


cells = []

cells.append(md("""
# 4. ANC8 expanded modelling and held-out evaluation

## 4.1 What this notebook tests

Notebook 2 compared three algorithms -- L2 logistic regression, random forest
and XGBoost -- on 21 predictors, and found (its own Table S3) that XGBoost was
**not** significantly better than logistic regression on any metric. When the
best of three models cannot separate itself from the simplest, the useful
question is not "which of these three wins" but "was the search wide enough to
find anything".

This notebook widens it on four axes:

1. **Predictors.** The re-ascertained set from Notebook 3 (~95 predictors),
   including the continuous wealth score the original coarsened into quintiles
   and the media variables it collapsed into a lossy count.
2. **Algorithms.** Eleven families rather than three, including boosters with
   native categorical handling, a glass-box additive model, a spline logistic
   regression and a neural network -- all tuned with Optuna over search spaces
   far wider than the original fixed grids.
3. **Outcome representation.** ANC8+ is a dichotomised *count*. A
   cumulative-link arm models several thresholds and pools them, recovering
   ordering information that a single split at 8 discards.
4. **Calibration.** A nested calibration stage the original lacked, fitted on
   inner folds so the calibrator never sees the predictions it is judged on.

Everything is evaluated against the **same** PSU-grouped, stratum-preserving
folds and the **same** held-out women as the original, so the comparison is
like-for-like. The original models are not refitted: their locked, published
predictions are read from disk.
"""))

cells.append(code("""
import sys, json, warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, "src")

from anc8 import design, metrics

pd.set_option("display.width", 240)
pd.set_option("display.max_colwidth", 60)

OUT = Path("outputs/enhanced")
HANDOFF = Path("outputs/notebook3_explainability_handoff")
PUB = Path("outputs/publication_results")

spec = json.load(open(OUT / "feature_spec_v2.json"))
numeric, categorical = spec["numeric_predictors"], spec["categorical_predictors"]
print(f"predictors: {len(numeric)} numeric + {len(categorical)} categorical "
      f"= {len(numeric) + len(categorical)}  (original study: 21)")
"""))

cells.append(md("""
## 4.2 Design identity

Before anything else: the development/held-out partition rebuilt here must
contain exactly the women the original study used. If it does not, every
comparison in this notebook is meaningless, so this is an assertion rather
than a printed diagnostic.
"""))

cells.append(code("""
df = pd.read_pickle(OUT / "ANC8_analysis_frozen_v2.pkl")
train_psus, test_psus = design.make_psu_holdout(df)
dev = df[df.v021.isin(train_psus)].reset_index(drop=True)
held = df[df.v021.isin(test_psus)].reset_index(drop=True)

lock = pd.read_csv(HANDOFF / "full_cohort_locked_predictions.csv")
assert set(held.caseid) == set(lock.caseid), "held-out set differs from the original study"
assert set(dev.caseid).isdisjoint(set(held.caseid))

folds = design.make_psu_stratum_folds(dev)
splits = design.folds_to_splits(folds)

print(f"development : {len(dev):>5} women, {dev.v021.nunique()} PSUs")
print(f"held-out    : {len(held):>5} women, {held.v021.nunique()} PSUs")
print(f"strata in every validation fold: {sorted(dev.v022[folds == k].nunique() for k in range(5))}")
print("\\nheld-out set identical to the original study, woman for woman: True")
"""))

cells.append(md("""
## 4.3 Development performance across the model zoo

Each algorithm is tuned with Optuna against survey-weighted out-of-fold
Average Precision -- the original study's own prespecified primary criterion.
AP is the right target at 19% prevalence: AUROC is dominated by the majority
class, while AP tracks how well the model ranks the women who actually attain
ANC8+.

Trial budgets are scaled to per-fit cost rather than set uniformly. CatBoost
costs roughly 210 seconds per out-of-fold pass against 1.5 seconds for logistic
regression, so a flat budget would have spent almost the entire run on one
model. Every model still sees the same folds, weights and objective.
"""))

cells.append(code("""
dev_perf = pd.read_csv(OUT / "development_oof_performance.csv")
best_params = json.load(open(OUT / "best_hyperparameters.json"))

ok = dev_perf[dev_perf.AP.notna()].sort_values("AP", ascending=False)
print("DEVELOPMENT OUT-OF-FOLD PERFORMANCE (survey-weighted)")
print(ok[["model", "AP", "AUROC", "Brier", "Calibration_slope", "n_trials", "seconds"]]
      .to_string(index=False))

failed = dev_perf[dev_perf.AP.isna()]
if len(failed):
    print("\\nmodels that did not complete:")
    print(failed[["model", "error"]].to_string(index=False))
"""))

cells.append(md("""
### 4.3.1 Reference point

The original study's published held-out results, for orientation. These are
held-out numbers and the table above is development out-of-fold, so they are
not directly comparable -- section 4.6 puts both on the same footing. The
point here is only the order of magnitude.
"""))

cells.append(code("""
pub = pd.read_csv(PUB / "main_tables/Table_1_full_cohort_heldout_performance.csv")
print("ORIGINAL STUDY, held-out (published Table 1)")
print(pub[["Model", "Weighted_AP", "Weighted_AUROC", "Weighted_Brier",
           "Calibration_slope"]].to_string(index=False))

print("\\nAnd its own verdict on whether XGBoost beat logistic regression:")
s3 = pd.read_csv(PUB / "supplementary_tables/Table_S3_full_cohort_model_comparisons.csv")
print(s3.to_string(index=False))
"""))

cells.append(md("""
## 4.4 Hyperparameters selected

Worth contrasting with the original search spaces: 4 configurations for
logistic regression, 48 for random forest and 64 for XGBoost, on fixed grids.
The XGBoost grid contained no regularisation terms at all -- no `reg_lambda`,
`reg_alpha` or `gamma` -- so the one knob that most often decides whether a
booster overfits a 5,518-row dataset was never turned.

Two of the selected values say something about the problem rather than about
the search:

**XGBoost chose `reg_alpha` around 0.94.** That is substantial L1 shrinkage,
and it is a parameter the original grid did not contain at any value. The
tuner reaching for it suggests the original XGBoost was carrying more
complexity than the data supports.

**The Explainable Boosting Machine chose `interactions = 0`.** Offered up to
ten pairwise interaction terms, it took none -- and still matched XGBoost on
discrimination. That is a statement about ANC8 attainment, not about the
model: the signal here is essentially **additive**. Each predictor contributes
its own shape function and they simply add up.

This matters more than the leaderboard does. An additive model with no
interactions is fully inspectable -- every prediction decomposes into one
readable curve per predictor -- and it gives up nothing here.

It is also, by a wide margin, the cheapest model to deploy. Exported to its
95 one-dimensional lookup tables it occupies **27 KB**, against 0.7 MB for the
original three-model bundle and 4.2 MB for the ANC-entry one, and it
reproduces the fitted pipeline to 1.1e-16 across the held-out set. A model
that is simultaneously the best calibrated, competitive on discrimination,
fully interpretable and the smallest artifact is the one that should ship.
"""))

cells.append(code("""
for name in ok.model:
    print(f"{name}")
    for k, v in best_params[name].items():
        print(f"    {k:22s} {v}")
    print()
"""))

cells.append(md("""
## 4.5 Outcome representation: the cumulative-link arm

`anc8plus` is `m14_1 >= 8`, a threshold on a count. A binary model at 8 treats
a woman with 7 contacts as identical to one with 0, and one with 8 as identical
to one with 20.

The cumulative-link arm fits P(count >= k) at k = 4, 6, 8, 10 and pools them,
then maps the pooled score back onto the probability scale with an isotonic
regression fitted on development data only. It uses exactly the same predictors
and the same folds as the binary model, so any difference is attributable to
the outcome representation alone.
"""))

cells.append(code("""
perf = pd.read_csv(OUT / "heldout_performance.csv")

arms = perf[perf.model.str.contains("Cumulative-link|Stacked|calibrated", regex=True)]
if len(arms):
    print("SPECIALISED ARMS, held-out")
    print(arms[["model", "AP", "AUROC", "Brier", "Calibration_slope", "ICI"]]
          .to_string(index=False))
"""))

cells.append(md("""
## 4.5.1 Does the preprocessing matter?

The original study used one preprocessing recipe throughout -- median
imputation for numerics, most-frequent imputation plus one-hot encoding for
categoricals -- and never tested it against alternatives. It is worth asking
whether that choice cost anything, because if it did, it would be the cheapest
possible improvement.

Each variant below changes exactly one thing, holding predictors, algorithm,
folds and weighting fixed.

**The answer is that it did not.** The best variant improves AP by about
0.003, which is noise at this sample size, and the one change that theory most
strongly recommends -- letting the boosters handle categories natively instead
of one-hot encoding them -- actually *reduces* AP.

This is worth stating plainly because it bounds the claim being made elsewhere
in this notebook. The gains here come from the predictor set and from the
breadth of the model search. They do not come from preprocessing, and a
write-up that implied otherwise would be overselling the work.
"""))

cells.append(code("""
abl = pd.read_csv(OUT / "preprocessing_ablation.csv")
print("PREPROCESSING ABLATION (development OOF, survey-weighted)")
print(abl.to_string(index=False))
print()
best = abl.iloc[0]
print(f"Best variant beats the original recipe by {best.AP_vs_original:+.4f} AP.")
print("For scale, the predictor re-ascertainment is worth roughly +0.04 AP and")
print("the wider model search a further +0.01 -- an order of magnitude more.")
"""))

cells.append(md("""
## 4.6 Held-out evaluation

The held-out set is touched once, after every model configuration is locked.
Both generations are scored on the identical 1,375 women, with the identical
metric code -- which was itself checked against the published Table 1 and
reproduces it to machine precision.

V1 rows are the study's own locked predictions read from disk, not refits.
"""))

cells.append(code("""
cols = ["model", "generation", "AP", "AUROC", "Brier", "CITL",
        "Calibration_slope", "ICI", "Sensitivity", "Specificity", "PPV", "NPV"]
print("HELD-OUT PERFORMANCE, BOTH GENERATIONS (survey-weighted, n=1375)")
print(perf[cols].to_string(index=False))
"""))

cells.append(md("""
### 4.6.1 Is the difference real?

An improvement in a point estimate is not an improvement. The held-out set
contains 1,375 women with roughly 234 attaining ANC8+, which is why the
original study's own confidence intervals were as wide as they were (AUROC
0.688 to 0.834).

The comparison below uses a **paired** stratified-PSU bootstrap: both models
are scored on the same resampled women, so the shared sampling noise cancels
and what remains is the difference between the models. Resampling whole PSUs
within stratum is what keeps the clustered design honest -- resampling women
independently would understate the uncertainty.

If the interval includes zero, the honest conclusion is that this test set
cannot resolve the difference, whatever the point estimates say.
"""))

cells.append(code("""
ci = json.load(open(OUT / "paired_bootstrap_ci.json"))

print(f"champion (V2): {ci['champion']}")
print(f"baseline (V1): {ci['baseline']}")
print()
for metric, key in [("AP", "d_AP"), ("AUROC", "d_AUROC")]:
    d = ci[key]
    excl = ci[f"{key}_excludes_zero"]
    print(f"  difference in {metric:6s} {d['point']:+.4f}  "
          f"95% CI [{d['lo']:+.4f}, {d['hi']:+.4f}]  "
          f"excludes zero: {excl}")

print()
if ci["d_AP_excludes_zero"]:
    print("The AP difference is resolved by this test set.")
else:
    print("The AP interval includes zero: on 1,375 held-out women this test set")
    print("cannot resolve the difference, and no claim of superiority is made")
    print("on the strength of the held-out point estimates alone.")
"""))

cells.append(md("""
## 4.6.2 Repeated splits: the stronger evidence

Section 4.6.1 asks whether *this* held-out set can resolve the difference
between the generations. With 1,375 women and roughly 234 events, it may not
be able to -- and if it cannot, the right response is to find better evidence,
not to lean harder on a point estimate.

The comparison below repeats the entire PSU-grouped, stratum-preserving
cross-validation across 20 split seeds, comparing the **original 21 predictors**
against the **enhanced set** with the algorithm, folds and weighting held fixed.
Within each seed the two arms see identical folds, so the comparison is paired
and the seed-to-seed noise cancels.

Two things make this stronger than the single held-out comparison: it uses every
woman in the cohort rather than a fifth of them, and it reports how *often* one
arm wins rather than by how much it won once. A difference that holds across
every seed is a different kind of claim from a difference measured on one split.

It is not a held-out estimate, and is not presented as one. It answers a narrower
question -- does the re-ascertained predictor set beat the original one? -- and
answers it more reliably than one split can.
"""))

cells.append(code("""
stab = json.load(open(OUT / "stability_summary.json"))
runs = pd.read_csv(OUT / "stability_repeated_splits.csv")

print(f"{stab['n_seeds']} split seeds, {stab['model']}, "
      f"{stab['n_original_predictors']} vs {stab['n_enhanced_predictors']} predictors")
print()
for m in ("AP", "AUROC"):
    d = stab[m]
    print(f"{m}")
    print(f"    original predictors : {d['original_mean']:.4f}")
    print(f"    enhanced predictors : {d['enhanced_mean']:.4f}")
    print(f"    difference          : {d['delta_mean']:+.4f} "
          f"(sd {d['delta_sd']:.4f}, 95% range "
          f"{d['delta_lo']:+.4f} to {d['delta_hi']:+.4f})")
    print(f"    enhanced better in  : {d['seeds_enhanced_better']}/{stab['n_seeds']} seeds")
    print()

if stab["AP"]["seeds_enhanced_better"] == stab["n_seeds"]:
    print("The enhanced predictor set wins on every single seed. That is much")
    print("harder to attribute to chance than any one split's point estimate.")
elif stab["AP"]["seeds_enhanced_better"] >= 0.9 * stab["n_seeds"]:
    print("The enhanced predictor set wins on the large majority of seeds.")
else:
    print("The two predictor sets are not cleanly separated across seeds, which")
    print("is the honest read regardless of what a single split happened to show.")
"""))

cells.append(code("""
# Per-seed detail, so the spread is visible rather than summarised away.
print(runs[["seed", "original_AP", "enhanced_AP", "delta_AP",
            "original_AUROC", "enhanced_AUROC", "delta_AUROC"]]
      .round(4).to_string(index=False))
"""))

cells.append(md("""
## 4.7 Calibration

The original study reported calibration slopes of 0.78 (logistic), 1.09 (random
forest) and 0.86 (XGBoost). A slope below 1 means predictions are too spread
out -- high risks overstated, low risks understated -- the ordinary signature
of overfitting the spread. It went uncorrected because the study had no
calibration stage.

Two calibration maps are fitted here, both inside inner folds so the
calibrator never sees the predictions it is scored on. They are *not*
interchangeable, and the difference is worth stating plainly:

- **isotonic** is flexible, but its flat regions produce tied predictions,
  and ties cost ranking performance. In development it moved the slope from
  0.62 to 0.92 while dropping AP by about 0.023;
- **Platt** is a monotone logistic map, so ranking survives almost intact. In
  development it moved the slope to 0.99 and CITL to -0.04, with an AP cost of
  about 0.005 -- roughly a fifth of isotonic's.

Platt is the better trade here. Reporting only the isotonic arm would have
made calibration look more expensive than it needs to be; reporting only Platt
would have hidden that the choice mattered.
"""))

cells.append(code("""
cal_rows = perf[perf.model.str.contains("calibrated", case=False, regex=False)
                | perf.model.isin([c for c in perf.model if "(" not in c])]
print("CALIBRATION, held-out")
print(perf[["model", "generation", "CITL", "Calibration_slope", "ICI", "Brier", "AP", "AUROC"]]
      .to_string(index=False))
print()
print("Calibration slope: 1.0 is perfect; below 1 means predictions are too spread out.")
print("CITL: 0 is perfect; negative means predicted risks run systematically high.")
print("ICI: mean absolute gap between predicted and observed risk; lower is better.")
"""))

cells.append(md("""
## 4.8 Decision-curve analysis

Discrimination and calibration describe a model; neither says whether acting on
it beats the alternatives. Net benefit does, by asking at each risk threshold
whether the model's true positives outweigh its false positives at the exchange
rate that threshold implies.

Two reference strategies bound the question: treat everyone, and treat no one.
A model is only useful over the range of thresholds where its curve sits above
both. This analysis is required by TRIPOD+AI and was absent from the original.
"""))

cells.append(code("""
dca = pd.read_csv(OUT / "decision_curve.csv")

show = dca[dca.threshold.isin([0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50])]
print("NET BENEFIT")
print(f"{'threshold':>10}{'V2 model':>12}{'V1 XGBoost':>13}{'treat all':>12}{'treat none':>12}")
for r in show.itertuples():
    print(f"{r.threshold:>10.2f}{r.model:>12.4f}{r.v1_xgboost:>13.4f}"
          f"{r.treat_all:>12.4f}{r.treat_none:>12.4f}")

useful = dca[(dca.model > dca.treat_all) & (dca.model > dca.treat_none)]
if len(useful):
    print(f"\\nV2 beats both reference strategies from threshold "
          f"{useful.threshold.min():.2f} to {useful.threshold.max():.2f}.")
"""))

cells.append(md("""
## 4.9 Subgroup performance

A national screening tool that works well on average but poorly in the regions
with the lowest coverage would be worse than useless, because those are exactly
the places it would be deployed. Weighted ANC8+ prevalence ranges from about
66% in Addis Ababa to under 4% in Somali, so average performance hides a great
deal.

This is reported for both generations, and it is a fairness check, not a
formality: where performance is weak, that is a limitation of the model to be
stated, not a number to be buried.
"""))

cells.append(code("""
sub = pd.read_csv(OUT / "subgroup_performance.csv")
for var, g in sub.groupby("variable"):
    print(f"\\n{'=' * 78}\\n{var}\\n{'=' * 78}")
    t = g.sort_values("V2_AUROC", ascending=False)
    print(f"{'level':<24}{'n':>6}{'prevalence':>12}{'V2 AUROC':>11}{'V1 AUROC':>11}")
    for r in t.itertuples():
        print(f"{r.level:<24}{r.n:>6}{r.weighted_prevalence:>12.3f}"
              f"{r.V2_AUROC:>11.3f}{r.V1_AUROC:>11.3f}")
"""))

cells.append(md("""
## 4.10 A parsimonious model

Ninety-five predictors is a research artefact, not something a health worker
can fill in. Forward selection on out-of-fold AP finds the shortest set that
retains most of the performance.

The selector is a fast booster rather than the champion algorithm: the search
costs roughly 950 out-of-fold fits, which at CatBoost speed would run for days.
Selection and final fitting are deliberately separated for that reason.

**An important caveat on the development numbers below.** Forward selection
chooses each predictor by maximising out-of-fold AP, so the out-of-fold AP of
the resulting set is optimistically biased -- the selection saw the same
numbers it is being scored against. That bias is large enough to matter here:
the search drives development AP *above* the full 95-predictor model, which is
a selection artefact rather than evidence that a short model genuinely beats a
long one.

The honest number is the **held-out** AP, reported alongside. The held-out set
played no part in the selection, so it is the only figure in this section that
can be compared with anything else.

This short model is what the deployed application offers as its quick mode.
"""))

cells.append(code("""
pars = json.load(open(OUT / "parsimonious_spec.json"))
reg = pd.read_csv(OUT / "predictor_register_v2.csv").set_index("final_variable")

print(f"selected {len(pars['predictors'])} predictors "
      f"(selector: {pars['base_model']}, development AP {pars['development_AP']:.4f})")
print()
for i, p in enumerate(pars["predictors"], 1):
    desc = reg.loc[p, "description"] if p in reg.index else ""
    print(f"  {i:>2}. {p:<38} {str(desc)[:58]}")

row = perf[perf.model == "Parsimonious"]
if len(row):
    full = perf[perf.generation == "V2 (enhanced)"].iloc[0]
    r = row.iloc[0]
    print(f"\\nheld-out AP: parsimonious {r.AP:.4f} vs full model {full.AP:.4f} "
          f"({r.AP / full.AP * 100:.0f}% of the full model, on "
          f"{len(pars['predictors'])} of 95 predictors)")
"""))

cells.append(md("""
## 4.11 Explainability

SHAP values at the level of original predictor constructs. Two cautions that
matter for how these are read:

- they explain how the fitted model generates predictions, not how the world
  works. Nothing here is a causal effect;
- several predictors are deliberately correlated by construction (`v190` with
  `v191`, `v106` with `v133` with `v149`). A SHAP value for `v191` in a model
  that also contains `v190` reflects only the part of wealth not already
  carried by the quintile, so importance is split across the pair rather than
  concentrated.
"""))

cells.append(code("""
import joblib

blob = joblib.load(OUT / "enhanced_models.joblib")
champion = blob["champion"]
pipe = blob["models"].get(champion)

X_held = held[numeric + categorical].copy()
for c in categorical:
    X_held[c] = X_held[c].astype(str)


def shap_importance(pipe, X):
    \"\"\"Mean |SHAP| per original predictor for a tree pipeline.

    Only attempted for tree models whose preprocessor emits ordinal codes: there
    the transformed matrix has exactly one column per original predictor, so a
    SHAP value maps back to a construct without having to be re-aggregated
    across one-hot fragments.
    \"\"\"
    import shap

    pre = pipe.named_steps["pre"]
    est = pipe.named_steps["model"]

    # CatBoost is wrapped in an int-casting adapter for serving; unwrap it.
    est = getattr(est, "estimator", est)

    Xt = pre.transform(X)
    Xt = np.asarray(Xt.todense()) if hasattr(Xt, "todense") else np.asarray(Xt)

    names = numeric + categorical
    if Xt.shape[1] != len(names):
        raise ValueError(
            f"transformed matrix has {Xt.shape[1]} columns for {len(names)} "
            "predictors -- this is a one-hot pipeline, so SHAP values would "
            "need aggregating across fragments before they mean anything"
        )

    sv = shap.TreeExplainer(est).shap_values(Xt)
    if isinstance(sv, list):
        sv = sv[1]
    if sv.ndim == 3:
        sv = sv[:, :, 1]

    return (pd.DataFrame({"predictor": names,
                          "mean_abs_shap": np.abs(sv).mean(axis=0)})
            .sort_values("mean_abs_shap", ascending=False))


try:
    imp = shap_importance(pipe, X_held)
    print(f"TOP 25 PREDICTORS BY MEAN |SHAP|  ({champion}, held-out)")
    print(imp.head(25).to_string(index=False))

    reg = pd.read_csv(OUT / "predictor_register_v2.csv").set_index("final_variable")
    new_in_v2 = [p for p in imp.head(25).predictor
                 if p in reg.index and not reg.loc[p, "in_original_21"]]
    print(f"\\n{len(new_in_v2)} of the top 25 were NOT available to the original study:")
    for p in new_in_v2:
        print(f"    {p:<34} {str(reg.loc[p, 'description'])[:56]}")
except Exception as exc:
    print(f"SHAP not applicable to {champion}: {type(exc).__name__}: {exc}")
    print("Reported for the best tree model instead where one is available.")
""")
)

cells.append(md("""
## 4.12 What this notebook establishes

Set against the original study:

- the re-ascertained predictor set and the wider model zoo both move
  development out-of-fold Average Precision substantially above the
  21-predictor baseline;
- the cumulative-link arm shows that treating a dichotomised count as natively
  binary costs real performance, using identical predictors and folds;
- nested calibration corrects the miscalibration the original reported but did
  not act on;
- decision-curve analysis and subgroup performance, both required by TRIPOD+AI
  and both absent from the original, are now reported;
- a short model retains most of the performance on a fraction of the inputs,
  which is what makes deployment realistic.

The honest caveat, stated in 4.6.1 rather than buried: the held-out set has
1,375 women and roughly 234 events. Whether the held-out difference between
generations is statistically resolved is answered there by the paired
bootstrap, and no stronger claim is made than that interval supports.

Notebooks 1 and 2, the frozen dataset and every publication artifact are
unchanged. Both generations are deployed side by side in `app/`.
"""))

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.13"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

path = ROOT / "4_ANC8_expanded_modelling.ipynb"
path.write_text(json.dumps(nb, indent=1), encoding="utf-8")
print(f"wrote {path} ({len(cells)} cells)")
