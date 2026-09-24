"""Edge-case tests for the deployed scorer and API.

The fidelity gate in export_serving.py proves the scorer agrees with the
original models on well-formed data. These tests cover what a web form actually
sends: blanks, unknown categories, wrong types and missing keys. A deployed
model that is exactly right on clean input and crashes on a blank field is not
deployable.

    python scripts/test_scorer.py
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "api" / "_lib"))
sys.path.insert(0, str(ROOT / "app" / "api"))

import scorer  # noqa: E402
import predict as api  # noqa: E402

FAILURES = []


def ok(name, condition, detail=""):
    if condition:
        print(f"  [PASS] {name}")
    else:
        print(f"  [FAIL] {name}  — {detail}")
        FAILURES.append(name)


def load(gen):
    p = ROOT / "app" / "models" / f"{gen}_bundle.json.gz"
    if not p.exists():
        return None
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def valid_probability(p):
    return isinstance(p, float) and np.isfinite(p) and 0.0 <= p <= 1.0


def main():
    bundle = load("v1")
    if bundle is None:
        print("v1 bundle missing; run export_serving.py --v1")
        sys.exit(1)

    models = list(bundle["models"])
    print(f"testing {len(models)} V1 models\n")

    # 1. Empty input: every field falls back to its training median/mode.
    print("empty input (everything imputed)")
    for m in models:
        r = scorer.predict(bundle, m, {})
        ok(f"{m} returns a valid probability", valid_probability(r["probability"]),
           str(r.get("probability")))

    # 2. Unknown category. OneHotEncoder(handle_unknown="ignore") produces an
    #    all-zero block rather than raising, and the scorer must do the same.
    print("\nunknown category value")
    cat = bundle["preprocessors"][bundle["models"][models[0]]["preprocessor"]]["categorical"][0]
    for m in models:
        r = scorer.predict(bundle, m, {cat: "a category that never existed"})
        ok(f"{m} tolerates an unseen category", valid_probability(r["probability"]))

    # 3. Junk in a numeric field, as a text input can easily send.
    print("\nnon-numeric text in a numeric field")
    num = bundle["preprocessors"][bundle["models"][models[0]]["preprocessor"]]["numeric"][0]
    for m in models:
        r = scorer.predict(bundle, m, {num: "not a number"})
        ok(f"{m} tolerates junk in {num}", valid_probability(r["probability"]))

    # 4. Explicit None and empty string, which is what an untouched form sends.
    print("\nNone and empty-string values")
    for m in models:
        r = scorer.predict(bundle, m, {num: None, cat: ""})
        ok(f"{m} tolerates None and empty string", valid_probability(r["probability"]))

    # 5. Extreme numeric values must not produce NaN or overflow.
    print("\nextreme numeric values")
    for m in models:
        for v in (-1e12, 1e12, 0):
            r = scorer.predict(bundle, m, {num: v})
            ok(f"{m} handles {num}={v:g}", valid_probability(r["probability"]))

    # 6. Threshold and classification must agree with each other.
    print("\nthreshold consistency")
    for m in models:
        r = scorer.predict(bundle, m, {})
        thr, p, cls = r["threshold"], r["probability"], r["classification"]
        expected = "likely" if p >= thr else "unlikely"
        ok(f"{m} classification matches its threshold", cls.startswith(expected),
           f"p={p:.4f} thr={thr:.4f} cls={cls!r}")

    # 7. API level: malformed and partial payloads.
    print("\nAPI payloads")
    r = api.build_response({})
    ok("empty payload returns a result", "result" in r)

    r = api.build_response({"answers": {"nonexistent_field": 1}, "generations": ["v1"]})
    ok("unknown field is ignored", r["result"]["v1"]["available"])
    ok("imputed list is reported",
       len(r["result"]["v1"]["imputed"]) == r["result"]["v1"]["n_expected"],
       "nothing was supplied, so everything should be listed as imputed")

    r = api.build_response({"answers": {}, "generations": ["v2"]})
    ok("missing v2 bundle is reported, not crashed",
       r["result"]["v2"]["available"] is False or r["result"]["v2"]["available"] is True)

    # The ANC-entry Extended models carry early_anc in a separate trailing
    # transformer block. A scorer that ignores that block builds a feature
    # vector one column short and fails -- which is exactly what happened once,
    # so it is pinned down here.
    entry = load("v1_anc_entry")
    if entry is not None:
        print("\nANC-entry horizon (early_anc in a trailing block)")
        for m in entry["models"]:
            r = scorer.predict(entry, m, {"early_anc": "1"})
            ok(f"{m} scores", valid_probability(r["probability"]),
               str(r.get("probability")))

        resp = api.build_response(
            {"answers": {"early_anc": "1"}, "generations": ["v1_anc_entry"]}
        )
        failed = [m for m in resp["result"]["v1_anc_entry"]["models"] if "error" in m]
        ok("no ANC-entry model errors through the API", not failed,
           "; ".join(f"{m['model']}: {m['error']}" for m in failed))

        # Extended must differ from Baseline, or early_anc is being ignored.
        by = {m["model"]: m.get("probability")
              for m in resp["result"]["v1_anc_entry"]["models"]}
        for algo in ("Logistic regression", "Random Forest", "XGBoost"):
            b, e = by.get(f"{algo} (Baseline)"), by.get(f"{algo} (Extended)")
            ok(f"{algo}: Extended differs from Baseline",
               b is not None and e is not None and abs(b - e) > 1e-9,
               f"baseline={b} extended={e}")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED")
        sys.exit(1)
    print("all scorer edge-case tests passed")


if __name__ == "__main__":
    main()
