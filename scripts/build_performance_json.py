"""Publish held-out performance figures for the web app.

The app shows a probability next to the performance of the model that produced
it. Without that context a number like "23%" invites more confidence than a
model with an AUROC of 0.76 can support.

V1 figures come from the study's published Table 1. V2 figures come from
outputs/enhanced/heldout_performance.csv once evaluation has run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "outputs" / "publication_results"
ENHANCED = ROOT / "outputs" / "enhanced"
OUT = ROOT / "app" / "public" / "model_performance.json"


def main():
    perf = {"v1": {}, "v2": {}, "prevalence": None}

    t1 = pd.read_csv(PUB / "main_tables/Table_1_full_cohort_heldout_performance.csv")
    for r in t1.itertuples():
        perf["v1"][r.Model] = {
            "AP": round(r.Weighted_AP, 4),
            "AUROC": round(r.Weighted_AUROC, 4),
            "AUROC_CI": [round(r.AUROC_CI_low, 4), round(r.AUROC_CI_high, 4)],
            "Brier": round(r.Weighted_Brier, 4),
            "calibration_slope": round(r.Calibration_slope, 3),
            "sensitivity": round(r.Sensitivity, 3),
            "specificity": round(r.Specificity, 3),
        }

    # ANC-entry horizon, from the study's published Table 2 (probability
    # metrics) and Table 3 (threshold metrics).
    t2 = pd.read_csv(PUB / "main_tables/Table_2_anc_entry_probability_performance.csv")
    t3 = pd.read_csv(PUB / "main_tables/Table_3_anc_entry_calibration_threshold_performance.csv")
    entry = {}
    for r in t2.itertuples():
        for spec, ap, auc, br in (
            ("Baseline", r.Baseline_Weighted_AP, r.Baseline_Weighted_AUROC,
             r.Baseline_Weighted_Brier),
            ("Extended", r.Extended_Weighted_AP, r.Extended_Weighted_AUROC,
             r.Extended_Weighted_Brier),
        ):
            t = t3[(t3.Algorithm == r.Algorithm) & (t3.Specification == spec)]
            entry[f"{r.Algorithm} ({spec})"] = {
                "AP": round(ap, 4),
                "AUROC": round(auc, 4),
                "Brier": round(br, 4),
                "calibration_slope": round(float(t.Calibration_slope.iloc[0]), 3)
                if len(t) else None,
                "sensitivity": round(float(t.Sensitivity.iloc[0]), 3) if len(t) else None,
                "specificity": round(float(t.Specificity.iloc[0]), 3) if len(t) else None,
            }
    perf["v1_anc_entry"] = entry

    hp = ENHANCED / "anc8plus" / "heldout_performance.csv"
    if hp.exists():
        d = pd.read_csv(hp)
        for r in d[d.generation == "V2 (enhanced)"].itertuples():
            perf["v2"][r.model] = {
                "AP": round(r.AP, 4),
                "AUROC": round(r.AUROC, 4),
                "Brier": round(r.Brier, 4),
                "calibration_slope": round(r.Calibration_slope, 3),
                "sensitivity": round(r.Sensitivity, 3),
                "specificity": round(r.Specificity, 3),
            }

    ci = ENHANCED / "anc8plus" / "paired_bootstrap_ci.json"
    if ci.exists():
        c = json.loads(ci.read_text())
        perf["comparison"] = {
            "champion": c["champion"],
            "baseline": c["baseline"],
            "delta_AP": round(c["d_AP"]["point"], 4),
            "delta_AP_CI": [round(c["d_AP"]["lo"], 4), round(c["d_AP"]["hi"], 4)],
            "delta_AP_significant": c["d_AP_excludes_zero"],
            "delta_AUROC": round(c["d_AUROC"]["point"], 4),
            "delta_AUROC_CI": [round(c["d_AUROC"]["lo"], 4), round(c["d_AUROC"]["hi"], 4)],
            "delta_AUROC_significant": c["d_AUROC_excludes_zero"],
        }

    reg = pd.read_csv(ROOT / "outputs" / "ANC8_outcome_register_final.csv")
    row = reg[reg.final_variable == "anc8plus"].iloc[0]
    perf["prevalence"] = {
        "weighted_percent": float(row.survey_weighted_prevalence_percent),
        "heldout_n": 1375,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(perf, indent=1), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"  v1 models: {list(perf['v1'])}")
    print(f"  v1_anc_entry models: {len(perf.get('v1_anc_entry', {}))}")
    print(f"  v2 models: {list(perf['v2'])}")


if __name__ == "__main__":
    main()
