"""A first-visit screener: who is likely to stop before four or eight contacts,
from what a clinic can ask in about two minutes.

    python scripts/run_clinic_screener.py

At a woman's first ANC visit a midwife can record a dozen facts without a survey:
age, previous births, schooling, whether the pregnancy was wanted, whether this
first visit is in the first trimester, minutes to the facility and how she came,
insurance, urban or rural, region, marital status, and five yes/no household items
(electricity, radio, television, mobile phone, bank account) that stand in for
wealth. This fits a logistic regression on those fields alone, on the ANC-entry
development women (the same partition as everything else), and reports it on the
held-out women next to the model that uses the full predictor pool, so the cost of
the short form is visible.

The model is written out as plain numbers (medians, scales, categories and
coefficients) for the browser, and a parity check runs the TypeScript scorer on
every held-out woman.

Writes outputs/screener/:
  screener.json            the model, its held-out performance, and the field spec
  heldout_performance.csv
  sample_register.csv      a SYNTHETIC register of 300 women for trying the screen:
                           each field drawn from its distribution within the
                           woman's region, so no row is a real person
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import cohorts, design, metrics  # noqa: E402

OUT = ROOT / "outputs" / "screener"
SEED = 2026
ASSETS = {"v119": "electricity", "v120": "radio", "v121": "television", "v169a": "mobile_phone", "v170": "bank_account"}

# field -> (kind, source column, question as the clinic asks it)
FIELDS = {
    "age": ("numeric", "v012", "Her age in years"),
    "previous_births": ("numeric", "v201", "Children she has given birth to before"),
    "minutes_to_facility": ("numeric", "s1101", "Minutes it takes her to reach a health facility"),
    "assets": ("numeric", None, "How many of: electricity, radio, television, mobile phone, bank account"),
    "early_first_visit": ("numeric", "early_anc", "Is this first visit in the first three months? (1 yes, 0 no)"),
    "education": ("categorical", "maternal_education", "Her schooling"),
    "pregnancy_wanted": ("categorical", "pregnancy_intention", "Was this pregnancy wanted then, later, or not at all?"),
    "transport": ("categorical", "transport_mode_group", "How she travels to the facility"),
    "insured": ("categorical", "health_insurance", "Health insurance"),
    "residence": ("categorical", "residence", "Urban or rural"),
    "region": ("categorical", "region", "Region"),
    "marital_status": ("categorical", "maternal_current_union_status", "Marital status"),
}


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def frame(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for f, (kind, src, _) in FIELDS.items():
        if f == "assets":
            out[f] = sum(df[c].eq(1).astype(float) for c in ASSETS)
        elif kind == "numeric":
            out[f] = pd.to_numeric(df[src], errors="coerce").astype(float)
        else:
            out[f] = df[src].astype(str).replace({"nan": np.nan})
    out.loc[out.minutes_to_facility >= 990, "minutes_to_facility"] = np.nan
    return out


class Spec:
    """Median-impute and standardise the numbers, one-hot the categories."""

    def fit(self, X: pd.DataFrame):
        self.num = [f for f, v in FIELDS.items() if v[0] == "numeric"]
        self.cat = [f for f, v in FIELDS.items() if v[0] == "categorical"]
        self.median = {c: float(X[c].median()) for c in self.num}
        filled = X[self.num].fillna(self.median)
        self.mean = {c: float(filled[c].mean()) for c in self.num}
        self.sd = {c: float(filled[c].std() or 1.0) for c in self.num}
        self.levels = {c: sorted(X[c].dropna().unique().tolist()) for c in self.cat}
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        cols = [((X[c].fillna(self.median[c]) - self.mean[c]) / self.sd[c]).to_numpy() for c in self.num]
        for c in self.cat:
            for lv in self.levels[c][1:]:  # first level is the reference
                cols.append((X[c] == lv).astype(float).to_numpy())
        return np.column_stack(cols)

    def names(self) -> list[str]:
        return self.num + [f"{c}={lv}" for c in self.cat for lv in self.levels[c][1:]]


def synthetic_register(e: pd.DataFrame, X: pd.DataFrame, rng: np.random.Generator, n: int = 300) -> pd.DataFrame:
    """Each synthetic woman: a region drawn by survey weight, then every field drawn
    independently from that region's own distribution. Realistic in each column,
    never a real person's combination."""
    w = (e.v005 / 1e6).to_numpy()
    regions = X.region.to_numpy()
    reg_p = pd.Series(w).groupby(regions).sum()
    reg_p = reg_p / reg_p.sum()
    rows = []
    for i in range(n):
        r = rng.choice(reg_p.index.to_numpy(), p=reg_p.to_numpy())
        m = regions == r
        row = {"woman_id": f"W{i + 1:03d}", "region": r}
        for f in FIELDS:
            if f == "region":
                continue
            vals = X.loc[m, f].to_numpy()
            ww = w[m] / w[m].sum()
            v = vals[rng.choice(len(vals), p=ww)]
            if f in ("age", "previous_births", "minutes_to_facility", "assets", "early_first_visit") and pd.notna(v):
                v = int(round(v))
            row[f] = v
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    e = cohorts.load("entry")
    X = frame(e)
    w = (e.v005 / 1e6).to_numpy()
    dev = (e.partition == "development").to_numpy()
    held = ~dev
    spec = Spec().fit(X[dev])
    Z = spec.transform(X)
    log(f"ANC-entry women: {dev.sum():,} development, {held.sum():,} held-out; {Z.shape[1]} columns")

    folds = design.folds_to_splits(design.make_psu_stratum_folds(e[dev].reset_index(drop=True)))
    out = {"fields": [{"key": f, "kind": v[0], "question": v[2],
                       **({"levels": spec.levels[f]} if v[0] == "categorical" else
                          {"median": spec.median[f], "mean": spec.mean[f], "sd": spec.sd[f]})}
                      for f, v in FIELDS.items()],
           "assets": list(ASSETS.values()), "rungs": {}, "n_development": int(dev.sum()),
           "n_heldout": int(held.sum())}
    perf_rows = []
    parity_rows = {}
    for outcome, rung in (("anc4plus", "anc4"), ("anc8plus", "anc8")):
        y = e[outcome].to_numpy().astype(int)
        # C chosen by cross-validated average precision on the development women only.
        best = None
        for C in (0.01, 0.03, 0.1, 0.3, 1.0):
            oof = np.zeros(dev.sum())
            for tr, va in folds:
                m = LogisticRegression(C=C, max_iter=3000)
                m.fit(Z[dev][tr], y[dev][tr], sample_weight=w[dev][tr])
                oof[va] = m.predict_proba(Z[dev][va])[:, 1]
            from sklearn.metrics import average_precision_score
            ap = average_precision_score(y[dev], oof, sample_weight=w[dev])
            if best is None or ap > best[1]:
                best = (C, ap)
        C = best[0]
        model = LogisticRegression(C=C, max_iter=3000).fit(Z[dev], y[dev], sample_weight=w[dev])
        p = model.predict_proba(Z[held])[:, 1]
        # the study's own metrics, survey-weighted, as for every other model
        pm = metrics.probability_metrics(y[held], p, w[held])
        ap, auc, slope = pm["AP"], pm["AUROC"], pm["Calibration_slope"]
        prev = float(np.average(y[held], weights=w[held]))
        log(f"{rung}: C {C}, held-out AP {ap:.3f} AUROC {auc:.3f} slope {slope:.2f} (prevalence {prev:.3f})")
        perf_rows.append({"rung": rung, "C": C, "AP": ap, "AUROC": auc, "calibration_slope": slope,
                          "prevalence": prev, "n": int(held.sum())})
        coefs = dict(zip(spec.names(), model.coef_[0].tolist()))
        # the full-pool reference from the horizons analysis, same held-out women
        a = json.loads((ROOT / "app" / "public" / "analysis.json").read_text(encoding="utf-8"))
        ref = [r for r in a["horizons"]["heldout"] if r["outcome"] == outcome and r["early_anc"]]
        out["rungs"][rung] = {
            "intercept": float(model.intercept_[0]), "coefficients": coefs, "C": C,
            "heldout": {"AP": ap, "AUROC": auc, "calibration_slope": slope, "prevalence": prev},
            "reference": [{"set": r["set"], "n_predictors": r["n_predictors"], "AP": r["AP"], "AUROC": r["AUROC"]} for r in ref],
        }
        parity_rows[rung] = p[:200].tolist()

    # A few held-out women as records, for the TypeScript parity check (fields only,
    # with the Python probabilities; kept out of the app and out of git).
    rec = X[held].head(200).copy()
    rec = rec.astype(object).where(rec.notna(), None)
    (OUT / "parity_cases.json").write_text(json.dumps({"records": rec.to_dict("records"), "p": parity_rows}),
                                          encoding="utf-8")
    pd.DataFrame(perf_rows).to_csv(OUT / "heldout_performance.csv", index=False)
    synthetic_register(e, X, np.random.default_rng(SEED)).to_csv(OUT / "sample_register.csv", index=False)
    out["minutes"] = round((time.time() - t0) / 60, 1)
    (OUT / "screener.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    log(f"done in {out['minutes']} min")


if __name__ == "__main__":
    main()
