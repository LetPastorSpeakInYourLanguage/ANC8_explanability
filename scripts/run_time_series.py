"""ANC over calendar time, from the survey's birth dates, and the sample datasets for
the studio's "Your data" screen.

    python scripts/run_time_series.py

The survey is one snapshot, but each woman's most recent birth has a date, so the
ladder can be followed by quarter and half-year of birth from mid-2021 to the end
of 2024. Two caveats travel with every series and are printed on the page:
  - only each woman's MOST RECENT birth is in the data, so the earlier periods
    under-represent women who have had another child since (younger, higher-parity);
  - a contact count is recalled less well the longer ago the birth was.
The edge periods (2021, 2025) are too thin and are left out.

Writes outputs/timeseries/:
  national_quarterly.csv    ANC1+/4+/8+ by quarter of birth, weighted, with 95% CIs
  regional_half_year.csv    the same by region and half-year
  sample_survey_quarterly.csv   a DHIS2-shaped sample built from the survey:
                            region x quarter, expected pregnancies and ANC counts
  sample_synthetic_monthly.csv  a SYNTHETIC monthly facility report for one
                            woreda (six facilities, four years), with seasonality,
                            a trend and a disruption, for trying the forecasters
  summary.json
Everything written is an aggregate or synthetic; no woman's record leaves here.
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

from anc8 import cohorts, design  # noqa: E402

OUT = ROOT / "outputs" / "timeseries"
POP = ROOT / "outputs" / "regional" / "population.json"
SEED = 2026
N_BOOT = 300
RUNGS = [("anc1plus", "anc1"), ("anc4plus", "anc4"), ("anc8plus", "anc8")]


def period(cmc: np.ndarray, per_year: int) -> np.ndarray:
    y = 1900 + (cmc - 1) // 12
    m = (cmc - 1) % 12
    k = m // (12 // per_year) + 1
    tag = "Q" if per_year == 4 else "H"
    return np.array([f"{int(a)}{tag}{int(b)}" for a, b in zip(y, k)])


def series(df: pd.DataFrame, key: str, by: list[str]) -> pd.DataFrame:
    rows = []
    for vals, g in df.groupby(by + [key]):
        vals = vals if isinstance(vals, tuple) else (vals,)
        row = dict(zip(by + ["period"], vals))
        row["n"] = len(g)
        w = g._w.to_numpy()
        boots = list(design.stratified_psu_bootstrap(g.v022.to_numpy(), g.v021.to_numpy(),
                                                     n_resamples=N_BOOT, seed=SEED)) if len(g) >= 20 else []
        for col, k in RUNGS:
            y = g[col].to_numpy().astype(float)
            row[k] = float(np.average(y, weights=w))
            if boots:
                b = [np.average(y[i], weights=w[i]) for i in boots]
                row[f"{k}_lo"], row[f"{k}_hi"] = float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))
        rows.append(row)
    return pd.DataFrame(rows)


def synthetic_monthly(rng: np.random.Generator) -> pd.DataFrame:
    """A made-up woreda: six facilities, 48 months, DHIS2-shaped. Seasonal dip in the
    main rains (June-September), a slow upward trend in ANC4+ and ANC8+, and a
    three-month disruption in one facility, so the forecasters have something to
    find. Nothing here is data."""
    facilities = {"Health centre A": 95, "Health centre B": 70, "Health post C": 30,
                  "Health post D": 25, "Health post E": 22, "Health post F": 18}
    months = pd.period_range("2021-07", periods=48, freq="M")
    rows = []
    for fac, size in facilities.items():
        for t, m in enumerate(months):
            season = 1 - 0.12 * np.sin(np.pi * (m.month - 5) / 4) if 6 <= m.month <= 9 else 1.0
            expected = size * (1 + 0.004 * t)
            shock = 0.45 if (fac == "Health post D" and 20 <= t <= 22) else 1.0
            p1 = min(0.97, (0.78 + 0.002 * t) * season * shock)
            p4 = min(p1, (0.50 + 0.004 * t) * season * shock)
            p8 = min(p4, (0.16 + 0.003 * t) * season * shock)
            n = rng.poisson(expected)
            a1 = rng.binomial(n, p1)
            a4 = rng.binomial(a1, p4 / p1)
            a8 = rng.binomial(a4, p8 / p4)
            rows.append({"period": str(m), "org_unit": fac, "expected_pregnancies": round(expected),
                         "anc1": a1, "anc4": a4, "anc8": a8})
    return pd.DataFrame(rows)


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    full = cohorts.load("full")
    full["_w"] = full.v005 / 1e6
    cmc = full.birth_cmc.to_numpy().astype(int)
    keep = (cmc >= (2022 - 1900) * 12 + 1) & (cmc <= (2024 - 1900) * 12 + 12)
    df = full[keep].copy()
    df["q"] = period(df.birth_cmc.to_numpy().astype(int), 4)
    df["h"] = period(df.birth_cmc.to_numpy().astype(int), 2)
    df["region"] = df.region.astype(str)

    nat = series(df, "q", [])
    nat.to_csv(OUT / "national_quarterly.csv", index=False)
    reg = series(df, "h", ["region"])
    reg.to_csv(OUT / "regional_half_year.csv", index=False)
    print(f"national quarterly: {len(nat)} quarters, n {nat.n.min()}-{nat.n.max()}")
    print(f"regional half-years: {len(reg)} cells, n {reg.n.min()}-{reg.n.max()}")

    # The survey-derived sample, in the shape a DHIS2 export has: one row per
    # region and quarter, a denominator and three counts.
    pop = json.loads(POP.read_text(encoding="utf-8"))["regions"]
    rq = series(df, "q", ["region"])
    rq["expected_pregnancies"] = [round(pop[r]["births"] / 4) for r in rq.region]
    for _, k in RUNGS:
        rq[k] = (rq[k] * rq.expected_pregnancies).round().astype(int)
    sample = rq.rename(columns={"region": "org_unit"})[
        ["period", "org_unit", "expected_pregnancies", "anc1", "anc4", "anc8"]]
    sample.to_csv(OUT / "sample_survey_quarterly.csv", index=False)

    synthetic_monthly(np.random.default_rng(SEED)).to_csv(OUT / "sample_synthetic_monthly.csv", index=False)

    (OUT / "summary.json").write_text(json.dumps({
        "periods": [str(nat.period.min()), str(nat.period.max())],
        "bootstrap_resamples": N_BOOT,
        "caveats": ["only each woman's most recent birth is in the survey",
                    "contact counts are recalled less well for older births"],
        "minutes": round((time.time() - t0) / 60, 1)}, indent=1), encoding="utf-8")
    print(f"done in {(time.time() - t0) / 60:.1f} min")


if __name__ == "__main__":
    main()
