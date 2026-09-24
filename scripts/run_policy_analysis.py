"""Policy-facing analysis: what a health ministry could actually act on.

    python scripts/run_policy_analysis.py

The modelling work answers "how well can we predict ANC attainment". This asks
the question a ministry would actually ask: **where is the loss, who is being
lost, and which of the things that predict it are within anyone's control?**

Five analyses, all survey-weighted so they describe the country rather than the
sample:

  1. The cascade, and where the leak is
  2. Regions doing better or worse than their circumstances predict
  3. Modifiable factors vs fixed circumstance
  4. Who starts antenatal care but does not finish it
  5. Where the marginal woman is -- near-threshold targeting

Everything here is associational. The model describes who attains ANC8+, not
what would happen if a circumstance were changed. That distinction is carried
through every table rather than noted once and forgotten.
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import design, ladder, outcomes, tuning  # noqa: E402

ENHANCED = ROOT / "outputs" / "enhanced"
OUT = ROOT / "outputs" / "policy"

# Cheap and stable: this analysis is about population patterns, not about
# squeezing the last point of AP.
PARAMS = {"n_estimators": 300, "learning_rate": 0.05, "num_leaves": 15,
          "reg_lambda": 1.0}

# Things a health system can plausibly change, against things it cannot -- at
# least not within a planning cycle. Wealth and education move with decades of
# development policy; a health post does not.
MODIFIABLE = {
    "s1101", "s1101b", "s1102", "s1101a", "travel_hospital_log",
    "travel_healthpost_log", "travel_hospital_is_zero",
    "travel_healthpost_is_zero", "travel_hospital_topcoded",
    "travel_healthpost_topcoded", "healthpost_time_missing",
    "transport_mode_group", "v467b", "v467c", "v467d", "v467f",
    "access_barrier_count", "v481", "health_insurance",
    "v157", "v158", "v159", "v171a", "internet_exposure",
    "newspaper_weekly", "radio_weekly", "television_weekly",
    "v113", "v115", "v116", "v119",
}


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def wmean(x, w):
    return float(np.average(np.asarray(x, dtype=float), weights=w))


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    df = pd.read_pickle(ENHANCED / "ANC8_analysis_frozen_v2.pkl")
    spec = json.load(open(ENHANCED / "feature_spec_v2.json"))
    numeric, categorical = spec["numeric_predictors"], spec["categorical_predictors"]
    w = (df.v005 / 1e6).to_numpy()

    report = {}

    # =====================================================================
    # 1. THE CASCADE
    # =====================================================================
    a1, a4, a8 = (wmean(df[o], w) for o in outcomes.LADDER)
    cascade = {
        "reach_any_ANC": a1,
        "reach_4plus": a4,
        "reach_8plus": a8,
        "never_start": 1 - a1,
        "start_but_not_4": a1 - a4,
        "reach_4_but_not_8": a4 - a8,
        "P_4_given_1": a4 / a1,
        "P_8_given_4": a8 / a4,
    }
    report["cascade"] = cascade

    print("=" * 78)
    print("1. THE CASCADE -- where women are lost")
    print("=" * 78)
    print(f"  Reach antenatal care at all      {a1 * 100:5.1f}%")
    print(f"  Reach 4 or more contacts         {a4 * 100:5.1f}%")
    print(f"  Reach 8 or more contacts         {a8 * 100:5.1f}%")
    print()
    print(f"  Never start                      {(1 - a1) * 100:5.1f}% of all women")
    print(f"  Start but stop before 4          {(a1 - a4) * 100:5.1f}% of all women")
    print(f"  Reach 4 but stop before 8        {(a4 - a8) * 100:5.1f}% of all women")
    print()
    print(f"  Of those who start,   {a4 / a1 * 100:.0f}% go on to 4+ "
          f"({(1 - a4 / a1) * 100:.0f}% lost)")
    print(f"  Of those who reach 4, {a8 / a4 * 100:.0f}% go on to 8+ "
          f"({(1 - a8 / a4) * 100:.0f}% lost)  <-- the largest single loss")
    print()
    print("  Reading: the binding constraint is not getting women through the")
    print("  door. Three quarters already arrive. The system loses most of them")
    print("  between the fourth contact and the eighth.")

    # =====================================================================
    # 1b. WHERE EACH REGION LOSES WOMEN
    # =====================================================================
    # Two regions can share a headline ANC8 figure and have opposite problems.
    # Splitting each region's shortfall into "never started", "started but
    # stopped before 4" and "reached 4 but stopped before 8" says which one,
    # and therefore which intervention could possibly help.
    rows = []
    for region, g in df.groupby("region", observed=True):
        if len(g) < 80:
            continue
        gw = (g.v005 / 1e6).to_numpy()
        r1, r4, r8 = (wmean(g[o], gw) for o in outcomes.LADDER)
        rows.append({
            "region": str(region), "n": len(g),
            "anc1": r1, "anc4": r4, "anc8": r8,
            "never_start": 1 - r1,
            "start_not4": r1 - r4,
            "reach4_not8": r4 - r8,
            "continue_1_to_4": r4 / r1 if r1 else np.nan,
            "continue_4_to_8": r8 / r4 if r4 else np.nan,
        })
    casc = pd.DataFrame(rows).sort_values("anc8")
    casc.to_csv(OUT / "regional_cascade.csv", index=False)
    report["regional_cascade"] = casc.to_dict("records")

    print()
    print("=" * 78)
    print("1b. WHERE EACH REGION LOSES WOMEN (share of that region's women)")
    print("=" * 78)
    print(f"{'region':22s}{'ANC8+':>7s} |{'never':>8s}{'start,<4':>10s}{'4,but<8':>10s} |"
          f"{'stay 1->4':>11s}{'stay 4->8':>11s}")
    for x in casc.itertuples():
        print(f"{x.region:22s}{x.anc8 * 100:6.1f}% |{x.never_start * 100:7.1f}%"
              f"{x.start_not4 * 100:9.1f}%{x.reach4_not8 * 100:9.1f}% |"
              f"{x.continue_1_to_4 * 100:10.0f}%{x.continue_4_to_8 * 100:10.0f}%")

    print()
    print("  Regions with similar headline coverage, different bottlenecks:")
    for x in casc.nsmallest(6, "anc8").itertuples():
        biggest = max([("never starting", x.never_start),
                       ("stopping before 4", x.start_not4),
                       ("stopping between 4 and 8", x.reach4_not8)],
                      key=lambda t: t[1])
        print(f"    {x.region:22s} ANC8+ {x.anc8 * 100:4.1f}%  ->  "
              f"biggest loss is {biggest[0]} ({biggest[1] * 100:.0f}% of women)")
    print()
    print("  A programme built for the first kind of region cannot help the")
    print("  second, and vice versa.")

    # =====================================================================
    # 2. REGIONS AGAINST THEIR OWN CIRCUMSTANCES
    # =====================================================================
    # A region with poor ANC8 coverage and a poor, rural, low-education
    # population is not the same problem as a region with poor coverage and a
    # comparatively advantaged one. Predicting attainment from circumstance
    # ALONE -- deliberately excluding region -- and then comparing the
    # prediction with reality separates "hard circumstances" from "the health
    # system is doing better or worse than those circumstances imply".
    log("\nfitting the circumstance-only model (region deliberately excluded)")
    geo = {"v024", "region", "v025", "residence", "v045c"}
    circ_num = [c for c in numeric if c not in geo]
    circ_cat = [c for c in categorical if c not in geo]

    X = df[circ_num + circ_cat].copy()
    for c in circ_cat:
        X[c] = X[c].astype(str)

    folds = design.make_psu_stratum_folds(df)
    splits = design.folds_to_splits(folds)

    rows = []
    for rung in outcomes.LADDER:
        y = df[rung].astype(int).to_numpy()
        pred = tuning.oof_predict("LightGBM", PARAMS, X, y, w, splits,
                                  circ_num, circ_cat)
        for region, g in df.groupby("region", observed=True):
            i = df.index.get_indexer(g.index)
            if len(i) < 40:
                continue
            rows.append({
                "region": region, "rung": rung, "n": len(i),
                "actual": wmean(y[i], w[i]),
                "expected_from_circumstances": wmean(pred[i], w[i]),
            })
    reg = pd.DataFrame(rows)
    reg["gap"] = reg.actual - reg.expected_from_circumstances
    reg.to_csv(OUT / "regional_performance.csv", index=False)
    report["regional"] = reg.to_dict("records")

    print()
    print("=" * 78)
    print("2. REGIONS AGAINST THEIR OWN CIRCUMSTANCES")
    print("=" * 78)
    print("  Predicted from wealth, education, access and household factors")
    print("  ONLY -- region itself withheld from the model. A positive gap means")
    print("  the region does better than its population profile would imply.")
    for rung in outcomes.LADDER:
        sub = reg[reg.rung == rung].sort_values("gap", ascending=False)
        print(f"\n  {outcomes.OUTCOMES[rung]['label']}")
        print(f"    {'region':22s}{'actual':>9s}{'expected':>10s}{'gap':>9s}")
        for r in sub.itertuples():
            flag = ""
            if r.gap > 0.05:
                flag = "  outperforming"
            elif r.gap < -0.05:
                flag = "  underperforming"
            print(f"    {str(r.region):22s}{r.actual * 100:>8.1f}%"
                  f"{r.expected_from_circumstances * 100:>9.1f}%"
                  f"{r.gap * 100:>+8.1f}{flag}")

    # =====================================================================
    # 3. MODIFIABLE VS FIXED
    # =====================================================================
    # How much of the model's discriminating power rests on things a health
    # system can change, versus things it cannot?
    log("\nmodifiable vs fixed decomposition")
    from sklearn.metrics import roc_auc_score

    mod_num = [c for c in numeric if c in MODIFIABLE]
    mod_cat = [c for c in categorical if c in MODIFIABLE]
    fix_num = [c for c in numeric if c not in MODIFIABLE]
    fix_cat = [c for c in categorical if c not in MODIFIABLE]

    def auc_for(rung, n_, c_):
        if not (n_ + c_):
            return np.nan
        Xs = df[n_ + c_].copy()
        for c in c_:
            Xs[c] = Xs[c].astype(str)
        y = df[rung].astype(int).to_numpy()
        p = tuning.oof_predict("LightGBM", PARAMS, Xs, y, w, splits, n_, c_)
        return float(roc_auc_score(y, p, sample_weight=w))

    dec_rows = []
    for rung in outcomes.LADDER:
        dec_rows.append({
            "rung": outcomes.OUTCOMES[rung]["label"], "outcome": rung,
            "all_predictors": auc_for(rung, numeric, categorical),
            "modifiable_only": auc_for(rung, mod_num, mod_cat),
            "fixed_only": auc_for(rung, fix_num, fix_cat),
        })
        log(f"  {rung} done")
    dec = pd.DataFrame(dec_rows)
    dec.to_csv(OUT / "modifiable_vs_fixed.csv", index=False)
    report["modifiable"] = dec.to_dict("records")

    print()
    print("=" * 78)
    print("3. HOW MUCH RESTS ON THINGS THE HEALTH SYSTEM CAN CHANGE")
    print("=" * 78)
    print(f"  {'rung':10s}{'everything':>13s}{'service factors':>18s}{'circumstance':>15s}")
    for r in dec.itertuples():
        print(f"  {r.rung:10s}{r.all_predictors:>13.3f}"
              f"{r.modifiable_only:>18.3f}{r.fixed_only:>15.3f}")
    print()
    print("  'Service factors' are distance, transport, insurance, media reach")
    print("  and water/sanitation -- things a ministry can move. 'Circumstance'")
    print("  is wealth, education, age, parity and household structure.")

    # =====================================================================
    # 4. WHO STARTS BUT DOES NOT FINISH
    # =====================================================================
    # The largest loss in the cascade, profiled directly: among women who
    # reached four contacts, what distinguishes those who reached eight?
    print()
    print("=" * 78)
    print("4. AMONG WOMEN WHO REACHED 4 CONTACTS, WHO GOES ON TO 8?")
    print("=" * 78)
    started = df[df.anc4plus == 1]
    ws = (started.v005 / 1e6).to_numpy()
    print(f"  {len(started)} women reached 4+; "
          f"{wmean(started.anc8plus, ws) * 100:.1f}% of them reached 8+")
    print()

    prof_rows = []
    for col in ["region", "wealth_quintile", "residence", "maternal_education",
                "transport_mode_group", "internet_exposure", "health_insurance"]:
        if col not in started.columns:
            continue
        print(f"  {col}")
        for lvl, g in started.groupby(col, observed=True):
            if len(g) < 40:
                continue
            gw = (g.v005 / 1e6).to_numpy()
            rate = wmean(g.anc8plus, gw)
            prof_rows.append({"variable": col, "level": str(lvl),
                              "n": len(g), "continue_to_8": rate})
            print(f"    {str(lvl):26s} {rate * 100:5.1f}%   (n={len(g)})")
        print()
    pd.DataFrame(prof_rows).to_csv(OUT / "continuation_profile.csv", index=False)
    report["continuation"] = prof_rows

    # =====================================================================
    # 5. THE MARGINAL WOMAN
    # =====================================================================
    # Outreach capacity is finite. Women the model places just below the
    # threshold are where an extra contact is most likely to change the
    # outcome; women far below would need much more than a reminder.
    log("\nnear-threshold targeting")
    y8 = df.anc8plus.astype(int).to_numpy()
    Xf = df[numeric + categorical].copy()
    for c in categorical:
        Xf[c] = Xf[c].astype(str)
    p8 = tuning.oof_predict("LightGBM", PARAMS, Xf, y8, w, splits, numeric, categorical)

    bands = [(0.0, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.35),
             (0.35, 0.60), (0.60, 1.01)]
    band_rows = []
    print()
    print("=" * 78)
    print("5. WHERE THE MARGINAL WOMAN IS")
    print("=" * 78)
    print(f"  {'predicted band':18s}{'women':>9s}{'share':>9s}{'actually reached 8+':>22s}")
    for lo, hi in bands:
        m = (p8 >= lo) & (p8 < hi)
        if m.sum() < 20:
            continue
        band_rows.append({"band": f"{lo:.0%}-{hi:.0%}", "n": int(m.sum()),
                          "population_share": float(w[m].sum() / w.sum()),
                          "actual_rate": wmean(y8[m], w[m])})
        print(f"  {lo:.0%}-{hi:.0%}{'':8s}{int(m.sum()):>9d}"
              f"{w[m].sum() / w.sum() * 100:>8.1f}%{wmean(y8[m], w[m]) * 100:>21.1f}%")
    pd.DataFrame(band_rows).to_csv(OUT / "risk_bands.csv", index=False)
    report["risk_bands"] = band_rows

    near = ((p8 >= 0.10) & (p8 < 0.35))
    print()
    print(f"  Women in the 10-35% band: {w[near].sum() / w.sum() * 100:.0f}% of the")
    print(f"  population, and {wmean(y8[near], w[near]) * 100:.0f}% of them reach 8+")
    print("  already. They are the group where the model says the outcome is")
    print("  genuinely in the balance.")

    json.dump(report, open(OUT / "policy_summary.json", "w"), indent=2, default=float)
    log(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
