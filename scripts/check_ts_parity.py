"""Gate: the browser scorer must agree with the Python scorer, exactly.

    python scripts/check_ts_parity.py

The what-if view scores in the browser for responsiveness. That is only
acceptable if the TypeScript port computes the same thing as the model that was
actually fitted and evaluated -- otherwise the app shows numbers no part of the
analysis produced.

So this runs every held-out woman through both implementations and fails if
they differ by more than TOLERANCE. It is the same discipline as the export
fidelity gate in export_serving.py: re-implementation risk is retired by
measurement, not by argument.
"""

from __future__ import annotations

import gzip
import json
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app" / "api" / "_lib"))

TOLERANCE = 1e-9

RUNNER = r"""
const fs = require('fs');
const { score } = require(process.argv[2]);
const bundle = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const rows = JSON.parse(fs.readFileSync(process.argv[4], 'utf8'));
const model = process.argv[5];
const out = rows.map(r => {
  const s = score(bundle, model, r);
  return { p: s.probability, sum: s.intercept + s.contributions.reduce((a,c)=>a+c.contribution,0) };
});
fs.writeFileSync(process.argv[6], JSON.stringify(out));
"""


def main():
    import scorer

    bundle_path = ROOT / "app" / "models" / "v2_bundle.json.gz"
    if not bundle_path.exists():
        print("v2 bundle not built yet; run scripts/export_serving.py --v2")
        sys.exit(1)

    with gzip.open(bundle_path, "rt", encoding="utf-8") as fh:
        bundle = json.load(fh)

    ebm_models = [n for n, m in bundle["models"].items() if m.get("kind") == "ebm"]
    if not ebm_models:
        print("no additive model in the bundle; nothing to score in the browser")
        sys.exit(1)

    from anc8 import design

    df = pd.read_pickle(ROOT / "outputs" / "enhanced" / "ANC8_analysis_frozen_v2.pkl")
    _, test_psus = design.make_psu_holdout(df)
    held = df[df.v021.isin(test_psus)].reset_index(drop=True)

    spec = json.load(open(ROOT / "outputs" / "enhanced" / "feature_spec_v2.json"))
    cols = spec["numeric_predictors"] + spec["categorical_predictors"]
    X = held[cols].copy()
    for c in spec["categorical_predictors"]:
        X[c] = X[c].astype(str)
    rows = X.astype(object).where(pd.notna(X), None).to_dict("records")

    # Compile the TypeScript port once, then drive it from node.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        js = tmp / "ebm.js"
        r = subprocess.run(
            ["npx", "tsc", str(ROOT / "app" / "src" / "lib" / "ebm.ts"),
             "--outDir", str(tmp), "--module", "commonjs", "--target", "es2020",
             "--skipLibCheck"],
            cwd=ROOT / "app", capture_output=True, text=True, shell=True,
        )
        if not js.exists():
            print("TypeScript compilation failed:")
            print(r.stdout[-2000:], r.stderr[-2000:])
            sys.exit(1)

        (tmp / "run.js").write_text(RUNNER, encoding="utf-8")
        (tmp / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
        (tmp / "rows.json").write_text(json.dumps(rows), encoding="utf-8")

        failures = 0
        for model in ebm_models:
            subprocess.run(
                ["node", str(tmp / "run.js"), str(js), str(tmp / "bundle.json"),
                 str(tmp / "rows.json"), model, str(tmp / "out.json")],
                cwd=ROOT, check=True, shell=True,
            )
            ts = json.loads((tmp / "out.json").read_text())
            ts_p = np.array([t["p"] for t in ts])
            ts_sum = np.array([t["sum"] for t in ts])

            py_p = np.array([scorer.predict(bundle, model, r)["probability"] for r in rows])

            d = np.abs(ts_p - py_p).max()
            ok = d < TOLERANCE
            failures += not ok
            print(f"  {model:30s} TS vs Python  max|diff|={d:.3e}  "
                  f"{'PASS' if ok else 'FAIL'}")

            # The displayed bars must reconstruct the displayed probability, or
            # the explanation is decorative rather than true.
            recon = np.abs(1 / (1 + np.exp(-ts_sum)) - ts_p).max()
            ok2 = recon < TOLERANCE
            failures += not ok2
            print(f"  {'':30s} contributions sum to probability: "
                  f"max|diff|={recon:.3e}  {'PASS' if ok2 else 'FAIL'}")

    print()
    if failures:
        print(f"{failures} PARITY FAILURES -- the browser scorer must not ship")
        sys.exit(1)
    print(f"browser scorer matches Python on all {len(rows)} held-out women")


if __name__ == "__main__":
    main()
