"""Run every remaining stage once tuning has finished.

    python scripts/finish_pipeline.py

Stages, in order:
    1. held-out evaluation        (run_evaluation.py)
    2. repeated-split stability   (run_stability.py)
    3. export V2 for serving      (export_serving.py --v2)
    4. rebuild the web form schema
    5. build and execute Notebook 4
    6. re-execute Notebook 3 so its SHA256 manifest covers the final artifacts
    7. end-to-end verification

A stage that fails stops the run and says which one, rather than leaving later
stages to fail confusingly on missing inputs.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SERVE_PY = ROOT / ".venv-serve" / "Scripts" / "python.exe"

STAGES = [
    ("held-out evaluation", [PY, "-u", "scripts/run_evaluation.py"]),
    ("repeated-split stability", [PY, "-u", "scripts/run_stability.py"]),
    ("export V2 for serving", [PY, "scripts/export_serving.py", "--v2"]),
    ("rebuild form schema", [PY, "scripts/build_form_schema.py"]),
    ("publish performance figures", [PY, "scripts/build_performance_json.py"]),
    ("original-21 drop-one analysis", [PY, "-u", "scripts/run_dropone.py"]),
    ("preprocessing ablation", [PY, "-u", "scripts/run_preprocessing_ablation.py"]),
    ("screening sensitivity", [PY, "-u", "scripts/run_screening_sensitivity.py"]),
    ("build Notebook 3", [PY, "scripts/build_notebook3.py"]),
    ("build Notebook 4", [PY, "scripts/build_notebook4.py"]),
    ("execute Notebook 4", [PY, "scripts/execute_nb.py", "4_ANC8_expanded_modelling.ipynb"]),
    ("re-execute Notebook 3", [PY, "scripts/execute_nb.py",
                               "3_ANC8_deep_EDA_and_feature_reascertainment.ipynb"]),
    ("verification", [str(SERVE_PY), "scripts/verify_all.py"]),
    ("scorer edge cases", [PY, "scripts/test_scorer.py"]),
]


def main():
    for name, cmd in STAGES:
        print(f"\n{'=' * 78}\n[{time.strftime('%H:%M:%S')}] {name}\n{'=' * 78}", flush=True)
        r = subprocess.run(cmd, cwd=ROOT)
        if r.returncode != 0:
            print(f"\nSTAGE FAILED: {name} (exit {r.returncode})", flush=True)
            sys.exit(r.returncode)
    print(f"\n[{time.strftime('%H:%M:%S')}] pipeline complete", flush=True)


if __name__ == "__main__":
    main()
