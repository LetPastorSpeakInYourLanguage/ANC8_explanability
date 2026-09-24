"""Say which interpreter you are in and whether it can run what you want.

    python scripts/check_environment.py

This project needs two environments -- the analysis one and a pinned one that
can still unpickle the original study's fitted models -- and the failure mode
when you are in the wrong one is a missing-module error several layers down
that does not point at the cause. This prints the answer directly.
"""

from __future__ import annotations

import importlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINNED = ROOT / "outputs" / "notebook3_explainability_handoff" / "software_environment.json"

# What each job actually needs.
ANALYSIS = ["pandas", "numpy", "scipy", "sklearn", "statsmodels", "xgboost",
            "lightgbm", "interpret", "shap", "optuna", "joblib", "matplotlib"]
SERVING = ["pandas", "numpy", "sklearn", "xgboost", "statsmodels", "joblib"]
FIGURES = ["pandas", "numpy", "matplotlib"]

DIST = {"sklearn": "scikit-learn"}


def version(mod: str):
    try:
        m = importlib.import_module(mod)
    except Exception as exc:
        return None, f"{type(exc).__name__}"
    return getattr(m, "__version__", "?"), None


def main():
    print("INTERPRETER")
    print(f"  executable   {sys.executable}")
    print(f"  python       {sys.version.split()[0]}")
    print(f"  platform     {platform.platform()}")

    in_serve = ".venv-serve" in sys.executable.replace("\\", "/")
    print(f"  environment  {'.venv-serve (pinned)' if in_serve else 'analysis'}")

    print("\nPACKAGES")
    found = {}
    for mod in sorted(set(ANALYSIS + SERVING)):
        v, err = version(mod)
        found[mod] = v
        name = DIST.get(mod, mod)
        print(f"  {name:16s} {v if v else '-- not installed (' + err + ')'}")

    print("\nWHAT THIS ENVIRONMENT CAN DO")
    jobs = [
        ("run the modelling pipeline (run_pipeline.py, run_tuning.py)", ANALYSIS),
        ("rebuild the figures (make_figures.py)", FIGURES),
        ("load the original study's fitted pickles (verify_all.py, "
         "export_serving.py --v1)", SERVING),
    ]
    for label, need in jobs:
        missing = [DIST.get(m, m) for m in need if not found.get(m)]
        mark = "yes" if not missing else "no "
        print(f"  [{mark}] {label}")
        if missing:
            print(f"        missing: {', '.join(missing)}")

    # The pinned pickles are the one hard version constraint in the project.
    if PINNED.exists():
        pin = json.loads(PINNED.read_text())
        sk = found.get("sklearn")
        want = pin.get("scikit_learn")
        print("\nTHE PINNED CONSTRAINT")
        print(f"  the V1 pipelines were fitted under scikit-learn {want}")
        if sk is None:
            print("  scikit-learn is not installed here")
        elif sk == want:
            print(f"  this environment has {sk} -- it can read them")
        else:
            print(f"  this environment has {sk} -- it CANNOT read them")
            print("  use .venv-serve for anything that loads a V1 pickle")

    print("\nIf a pipeline stage fails on a missing optuna or interpret, you are")
    print("almost certainly running the pinned interpreter by accident.")


if __name__ == "__main__":
    main()
