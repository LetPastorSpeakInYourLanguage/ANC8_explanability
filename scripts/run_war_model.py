"""A model of what armed conflict does to antenatal care, for the conflict simulator.

    python scripts/run_war_model.py            # 200 bootstrap resamples
    python scripts/run_war_model.py --quick    # 20, for a smoke test

The Tigray war is the one full conflict-and-ceasefire the survey window covers.
This script turns it into a model a planner can move to another region:

  exposure   how much of a pregnancy fell under conflict. Each calendar month
             carries a disruption level: 1 while the conflict runs and, after a
             ceasefire, a level that decays as services return, exp(-months/tau).
             A birth's exposure is the average disruption over its nine months.
             tau = 0 means services come back the day the fighting stops.

  shock      per rung, on the log-odds scale: how much a fully exposed pregnancy's
             odds of reaching ANC1+, ANC4+ or ANC8+ fall. Fitted by weighted
             logistic regression on Tigray and the regions with no major conflict
             in the period, with region and half-year-of-birth fixed effects, so
             the national trend and the extra recall error of older births are
             absorbed by the comparison regions (the same design as the
             difference-in-differences in run_wartime_analysis.py).

  tau        one recovery lag shared by the three rungs (services come back as a
             whole), chosen on a grid by the pooled likelihood.

Uncertainty: the whole fit, tau included, is repeated on stratified PSU bootstrap
resamples. The simulator draws from these resamples, so its bands carry both.

Amhara is the out-of-sample check. The Fano insurgency (from August 2023) falls on
the recent births; the model has never seen Amhara. Its baseline is estimated from
Amhara births with no conflict exposure, then the Tigray-fitted shock is applied
at full intensity, and separately the one intensity that fits Amhara best is
estimated. Both are reported whether they fit or not.

Shifting a region's odds by the Tigray shock is a transfer assumption: it treats a
conflict elsewhere as the same kind of disruption to services. The output says so.

Writes outputs/war/:
  war_model.json       shocks, tau, bootstrap draws, backtest, observed series
  observed_by_half.csv the ladder per region and half-year of birth, with 95% CIs
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from anc8 import cohorts, design  # noqa: E402
from run_wartime_analysis import CONTESTED, load_windows  # noqa: E402

OUT = ROOT / "outputs" / "war"
RUNGS = ["anc1plus", "anc4plus", "anc8plus"]
PREG = 9
TAU_GRID = [0, 1, 2, 3, 4, 6, 9, 12, 18, 24, 36, 48]
# How fast services adapt while fighting continues (months); None = they do not.
KAPPA_GRID = [1, 2, 3, 4, 6, 9, 12, 18, 24, 36, None]
INTENSITY_GRID = np.round(np.arange(0, 1.51, 0.05), 2)
SEED = 2026


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def half_label(cmc: np.ndarray) -> np.ndarray:
    """Half-year of birth, e.g. 2023H2. The thin edges are folded inwards: the few
    2021 births join 2022H1 and the 2025 births join 2024H2."""
    y = 1900 + (np.asarray(cmc, float) - 1) // 12
    m = (np.asarray(cmc, float) - 1) % 12 + 1
    h = np.where(m <= 6, 1, 2)
    lab = np.char.add(np.char.add(y.astype(int).astype(str), "H"), h.astype(str))
    lab = np.where(y < 2022, "2022H1", lab)
    lab = np.where(y >= 2025, "2024H2", lab)
    return lab


def disruption_exposure(birth_cmc: np.ndarray, start: int, end: int, tau: float,
                        kappa: float | None = None) -> np.ndarray:
    """Average disruption over each pregnancy's nine months.

    Inside [start, end] the disruption is 1, or exp(-(m - start) / kappa) when
    services adapt while the fighting goes on. After `end` it decays from its level
    at the ceasefire as exp(-(m - end) / tau). Before `start` it is 0.
    """
    b = np.asarray(birth_cmc, float)
    months = b[:, None] - np.arange(PREG)[None, :]
    inside = (months >= start) & (months <= end)
    level = np.exp(-(months - start) / kappa) if kappa else np.ones_like(months)
    d = np.where(inside, level, 0.0)
    if tau > 0:
        at_end = np.exp(-(end - start) / kappa) if kappa else 1.0
        d = np.where(months > end, at_end * np.exp(-(months - end) / tau), d)
    return d.mean(axis=1)


def design_matrix(df: pd.DataFrame, regions: list[str], halves: list[str]) -> np.ndarray:
    R = (df.region.astype(str).to_numpy()[:, None] == np.array(regions)[None, 1:]).astype(float)
    H = (df.half.to_numpy()[:, None] == np.array(halves)[None, 1:]).astype(float)
    return np.hstack([R, H])


def fit_logit(X, y, w):
    m = LogisticRegression(penalty=None, solver="lbfgs", max_iter=500)
    m.fit(X, y, sample_weight=w)
    p = np.clip(m.predict_proba(X)[:, 1], 1e-9, 1 - 1e-9)
    ll = float((w * (y * np.log(p) + (1 - y) * np.log(1 - p))).sum())
    return m, ll


def fit_war(df: pd.DataFrame, war: dict, regions: list[str], halves: list[str],
            taus: list[float] | None = None) -> dict:
    """Shocks per rung and the shared recovery lag, on one (re)sample. With `taus`
    of length one the lag is fixed and only the shocks are estimated."""
    base = design_matrix(df, regions, halves)
    w = df._w.to_numpy()
    tig = (df.region.astype(str) == "Tigray").to_numpy()
    best, profile = None, {}
    for tau in (taus or TAU_GRID):
        x = np.where(tig, disruption_exposure(df.birth_cmc.to_numpy(), war["start"], war["end"], tau), 0.0)
        X = np.hstack([base, x[:, None]])
        fits = {r: fit_logit(X, df[r].to_numpy().astype(int), w) for r in RUNGS}
        ll = sum(f[1] for f in fits.values())
        profile[tau] = {"ll": ll, "shock": {r: float(f[0].coef_[0][-1]) for r, f in fits.items()}}
        if best is None or ll > best["ll"]:
            best = {"ll": ll, "tau": tau, "models": {r: f[0] for r, f in fits.items()}, "x": x}
    best["shock"] = profile[best["tau"]]["shock"]
    best["profile"] = profile
    return best


def weighted_ci(y, w, strata, psus, n_boot, seed):
    est = float(np.average(y, weights=w))
    if n_boot == 0 or len(y) < 10:
        return est, np.nan, np.nan
    bs = [np.average(y[i], weights=w[i]) for i in
          design.stratified_psu_bootstrap(strata, psus, n_resamples=n_boot, seed=seed)]
    return est, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def observed_series(full: pd.DataFrame, n_boot: int) -> pd.DataFrame:
    rows = []
    groups = [(str(r), full.region.astype(str) == r) for r in sorted(full.region.astype(str).unique())]
    groups.append(("Regions without conflict", ~full.region.astype(str).isin(CONTESTED)))
    for name, m in groups:
        g = full[m.to_numpy()]
        for h, gh in g.groupby("half"):
            row = {"region": name, "half": h, "n": len(gh)}
            for r, key in [("anc1plus", "anc1"), ("anc4plus", "anc4"), ("anc8plus", "anc8")]:
                est, lo, hi = weighted_ci(gh[r].to_numpy().astype(float), gh._w.to_numpy(),
                                          gh.v022.to_numpy(), gh.v021.to_numpy(), n_boot, SEED)
                row.update({key: est, f"{key}_lo": lo, f"{key}_hi": hi})
            rows.append(row)
    return pd.DataFrame(rows)


def amhara_backtest(full: pd.DataFrame, fit: dict, fano: dict, incursion: dict,
                    regions: list[str], halves: list[str]) -> dict:
    """Predict Amhara's Fano-period births from the Tigray model, never fitted on Amhara."""
    a = full[full.region.astype(str) == "Amhara"].copy()
    b = a.birth_cmc.to_numpy()
    x_fano = disruption_exposure(b, fano["start"], fano["end"], fit["tau"])
    x_inc = disruption_exposure(b, incursion["start"], incursion["end"], 0)
    clean = (x_fano == 0) & (x_inc == 0)
    w = a._w.to_numpy()
    H = (a.half.to_numpy()[:, None] == np.array(halves)[None, 1:]).astype(float)
    out = {"n_baseline": int(clean.sum()), "n_exposed": int((x_fano > 0).sum())}
    offsets, alphas = {}, {}
    for r in RUNGS:
        m = fit["models"][r]
        coefs = m.coef_[0]
        n_reg = len(regions) - 1
        half_eff = H @ coefs[n_reg:n_reg + len(halves) - 1]
        # Amhara's own level, from its unexposed births, holding the time effects fixed.
        y = a[r].to_numpy().astype(int)
        grid = np.linspace(-6, 6, 1201)
        lls = []
        for al in grid:
            p = np.clip(1 / (1 + np.exp(-(al + half_eff[clean]))), 1e-9, 1 - 1e-9)
            lls.append((w[clean] * (y[clean] * np.log(p) + (1 - y[clean]) * np.log(1 - p))).sum())
        alphas[r] = float(grid[int(np.argmax(lls))])
        offsets[r] = alphas[r] + half_eff
    # The one intensity that fits Amhara's exposed births best, all rungs together.
    ex = x_fano > 0
    lls = []
    for I in INTENSITY_GRID:
        tot = 0.0
        for r in RUNGS:
            y = a[r].to_numpy().astype(int)[ex]
            p = np.clip(1 / (1 + np.exp(-(offsets[r][ex] + I * fit["shock"][r] * x_fano[ex]))), 1e-9, 1 - 1e-9)
            tot += (w[ex] * (y * np.log(p) + (1 - y) * np.log(1 - p))).sum()
        lls.append(tot)
    I_fit = float(INTENSITY_GRID[int(np.argmax(lls))])
    out["intensity_fit"] = I_fit

    # Or: the full Tigray shock at onset, absorbed by services while fighting goes on.
    def ll_kappa(k):
        x = disruption_exposure(b, fano["start"], fano["end"], fit["tau"], k)
        tot = 0.0
        for r in RUNGS:
            y = a[r].to_numpy().astype(int)[ex]
            p = np.clip(1 / (1 + np.exp(-(offsets[r][ex] + fit["shock"][r] * x[ex]))), 1e-9, 1 - 1e-9)
            tot += (w[ex] * (y * np.log(p) + (1 - y) * np.log(1 - p))).sum()
        return tot
    kl = [ll_kappa(k) for k in KAPPA_GRID]
    kappa = KAPPA_GRID[int(np.argmax(kl))]
    out["kappa_fit"] = kappa
    x_adapt = disruption_exposure(b, fano["start"], fano["end"], fit["tau"], kappa)

    rows = []
    for h in sorted(set(a.half)):
        m = (a.half == h).to_numpy()
        row = {"half": h, "n": int(m.sum()), "exposure": float(np.average(x_fano[m], weights=w[m]))}
        for r, key in [("anc1plus", "anc1"), ("anc4plus", "anc4"), ("anc8plus", "anc8")]:
            row[f"observed_{key}"] = float(np.average(a[r].to_numpy()[m], weights=w[m]))
            for tag, I, x in (("full", 1.0, x_fano), ("fit", I_fit, x_fano), ("none", 0.0, x_fano),
                              ("adapt", 1.0, x_adapt)):
                p = 1 / (1 + np.exp(-(offsets[r][m] + I * fit["shock"][r] * x[m])))
                row[f"{tag}_{key}"] = float(np.average(p, weights=w[m]))
        rows.append(row)
    out["rows"] = rows
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    n_boot = 20 if args.quick else 200
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)

    windows = {w["window"]: w for w in load_windows(0)}
    war, fano, inc = windows["tigray_war"], windows["fano_insurgency"], windows["northern_incursion"]

    full = cohorts.load("full")
    full["_w"] = full.v005 / 1e6
    full["half"] = half_label(full.birth_cmc.to_numpy())
    halves = sorted(full.half.unique())

    fit_df = full[~full.region.astype(str).isin(CONTESTED - {"Tigray"})].reset_index(drop=True)
    regions = ["Tigray"] + sorted(set(fit_df.region.astype(str)) - {"Tigray"})
    log(f"fit sample: {len(fit_df):,} women in {len(regions)} regions; halves {halves}")

    point = fit_war(fit_df, war, regions, halves)
    log(f"point fit: tau {point['tau']} months, shocks "
        + ", ".join(f"{r} {v:+.3f}" for r, v in point["shock"].items()))

    draws = []
    for i, idx in enumerate(design.stratified_psu_bootstrap(
            fit_df.v022.to_numpy(), fit_df.v021.to_numpy(), n_resamples=n_boot, seed=SEED)):
        # The lag is held at its estimate: the data cover about two years after the
        # ceasefire, too short to pin a slow recovery down, and letting it float lets
        # a very slow recovery trade off against an implausibly deep shock. Its own
        # uncertainty is the profile-likelihood range below, and the simulator lets
        # the user move it.
        f = fit_war(fit_df.iloc[idx].reset_index(drop=True), war, regions, halves, taus=[point["tau"]])
        draws.append({"tau": f["tau"], **{r: round(f["shock"][r], 4) for r in RUNGS}})
        if (i + 1) % 25 == 0:
            log(f"  bootstrap {i + 1}/{n_boot}")
    D = pd.DataFrame(draws)

    # In-sample fit for Tigray by half-year: what the model says happened.
    tig = fit_df.region.astype(str) == "Tigray"
    X = np.hstack([design_matrix(fit_df, regions, halves), point["x"][:, None]])
    fitted = []
    for h in halves:
        m = (tig & (fit_df.half == h)).to_numpy()
        if not m.any():
            continue
        row = {"half": h, "exposure": float(np.average(point["x"][m], weights=fit_df._w[m]))}
        for r, key in [("anc1plus", "anc1"), ("anc4plus", "anc4"), ("anc8plus", "anc8")]:
            p = point["models"][r].predict_proba(X[m])[:, 1]
            X0 = X[m].copy()
            X0[:, -1] = 0
            p0 = point["models"][r].predict_proba(X0)[:, 1]
            row[key] = float(np.average(p, weights=fit_df._w[m]))
            row[f"{key}_no_war"] = float(np.average(p0, weights=fit_df._w[m]))
        fitted.append(row)

    # The check the simulator rests on: the model, run on Tigray at intensity 1, should
    # reproduce the difference-in-differences estimated directly from the data.
    exp_any = disruption_exposure(fit_df.birth_cmc.to_numpy(), war["start"], war["end"], 0)
    during = (tig & (exp_any * PREG >= 3)).to_numpy()
    after = (tig & (exp_any == 0)).to_numpy()
    did_check = {}
    for r in RUNGS:
        p = point["models"][r].predict_proba(X)[:, 1]
        X0 = X.copy()
        X0[:, -1] = 0
        p0 = point["models"][r].predict_proba(X0)[:, 1]
        eff = p0 - p  # what the war took from each woman
        wd, wa = fit_df._w.to_numpy()[during], fit_df._w.to_numpy()[after]
        did_check[r] = float(np.average(eff[during], weights=wd) - np.average(eff[after], weights=wa))
    ref = pd.read_csv(ROOT / "outputs" / "wartime" / "tigray_difference_in_differences.csv")
    ref = ref[(ref.window_shift_months == 0) & (ref.controls == "peaceful regions")].set_index("measure")
    did_check = {r: {"model": v, "did": float(ref.loc[r, "did"]), "lo": float(ref.loc[r, "lo"]),
                     "hi": float(ref.loc[r, "hi"])} for r, v in did_check.items()}
    log("  model vs DiD: " + ", ".join(f"{r} {v['model']:+.3f} (DiD {v['did']:+.3f})" for r, v in did_check.items()))

    log("Amhara backtest")
    back = amhara_backtest(full, point, fano, inc, regions, halves)
    # Its intensity interval: refit the Amhara intensity on every bootstrap's shocks.
    I_draws, K_draws = [], []
    for d in draws[: min(len(draws), 100)]:
        f = dict(point)
        f["shock"] = {r: d[r] for r in RUNGS}
        f["tau"] = d["tau"]
        bt = amhara_backtest(full, f, fano, inc, regions, halves)
        I_draws.append(bt["intensity_fit"])
        K_draws.append(bt["kappa_fit"] if bt["kappa_fit"] is not None else 999)
        d["kappa"] = bt["kappa_fit"]
    back["intensity_lo"] = float(np.percentile(I_draws, 2.5))
    back["intensity_hi"] = float(np.percentile(I_draws, 97.5))
    back["kappa_interval"] = [float(np.percentile(K_draws, 2.5)), float(np.percentile(K_draws, 97.5))]
    log(f"  Amhara adaptation {back['kappa_fit']} months ({back['kappa_interval']})")
    log(f"  Amhara intensity {back['intensity_fit']:.2f} "
        f"({back['intensity_lo']:.2f} to {back['intensity_hi']:.2f})")

    log("observed series by region and half-year")
    obs = observed_series(full, 0 if args.quick else 300)
    obs.to_csv(OUT / "observed_by_half.csv", index=False)

    # Profile likelihood for the lag: every tau within 1.92 log-likelihood units of the
    # best (a 95% likelihood-ratio interval) is consistent with the data.
    llmax = point["ll"]
    tau_supported = [t for t, v in point["profile"].items() if 2 * (llmax - v["ll"]) <= 3.84]
    tau_profile = [{"tau": t, "delta_ll": v["ll"] - llmax, "shock": v["shock"]}
                   for t, v in point["profile"].items()]
    log(f"  tau supported by the data: {min(tau_supported)} to {max(tau_supported)} months")

    def q(col):
        return [float(np.percentile(D[col], 2.5)), float(np.percentile(D[col], 97.5))]

    out = {
        "quick": args.quick,
        "bootstrap_resamples": n_boot,
        "fit": {
            "regions": regions,
            "n": int(len(fit_df)),
            "n_tigray": int(tig.sum()),
            "tau_months": point["tau"],
            "tau_supported": [min(tau_supported), max(tau_supported)],
            "tau_profile": tau_profile,
            "shock": {r: {"log_odds": point["shock"][r], "interval": q(r),
                          "odds_ratio": float(np.exp(point["shock"][r]))} for r in RUNGS},
        },
        "draws": draws,
        "fitted_tigray": fitted,
        "did_check": did_check,
        "backtest_amhara": back,
        "windows": [{k: (v if not isinstance(v, np.integer) else int(v)) for k, v in w.items()}
                    for w in windows.values()],
        "minutes": round((time.time() - t0) / 60, 1),
    }
    (OUT / "war_model.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    log(f"done in {out['minutes']} min")


if __name__ == "__main__":
    main()
