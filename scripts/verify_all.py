"""End-to-end verification of every claim this project makes.

    python scripts/verify_all.py

Each check either passes or fails loudly. The point is that nothing downstream
is trustworthy if the early gates fail: if the rebuilt held-out set is not the
original's held-out set, every old-versus-new comparison is meaningless, so
that is checked first and hard.

The V1 fidelity checks need the pinned environment and are skipped (reported,
not hidden) when run elsewhere.
"""

from __future__ import annotations

import gzip
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app" / "api" / "_lib"))

HANDOFF = ROOT / "outputs" / "notebook3_explainability_handoff"
PUB = ROOT / "outputs" / "publication_results"
ENHANCED = ROOT / "outputs" / "enhanced"
MODELS = ROOT / "app" / "models"

RESULTS = []


def check(name, condition, detail=""):
    RESULTS.append((name, bool(condition), detail))
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {name}" + (f"  — {detail}" if detail else ""))
    return bool(condition)


def section(title):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


# ---------------------------------------------------------------------------
section("1. DESIGN IDENTITY — the rebuilt split must be the study's locked split")
# ---------------------------------------------------------------------------
from anc8 import design, metrics  # noqa: E402

frozen = pd.read_pickle(ROOT / "outputs" / "ANC8_analysis_frozen.pkl")
base = frozen[frozen.anc8plus.notna()].copy()
train_psus, test_psus = design.make_psu_holdout(base)
dev = base[base.v021.isin(train_psus)]
held = base[base.v021.isin(test_psus)]
lock = pd.read_csv(HANDOFF / "full_cohort_locked_predictions.csv")

check("held-out caseid set identical to the locked split", set(held.caseid) == set(lock.caseid),
      f"n={len(held)}")
check("held-out PSU set identical", set(held.v021) == set(lock.v021))
check("development size matches the locked 5518", len(dev) == 5518, f"n={len(dev)}")
check("no PSU spans development and held-out", set(dev.v021).isdisjoint(set(held.v021)))

folds = design.make_psu_stratum_folds(dev)
splits = design.folds_to_splits(folds)
check("every validation fold contains all 27 strata",
      all(dev.v022[folds == k].nunique() == 27 for k in range(5)))
check("no PSU spans fit and validation within a fold",
      all(set(dev.v021.iloc[f]).isdisjoint(set(dev.v021.iloc[v])) for f, v in splits))

# ---------------------------------------------------------------------------
section("2. METRIC REPRODUCTION — our metric code must reproduce the 21-predictor Table 1")
# ---------------------------------------------------------------------------
pub = pd.read_csv(PUB / "main_tables/Table_1_full_cohort_heldout_performance.csv")
y, w = lock.anc8plus_observed.to_numpy(), lock.survey_weight.to_numpy()

for model, col in [("Logistic regression", "prob_logistic"),
                   ("Random Forest", "prob_random_forest"),
                   ("XGBoost", "prob_xgboost")]:
    m = metrics.probability_metrics(y, lock[col].to_numpy(), w)
    r = pub[pub.Model == model].iloc[0]
    worst = max(abs(m[k] - r[p]) for k, p in
                [("AP", "Weighted_AP"), ("AUROC", "Weighted_AUROC"),
                 ("Brier", "Weighted_Brier"), ("CITL", "CITL"),
                 ("Calibration_slope", "Calibration_slope")])
    check(f"Table 1 reproduced for {model}", worst < 1e-6, f"max|diff|={worst:.2e}")

# ---------------------------------------------------------------------------
section("3. LEAKAGE AUDIT — no delivery-era or refused variable in the full pool")
# ---------------------------------------------------------------------------
if (ENHANCED / "feature_spec_v2.json").exists():
    from anc8 import features

    spec = json.load(open(ENHANCED / "feature_spec_v2.json"))
    preds = set(spec["numeric_predictors"]) | set(spec["categorical_predictors"])

    bad = [c for c in preds if str(c).lower().startswith(
        ("m13", "m14", "m15", "m16", "m17", "m18", "m19"))]
    check("no delivery-era m13*-m19* variables", not bad, str(bad))
    check("no temporality-refused variables reappeared",
          not (set(features.TEMPORAL_EXCLUSIONS) & preds),
          str(sorted(set(features.TEMPORAL_EXCLUSIONS) & preds)))
    check("no outcome variables among predictors",
          not ({"anc8plus", "anc4plus"} & preds))
    check("no survey design variables among predictors",
          not ({"v005", "v021", "v022", "v001"} & preds))
    check("v394 specifically excluded", "v394" not in preds)
else:
    check("full-pool feature spec exists", False, "run notebook 3 first")

# ---------------------------------------------------------------------------
section("4. SERVING FIDELITY — the deployed scorer must match the locked predictions")
# ---------------------------------------------------------------------------
if (MODELS / "v1_bundle.json.gz").exists():
    import scorer

    with gzip.open(MODELS / "v1_bundle.json.gz", "rt", encoding="utf-8") as fh:
        bundle = json.load(fh)

    arch = json.load(open(HANDOFF / "predictor_architecture.json"))
    hframe = lock[["caseid"]].merge(frozen, on="caseid", how="left", validate="one_to_one")
    X = hframe[arch["full_cohort_predictors"]]
    rows = X.astype(object).where(pd.notna(X), None).to_dict("records")

    tol = {"Logistic regression": 1e-9, "Random Forest": 1e-9, "XGBoost": 1e-6}
    for model, col in [("Logistic regression", "prob_logistic"),
                       ("Random Forest", "prob_random_forest"),
                       ("XGBoost", "prob_xgboost")]:
        mine = np.array([scorer.predict(bundle, model, r)["probability"] for r in rows])
        d = np.abs(mine - lock[col].to_numpy()).max()
        check(f"deployed {model} matches its locked held-out probabilities", d < tol[model],
              f"max|diff|={d:.2e} over all {len(rows)} held-out women")
else:
    check("21-predictor serving bundle exists", False, "run export_serving.py --v1")

# ---------------------------------------------------------------------------
section("4b. ANC-ENTRY HORIZON — the study's six second-horizon models")
# ---------------------------------------------------------------------------
if (MODELS / "v1_anc_entry_bundle.json.gz").exists():
    with gzip.open(MODELS / "v1_anc_entry_bundle.json.gz", "rt", encoding="utf-8") as fh:
        eb = json.load(fh)

    elock = pd.read_csv(HANDOFF / "anc_entry_locked_predictions.csv")
    eheld = pd.read_pickle(HANDOFF / "anc_entry_heldout.pkl")
    eframe = elock[["caseid"]].merge(eheld, on="caseid", how="left", validate="one_to_one")

    cols = {
        "Logistic regression (Baseline)": "prob_logistic_baseline",
        "Logistic regression (Extended)": "prob_logistic_extended",
        "Random Forest (Baseline)": "prob_rf_baseline",
        "Random Forest (Extended)": "prob_rf_extended",
        "XGBoost (Baseline)": "prob_xgb_baseline",
        "XGBoost (Extended)": "prob_xgb_extended",
    }
    for mname, col in cols.items():
        pre = eb["preprocessors"][eb["models"][mname]["preprocessor"]]
        need = pre["numeric"] + pre.get("binary", []) + pre["categorical"] + pre.get("extra", [])
        Xe = eframe[need]
        rws = Xe.astype(object).where(pd.notna(Xe), None).to_dict("records")
        mine = np.array([scorer.predict(eb, mname, r)["probability"] for r in rws])
        d = np.abs(mine - elock[col].to_numpy()).max()
        t = 1e-6 if "XGBoost" in mname else 1e-9
        check(f"deployed {mname} matches its locked predictions", d < t, f"max|diff|={d:.2e}")
else:
    check("ANC-entry bundle exists", False, "run export_serving.py --v1")

# ---------------------------------------------------------------------------
section("4c. THE LADDER -- every rung must share one split, and be nested")
# ---------------------------------------------------------------------------
from anc8 import outcomes  # noqa: E402

frozen_v2 = pd.read_pickle(ENHANCED / "ANC8_analysis_frozen_v2.pkl")

present = [o for o in outcomes.LADDER if o in frozen_v2.columns]
check("all three ladder outcomes present", len(present) == 3, str(present))

if len(present) == 3:
    ok_rows = frozen_v2[present].notna().all(axis=1)
    nested = ((frozen_v2.loc[ok_rows, "anc8plus"] <= frozen_v2.loc[ok_rows, "anc4plus"]).all()
              and (frozen_v2.loc[ok_rows, "anc4plus"] <= frozen_v2.loc[ok_rows, "anc1plus"]).all())
    # Reaching eight contacts entails reaching four and one. A violation means
    # the outcomes came from different data, which would invalidate every
    # cross-rung comparison built on them.
    check("outcomes are nested (ANC8+ implies ANC4+ implies ANC1+)", nested)

    wv2 = (frozen_v2.v005 / 1e6).to_numpy()
    for o in present:
        obs = float(np.average(frozen_v2[o], weights=wv2))
        expected = outcomes.OUTCOMES[o]["weighted_prevalence"]
        check(f"{outcomes.OUTCOMES[o]['label']} weighted prevalence matches registry",
              abs(obs - expected) < 5e-4, f"{obs:.4f} vs {expected:.4f}")

# The split is built without reference to any outcome, so it must be identical
# for every rung -- that is what makes their importances comparable at all.
tr_v2, te_v2 = design.make_psu_holdout(frozen_v2)
held_v2 = frozen_v2[frozen_v2.v021.isin(te_v2)]
check("ladder held-out set is the locked held-out set",
      set(held_v2.caseid) == set(lock.caseid), f"n={len(held_v2)}")

for rung in outcomes.LADDER:
    d = ENHANCED / rung
    if (d / "heldout_performance.csv").exists():
        hp = pd.read_csv(d / "heldout_performance.csv")
        check(f"{rung}: held-out performance present", len(hp) > 0,
              f"{len(hp)} model rows")

# ---------------------------------------------------------------------------
section("5. API — the serverless endpoint returns the locked numbers")
# ---------------------------------------------------------------------------
sys.path.insert(0, str(ROOT / "app" / "api"))
try:
    import predict as api

    r = lock.iloc[0]
    woman = frozen[frozen.caseid == r.caseid].iloc[0]
    answers = {}
    for k in arch["full_cohort_predictors"]:
        v = woman[k]
        if pd.isna(v):
            answers[k] = None
        elif isinstance(v, (int, float, np.integer, np.floating)):
            answers[k] = float(v)
        else:
            answers[k] = str(v)

    resp = api.build_response({"answers": answers, "generations": ["v1"]})
    got = {m["model"]: m["probability"] for m in resp["result"]["v1"]["models"]
           if "probability" in m}
    expect = {"Logistic regression": r.prob_logistic,
              "Random Forest": r.prob_random_forest,
              "XGBoost": r.prob_xgboost}
    worst = max(abs(got[k] - expect[k]) for k in expect)
    check("API reproduces locked probabilities for a known woman", worst < 1e-6,
          f"caseid {r.caseid.strip()}, max|diff|={worst:.2e}")
    check("API reports all 21 inputs supplied",
          resp["result"]["v1"]["n_supplied"] == 21)
except Exception as exc:
    check("API importable and scoring", False, f"{type(exc).__name__}: {exc}")

# ---------------------------------------------------------------------------
section("6. DEPLOYMENT SIZE — must fit Vercel's 250 MB serverless limit")
# ---------------------------------------------------------------------------
NUMPY_UNZIPPED_MB = 57.5  # measured from the manylinux cp313 wheel
model_mb = sum(p.stat().st_size for p in MODELS.glob("*.json.gz")) / 1e6 if MODELS.exists() else 0
total = NUMPY_UNZIPPED_MB + model_mb
check("serving bundle fits the 250 MB limit", total < 250,
      f"numpy {NUMPY_UNZIPPED_MB:.1f} MB + models {model_mb:.2f} MB = {total:.1f} MB")

# Inspect requirement lines only: the file explains in comments WHY the heavy
# packages are absent, so scanning the whole text would trip on its own prose.
req_lines = [
    ln.strip() for ln in (ROOT / "app" / "requirements.txt").read_text().splitlines()
    if ln.strip() and not ln.strip().startswith("#")
]
heavy = [ln for ln in req_lines
         if any(p in ln.lower() for p in ("scikit-learn", "scipy", "xgboost", "pandas"))]
check("requirements.txt pins numpy only and no heavy deps",
      any(ln.startswith("numpy") for ln in req_lines) and not heavy,
      f"requires: {req_lines}")

# ---------------------------------------------------------------------------
section("7. 21-PREDICTOR ARTIFACTS UNTOUCHED")
# ---------------------------------------------------------------------------
manifest = pd.read_csv(HANDOFF / "SHA256_MANIFEST.csv")
import hashlib

col = "sha256" if "sha256" in manifest.columns else manifest.columns[-1]
namecol = "filename" if "filename" in manifest.columns else manifest.columns[0]
drift = []
for row in manifest.itertuples():
    f = HANDOFF / getattr(row, namecol)
    if f.exists():
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        if h != getattr(row, col):
            drift.append(f.name)
check("21-predictor handoff files match their recorded SHA256", not drift, str(drift))

# ---------------------------------------------------------------------------
section("SUMMARY")
# ---------------------------------------------------------------------------
passed = sum(1 for _, ok, _ in RESULTS if ok)
failed = [n for n, ok, _ in RESULTS if not ok]
print(f"\n{passed}/{len(RESULTS)} checks passed")
if failed:
    print("\nFAILED:")
    for n in failed:
        print(f"  - {n}")
    sys.exit(1)
print("\nAll checks passed.")
