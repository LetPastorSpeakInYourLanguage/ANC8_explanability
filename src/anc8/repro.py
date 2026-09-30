"""Plumbing for the reproduction notebooks (reproduction/notebooks*/).

Every notebook starts with `repro.setup()`, runs its stage, and ends with checks
against the study's own results in reproduction/reference/: the content
fingerprints of the analysis frames, the digests of the split, the predictor sets,
the tuned models' development and held-out average precision.

    from anc8 import repro
    P = repro.setup(quick=False)
    ...
    repro.check("the cohort has 6,893 women", len(df) == 6893)
    repro.report()
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "reference"
_RESULTS: list[tuple[str, bool, str]] = []
STATE = {"quick": False}

# A smoke run: few search trials, so the whole chain runs in about an hour. Its
# numbers will not match the study's, and the comparisons say so instead of failing.
QUICK_TRIALS = 3


class Paths:
    def __init__(self, quick: bool):
        self.quick = quick
        self.project = ROOT
        self.reference = REFERENCE
        self.outputs = ROOT / "outputs"
        # the model library's cells: <results>/results/<set>/<rung>/<model>.npz
        self.results = ROOT / "quick" if quick else ROOT


def setup(quick: bool = False) -> Paths:
    """Work from the project folder with the package importable; in a quick run, cut
    the search budgets."""
    # scripts/run_notebooks.py --quick runs every notebook as a smoke run
    quick = quick or os.environ.get("ANC8_QUICK") == "1"
    os.chdir(ROOT)
    for p in (ROOT / "scripts", ROOT / "src"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    STATE["quick"] = quick
    if quick:
        from . import tuning
        for k in tuning.TRIALS:
            tuning.TRIALS[k] = min(tuning.TRIALS[k], QUICK_TRIALS)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    print(f"project folder: {ROOT}")
    print(f"mode: {'QUICK smoke run (numbers will differ from the study)' if quick else 'full reproduction'}")
    return Paths(quick)


def reference(name: str):
    """A file from reproduction/reference/: the study's own results, for comparison."""
    p = REFERENCE / name
    if p.suffix == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    return pd.read_csv(p)


def fingerprint(df: pd.DataFrame) -> str:
    """A content hash of a frame (columns, types and every value). Unlike the file's
    own hash, it does not depend on the pandas version that wrote the pickle."""
    df = df.copy()
    kinds = []
    for c in df.columns:
        s = df[c]
        # Labels are compared as text: pandas versions store them as "object", "str"
        # or "category", and the models read them as text whatever the storage.
        if s.dtype == object or isinstance(s.dtype, (pd.StringDtype, pd.CategoricalDtype)):
            df[c] = [None if pd.isna(v) else str(v) for v in s.astype(object)]
            kinds.append("text")
        else:
            kinds.append(str(s.dtype))
    h = hashlib.sha256()
    h.update("|".join(map(str, df.columns)).encode())
    h.update("|".join(kinds).encode())
    h.update(pd.util.hash_pandas_object(df, index=True).to_numpy().tobytes())
    return h.hexdigest()[:16]


def check(label: str, ok: bool, detail: str = "") -> None:
    ok = bool(ok)
    _RESULTS.append((label, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  -- {detail}" if detail else ""))


def report():
    """The notebook's checks, at the end."""
    bad = [r for r in _RESULTS if not r[1]]
    print(f"\n{len(_RESULTS) - len(bad)} of {len(_RESULTS)} checks passed")
    if bad and STATE["quick"]:
        print("(a quick run is not expected to match the study's numbers)")
    for label, _, detail in bad:
        print(f"  FAILED: {label}  {detail}")
    _RESULTS.clear()


def run_script(script: str, *args: str) -> None:
    """Run one of the stage scripts in scripts/, showing its output as it goes."""
    cmd = [sys.executable, "-u", str(ROOT / "scripts" / script), *map(str, args)]
    print("$", " ".join(cmd[2:]))
    t0 = time.time()
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    for line in proc.stdout:
        print(line, end="")
    if proc.wait() != 0:
        raise RuntimeError(f"{script} failed (exit {proc.returncode})")
    print(f"({(time.time() - t0) / 60:.1f} min)")


def compare_cells(results: Path, models, sets=None, tol=None) -> pd.DataFrame:
    """Each model's development and held-out AP against the study's, per set and rung."""
    from . import library as lib

    ref = reference("expected_results.csv").set_index(["set", "rung", "model"])
    rows = []
    for s in sets or lib.SETS:
        for r in lib.RUNGS:
            for m in models:
                p = lib.cell_path(results, s, r, m)
                if not p.exists():
                    rows.append({"set": s, "rung": r, "model": m, "status": "missing"})
                    continue
                meta = lib.load_cell(results, s, r, m)["meta"]
                dev = meta["dev_metrics"].get("AP_seed_mean", meta["dev_metrics"]["AP"])
                held = meta["held_metrics"]["AP"]
                e = ref.loc[(s, r, m)] if (s, r, m) in ref.index else None
                rows.append({"set": s, "rung": r, "model": m, "dev_AP": dev, "held_AP": held,
                             "study_dev_AP": None if e is None else e.dev_AP,
                             "study_held_AP": None if e is None else e.held_AP,
                             "status": "ok"})
    out = pd.DataFrame(rows)
    if "study_held_AP" in out:
        out["gap"] = np.maximum((out.dev_AP - out.study_dev_AP).abs(), (out.held_AP - out.study_held_AP).abs())
        worst = float(out.gap.max()) if out.gap.notna().any() else float("nan")
        tol = tol if tol is not None else 1e-6
        check(f"{len(out[out.status == 'ok'])} models match the study's AP (tolerance {tol:g})",
              out.status.eq("ok").all() and worst <= tol, f"largest difference {worst:.2e}")
    return out


def compare_table(got: pd.DataFrame, name: str, keys: list, value: str, label: str, tol: float = 1e-6) -> None:
    """A table of results against the study's copy in reference/, row for row on `keys`.
    Rows the study has and this run does not (a model not run here) are left out."""
    ref = reference(name)
    m = got.merge(ref[keys + [value]], on=keys, how="left", suffixes=("", "_study"))
    missing = int(m[f"{value}_study"].isna().sum())
    gap = float((m[value] - m[f"{value}_study"]).abs().max()) if len(m) else float("nan")
    check(f"{label}: the study's, to {tol:g}", missing == 0 and gap <= tol,
                 f"{len(m)} rows, largest difference {gap:.1e}" + (f", {missing} not in the study's" if missing else ""))
