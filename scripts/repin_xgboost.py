"""Refit the library's XGBoost cells on one thread (a one-off repair).

    python scripts/repin_xgboost.py --root "G:/My Drive/ANC8_training"

XGBoost's row and column sampling depends on the thread count. The library tuned
XGBoost with one thread per fold, but fitted the final model with several, so the
held-out predictions depended on the machine. src/anc8/models.py now pins XGBoost to
one thread. This script, per set and rung:

  1. re-runs the out-of-fold predictions with the stored settings and checks they
     equal the stored ones (they were made on one thread, so they must);
  2. refits the final model on one thread and rewrites the cell's held-out
     predictions and metrics;
  3. removes the cell's calibrated versions and the lineup ensembles built on it,
     so the scheduler re-makes them from the corrected cell.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import library as lib, metrics, tuning  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    args = ap.parse_args()

    for set_ in lib.SETS:
        for rung in lib.RUNGS:
            d = lib.data(set_, rung)
            path = lib.cell_path(args.root, set_, rung, "XGBoost")
            cell = lib.load_cell(args.root, set_, rung, "XGBoost")
            meta, p = cell["meta"], cell["meta"]["params"]
            oof = tuning.oof_predict("XGBoost", p, d.X_dev, d.y_dev, d.w_dev, d.splits,
                                     d.numeric, d.categorical, n_jobs=5)
            gap_oof = float(np.max(np.abs(oof - cell["dev_oof"])))
            assert gap_oof < 1e-9, f"{set_}/{rung}: out-of-fold predictions moved by {gap_oof:.2e}"
            pipe = tuning.fit_final("XGBoost", p, d.X_dev, d.y_dev, d.w_dev, d.numeric, d.categorical)
            held = pipe.predict_proba(d.X_held)[:, 1]
            before = meta["held_metrics"]["AP"]
            meta["held_metrics"] = metrics.probability_metrics(d.y_held, held, d.w_held)
            meta["final_fit"] = "one thread (XGBoost's sampling depends on the thread count)"
            tmp = path.with_name(path.name + ".tmp")
            with open(tmp, "wb") as fh:
                np.savez_compressed(fh, dev_oof=cell["dev_oof"], held=held,
                                    meta=np.array(json.dumps(meta, default=lib._json_default)))
            tmp.replace(path)
            for m in lib.CALIBRATIONS:
                lib.cell_path(args.root, set_, rung, lib.calibrated_name("XGBoost", m)).unlink(missing_ok=True)
            for ln in lib.LINEUPS:
                shutil.rmtree(path.parent / ln, ignore_errors=True)
            print(f"{set_}/{rung}: held-out AP {before:.4f} -> {meta['held_metrics']['AP']:.4f}", flush=True)


if __name__ == "__main__":
    main()
