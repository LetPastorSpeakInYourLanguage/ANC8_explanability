"""What-if scenarios for the planner: g-computation with the fitted rung models.

    python scripts/run_scenarios.py            # 200 bootstrap resamples
    python scripts/run_scenarios.py --quick    # 20

A lever is something a health system can change, written as an edit to each woman's
record: "a health post within 30 minutes" sets her travel time to at most 30
minutes; "insured" sets her insurance to yes. Every woman is re-scored by the
explainable boosting model for each rung with the lever applied, and the average
change in her predicted chance, by region, is the lever's effect (g-computation, or
standardisation). Women already in the better state are unchanged.

Levers combine exactly. With seven levers there are 128 on/off combinations; each
woman is scored under every one. If a planner reaches a share f_i of the women each
lever could move, at random and independently, a woman's expected chance is the
sum over combinations S of prod(f_i, i in S) prod(1 - f_j, j not in S) p_S, and
because averaging is linear the same weights apply to each region's average of p_S.
So the browser can compute any mix of coverages exactly from 128 numbers per region
and rung. Reaching the women who would gain most first (targeting) is also given,
per lever, as a curve.

An eighth lever, an earlier first visit, needs a model that knows when ANC started.
It is fitted here on the ANC-entry cohort (logistic regression, all predictors plus
early_anc) and applies to women who start ANC; it is added on top of the others.

Uncertainty: stratified PSU bootstrap of each region's average effect with the
model held fixed (who lives where), plus the same effects from the logistic
regression as a check that the answer is not one model's quirk.

All of this is association-based: it says what the model expects if women's
circumstances changed, not what an intervention would cause.

Writes outputs/scenarios/scenarios.json.
"""

from __future__ import annotations

import argparse
import itertools
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
sys.path.insert(0, str(ROOT / "scripts"))

from anc8 import cohorts, design  # noqa: E402

ENHANCED = ROOT / "outputs" / "enhanced"
OUT = ROOT / "outputs" / "scenarios"
RUNGS = {"anc1plus": "anc1", "anc4plus": "anc4", "anc8plus": "anc8"}
SEED = 2026
DECILES = np.linspace(0, 1, 11)


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


# ------------------------------------------------------------------ the levers
# Each returns (edited copy, mask of women it changes). They touch disjoint columns,
# so applying several in sequence is the same as applying them together.

def _set(d, mask, col, value):
    """Assign in the column's own dtype (the frame mixes float32 and float64)."""
    dt = d[col].dtype
    if pd.api.types.is_numeric_dtype(dt) and not isinstance(value, str):
        value = np.asarray(value).astype(dt).item()
    d.loc[mask, col] = value


def _healthpost(d):
    m = d.s1101b.notna() & (d.s1101b > 30)
    _set(d, m, "s1101b", 30.0)
    _set(d, m, "travel_healthpost_log", np.log1p(30.0))
    _set(d, m, "travel_healthpost_topcoded", 0.0)
    return m


def _hospital(d):
    m = d.s1101 > 60
    _set(d, m, "s1101", 60.0)
    _set(d, m, "travel_hospital_log", np.log1p(60.0))
    _set(d, m, "travel_hospital_topcoded", 0.0)
    if "v115" in d:
        _set(d, m & (d.v115 < 998) & (d.v115 > 60), "v115", 60)
    return m


def _barriers(d):
    m = (d.v467c == 1) | (d.v467d == 1)
    for c in ("v467c", "v467d"):
        _set(d, d[c] == 1, c, 2)
    d["access_barrier_count"] = sum(d[c].eq(1).astype(float) for c in ("v467b", "v467c", "v467d", "v467f"))
    return m


def _insurance(d):
    m = d.health_insurance.astype(str) != "Yes"
    _set(d, m, "health_insurance", "Yes")
    _set(d, m, "v481", 1)
    return m


def _information(d):
    m = d.v158 < 2
    _set(d, m, "v158", 2)
    _set(d, m, "radio_weekly", 1.0)
    return m


def _intention(d):
    m = d.pregnancy_intention.astype(str).isin(["Wanted later", "Wanted no more"])
    _set(d, m, "pregnancy_intention", "Wanted then")
    return m


def _agency(d):
    items = [c for c in ("v743a", "v743b", "v743d", "v743f") if c in d]
    m = pd.Series(False, index=d.index)
    for c in items:
        alone = d[c].isin([4, 5, 6])  # husband, someone else or other alone
        m |= alone
        _set(d, alone, c, 2)  # jointly
    hp = d.healthcare_decision_participation.astype(str) == "Does not participate"
    m |= hp
    _set(d, hp, "healthcare_decision_participation", "Participates")
    d["decision_participation_count"] = sum(d[c].isin([1, 2]).astype(float) for c in items)
    return m


LEVERS = [
    {"key": "healthpost", "label": "Health post within 30 minutes", "concept": "healthpost",
     "who": "women more than 30 minutes from a health post", "apply": _healthpost},
    {"key": "hospital", "label": "Health centre or hospital within an hour", "concept": "hospital",
     "who": "women more than an hour from a health centre or hospital", "apply": _hospital},
    {"key": "barriers", "label": "Distance and cost no longer a big problem", "concept": "barriers",
     "who": "women for whom distance or money is a big problem", "apply": _barriers},
    {"key": "insurance", "label": "Health insurance", "concept": "insurance",
     "who": "uninsured women", "apply": _insurance},
    {"key": "information", "label": "Weekly radio health messages", "concept": "information",
     "who": "women who do not listen to radio weekly", "apply": _information},
    {"key": "intention", "label": "Every pregnancy wanted (family planning)", "concept": "intention",
     "who": "women whose pregnancy was mistimed or unwanted", "apply": _intention},
    {"key": "agency", "label": "Women share household decisions", "concept": "agency",
     "who": "women with no say in household or health decisions", "apply": _agency},
]


def model_matrix(df, numeric, categorical):
    X = df[numeric + categorical].copy()
    for c in categorical:
        X[c] = X[c].astype(str)
    return X


def weighted_by_region(values: np.ndarray, w: np.ndarray, reg_idx: np.ndarray, n_reg: int) -> np.ndarray:
    """Weighted mean of each column of `values` within each region; the last row is national."""
    V = values if values.ndim == 2 else values[:, None]
    num = np.stack([np.bincount(reg_idx, weights=w * V[:, j], minlength=n_reg) for j in range(V.shape[1])], 1)
    den = np.bincount(reg_idx, weights=w, minlength=n_reg)[:, None]
    nat = (w[:, None] * V).sum(0, keepdims=True) / w.sum()
    return np.vstack([num / den, nat])


def early_visit(full: pd.DataFrame, n_boot: int) -> dict:
    """The earlier-first-visit lever, from a model fitted on the ANC-entry cohort."""
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    blob = joblib_load(ENHANCED / "anc8plus" / "enhanced_models.joblib")
    numeric, categorical = blob["numeric"], blob["categorical"]
    e = cohorts.load("entry")
    w = (e.v005 / 1e6).to_numpy()
    dev = (e.partition == "development").to_numpy()
    X = model_matrix(e, numeric, categorical)
    X["early_anc"] = e.early_anc.astype(float)
    pre = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)),
                          ("sc", StandardScaler())]), numeric + ["early_anc"]),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=20), categorical),
    ])
    regions = sorted(full.region.astype(str).unique())
    reg_idx = pd.Categorical(e.region.astype(str), categories=regions).codes
    # share of each region's women (full cohort) who are in the ANC-entry cohort's
    # situation: started ANC. The lever's effect among them is scaled by it.
    fw = (full.v005 / 1e6).to_numpy()
    fidx = pd.Categorical(full.region.astype(str), categories=regions).codes
    start_share = weighted_by_region(full.anc1plus.to_numpy().astype(float), fw, fidx, len(regions))[:, 0]

    out = {"who": "women who start ANC after the first three months", "rungs": {},
           "eligible": None, "n": int(len(e))}
    late = (e.early_anc == 0).to_numpy()
    out["eligible"] = (weighted_by_region(late.astype(float), w, reg_idx, len(regions))[:, 0]
                       * start_share).tolist()
    for outcome in ("anc4plus", "anc8plus"):
        y = e[outcome].to_numpy().astype(int)
        pipe = Pipeline([("pre", pre), ("m", LogisticRegression(C=0.1, max_iter=2000))])
        pipe.fit(X[dev], y[dev], m__sample_weight=w[dev])
        X1 = X.copy()
        X1["early_anc"] = 1.0
        gain = pipe.predict_proba(X1)[:, 1] - pipe.predict_proba(X)[:, 1]
        pt = weighted_by_region(gain, w, reg_idx, len(regions))[:, 0] * start_share
        boots = []
        for idx in design.stratified_psu_bootstrap(e.v022.to_numpy(), e.v021.to_numpy(), n_resamples=n_boot, seed=SEED):
            boots.append(weighted_by_region(gain[idx], w[idx], reg_idx[idx], len(regions))[:, 0] * start_share)
        B = np.array(boots)
        out["rungs"][RUNGS[outcome]] = {"effect": pt.tolist(),
                                        "lo": np.nanpercentile(B, 2.5, 0).tolist(),
                                        "hi": np.nanpercentile(B, 97.5, 0).tolist()}
        log(f"  early visit: {outcome} national {pt[-1] * 100:+.2f} pt")
    return out


def joblib_load(p):
    import joblib
    return joblib.load(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    n_boot = 20 if args.quick else 200
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)

    full = cohorts.load("full")
    w = (full.v005 / 1e6).to_numpy()
    regions = sorted(full.region.astype(str).unique())
    reg_idx = pd.Categorical(full.region.astype(str), categories=regions).codes
    names = regions + ["Ethiopia"]

    # Who each lever could move, per region.
    masks = {}
    for lv in LEVERS:
        d = full.copy()
        masks[lv["key"]] = lv["apply"](d).to_numpy()
    eligible = {k: weighted_by_region(m.astype(float), w, reg_idx, len(regions))[:, 0].tolist()
                for k, m in masks.items()}

    subsets = list(itertools.product([0, 1], repeat=len(LEVERS)))
    out = {"levers": [{k: v for k, v in lv.items() if k != "apply"} for lv in LEVERS],
           "regions": names, "subsets": ["".join(map(str, s)) for s in subsets],
           "eligible": eligible, "rungs": {}, "bootstrap_resamples": n_boot}

    frames = {}
    for s in subsets:
        d = full.copy()
        for on, lv in zip(s, LEVERS):
            if on:
                lv["apply"](d)
        frames[s] = d

    for outcome, rung in RUNGS.items():
        blob = joblib_load(ENHANCED / outcome / "enhanced_models.joblib")
        numeric, categorical = blob["numeric"], blob["categorical"]
        ebm = blob["models"]["Explainable Boosting"]
        lr = blob["models"].get("Logistic regression")
        P = np.column_stack([ebm.predict_proba(model_matrix(frames[s], numeric, categorical))[:, 1] for s in subsets])
        means = weighted_by_region(P, w, reg_idx, len(regions))  # (regions+1, 128)
        singles = [subsets.index(tuple(int(j == i) for j in range(len(LEVERS)))) for i in range(len(LEVERS))]
        all_on = subsets.index(tuple([1] * len(LEVERS)))
        gains = P[:, singles + [all_on]] - P[:, [0]]  # women x (levers + all)

        # Targeting: reach the women who would gain most first. For each lever and
        # region, the region's average gain when the top x% of its eligible women
        # (by weight) are reached.
        targeted = {}
        for i, lv in enumerate(LEVERS):
            g = gains[:, i]
            m = masks[lv["key"]]
            curves = []
            for ri in range(len(regions) + 1):
                sel = m & ((reg_idx == ri) if ri < len(regions) else True)
                tot_w = w[(reg_idx == ri) if ri < len(regions) else slice(None)].sum()
                gs, ws = g[sel], w[sel]
                order = np.argsort(-gs)
                cw = np.cumsum(ws[order])
                cg = np.cumsum((gs * ws)[order])
                if len(cw) == 0:
                    curves.append([0.0] * len(DECILES))
                    continue
                pts = [0.0] + [float(np.interp(f * cw[-1], cw, cg) / tot_w) for f in DECILES[1:]]
                curves.append(pts)
            targeted[lv["key"]] = curves

        boots = []
        for idx in design.stratified_psu_bootstrap(full.v022.to_numpy(), full.v021.to_numpy(),
                                                   n_resamples=n_boot, seed=SEED):
            boots.append(weighted_by_region(gains[idx], w[idx], reg_idx[idx], len(regions)))
        B = np.array(boots)  # (boot, regions+1, levers+1)
        lo, hi = np.nanpercentile(B, 2.5, 0), np.nanpercentile(B, 97.5, 0)

        check = None
        if lr is not None:
            PL0 = lr.predict_proba(model_matrix(frames[subsets[0]], numeric, categorical))[:, 1]
            lr_gain = np.column_stack([
                lr.predict_proba(model_matrix(frames[subsets[j]], numeric, categorical))[:, 1] - PL0
                for j in singles + [all_on]])
            check = weighted_by_region(lr_gain, w, reg_idx, len(regions)).tolist()

        out["rungs"][rung] = {
            "means": np.round(means, 5).tolist(),
            "gain": weighted_by_region(gains, w, reg_idx, len(regions)).tolist(),
            "lo": lo.tolist(), "hi": hi.tolist(),
            "logistic_check": check,
            "targeted": targeted,
        }
        nat = out["rungs"][rung]["gain"][-1]
        log(f"{rung}: " + ", ".join(f"{lv['key']} {g * 100:+.2f}" for lv, g in zip(LEVERS, nat))
            + f", all {nat[-1] * 100:+.2f} pt")

    log("earlier first visit (ANC-entry model)")
    out["early_visit"] = early_visit(full, n_boot)
    out["minutes"] = round((time.time() - t0) / 60, 1)
    (OUT / "scenarios.json").write_text(json.dumps(out), encoding="utf-8")
    log(f"done in {out['minutes']} min")


if __name__ == "__main__":
    main()
