"""What each library model leans on, per predictor set and rung.

    python scripts/run_explainability.py          # needs scripts/fit_library_models.py first

For every predictor set and rung, and each of logistic regression, random forest,
XGBoost and explainable boosting (the fitted objects from fit_library_models.py),
on the held-out women with their survey weights:

  logistic regression   exact: the model's log-odds is a sum over predictors, so a
                        woman's contribution from a predictor is its coefficients
                        times her values, measured from the weighted average woman.
  explainable boosting  exact: the model is a sum of one learned curve per predictor
                        (and a few pairs); its own term scores, centred the same way.
                        A pair's contribution is split equally between its two.
  random forest,        TreeSHAP: the exact Shapley attribution for a tree ensemble,
  XGBoost               in probability (forest) or log-odds (XGBoost) units.

A predictor's importance is its weighted mean absolute contribution; its share is
that over the model's total, so shares are comparable across models even though the
units differ. Effects: the average contribution at each level of a categorical
predictor or in each fifth of a numeric one, which shows the direction.

Writes outputs/explain/:
  importance.csv   set, rung, model, predictor, mean_abs, share, rank
  effects.json     {set: {rung: {model: {predictor: [{level, effect, n}]}}}}
  agreement.csv    per set and rung: each predictor's share under every model, its
                   mean rank, and how many models put it in their top five
  concordance.csv  per set and rung: Spearman correlation of shares between models
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import explain, library as lib  # noqa: E402

MODELS_DIR = ROOT / "outputs" / "library" / "models"
OUT = ROOT / "outputs" / "explain"
TOP = 5


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def wmean(a, w, axis=0):
    return np.average(a, weights=w, axis=axis)


# ------------------------------------------------------------------ summaries
def effects(contrib, X, numeric, categorical, w):
    """Average contribution by level (categorical) or fifth (numeric)."""
    out = {}
    names = list(numeric) + list(categorical)
    for j, name in enumerate(names):
        x = X[name]
        rows = []
        if name in categorical:
            for level, idx in pd.Series(np.arange(len(x))).groupby(x.astype(str).to_numpy()).groups.items():
                idx = np.asarray(idx)
                rows.append({"level": str(level), "effect": float(wmean(contrib[idx, j], w[idx])), "n": int(len(idx))})
            rows.sort(key=lambda r: r["effect"])
        else:
            v = pd.to_numeric(x, errors="coerce")
            ok = v.notna().to_numpy()
            if ok.sum() < 10:
                continue
            q = pd.qcut(v[ok], 5, duplicates="drop")
            for iv, idx in pd.Series(np.flatnonzero(ok)).groupby(q.to_numpy()).groups.items():
                idx = np.asarray(pd.Series(np.flatnonzero(ok))[idx])
                rows.append({"level": f"{iv.left:.3g}–{iv.right:.3g}", "effect": float(wmean(contrib[idx, j], w[idx])),
                             "n": int(len(idx))})
        out[name] = rows
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, eff = [], {}
    for set_ in lib.SETS:
        for rung in lib.RUNGS:
            b = joblib.load(MODELS_DIR / f"{set_}_{rung}.joblib")
            num, cat = b["numeric"], b["categorical"]
            names = list(num) + list(cat)
            _, held = lib.partitions()
            X = lib.design_matrix(held, num, cat)
            w = (held.v005 / 1e6).to_numpy()
            for model, pipe in b["models"].items():
                c = explain.contributions(model, pipe, X, num, cat, w)
                imp = wmean(np.abs(c), w)
                share = imp / imp.sum() if imp.sum() > 0 else imp
                order = np.argsort(-imp)
                rank = np.empty(len(names), int)
                rank[order] = np.arange(1, len(names) + 1)
                for j, name in enumerate(names):
                    rows.append({"set": set_, "rung": rung, "model": model, "predictor": name,
                                 "mean_abs": float(imp[j]), "share": float(share[j]), "rank": int(rank[j])})
                eff.setdefault(set_, {}).setdefault(rung, {})[model] = effects(c, X, num, cat, w)
                log(f"{set_}/{rung} {model}: top {names[order[0]]} ({share[order[0]]:.2f})")

    imp = pd.DataFrame(rows)
    imp.to_csv(OUT / "importance.csv", index=False)
    (OUT / "effects.json").write_text(json.dumps(eff), encoding="utf-8")

    agree, conc = [], []
    for (set_, rung), g in imp.groupby(["set", "rung"]):
        wide = g.pivot(index="predictor", columns="model", values="share")
        ranks = g.pivot(index="predictor", columns="model", values="rank")
        wide["mean_rank"] = ranks.mean(axis=1)
        wide["top5_models"] = (ranks <= TOP).sum(axis=1)
        wide = wide.sort_values("mean_rank").reset_index()
        wide.insert(0, "rung", rung)
        wide.insert(0, "set", set_)
        agree.append(wide)
        models = list(ranks.columns)
        for i, a in enumerate(models):
            for bm in models[i + 1:]:
                conc.append({"set": set_, "rung": rung, "a": a, "b": bm,
                             "spearman": float(g.pivot(index="predictor", columns="model", values="share")[[a, bm]]
                                               .corr(method="spearman").iloc[0, 1])})
    pd.concat(agree).to_csv(OUT / "agreement.csv", index=False)
    pd.DataFrame(conc).to_csv(OUT / "concordance.csv", index=False)
    log(f"wrote {OUT}")


if __name__ == "__main__":
    main()
