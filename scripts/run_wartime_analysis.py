"""Antenatal care for pregnancies that overlapped armed conflict.

    python scripts/run_wartime_analysis.py

The full cohort reaches back to births in mid-2021, and in the north many of
those pregnancies ran during the Tigray war (Nov 2020 - Nov 2022) or the
Tigrayan incursion into Afar and Amhara (Jul - Dec 2021). The Fano insurgency
in Amhara (full-scale from Aug 2023) falls instead on the RECENT births. So
"old birth" is not the same thing as "wartime birth", and exposure is
assigned by the calendar window of each pregnancy, not by birth age.

A pregnancy counts as exposed if at least EXPOSED_MONTHS of its nine months
fall inside a conflict window for the woman's region (docs/conflict_windows.csv,
with sources). Every result is repeated with the windows moved three months in
each direction, so no conclusion hangs on a single date.

The core estimate is a difference-in-differences. Comparing wartime and
post-war births within Tigray alone would mix the war with two other things
that also differ between older and newer births: the national trend in ANC,
and the extra recall error of a count remembered years later. Regions without
major conflict in the period experienced both of those and not the war, so
subtracting their change over the same calendar periods leaves the part
associated with the war.

What this cannot do, and says so: it describes women who were interviewed.
Women displaced out of their region, or who died, are not in the survey, and
some enumeration areas were excluded for security reasons. Those are
plausibly the worst-affected, so the estimates are more likely too small than
too large.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import cohorts, design, tuning  # noqa: E402

OUT = ROOT / "outputs" / "wartime"
WINDOWS = ROOT / "docs" / "conflict_windows.csv"

EXPOSED_MONTHS = 3
PREGNANCY_MONTHS = 9
# Regions with no major armed conflict in the period, used as the comparison.
# Oromia (OLA insurgency) and Benishangul-Gumuz (Metekel violence) had their
# own conflicts, so they are excluded from the main control group and added
# back in a sensitivity run.
CONTESTED = {"Tigray", "Afar", "Amhara", "Oromia", "Benishangul-Gumuz"}
N_BOOT = 1000

RUNGS = ["anc1plus", "anc4plus", "anc8plus"]


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def ym_to_cmc(ym: str) -> int:
    y, m = map(int, ym.split("-"))
    return (y - 1900) * 12 + m


def load_windows(shift: int = 0) -> list[dict]:
    w = pd.read_csv(WINDOWS)
    return [{"window": r.window, "regions": r.regions.split("|"),
             "start": ym_to_cmc(r.start) + shift, "end": ym_to_cmc(r.end) + shift}
            for r in w.itertuples()]


def exposure(df: pd.DataFrame, windows: list[dict]) -> pd.DataFrame:
    """Months of each pregnancy inside each window that applies to its region."""
    end = df.birth_cmc.to_numpy(dtype=float)
    start = end - (PREGNANCY_MONTHS - 1)
    region = df.region.astype(str).to_numpy()
    out = pd.DataFrame(index=df.index)
    for w in windows:
        overlap = np.clip(np.minimum(end, w["end"]) - np.maximum(start, w["start"]) + 1,
                          0, PREGNANCY_MONTHS)
        overlap = np.where(np.isin(region, w["regions"]), overlap, 0)
        out[w["window"]] = overlap
    out["exposed_any"] = (out[[w["window"] for w in windows]] >= EXPOSED_MONTHS).any(axis=1)
    return out


def wmean(x, w):
    x, w = np.asarray(x, float), np.asarray(w, float)
    return float((x * w).sum() / w.sum()) if w.sum() > 0 else np.nan


def cascade(n, w):
    """Where women sit on the ladder: never / start<4 / 4 to <8 / 8+."""
    return {"never": wmean(n < 1, w), "start_lt4": wmean((n >= 1) & (n < 4), w),
            "four_lt8": wmean((n >= 4) & (n < 8), w), "eight_plus": wmean(n >= 8, w)}


def did_all(frame, region, controls, measures):
    """Difference-in-differences for every measure at once.

    The control change is the average of WITHIN-region changes, each region
    weighted by its total survey weight -- not the change in the pooled
    control mean. Pooling is wrong here: the regional mix of births differs
    between the two periods, so the pooled mean can fall while every region
    rises (Simpson's paradox), and that artefact would be subtracted from
    Tigray as if it were a national trend.
    """
    keys = [frame.region.to_numpy(), frame.period.to_numpy()]
    wsum = frame._w.groupby(keys).sum()
    means = (frame[measures].mul(frame._w, axis=0).groupby(keys).sum()
             .div(wsum, axis=0))
    out = {}
    try:
        t = means.loc[(region, "after")] - means.loc[(region, "during")]
    except KeyError:
        return {m: np.nan for m in measures}
    changes, weights = [], []
    for c in controls:
        if (c, "after") in means.index and (c, "during") in means.index:
            changes.append(means.loc[(c, "after")] - means.loc[(c, "during")])
            weights.append(wsum.loc[c].sum())
    if not changes:
        return {m: np.nan for m in measures}
    ctrl = pd.concat(changes, axis=1).mul(weights, axis=1).sum(axis=1) / sum(weights)
    for m in measures:
        out[m] = float(t[m] - ctrl[m])
    out["_control_change"] = ctrl.to_dict()
    out["_tigray_change"] = t.to_dict()
    return out


def tigray_did(df, shift=0, controls=None):
    """Tigray's wartime gap, net of the national trend and recall."""
    tw = next(w for w in load_windows(shift) if w["window"] == "tigray_war")
    end = df.birth_cmc.to_numpy(dtype=float)
    start = end - (PREGNANCY_MONTHS - 1)
    overlap = np.clip(np.minimum(end, tw["end"]) - np.maximum(start, tw["start"]) + 1, 0, 9)
    # "during" = at least 3 months of the pregnancy inside the war window;
    # "after"  = conceived after the ceasefire. Partly exposed births in
    # between are dropped rather than forced into either group.
    period = np.where(overlap >= EXPOSED_MONTHS, "during",
                      np.where(start > tw["end"], "after", "between"))
    f = df.assign(period=period, _w=df.v005 / 1e6)
    f = f[f.period != "between"].copy()
    n = f.anc_contacts.fillna(0).to_numpy()
    f["never"] = (n < 1).astype(float)
    f["start_lt4"] = ((n >= 1) & (n < 4)).astype(float)
    f["four_lt8"] = ((n >= 4) & (n < 8)).astype(float)
    f["eight_plus"] = (n >= 8).astype(float)
    ctrl = controls or sorted(set(df.region.astype(str)) - CONTESTED)
    f["region"] = f.region.astype(str)
    return f, ctrl


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = cohorts.load("full")
    df["region"] = df.region.astype(str)
    w = (df.v005 / 1e6).to_numpy()
    report = {"windows": load_windows(), "exposed_months": EXPOSED_MONTHS}

    # ---- 1. who was exposed --------------------------------------------------
    ex = exposure(df, load_windows())
    df = pd.concat([df, ex], axis=1)
    counts = []
    for win in [c for c in ex.columns if c != "exposed_any"]:
        sel = df[win] >= EXPOSED_MONTHS
        for region, g in df[sel].groupby("region"):
            counts.append({"window": win, "region": region, "n_exposed": len(g)})
    counts = pd.DataFrame(counts)
    counts.to_csv(OUT / "exposure_counts.csv", index=False)
    log("women whose pregnancy overlapped a conflict window by >= 3 months:")
    for r in counts.itertuples():
        log(f"  {r.window:20s} {r.region:12s} n={r.n_exposed}")

    # ---- 2. ANC by region and birth period ------------------------------------
    df["period"] = np.where(df.months_since_birth < 24, "recent (<24m)", "older (24-35m)")
    rows = []
    for (region, period), g in df.groupby(["region", "period"]):
        gw = (g.v005 / 1e6).to_numpy()
        rows.append({"region": region, "period": period, "n": len(g),
                     **{r: wmean(g[r], gw) for r in RUNGS},
                     "share_exposed": float(g.exposed_any.mean())})
    by_period = pd.DataFrame(rows)
    by_period.to_csv(OUT / "anc_by_region_period.csv", index=False)

    # ---- 3. Tigray difference-in-differences ----------------------------------
    log("\nTigray: wartime vs post-war pregnancies, net of other regions")
    measures = RUNGS + ["never", "start_lt4", "four_lt8", "eight_plus"]
    did_rows = []
    for shift in (-3, 0, 3):
        for ctrl_name, extra in (("peaceful regions", []),
                                 ("all other regions", ["Oromia", "Benishangul-Gumuz"])):
            f, ctrl = tigray_did(df, shift=shift)
            ctrl = ctrl + extra
            point = did_all(f, "Tigray", ctrl, measures)

            # Stratified PSU bootstrap over the whole frame used, so Tigray and
            # the controls are resampled together, as they were sampled.
            boots = {m: [] for m in measures}
            idx_gen = design.stratified_psu_bootstrap(
                f.v022.to_numpy(), f.v021.to_numpy(),
                n_resamples=N_BOOT if (shift == 0 and not extra) else 300, seed=11)
            for idx in idx_gen:
                b = did_all(f.iloc[idx], "Tigray", ctrl, measures)
                for m in measures:
                    boots[m].append(b[m])
            n_t = f[f.region == "Tigray"].period.value_counts().to_dict()
            tg = f[f.region == "Tigray"]
            for m in measures:
                b = np.asarray(boots[m], dtype=float)
                did_rows.append({
                    "measure": m, "window_shift_months": shift, "controls": ctrl_name,
                    "did": point[m], "lo": float(np.nanquantile(b, 0.025)),
                    "hi": float(np.nanquantile(b, 0.975)),
                    "tigray_during_n": n_t.get("during", 0),
                    "tigray_after_n": n_t.get("after", 0),
                    "tigray_during": wmean(tg[tg.period == "during"][m], tg[tg.period == "during"]._w),
                    "tigray_after": wmean(tg[tg.period == "after"][m], tg[tg.period == "after"]._w),
                    "control_change_within_region": point["_control_change"][m],
                })
    dd = pd.DataFrame(did_rows)
    dd.to_csv(OUT / "tigray_difference_in_differences.csv", index=False)

    # Every region over the same two calendar periods the difference-in-
    # differences uses, so Tigray can be read against each region directly.
    f, _ = tigray_did(df)
    rows = []
    for (region, period), g in f.groupby(["region", "period"]):
        rows.append({"region": region, "period": period, "n": len(g),
                     **{m: wmean(g[m], g._w) for m in measures}})
    by_war = pd.DataFrame(rows)
    by_war.to_csv(OUT / "region_by_war_period.csv", index=False)
    main_dd = dd[(dd.window_shift_months == 0) & (dd.controls == "peaceful regions")]
    for r in main_dd.itertuples():
        log(f"  {r.measure:11s} Tigray {r.tigray_during * 100:5.1f}% -> {r.tigray_after * 100:5.1f}%"
            f"   controls (within-region) {r.control_change_within_region * 100:+5.1f} pts"
            f"   DiD {r.did * 100:+5.1f} pts [{r.lo * 100:+.1f}, {r.hi * 100:+.1f}]")
    log(f"  Tigray n: during {int(main_dd.tigray_during_n.iloc[0])}, "
        f"after {int(main_dd.tigray_after_n.iloc[0])}")
    report["tigray_did"] = main_dd.to_dict("records")
    rob = dd[dd.measure.isin(["anc1plus", "anc4plus", "anc8plus", "never"])]
    log("  robustness (DiD, pts) by window shift and control group:")
    for (m, c), g in rob.groupby(["measure", "controls"]):
        log(f"    {m:9s} {c:18s} " + "  ".join(
            f"{int(r.window_shift_months):+d}m: {r.did * 100:+5.1f}" for r in g.itertuples()))

    # ---- 4. did the drivers change under conflict? ----------------------------
    # Within the three northern regions, does wealth or distance predict ANC4+
    # differently for exposed pregnancies? Weighted logistic regression with
    # cluster-robust errors; small samples, so read the direction, not the
    # decimal.
    log("\ninteraction of exposure with wealth and distance (northern regions)")
    import statsmodels.api as sm

    north = df[df.region.isin(["Tigray", "Afar", "Amhara"])].copy()
    north["exposed"] = north.exposed_any.astype(float)
    north["wealth_z"] = (north.v191 - north.v191.mean()) / north.v191.std()
    trav = np.log1p(pd.to_numeric(north.s1101b, errors="coerce"))
    north["healthpost_log_z"] = (trav - trav.mean()) / trav.std()
    north = north.dropna(subset=["healthpost_log_z", "wealth_z"])
    inter = []
    for rung in RUNGS:
        X = pd.DataFrame({
            "exposed": north.exposed, "wealth": north.wealth_z,
            "distance": north.healthpost_log_z,
            "exposed_x_wealth": north.exposed * north.wealth_z,
            "exposed_x_distance": north.exposed * north.healthpost_log_z,
        })
        X = sm.add_constant(pd.concat([X, pd.get_dummies(north.region, drop_first=True,
                                                          dtype=float)], axis=1))
        mod = sm.GLM(north[rung].astype(float), X, family=sm.families.Binomial(),
                     freq_weights=(north.v005 / north.v005.mean()).to_numpy())
        fit = mod.fit(cov_type="cluster", cov_kwds={"groups": north.v021.to_numpy()})
        for term in ("exposed", "exposed_x_wealth", "exposed_x_distance", "wealth", "distance"):
            inter.append({"outcome": rung, "term": term,
                          "odds_ratio": float(np.exp(fit.params[term])),
                          "lo": float(np.exp(fit.conf_int().loc[term, 0])),
                          "hi": float(np.exp(fit.conf_int().loc[term, 1])),
                          "p": float(fit.pvalues[term]), "n": int(len(north))})
    inter = pd.DataFrame(inter)
    inter.to_csv(OUT / "exposure_interactions.csv", index=False)
    for r in inter[inter.outcome == "anc4plus"].itertuples():
        log(f"  ANC4+  {r.term:20s} OR {r.odds_ratio:5.2f} [{r.lo:.2f}, {r.hi:.2f}]  p={r.p:.3f}")

    # ---- 5. regions against their circumstances, recent births only ----------
    # The earlier finding that Tigray "underperforms its circumstances" used
    # all births, including wartime ones. Refit on the recent cohort, where
    # Tigray's pregnancies are mostly post-war, and see if it survives.
    log("\nregions against their circumstances, recent births only")
    spec = json.load(open(ROOT / "outputs" / "enhanced" / "feature_spec_v2.json"))
    geo = {"v024", "region", "v025", "residence", "v045c"}
    num = [c for c in spec["numeric_predictors"] if c not in geo]
    cat = [c for c in spec["categorical_predictors"] if c not in geo]
    params = {"n_estimators": 300, "learning_rate": 0.05, "num_leaves": 15, "reg_lambda": 1.0}
    gap_rows = []
    for cohort in ("full", "recent"):
        d = cohorts.load(cohort)
        d["region"] = d.region.astype(str)
        X = d[num + cat].copy()
        for c in cat:
            X[c] = X[c].astype(str)
        dw = (d.v005 / 1e6).to_numpy()
        splits = cohorts.folds(d)
        for rung in RUNGS:
            y = d[rung].astype(int).to_numpy()
            pred = tuning.oof_predict("LightGBM", params, X, y, dw, splits, num, cat, n_jobs=5)
            for region, g in d.groupby("region"):
                i = d.index.get_indexer(g.index)
                gap_rows.append({"cohort": cohort, "outcome": rung, "region": region,
                                 "n": len(i), "actual": wmean(y[i], dw[i]),
                                 "expected": wmean(pred[i], dw[i])})
            if cohort == "full":
                # Tigray on pregnancies conceived after the ceasefire only --
                # the recent window still contains some wartime pregnancies.
                tw = next(w for w in load_windows() if w["window"] == "tigray_war")
                start = d.birth_cmc.to_numpy(dtype=float) - (PREGNANCY_MONTHS - 1)
                i = np.flatnonzero((d.region == "Tigray").to_numpy() & (start > tw["end"]))
                gap_rows.append({"cohort": "post-war pregnancies", "outcome": rung,
                                 "region": "Tigray", "n": len(i),
                                 "actual": wmean(y[i], dw[i]),
                                 "expected": wmean(pred[i], dw[i])})
    gaps = pd.DataFrame(gap_rows)
    gaps["gap"] = gaps.actual - gaps.expected
    gaps.to_csv(OUT / "regional_gap_by_cohort.csv", index=False)
    pw = gaps[gaps.cohort == "post-war pregnancies"]
    for r in pw.itertuples():
        log(f"  Tigray, post-war pregnancies only ({r.n} women): {r.outcome} "
            f"actual {r.actual * 100:.1f}%  expected {r.expected * 100:.1f}%  gap {r.gap * 100:+.1f}")
    piv = gaps[(gaps.outcome == "anc8plus") & gaps.cohort.isin(["full", "recent"])].pivot(
        index="region", columns="cohort", values="gap")
    for region, r in piv.sort_values("recent").iterrows():
        log(f"  {region:22s} ANC8+ gap  all births {r['full'] * 100:+5.1f}   "
            f"recent births {r['recent'] * 100:+5.1f}")

    json.dump(report, open(OUT / "wartime_summary.json", "w"), indent=2, default=str)
    log(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
