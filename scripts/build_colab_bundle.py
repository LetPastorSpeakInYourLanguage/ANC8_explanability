"""Write the model-library training folder to Google Drive, for Colab.

    python scripts/build_colab_bundle.py                       # G:/My Drive/ANC8_training
    python scripts/build_colab_bundle.py --out D:/somewhere    # anywhere else

The folder holds a copy of the code and only the derived files the library
needs, laid out as in this repository so every path resolves unchanged:

    ANC8_training/
      train_all.ipynb         open in Colab, runtime T4 GPU, Run all
      requirements-colab.txt  the analysis environment's versions
      repo/                   src/anc8, scripts/train_library.py, outputs/...
      results/                one .npz per model, set and rung (written by both machines)
      logs/                   one log per job

The survey file itself is not copied. Re-running this refreshes the code and
data in place and leaves results/ alone. Colab runs the code from this folder,
so each new job picks up the refreshed version.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import nbformat as nbf
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("G:/My Drive/ANC8_training")
RUNGS = ("anc1plus", "anc4plus", "anc8plus")

COPY = [
    "outputs/enhanced/ANC8_analysis_frozen_v2.pkl",
    "outputs/enhanced/birth_timing.parquet",
    "outputs/enhanced/feature_spec_v2.json",
    "outputs/enhanced/redundancy/redundancy_summary.json",
    "outputs/enhanced/redundancy/duplicate_pairs.csv",
    "outputs/ANC8_analysis_frozen.pkl",
    "outputs/notebook3_explainability_handoff/predictor_architecture.json",
    "scripts/train_library.py",
    *[f"outputs/enhanced/{r}/parsimonious_spec.json" for r in RUNGS],
    *[f"outputs/feature_value/full/{r}/summary.json" for r in RUNGS],
]

REQUIREMENTS = """\
# The versions the analysis environment runs (release/requirements.txt), plus
# CatBoost. torch is Colab's own CUDA build.
numpy==2.5.0
pandas==3.0.3
scipy==1.18.0
scikit-learn==1.9.0
xgboost==3.3.0
lightgbm==4.6.0
catboost==1.2.10
interpret==0.7.8
optuna==5.0.0
joblib==1.5.3
threadpoolctl==3.6.0
pyarrow==25.0.1
"""

NOTEBOOK = [
    ("md", """# ANC8 model library: GPU jobs

Trains the library's GPU jobs (CatBoost and the two networks, on every predictor set and rung)
and writes each finished model to `results/` in this Drive folder. The CPU jobs run on the other
machine into the same folder.

Progress is written to `logs/` in this Drive folder every minute: `runner_gpu.log` (every start, finish and
failure), `runner_gpu.json` (what is running now) and one log per job.

**Runtime → Change runtime type → T4 GPU**, then **Run all**. If the session disconnects, run all
again: finished models are skipped and the run carries on."""),
    ("code", """from google.colab import drive
drive.mount('/content/drive')"""),
    ("code", """import subprocess, sys
BASE = '/content/drive/MyDrive/ANC8_training'
# The code runs straight from Drive, so every new job picks up the latest version.
WORK = f'{BASE}/repo'
r = subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', f'{BASE}/requirements-colab.txt'])
print('pinned environment installed' if r.returncode == 0 else 'PINNED INSTALL FAILED: see the pip output above')"""),
    ("code", """!nvidia-smi -L
!python -c "import torch, catboost, sklearn, pandas; print('cuda', torch.cuda.is_available(), '| catboost', catboost.__version__, '| sklearn', sklearn.__version__, '| pandas', pandas.__version__)\""""),
    ("code", """!cd "{WORK}" && python -u scripts/train_library.py --root "{BASE}" --device gpu --workers 2 --local-logs /content/logs --heartbeat 300"""),
    ("code", """!cd "{WORK}" && python scripts/train_library.py --root "{BASE}" --status"""),
]


def write_notebook(path: Path):
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(s) if k == "md" else nbf.v4.new_code_cell(s) for k, s in NOTEBOOK]
    nb.metadata = {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"},
                   "kernelspec": {"name": "python3", "display_name": "Python 3"},
                   "language_info": {"name": "python"}}
    nbf.write(nb, str(path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    out = args.out
    repo = out / "repo"
    # Updated in place, never removed: a running Colab session imports from here.
    shutil.copytree(ROOT / "src" / "anc8", repo / "src" / "anc8",
                    ignore=shutil.ignore_patterns("__pycache__"), dirs_exist_ok=True)
    for rel in COPY:
        dst = repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)

    # The two design checks need only the ids and the folds, not the old models' predictions.
    idx = pd.read_csv(ROOT / "outputs/enhanced/anc8plus/development_index.csv", usecols=["caseid", "fold"])
    (repo / "outputs/enhanced/anc8plus").mkdir(parents=True, exist_ok=True)
    idx.to_csv(repo / "outputs/enhanced/anc8plus/development_index.csv", index=False)
    lock = pd.read_csv(ROOT / "outputs/notebook3_explainability_handoff/full_cohort_locked_predictions.csv",
                       usecols=["caseid"])
    lock.to_csv(repo / "outputs/notebook3_explainability_handoff/full_cohort_locked_predictions.csv", index=False)

    (out / "requirements-colab.txt").write_text(REQUIREMENTS, encoding="utf-8")
    write_notebook(out / "train_all.ipynb")
    for d in ("results", "logs"):
        (out / d).mkdir(parents=True, exist_ok=True)

    size = sum(p.stat().st_size for p in repo.rglob("*") if p.is_file())
    print(f"wrote {out}: repo/ {size / 1e6:.1f} MB, train_all.ipynb, requirements-colab.txt")


if __name__ == "__main__":
    main()
