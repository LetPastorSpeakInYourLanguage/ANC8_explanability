"""Collect the model library from the training folder into outputs/library/.

    python scripts/merge_library.py                                  # from G:/My Drive/ANC8_training
    python scripts/merge_library.py --root <training folder>

Copies every finished cell (results/<set>/<rung>/<model>.npz) into
outputs/library/results/, checks each was scored on the study's development and
held-out women, and writes outputs/library/summary.csv: one row per cell with
its development and held-out AP and AUROC, predictors, trials, device and time.
Reports every cell of the grid that is still missing, and exits non-zero if any is.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import library as lib  # noqa: E402

OUT = ROOT / "outputs" / "library"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("G:/My Drive/ANC8_training"))
    args = ap.parse_args()

    dev, held = lib.partitions()
    want_dev, want_held = lib._digest(dev.caseid), lib._digest(held.caseid)

    rows, missing = [], []
    need = {m for m in lib.LINEUPS["four"]} | {lib.calibrated_name(m, c) for m in lib.LINEUPS["four"]
                                               for c in lib.CALIBRATIONS}
    everything = lib.jobs() + [j for ln in lib.LINEUPS for j in lib.lineup_jobs(ln)]
    for job in everything:
        for rung, model in job.cells:
            src = lib.cell_path(args.root, job.set, rung, model)
            if not src.exists():
                # every family is on record, but only the lineups' cells must be there
                if model in need or job.lineup:
                    missing.append(f"{job.set}/{rung}/{model}")
                continue
            dst = lib.cell_path(OUT, job.set, rung, model)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            m = lib.load_cell(OUT, job.set, rung, model)["meta"]
            assert m["dev_digest"] == want_dev and m["held_digest"] == want_held, \
                f"{job.set}/{rung}/{model} was not scored on the study's women"
            rows.append({
                "set": job.set, "rung": rung, "model": model, "kind": job.kind,
                "n_predictors": m["n_predictors"],
                "dev_AP": m["dev_metrics"].get("AP_seed_mean", m["dev_metrics"]["AP"]),
                "dev_AUROC": m["dev_metrics"]["AUROC"],
                "held_AP": m["held_metrics"]["AP"], "held_AUROC": m["held_metrics"]["AUROC"],
                "held_Brier": m["held_metrics"]["Brier"],
                "n_trials": m.get("n_trials"), "device": m["device"], "seconds": m.get("seconds"),
            })

    OUT.mkdir(parents=True, exist_ok=True)
    summary = pd.DataFrame(rows).sort_values(["set", "rung", "held_AP"], ascending=[True, True, False])
    summary.to_csv(OUT / "summary.csv", index=False)
    total = len(rows) + len(missing)
    print(f"{len(rows)} of {total} cells merged into {OUT}")
    if missing:
        print(f"{len(missing)} missing:")
        for m in missing:
            print(f"  {m}")
        sys.exit(1)


if __name__ == "__main__":
    main()
