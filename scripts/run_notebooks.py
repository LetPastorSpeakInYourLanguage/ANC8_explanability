"""Run the reproduction notebooks in order, from the command line.

    python scripts/run_notebooks.py                 # the core track, 00 to 13
    python scripts/run_notebooks.py --ebm           # then the explainable boosting track
    python scripts/run_notebooks.py --from 07       # resume at a notebook
    python scripts/run_notebooks.py --quick         # a smoke run (about an hour, numbers will differ)

Each notebook is executed from its own folder, exactly as in Jupyter, and the
executed copy, with its tables, figures and checks, is written to executed/.
The notebooks themselves are left without outputs. The run stops at the first
notebook with an error; everything already saved (tuned models included) is
kept, so `--from` picks up where it stopped.

Executed copies show aggregate results only, never a woman's record, so they
can be shared with the study's reviewers.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="3 search trials per model; for checking that everything runs")
    ap.add_argument("--ebm", action="store_true", help="also run notebooks_ebm/ after the core track")
    ap.add_argument("--from", dest="start", default="00", help="the first notebook to run, by its number (07, E1)")
    ap.add_argument("--only", nargs="*", help="run just these notebooks, by number")
    args = ap.parse_args()

    if args.quick:
        os.environ["ANC8_QUICK"] = "1"
    books = sorted((ROOT / "notebooks").glob("*.ipynb"))
    if args.ebm or args.start.upper().startswith("E"):
        books += sorted((ROOT / "notebooks_ebm").glob("*.ipynb"))
    number = lambda p: p.name.split("_")[0].upper()
    order = [number(p) for p in books]
    start = args.start.upper().zfill(2) if not args.start.upper().startswith("E") else args.start.upper()
    if start not in order:
        sys.exit(f"no notebook {args.start}; there are {', '.join(order)}")
    books = books[order.index(start):]
    if args.only:
        want = {o.upper().zfill(2) if not o.upper().startswith("E") else o.upper() for o in args.only}
        books = [p for p in books if number(p) in want]

    out = ROOT / "executed"
    out.mkdir(exist_ok=True)
    t_all = time.time()
    for path in books:
        t0 = time.time()
        print(f"{path.parent.name}/{path.name} ...", flush=True)
        nb = nbformat.read(path, as_version=4)
        client = NotebookClient(nb, timeout=None, kernel_name="python3",
                                resources={"metadata": {"path": str(path.parent)}})
        failed = None
        try:
            client.execute()
        except Exception as exc:  # the error is in the notebook's outputs too
            failed = exc
        nbformat.write(nb, out / path.name)
        checks = [line for c in nb.cells for o in c.get("outputs", []) if o.get("output_type") == "stream"
                  for line in o.get("text", "").splitlines() if "checks passed" in line or line.strip().startswith("FAILED")]
        for line in checks:
            print("   ", line.strip())
        print(f"    {(time.time() - t0) / 60:.1f} min -> executed/{path.name}", flush=True)
        if failed is not None:
            print(f"\nstopped: {path.name} raised an error; see executed/{path.name}\n{str(failed)[-2000:]}")
            sys.exit(1)
    print(f"\nall done in {(time.time() - t_all) / 60:.0f} min")


if __name__ == "__main__":
    main()
