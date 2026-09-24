"""Did screening on the full cohort leak the held-out set into feature selection?

Notebook 3 screens all 6,648 IR columns against the outcome using the whole
analytic cohort, held-out women included. That is a mild form of selection
leakage: the variables admitted to the enhanced model were chosen with some
sight of the data the model is later judged on, which would bias the held-out
evaluation optimistically.

The defensible version is to screen on the development partition only. This
script runs both and compares them, so the size of the problem is measured
rather than asserted.

Selection here was driven mostly by temporality and by domain -- whole blocks
of wealth, education, partner, household, media, access and empowerment
variables were admitted together rather than cherry-picked off the top of an
AUC ranking -- so the expectation is that it makes little difference. That
expectation still has to be checked.

    python scripts/run_screening_sensitivity.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import design, features, screening  # noqa: E402

OUT = ROOT / "outputs" / "enhanced"
TOP_N = 40


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def main():
    reader = pd.read_stata(ROOT / "ETIR8AFL.dta", iterator=True)
    labels = reader.variable_labels()
    ir = pd.read_stata(ROOT / "ETIR8AFL.dta", convert_categoricals=False)
    cohort = ir[ir.m14_1.notna() & ir.m14_1.between(0, 97)].copy()

    frozen = pd.read_pickle(ROOT / "outputs" / "ANC8_analysis_frozen.pkl")
    base = frozen[frozen.anc8plus.notna()]
    train_psus, _ = design.make_psu_holdout(base)
    dev_ids = set(base[base.v021.isin(train_psus)].caseid)
    dev_cohort = cohort[cohort.caseid.isin(dev_ids)]

    log(f"full cohort {len(cohort)}   development only {len(dev_cohort)}")

    def screen_of(c):
        y = (c.m14_1 >= 8).astype(int).to_numpy()
        w = (c.v005 / 1e6).to_numpy()
        return screening.screen(c, labels, y, w)

    s_full = screen_of(cohort)
    s_dev = screen_of(dev_cohort)

    cf = s_full[s_full.screen_status == "candidate"].set_index("variable")
    cd = s_dev[s_dev.screen_status == "candidate"].set_index("variable")

    admitted = list(features.NUMERIC_RAW) + list(features.ORDINAL_RAW) \
        + list(features.NOMINAL_RAW) + list(features.BINARY_RAW)
    admitted = [v for v in dict.fromkeys(admitted)]

    rankable_full = [v for v in admitted if v in cf.index]
    rankable_dev = [v for v in admitted if v in cd.index]

    top_f = set(cf.head(TOP_N).index)
    top_d = set(cd.head(TOP_N).index)

    rows = []
    for v in admitted:
        rows.append({
            "variable": v,
            "label": labels.get(v, ""),
            "auc_full_cohort": cf.loc[v, "weighted_auc"] if v in cf.index else None,
            "auc_development_only": cd.loc[v, "weighted_auc"] if v in cd.index else None,
            "candidate_full": v in cf.index,
            "candidate_development": v in cd.index,
        })
    comp = pd.DataFrame(rows)
    comp["auc_shift"] = comp.auc_development_only - comp.auc_full_cohort
    comp.to_csv(OUT / "screening_sensitivity.csv", index=False)

    summary = {
        "admitted_variables": len(admitted),
        "rankable_full_cohort": len(rankable_full),
        "rankable_development_only": len(rankable_dev),
        "admitted_lost_under_development_screening":
            sorted(set(rankable_full) - set(rankable_dev)),
        "top_n": TOP_N,
        "top_n_overlap": len(top_f & top_d),
        "in_full_top_n_only": sorted(top_f - top_d),
        "max_abs_auc_shift": float(comp.auc_shift.abs().max()),
        "mean_auc_shift": float(comp.auc_shift.mean()),
    }
    json.dump(summary, open(OUT / "screening_sensitivity.json", "w"), indent=2)

    print()
    print("SCREENING SENSITIVITY: full cohort vs development only")
    print(f"  admitted variables still rankable candidates : "
          f"{len(rankable_dev)}/{len(rankable_full)}")
    print(f"  top-{TOP_N} overlap                                : "
          f"{summary['top_n_overlap']}/{TOP_N}")
    print(f"  largest AUC shift for an admitted variable    : "
          f"{summary['max_abs_auc_shift']:+.4f}")
    print(f"  mean AUC shift                               : "
          f"{summary['mean_auc_shift']:+.4f}")
    if summary["admitted_lost_under_development_screening"]:
        print("  admitted variables that would NOT have been candidates:")
        for v in summary["admitted_lost_under_development_screening"]:
            print(f"      {v}")
    else:
        print("  every admitted variable survives development-only screening")


if __name__ == "__main__":
    main()
