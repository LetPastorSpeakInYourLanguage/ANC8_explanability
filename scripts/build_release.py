"""Assemble the self-contained package another researcher can run.

    python scripts/build_release.py             # build release/
    python scripts/build_release.py --zip       # and archive it

Everything in release/ is copied or derived from artifacts in this repository,
never hand-written into place, so re-running this after a stage completes picks
up the new results. The package is meant to be handed over whole: notebooks,
tooling, the derived dataset, fitted models, every table and figure, the
documentation, and a test suite that checks the copy still reproduces the
numbers.

The one thing it cannot contain is the raw DHS Individual Recode. That file is
distributed under a licence that does not permit redistribution, so the package
ships the *derived* analysis dataset plus the code and instructions to rebuild
it from a copy obtained directly from DHS. release/data/README.md says so in
the place someone will look.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
REL = ROOT / "release"

OUTPUTS = ROOT / "outputs"
ENHANCED = OUTPUTS / "enhanced"


def log(m):
    print(m, flush=True)


def copy_tree(src: Path, dst: Path, patterns=None, skip=()):
    """Copy the files under src that match, keeping the layout."""
    if not src.exists():
        return 0
    n = 0
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(src)
        if any(part in skip for part in rel.parts):
            continue
        if patterns and p.suffix.lower() not in patterns:
            continue
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, out)
        n += 1
    return n


def copy_file(src: Path, dst: Path) -> bool:
    if not src.exists():
        log(f"    missing, skipped: {src.relative_to(ROOT)}")
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


# ------------------------------------------------------------------ the data
def export_dataset():
    """The derived analysis dataset, in formats that outlive this pickle.

    A pickle is only readable by a compatible pandas; parquet and CSV are not
    tied to one library version, and a package meant to be opened years from
    now should not depend on unpickling.
    """
    src = ENHANCED / "ANC8_analysis_frozen_v2.pkl"
    if not src.exists():
        log("    frozen dataset missing -- run the feature stage first")
        return
    df = pd.read_pickle(src)
    out = REL / "data"
    out.mkdir(parents=True, exist_ok=True)

    shutil.copy2(src, out / src.name)
    # Birth timing (months since the index birth, its date, the pregnancy
    # outcome) -- derived from the raw file and needed for the recent-birth
    # cohort and the wartime analysis, so a package without the raw file can
    # still run both.
    timing = ENHANCED / "birth_timing.parquet"
    if timing.exists():
        shutil.copy2(timing, out / timing.name)
    try:
        df.to_parquet(out / "ANC8_analysis_frozen_v2.parquet", index=False)
        log("    parquet written")
    except Exception as exc:
        log(f"    parquet unavailable ({type(exc).__name__}); CSV still written")
    df.to_csv(out / "ANC8_analysis_frozen_v2.csv.gz", index=False,
              compression="gzip")

    # A codebook, because 100-odd DHS variable names are not self-describing.
    spec_path = ENHANCED / "feature_spec_v2.json"
    spec = json.loads(spec_path.read_text()) if spec_path.exists() else {}
    numeric = set(spec.get("numeric_predictors", []))
    categorical = set(spec.get("categorical_predictors", []))

    labels = {}
    screen = ENHANCED / "candidate_screening.csv"
    if screen.exists():
        s = pd.read_csv(screen)
        labels = dict(zip(s.variable.astype(str), s.label.astype(str)))

    rows = []
    for c in df.columns:
        col = df[c]
        role = ("predictor (numeric)" if c in numeric else
                "predictor (categorical)" if c in categorical else
                "outcome" if c.startswith("anc") else
                "survey design" if c in ("v021", "v022", "v005", "caseid") else
                "auxiliary")
        rows.append({
            "variable": c,
            "label": labels.get(c, ""),
            "role": role,
            "dtype": str(col.dtype),
            "n_missing": int(col.isna().sum()),
            "n_unique": int(col.nunique(dropna=True)),
            "example_values": "; ".join(
                str(v)[:24] for v in col.dropna().unique()[:5]),
        })
    pd.DataFrame(rows).to_csv(out / "codebook.csv", index=False)

    # The exact held-out partition, so a reader can check their split matches
    # ours without re-deriving it.
    try:
        from anc8 import design
        train_psus, test_psus = design.make_psu_holdout(df)
        pd.DataFrame({
            "caseid": df.caseid,
            "partition": ["held-out" if p in set(test_psus) else "development"
                          for p in df.v021],
        }).to_csv(out / "partition.csv", index=False)
        log(f"    partition written ({len(test_psus)} held-out PSUs)")
    except Exception as exc:
        log(f"    partition not written: {type(exc).__name__}: {exc}")

    log(f"    dataset: {len(df):,} rows x {df.shape[1]} columns")


# ------------------------------------------------------------------ manifest
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest():
    rows = []
    for p in sorted(REL.rglob("*")):
        if not p.is_file() or p.name == "MANIFEST_SHA256.csv":
            continue
        rows.append({
            "path": str(p.relative_to(REL)).replace("\\", "/"),
            "bytes": p.stat().st_size,
            "sha256": sha256(p),
        })
    man = pd.DataFrame(rows)
    man.to_csv(REL / "MANIFEST_SHA256.csv", index=False)
    return man


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", action="store_true", help="archive the package too")
    ap.add_argument("--clean", action="store_true", help="delete release/ first")
    ap.add_argument("--no-execute", action="store_true",
                    help="ship the notebooks unrun")
    args = ap.parse_args()

    if args.clean and REL.exists():
        shutil.rmtree(REL)
    REL.mkdir(parents=True, exist_ok=True)

    log("code")
    n = copy_tree(ROOT / "src", REL / "src", skip={"__pycache__"})
    log(f"    src/                      {n} files")
    n = copy_tree(ROOT / "scripts", REL / "scripts", patterns={".py", ".sh"},
                  skip={"__pycache__"})
    log(f"    scripts/                  {n} files")

    log("data")
    export_dataset()

    # The ANC-entry horizon's cohort: which women, early ANC, and partition.
    sys.path.insert(0, str(ROOT / "src"))
    from anc8 import cohorts as _cohorts
    (REL / "data").mkdir(parents=True, exist_ok=True)
    _cohorts.entry_table().to_csv(REL / "data" / "anc_entry.csv", index=False)
    log("    data/anc_entry.csv        the ANC-entry cohort (5,001 women)")

    log("fitted models")
    n = 0
    for name in ("v1_bundle.json.gz", "v1_anc_entry_bundle.json.gz",
                 "v2_bundle.json.gz", "pool_anc1plus_bundle.json.gz",
                 "pool_anc4plus_bundle.json.gz", "small_bundle.json.gz"):
        n += copy_file(ROOT / "app" / "models" / name, REL / "models" / name)
    for name in ("ebm_bundle.json", "browser_models.json"):
        n += copy_file(ROOT / "app" / "public" / name, REL / "models" / name)
    for rung in ("anc1plus", "anc4plus", "anc8plus"):
        src = ENHANCED / rung / "enhanced_models.joblib"
        if src.exists():
            n += copy_file(src, REL / "models" / f"enhanced_models_{rung}.joblib")
    for name in ("full_cohort_final_models.joblib", "anc_entry_final_models.joblib"):
        n += copy_file(OUTPUTS / "notebook3_explainability_handoff" / name,
                       REL / "models" / f"v1_{name}")
    log(f"    models/                   {n} files")

    log("result tables")
    n = copy_tree(ENHANCED, REL / "artifacts" / "enhanced",
                  patterns={".csv", ".json"})
    log(f"    artifacts/enhanced/       {n} files")
    n = copy_tree(OUTPUTS / "ladder", REL / "artifacts" / "ladder")
    log(f"    artifacts/ladder/         {n} files")
    n = copy_tree(OUTPUTS / "policy", REL / "artifacts" / "policy")
    log(f"    artifacts/policy/         {n} files")
    n = copy_tree(OUTPUTS / "feature_value", REL / "artifacts" / "feature_value",
                  patterns={".csv", ".json"})
    log(f"    artifacts/feature_value/  {n} files")
    n = copy_tree(OUTPUTS / "wartime", REL / "artifacts" / "wartime",
                  patterns={".csv", ".json"})
    n += copy_file(ROOT / "docs" / "conflict_windows.csv",
                   REL / "artifacts" / "wartime" / "conflict_windows.csv")
    log(f"    artifacts/wartime/        {n} files")
    for sub in ("horizons", "predictor_value"):
        n = copy_tree(OUTPUTS / sub, REL / "artifacts" / sub, patterns={".csv", ".json"})
        log(f"    artifacts/{sub + '/':22s}{n} files")
    # The 21-predictor models' held-out tables, bootstrap distributions and
    # locked predictions (outputs/publication_results/ in the repository).
    n = copy_tree(OUTPUTS / "publication_results",
                  REL / "artifacts" / "models_21_predictor")
    log(f"    artifacts/models_21_predictor/  {n} files")
    n = 0
    for name in ("ANC8_outcome_register_final.csv", "ANC8_predictor_register_final.csv",
                 "ANC8_artifact_manifest_final.csv",
                 "ANC_contact_count_weighted_distribution.csv",
                 "ANC_contact_count_descriptive_summary.csv"):
        n += copy_file(OUTPUTS / name, REL / "artifacts" / "registers" / name)
    log(f"    artifacts/registers/      {n} files")

    log("figures")
    n = copy_tree(OUTPUTS / "figures", REL / "figures")
    n += copy_file(OUTPUTS / "Figure_ANC_contact_count_weighted_distribution.png",
                   REL / "figures" / "Figure_ANC_contact_count_weighted_distribution.png")
    log(f"    figures/                  {n} files")

    log("app payload (what the deployed site reads)")
    n = copy_tree(ROOT / "app" / "public", REL / "app_payload")
    log(f"    app_payload/              {n} files")

    log("tests")
    n = 0
    for name in ("run_tests.py", "verify_all.py", "test_scorer.py",
                 "check_ts_parity.py", "check_environment.py"):
        n += copy_file(ROOT / "scripts" / name, REL / "tests" / name)
    log(f"    tests/                    {n} files")

    log("documentation")
    n = 0
    for name in ("FINDINGS.md", "INSIGHTS.md"):
        n += copy_file(ROOT / name, REL / "docs" / name)
    n += copy_tree(ROOT / "docs", REL / "docs", patterns={".md", ".csv"})
    # The map is written for the repository layout; in the package FINDINGS
    # and INSIGHTS sit beside it and the guide is one level up.
    m = REL / "docs" / "README.md"
    if m.exists():
        t = m.read_text(encoding="utf-8")
        for a, b in (("../INSIGHTS.md", "INSIGHTS.md"), ("../FINDINGS.md", "FINDINGS.md"),
                     ("../release/GUIDE.md", "../GUIDE.md")):
            t = t.replace(a, b)
        m.write_text(t, encoding="utf-8")
    log(f"    docs/                     {n} files (GUIDE.md written separately)")

    log("notebooks")
    try:
        import build_release_notebooks  # noqa: F401
    except Exception:
        sys.path.insert(0, str(ROOT / "scripts"))
        import build_release_notebooks  # noqa: F401
    written = build_release_notebooks.build(REL / "notebooks")
    log(f"    notebooks/                {written} notebooks")

    # Ship them already run. A notebook full of empty output cells asks the
    # reader to take the narrative on trust; one with its tables and figures in
    # place can be read straight through, and still re-executed to check.
    if not args.no_execute:
        import subprocess
        for nb in sorted((REL / "notebooks").glob("*.ipynb")):
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "execute_nb.py"), nb.name],
                cwd=str(REL / "notebooks"), capture_output=True, text=True,
                timeout=3600)
            state = "executed" if r.returncode == 0 else "FAILED"
            log(f"      {state}: {nb.name}")
            if r.returncode != 0:
                log("        " + (r.stdout or r.stderr).strip().splitlines()[-1][:120])

    log("guide and environment")
    import build_release_docs
    build_release_docs.build(REL)

    log("manifest")
    man = write_manifest()
    total = man.bytes.sum()
    log(f"    {len(man)} files, {total / 1e6:.1f} MB")

    if args.zip:
        archive = ROOT / "ANC8_reproduction_package.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for p in sorted(REL.rglob("*")):
                if p.is_file():
                    z.write(p, Path("ANC8_reproduction_package") / p.relative_to(REL))
        log(f"\narchive: {archive}  ({archive.stat().st_size / 1e6:.1f} MB)")

    log(f"\nrelease package: {REL}")


if __name__ == "__main__":
    main()
