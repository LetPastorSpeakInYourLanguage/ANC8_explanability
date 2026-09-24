"""How each predictor's value changes up the ladder: one predictor x rung matrix.

    python scripts/run_predictor_matrix.py [--cohort full]

Assembled from results already on disk; nothing is refitted.

For every candidate and every rung (ANC1+, ANC4+, ANC8+):

  marginal     its value relative to the 21-predictor set, on the same
               fixed logistic regression -- the AP lost when a member of the
               21 is dropped from it, or the AP gained when a non-member is
               added to it. One number, one scale, for all 88.
  pool_loss    the AP lost when it is removed from the full pool of 88.
  tier         where forward selection from nothing placed it.
  ebm / shap   its share of total importance in the full-pool EBM and in SHAP
               on XGBoost (the ladder analysis; duplicates folded into twins).

AP differences are not comparable across rungs -- the room above the base rate
runs from about 0.14 AP on ANC1+ to about 0.31 on ANC8+ -- so each AP quantity
is also given as a share of that rung's ceiling: the full pool's AP minus the
prevalence. That is what the cross-rung comparison reads.

Output: outputs/predictor_value/<cohort>/matrix.csv and summary.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FV = ROOT / "outputs" / "feature_value"
LAD = ROOT / "outputs" / "ladder"
OUT = ROOT / "outputs" / "predictor_value"
RUNGS = ("anc1plus", "anc4plus", "anc8plus")
# The ladder analysis used current age; the selection study age at the birth.
LADDER_ALIAS = {"v012": "age_at_birth"}


def rung_frame(cohort: str, rung: str) -> pd.DataFrame | None:
    d = FV / cohort / rung
    need = ["summary.json", "add_one_to_21.csv", "remove_one_from_all.csv",
            "forward_steps.csv", "drop_one_within_21.csv"]
    if not all((d / n).exists() for n in need):
        return None
    js = json.loads((d / "summary.json").read_text())
    a = js["anchors"]
    ceiling = a["all88"] - a["prevalence"]

    add = pd.read_csv(d / "add_one_to_21.csv").set_index("predictor")
    drop = pd.read_csv(d / "drop_one_within_21.csv").set_index("predictor")
    pool = pd.read_csv(d / "remove_one_from_all.csv").set_index("predictor")
    steps = pd.read_csv(d / "forward_steps.csv")
    tier = dict(zip(steps.predictor, steps.tier))

    names = list(pool.index)
    rows = []
    for c in names:
        in21 = c in drop.index
        marginal = drop.loss.get(c) if in21 else add.gain.get(c)
        consistent = (drop.seeds_positive.get(c) if in21 else add.seeds_positive.get(c))
        rows.append({
            "predictor": c, "in_21": in21,
            "marginal": marginal, "marginal_seeds": consistent,
            "pool_loss": pool.loss.get(c),
            "tier": tier.get(c) if tier.get(c) in ("tier 1", "tier 2") else "",
        })
    out = pd.DataFrame(rows)
    out["marginal_share"] = out.marginal / ceiling
    out["pool_loss_share"] = out.pool_loss / ceiling
    out["clears_threshold"] = (out.marginal >= js["threshold"]) & \
        (out.marginal_seeds >= js["min_seeds_positive"])
    out["rung"] = rung
    out["ceiling"] = ceiling
    return out


def ladder_shares() -> pd.DataFrame:
    parts = []
    for method, name in (("EBM", "ebm"), ("SHAP", "shap")):
        p = LAD / f"importance_{method}.csv"
        if not p.exists():
            continue
        d = pd.read_csv(p, index_col=0)
        d.index = [LADDER_ALIAS.get(i, i) for i in d.index]
        long = d[list(RUNGS)].stack().rename(name).reset_index()
        long.columns = ["predictor", "rung", name]
        parts.append(long.set_index(["predictor", "rung"]))
    if not parts:
        return pd.DataFrame()
    dom = None
    p = LAD / "importance_EBM.csv"
    if p.exists():
        d = pd.read_csv(p, index_col=0)
        dom = {LADDER_ALIAS.get(i, i): v for i, v in d.domain.items()}
    out = pd.concat(parts, axis=1).reset_index()
    if dom:
        out["domain"] = out.predictor.map(dom)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", default="full")
    args = ap.parse_args()

    frames = [f for r in RUNGS if (f := rung_frame(args.cohort, r)) is not None]
    if not frames:
        raise SystemExit("no complete rung yet -- run run_feature_value.py first")
    m = pd.concat(frames, ignore_index=True)
    lad = ladder_shares()
    if len(lad):
        m = m.merge(lad, on=["predictor", "rung"], how="left")

    out = OUT / args.cohort
    out.mkdir(parents=True, exist_ok=True)
    m.to_csv(out / "matrix.csv", index=False)

    # The shift from reaching care to completing it, per predictor.
    wide = m.pivot(index="predictor", columns="rung", values="marginal_share")
    summary = {"cohort": args.cohort, "rungs": sorted(m.rung.unique().tolist()),
               "n_predictors": int(m.predictor.nunique())}
    if {"anc1plus", "anc8plus"} <= set(wide.columns):
        shift = (wide.anc8plus - wide.anc1plus).dropna().sort_values()
        summary["rises_toward_anc8"] = shift.tail(10)[::-1].round(4).to_dict()
        summary["falls_toward_anc8"] = shift.head(10).round(4).to_dict()
    json.dump(summary, open(out / "summary.json", "w"), indent=2)
    print(f"{len(m)} rows, {m.predictor.nunique()} predictors, rungs {summary['rungs']} -> {out}")


if __name__ == "__main__":
    main()
