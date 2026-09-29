"""Composite women for the Model lab: what the networks say about a typical woman of
each region and wealth group.

    python scripts/build_lab_profiles.py

For each region x wealth quintile cell with at least MIN_N women (and for each
region, and for Ethiopia, overall) every predictor is set to its survey-weighted
median (numbers) or most common answer (categories) in that cell. The result is a
composite, not a person: each answer is the commonest one among those women, so no
row is anybody's record. These are aggregates and can be shipped with the app.

Writes outputs/deep/profiles.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_deep_models as rdm  # noqa: E402

MIN_N = 25
QUINTILES = ["Poorest", "Poorer", "Middle", "Richer", "Richest"]


def wmedian(x: np.ndarray, w: np.ndarray) -> float | None:
    m = ~np.isnan(x)
    if not m.any():
        return None
    o = np.argsort(x[m])
    cw = np.cumsum(w[m][o])
    return float(x[m][o][np.searchsorted(cw, cw[-1] / 2)])


def wmode(x: pd.Series, w: np.ndarray) -> str | None:
    s = pd.Series(w, index=x.index).groupby(x.astype(str).where(x.notna(), None)).sum()
    return None if s.empty else str(s.idxmax())


def profile(g: pd.DataFrame, numeric: list[str], categorical: list[str]) -> dict:
    w = (g.v005 / 1e6).to_numpy()
    rec = {c: wmedian(pd.to_numeric(g[c], errors="coerce").to_numpy(float), w) for c in numeric}
    rec.update({c: wmode(g[c], w) for c in categorical})
    return rec


def main():
    df, _, _, _, numeric, categorical = rdm.load()
    quint = df.wealth_quintile.astype(str)
    out = []
    groups = [("Ethiopia", None, np.ones(len(df), bool))]
    for r in sorted(df.region.astype(str).unique()):
        groups.append((r, None, (df.region.astype(str) == r).to_numpy()))
    for r in ["Ethiopia"] + sorted(df.region.astype(str).unique()):
        base = np.ones(len(df), bool) if r == "Ethiopia" else (df.region.astype(str) == r).to_numpy()
        for q in QUINTILES:
            groups.append((r, q, base & (quint == q).to_numpy()))
    for region, q, m in groups:
        if m.sum() < MIN_N:
            continue
        out.append({"region": region, "wealth": q, "n": int(m.sum()),
                    "record": profile(df[m], numeric, categorical)})
    path = ROOT / "outputs" / "deep" / "profiles.json"
    path.write_text(json.dumps({"min_n": MIN_N, "profiles": out}), encoding="utf-8")
    print(f"{len(out)} composite profiles -> {path}")


if __name__ == "__main__":
    main()
