"""Regions against their circumstances, on the 21 predictors.

    python scripts/run_regional_gap.py

For each region and rung: the share of its women who reach the rung, against the
share a model predicts from their circumstances alone. The model is the study's
logistic regression on the 21 predictors (the setting its grid chose at that rung),
with region and residence left out: those are the places being compared, so
leaving them out asks "given who lives here, how many would we expect?". Every
woman's prediction is out of fold, so no woman is scored by a model that saw her.

A region above its expected share does better than its population predicts (a place
to learn from); below it, something about the region itself -- services, conflict,
geography -- holds women back beyond their circumstances.

Tigray is also scored on the pregnancies conceived after the ceasefire alone,
because the recent window still holds wartime pregnancies.

Writes outputs/wartime/regional_gap_by_cohort.csv (read by export_viz_data.py).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from anc8 import cohorts, library as lib, tuning  # noqa: E402
from run_wartime_analysis import PREGNANCY_MONTHS, load_windows  # noqa: E402

OUT = ROOT / "outputs" / "wartime" / "regional_gap_by_cohort.csv"
PLACE = {"region", "residence"}


def wmean(x, w):
    return float(np.average(x, weights=w))


def main():
    num = [c for c in lib.S21_NUMERIC if c not in PLACE]
    cat = [c for c in lib.S21_CATEGORICAL if c not in PLACE]
    rows = []
    for cohort in ("full", "recent"):
        d = lib.raw_frame(cohort)
        d["region"] = d.region.astype(str)
        X = lib.design_matrix(d, num, cat)
        w = (d.v005 / 1e6).to_numpy()
        splits = cohorts.folds(d)
        for rung in lib.RUNGS:
            params = lib.load_cell(ROOT / "outputs" / "core", "s21", rung, "Logistic regression")["meta"]["params"]
            y = d[rung].astype(int).to_numpy()
            pred = tuning.oof_predict("Logistic regression", params, X, y, w, splits, num, cat, n_jobs=5)
            for region, g in d.groupby("region"):
                i = d.index.get_indexer(g.index)
                rows.append({"cohort": cohort, "outcome": rung, "region": region, "n": len(i),
                             "actual": wmean(y[i], w[i]), "expected": wmean(pred[i], w[i])})
            if cohort == "full":
                tw = next(x for x in load_windows() if x["window"] == "tigray_war")
                start = d.birth_cmc.to_numpy(dtype=float) - (PREGNANCY_MONTHS - 1)
                i = np.flatnonzero((d.region == "Tigray").to_numpy() & (start > tw["end"]))
                rows.append({"cohort": "post-war pregnancies", "outcome": rung, "region": "Tigray", "n": len(i),
                             "actual": wmean(y[i], w[i]), "expected": wmean(pred[i], w[i])})
            print(f"  {cohort} {rung}: done", flush=True)
    gaps = pd.DataFrame(rows)
    gaps["gap"] = gaps.actual - gaps.expected
    gaps.to_csv(OUT, index=False)
    piv = gaps[gaps.outcome == "anc8plus"].pivot_table(index="region", columns="cohort", values="gap")
    print((piv * 100).round(1).sort_values("recent").to_string())
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
