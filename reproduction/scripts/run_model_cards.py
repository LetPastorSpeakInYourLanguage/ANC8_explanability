"""One card per model, predictor set and rung, for the studio's Model analysis screen.

    python scripts/merge_library.py              # first: collect the trained library
    python scripts/run_model_cards.py            # 500 bootstrap resamples
    python scripts/run_model_cards.py --quick    # 30, for a smoke test

The models are the library in outputs/library/ (scripts/train_library.py): every
model family, its calibrated versions, the two ensembles and the two networks, on
each of four duplicate-free predictor sets (the full pool of 86, the 21-predictor
set, the short set and the parsimonious set), at every rung.

Everything here is scored on the same 1,375 held-out women, survey-weighted, and
everything is an aggregate: the per-woman predictions are read and joined to the
survey design in memory, and only summaries are written.

Per model, set and rung:

  metrics     average precision, AUROC, Brier, calibration (intercept and slope, ICI),
              prevalence, and the lift of AP over prevalence (what chance would score).
              95% intervals for AP and AUROC come from a stratified PSU bootstrap.
  chance      the planning question: rank women and ask how much of the smaller group
              (those who miss the rung at ANC1+ and ANC4+, those who reach it at ANC8+)
              sits in the top share of the ranking (cumulative gains); plus the ROC and
              precision-recall curves.
  calibration deciles of predicted chance against what happened.
  threshold   sensitivity, specificity, PPV and NPV at the operating threshold that
              was chosen on the development women, with the weighted 2x2 as shares.
  subgroups   AUROC by region, wealth, mother's education and residence; a cell with
              fewer than 25 women, or a single outcome class, is dropped.
  paired      95% interval of the AP and AUROC difference against the best held-out
              model and against logistic regression on the same set and rung, on the
              same resamples.
  tuning      how the model was built: sampler, trials, folds, search space with the
              chosen value, or a one-line "how built".

Writes outputs/model_cards/model_cards.json and summary.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import warnings
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import design, library as lib, metrics  # noqa: E402
from anc8 import models as zoo  # noqa: E402

LIBRARY = ROOT / "outputs" / "core"
OUT = ROOT / "outputs" / "model_cards"
RUNGS = {"anc1plus": "anc1", "anc4plus": "anc4", "anc8plus": "anc8"}
NETS = set(lib.NETS.values())
MIN_CELL = 25
SEED = 2026
DIMS = [("region", "region"), ("wealth_quintile", "wealth"),
        ("maternal_education", "education"), ("residence", "residence")]


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


# ------------------------------------------------------------------ naming
def key_of(model: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")


def card_key(set_: str, model: str) -> str:
    return f"{set_}.{key_of(model)}"


def base_of(model: str) -> str:
    return re.sub(r" \((isotonic|platt) calibrated\)$", "", model)


LINEAR = ("Logistic regression", "Elastic net logistic", "Spline logistic")

WHAT = {
    "Logistic regression": "A weighted sum of the predictors, turned into a chance. The plain baseline.",
    "Elastic net logistic": "Logistic regression that shrinks weak predictors towards zero, and drops some.",
    "Spline logistic": "Logistic regression whose curves can bend, so age and distance need not be straight lines.",
    "Random Forest": "Hundreds of decision trees, each on a random slice, averaged.",
    "Extra Trees": "Random forest with random split points: faster, smoother.",
    "XGBoost": "Trees added one at a time, each correcting the last. The usual accuracy leader.",
    "LightGBM": "Gradient boosting that grows trees leaf by leaf; quick on wide tables.",
    "CatBoost": "Gradient boosting built to handle categories directly, each category on its own.",
    "HistGradientBoosting": "Scikit-learn's boosting on binned predictors.",
    "Explainable Boosting": "Boosting kept additive: one curve per predictor, so every score can be read.",
    "MLP": "A small feed-forward neural network.",
    "Ladder transformer": "A network with attention across predictors that scores all three rungs at once.",
    "Contact-sequence encoder-decoder": "A network that walks the visits in order and stops where care stops.",
    "Stacked ensemble": "A logistic blend of the five best models' predictions on this set.",
    "Cumulative-link ensemble": "Uses the visit count itself: models several thresholds and pools them.",
}

HOW_BUILT = {
    "Stacked ensemble": "Not tuned on its own: a logistic regression blends the five best tuned models' out-of-fold predictions.",
    "Cumulative-link ensemble": "Not tuned on its own: the set's best tuned model, fitted at several contact thresholds and pooled.",
}

PRE_LINEAR = "Numbers: median fill and scaling. Categories: most-frequent fill and one-hot."
PRE_TREE = "Numbers: median fill. Categories: coded as integers the trees split on."


def group_of(model: str) -> str:
    b = base_of(model)
    if b in LINEAR:
        return "Linear"
    if model != b or b in ("Stacked ensemble", "Cumulative-link ensemble"):
        return "Ensembles & calibrated"
    if b in ("MLP", *NETS):
        return "Neural"
    return "Trees & boosting"


def family_of(model: str, set_: str) -> dict:
    b = base_of(model)
    what = WHAT.get(b, "")
    if model != b:
        method = "isotonic" if "isotonic" in model else "Platt"
        what = f"{b}, recalibrated by {method} scaling fitted on inner folds."
    pre = PRE_LINEAR if b in LINEAR or b == "MLP" else PRE_TREE
    if b in NETS:
        pre = "Numbers scaled; every predictor becomes a token the network attends over."
    if b in ("Stacked ensemble", "Cumulative-link ensemble"):
        pre = "Works on the base models' predictions."
    return {"key": card_key(set_, model), "slug": key_of(model), "set": set_, "name": model,
            "group": group_of(model), "what": what, "pre": pre}


# ------------------------------------------------------------------ search spaces
class _Recorder:
    """A stand-in for an Optuna trial that records the space instead of sampling."""

    def __init__(self):
        self.space = {}

    def suggest_float(self, name, low, high, log=False, step=None):
        self.space[name] = {"kind": "float", "low": low, "high": high, "log": bool(log)}
        return low

    def suggest_int(self, name, low, high, step=1, log=False):
        self.space[name] = {"kind": "int", "low": low, "high": high, "step": step, "log": bool(log)}
        return low

    def suggest_categorical(self, name, choices):
        self.space[name] = {"kind": "cat", "choices": [c if c is not None else "none" for c in choices]}
        return choices[0]


def search_space(name: str) -> dict | None:
    rec = _Recorder()
    try:
        zoo.suggest(rec, name)
    except ValueError:
        return None
    return rec.space


def tuning_block(model: str, meta: dict) -> dict:
    b = base_of(model)
    if "network" in meta:
        return {"tuned": False, "network": meta["network"],
                "how": "Trained, not searched: fixed settings, early stopping on held-back clusters, "
                       "three seeds averaged in development."}
    if "grid" in meta:
        chosen = meta["params"]
        return {
            "tuned": True,
            "sampler": "Grid prespecified in notebook 2",
            "objective": "Survey-weighted average precision, out of fold",
            "folds": "5 folds; whole clusters stay together, strata balanced",
            "trials": meta.get("n_settings"),
            "seconds": meta.get("seconds"),
            "grid": [{"param": p, "values": ["none" if v is None else v for v in vals],
                      "chosen": "none" if chosen.get(p) is None else chosen.get(p)}
                     for p, vals in meta["grid"].items()],
        }
    space = search_space(b) if model == b else None
    if space is not None and "params" in meta:
        chosen = meta["params"]
        return {
            "tuned": True,
            "sampler": "Optuna TPE, seed 2026",
            "objective": "Survey-weighted average precision, out of fold",
            "folds": "5 folds; whole clusters stay together, strata balanced",
            "trials": meta.get("n_trials"),
            "seconds": meta.get("seconds"),
            "space": [{"param": p, **sp, "chosen": (chosen.get(p) if chosen.get(p) is not None else "none")}
                      for p, sp in space.items() if p in chosen],
        }
    if b in HOW_BUILT:
        how = HOW_BUILT[b]
        base = meta.get("base_models") or meta.get("base_model")
        if base:
            how += f" Built on: {', '.join(base) if isinstance(base, list) else base}."
        return {"tuned": False, "how": how}
    return {"tuned": False, "how": f"Not tuned again: the tuned {b} model, recalibrated on inner folds."}


# ------------------------------------------------------------------ curves
def wshare_gains(y, p, w, target, pts=21):
    """Cumulative gains for finding the smaller group: women who miss the rung
    (target "miss", ranked by 1 - p) or who reach it (target "reach", ranked by p)."""
    hit = (1 - y) if target == "miss" else y
    score = (1 - p) if target == "miss" else p
    order = np.argsort(-score, kind="mergesort")
    cw = np.cumsum(w[order]) / w.sum()
    cm = np.cumsum((w * hit)[order]) / (w * hit).sum()
    grid = np.linspace(0, 1, pts)
    return np.interp(grid, np.r_[0, cw], np.r_[0, cm])


def roc_points(y, p, w, pts=41):
    fpr, tpr, _ = roc_curve(y, p, sample_weight=w)
    grid = np.linspace(0, 1, pts)
    return grid, np.interp(grid, fpr, tpr)


def pr_points(y, p, w, pts=41):
    prec, rec, _ = precision_recall_curve(y, p, sample_weight=w)
    # interpolated precision: best precision at any recall at or beyond r
    best = np.maximum.accumulate(prec[::-1])[::-1]
    grid = np.linspace(0, 1, pts)
    out = np.empty(pts)
    for i, r in enumerate(grid):
        ok = rec >= r - 1e-12
        out[i] = best[ok].max() if ok.any() else 0.0
    return grid, out


def calibration_deciles(y, p, w, bins=10):
    order = np.argsort(p, kind="mergesort")
    out = []
    for chunk in np.array_split(order, bins):
        out.append({"predicted": float(np.average(p[chunk], weights=w[chunk])),
                    "observed": float(np.average(y[chunk], weights=w[chunk])), "n": int(len(chunk))})
    return out


def operating_point(y, p, w, thr):
    t = metrics.threshold_metrics(y, p, thr, w)
    pred = p >= thr
    W = w.sum()
    return {
        "threshold": t["Threshold"], "sensitivity": t["Sensitivity"], "specificity": t["Specificity"],
        "ppv": t["PPV"], "npv": t["NPV"], "flagged": t["Predicted_positive_rate"],
        "tp": float(w[pred & (y == 1)].sum() / W), "fp": float(w[pred & (y == 0)].sum() / W),
        "fn": float(w[~pred & (y == 1)].sum() / W), "tn": float(w[~pred & (y == 0)].sum() / W),
    }


def safe_auc(y, p, w):
    return float(roc_auc_score(y, p, sample_weight=w)) if len(np.unique(y)) == 2 else np.nan


def subgroup_auc(y, p, w, held):
    out = {}
    for col, key in DIMS:
        rows = []
        for level, idx in held.groupby(col).indices.items():
            if len(idx) < MIN_CELL or len(np.unique(y[idx])) < 2:
                continue
            rows.append({"level": str(level), "n": int(len(idx)), "auroc": safe_auc(y[idx], p[idx], w[idx])})
        out[key] = sorted(rows, key=lambda r: -r["auroc"])
    return out


def ci(a):
    return [float(np.nanpercentile(a, 2.5)), float(np.nanpercentile(a, 97.5))]


# ------------------------------------------------------------------ main
def lineup_models(lineup: str) -> dict:
    """{display name: library cell name} for a lineup: its models, as tuned.

    The library also holds each model's isotonic and Platt recalibrations and two
    ensembles. None earns a place in the studio: Platt never changes the ranking,
    isotonic costs average precision at every rung, the stacked ensemble's edge
    over the best single model is inside its interval, and the cumulative-link
    ensemble comes last. They stay in the library as a record."""
    return {m: m for m in lib.LINEUPS[lineup]}


def cells_for(library: Path, set_: str, rung: str, lineup: str) -> dict:
    """The lineup's models in the library for one set and rung: {display name: cell}."""
    out = {}
    for name, cell in lineup_models(lineup).items():
        if lib.cell_path(library, set_, rung, cell).exists():
            out[name] = lib.load_cell(library, set_, rung, cell)
    return out


# The kind of importance each base model reports (outputs/explain, run_explainability.py).
SHARE_KIND = {"Logistic regression": "logistic", "Explainable Boosting": "ebm",
              "Random Forest": "shap", "XGBoost": "shap"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--library", type=Path, default=LIBRARY, help="where the merged library lives")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--lineup", default="three", choices=list(lib.LINEUPS))
    args = ap.parse_args()
    n_boot = 30 if args.quick else 500

    dev_all, held = lib.partitions()
    held = held.reset_index(drop=True)
    boots = list(design.stratified_psu_bootstrap(held.v022.to_numpy(), held.v021.to_numpy(), n_boot, SEED))

    cards: dict = {}
    fams: dict = {}
    cross = []
    summary = {}

    for set_ in lib.SETS:
        for rung, short in RUNGS.items():
            cells = cells_for(args.library, set_, rung, args.lineup)
            if not cells:
                log(f"{set_}/{rung}: nothing in the library yet")
                continue
            y = held[rung].astype(int).to_numpy().astype(float)
            w = (held.v005 / 1e6).to_numpy()
            prev = float(np.average(y, weights=w))
            target = "miss" if prev >= 0.5 else "reach"
            share = (1 - prev) if target == "miss" else prev
            probs = {m: c["held"] for m, c in cells.items()}
            log(f"{set_}/{rung}: {len(probs)} models, prevalence {prev:.3f}, {n_boot} resamples")

            # bootstrap resamples, shared by every model so the differences are paired
            boot_ap, boot_au = {}, {}
            for m, p in probs.items():
                a = np.empty(n_boot)
                u = np.empty(n_boot)
                for i, ix in enumerate(boots):
                    yy = y[ix]
                    if len(np.unique(yy)) < 2:
                        a[i] = u[i] = np.nan
                        continue
                    a[i] = average_precision_score(yy, p[ix], sample_weight=w[ix])
                    u[i] = roc_auc_score(yy, p[ix], sample_weight=w[ix])
                boot_ap[m], boot_au[m] = a, u

            point = {m: metrics.probability_metrics(y, p, w) for m, p in probs.items()}
            best = max(point, key=lambda m: point[m]["AP"])
            rank_ap = {m: i + 1 for i, m in enumerate(sorted(point, key=lambda m: -point[m]["AP"]))}
            summary.setdefault(set_, {})[short] = {"best": best, "prevalence": prev, "n_models": len(probs)}

            for m, p in probs.items():
                meta = cells[m]["meta"]
                fam = family_of(m, set_)
                fams[fam["key"]] = fam
                pm = point[m]
                dm = meta["dev_metrics"]
                dev_ap = float(dm.get("AP_seed_mean", dm["AP"]))
                dev_auc = float(dm["AUROC"])
                gx = np.array(wshare_gains(y, p, w, target))
                fx, fy = roc_points(y, p, w)
                rx, ry = pr_points(y, p, w)

                def paired(other):
                    if other == m or other not in probs:
                        return None
                    return {"vs": other, "key": card_key(set_, other),
                            "ap": float(point[m]["AP"] - point[other]["AP"]),
                            "ap_ci": ci(boot_ap[m] - boot_ap[other]),
                            "auroc": float(pm["AUROC"] - point[other]["AUROC"]),
                            "auroc_ci": ci(boot_au[m] - boot_au[other])}

                card = {
                    "ap": pm["AP"], "ap_ci": ci(boot_ap[m]), "auroc": pm["AUROC"], "auroc_ci": ci(boot_au[m]),
                    "brier": pm["Brier"], "citl": pm["CITL"], "slope": pm["Calibration_slope"], "ici": pm["ICI"],
                    "prevalence": prev, "target": target, "target_share": share, "lift": pm["AP"] - prev,
                    "ratio": pm["AP"] / prev, "rank": rank_ap[m], "of": len(probs),
                    "dev_ap": dev_ap, "dev_auroc": dev_auc, "optimism": dev_ap - pm["AP"],
                    "top10": float(np.interp(0.1, np.linspace(0, 1, 21), gx)),
                    "top20": float(np.interp(0.2, np.linspace(0, 1, 21), gx)),
                    "gains": gx.tolist(),
                    "roc": [fx.tolist(), fy.tolist()], "pr": [rx.tolist(), ry.tolist()],
                    "calibration": calibration_deciles(y, p, w),
                    "operating": operating_point(y, p, w, meta["threshold"]),
                    "subgroups": subgroup_auc(y, p, w, held),
                    "vs_best": paired(best), "vs_logistic": paired("Logistic regression"),
                    "tuning": tuning_block(m, meta),
                    "n_predictors": meta["n_predictors"],
                    "predictors": meta["predictors"]["numeric"] + meta["predictors"]["categorical"],
                }
                if m in lib.LINEUPS[args.lineup]:
                    dc = metrics.decision_curve(y, p, w)
                    card["decision"] = {"t": dc.threshold.round(2).tolist(), "model": dc.model.tolist(),
                                        "all": dc.treat_all.tolist()}
                cards.setdefault(fam["key"], {})[short] = card
                cross.append({"key": fam["key"], "set": set_, "rung": short, "ap": pm["AP"],
                              "auroc": pm["AUROC"], "brier": pm["Brier"],
                              "slope": pm["Calibration_slope"], "lift": card["lift"]})

    # What each base model leans on (scripts/run_explainability.py): its own exact
    # shares for logistic regression and explainable boosting, TreeSHAP for the trees.
    imp_p = ROOT / "outputs" / "explain" / "importance.csv"
    if imp_p.exists():
        import pandas as pd
        imp = pd.read_csv(imp_p)
        for (set_, rung, model), g in imp.groupby(["set", "rung", "model"]):
            card = cards.get(card_key(set_, model), {}).get(RUNGS[rung])
            if card is None:
                continue
            top = g.sort_values("share", ascending=False).head(8)
            card["shares"] = {"kind": SHARE_KIND.get(model, "shap"),
                              "rows": [{"predictor": r.predictor, "share": float(r.share)} for r in top.itertuples()]}

    # What tuning bought and which settings matter (scripts/run_hyperparameter_ablation.py):
    # the lineup's models on the full pool, development out-of-fold AP.
    tuning = {}
    for rung, short in RUNGS.items():
        f = ROOT / "outputs" / "library" / "tuning" / f"ablation_s21_{rung}.csv"
        if not f.exists():
            continue
        import pandas as pd
        a = pd.read_csv(f)
        for model, g in a[a.model.isin(lib.LINEUPS[args.lineup])].groupby("model"):
            d0 = g[g.parameter == "(library defaults)"].AP
            t0 = g[g.parameter == "(tuned optimum)"].AP
            real = g[~g.parameter.str.startswith("(")]
            tuning.setdefault(short, {})[model] = {
                "defaults_ap": float(d0.iloc[0]) if len(d0) else None,
                "tuned_ap": float(t0.iloc[0]) if len(t0) else None,
                "params": [{"parameter": par, "tuned": str(gg.tuned_value.iloc[0]),
                            "worst": float(gg.AP_vs_tuned.min()), "best": float(gg.AP_vs_tuned.max())}
                           for par, gg in real.groupby("parameter")],
            }

    meta = {"n_development": int(len(dev_all)), "n_heldout": int(len(held)), "resamples": n_boot,
            "lineup": args.lineup, "models": lib.LINEUPS[args.lineup],
            "sets": [{"key": s, "label": lib.SET_LABEL[s]} for s in lib.SETS if s in summary]}
    result = {"meta": meta, "families": fams, "cards": cards, "cross": cross, "tuning": tuning}
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "model_cards.json").write_text(json.dumps(result), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps({"meta": meta, **summary}, indent=1), encoding="utf-8")
    log(f"wrote {len(fams)} families, {sum(len(v) for v in cards.values())} cards")


if __name__ == "__main__":
    main()
