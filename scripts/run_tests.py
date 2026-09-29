"""The check suite: everything verifiable without refitting a model.

    python scripts/run_tests.py             # from the repository
    python tests/run_tests.py               # from the release package

Each test prints PASS or FAIL with the value it found, and the process exits
non-zero if any failed. Tests whose inputs are absent report SKIP rather than
passing quietly -- a suite that goes green because it checked nothing is worse
than one that fails.

The tests are ordered so that a failure high up explains the failures below it.
If the held-out partition does not match the study's one partition, every
comparison in the project is meaningless and nothing after that check is worth
reading.
"""

from __future__ import annotations

import json
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve()
# Works from scripts/ in the repository and from tests/ in the release package.
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

# The release package rearranges where things live; look in both places.
CANDIDATE_DATA = [ROOT / "data", ROOT / "outputs" / "enhanced"]
CANDIDATE_ARTIFACTS = [ROOT / "artifacts" / "enhanced", ROOT / "outputs" / "enhanced"]
CANDIDATE_FIGURES = [ROOT / "figures", ROOT / "outputs" / "figures"]
CANDIDATE_LADDER = [ROOT / "artifacts" / "ladder", ROOT / "outputs" / "ladder"]
CANDIDATE_POLICY = [ROOT / "artifacts" / "policy", ROOT / "outputs" / "policy"]

RESULTS = []

EXPECTED_PREVALENCE = {"anc1plus": 0.7760, "anc4plus": 0.5243, "anc8plus": 0.1916}
EXPECTED_N = 6893
EXPECTED_HELDOUT = 1375
EXPECTED_DEV = 5518


def first(paths):
    for p in paths:
        if Path(p).exists():
            return Path(p)
    return None


def find(name, candidates):
    for base in candidates:
        p = Path(base) / name
        if p.exists():
            return p
    return None


def record(kind, name, detail=""):
    RESULTS.append((kind, name))
    print(f"  [{kind}] {name}" + (f"  -- {detail}" if detail else ""))


def check(name, ok, detail=""):
    record("PASS" if ok else "FAIL", name, detail)
    return bool(ok)


def skip(name, why):
    record("SKIP", name, why)


def section(t):
    print(f"\n{t}\n{'-' * len(t)}")


def load_dataset():
    for base in CANDIDATE_DATA:
        for name in ("ANC8_analysis_frozen_v2.parquet",
                     "ANC8_analysis_frozen_v2.pkl",
                     "ANC8_analysis_frozen_v2.csv.gz"):
            p = Path(base) / name
            if not p.exists():
                continue
            try:
                if p.suffix == ".parquet":
                    return pd.read_parquet(p), p
                if p.suffix == ".pkl":
                    return pd.read_pickle(p), p
                return pd.read_csv(p), p
            except Exception:
                continue
    return None, None


def wmean(x, w):
    return float(np.sum(np.asarray(x, float) * w) / np.sum(w))


# ===========================================================================
def test_dataset():
    section("1. THE ANALYSIS DATASET")
    df, path = load_dataset()
    if df is None:
        skip("dataset loads", "no analysis dataset found in data/ or outputs/enhanced/")
        return None
    check("dataset loads", True, f"{path.name}, {len(df):,} rows x {df.shape[1]} columns")
    check(f"row count is {EXPECTED_N}", len(df) == EXPECTED_N, f"{len(df)}")

    w = (df.v005 / 1e6).to_numpy()
    for rung, expect in EXPECTED_PREVALENCE.items():
        if rung not in df.columns:
            skip(f"{rung} weighted prevalence", "column absent")
            continue
        got = wmean(df[rung], w)
        check(f"{rung} weighted prevalence is {expect:.4f}",
              abs(got - expect) < 5e-4, f"{got:.4f}")

    if all(r in df.columns for r in EXPECTED_PREVALENCE):
        nested = ((df.anc8plus <= df.anc4plus) & (df.anc4plus <= df.anc1plus)).all()
        check("the outcome ladder is nested for every woman", bool(nested))

    if "anc_contacts" in df.columns:
        n = df.anc_contacts.fillna(0)
        agree = ((n >= 8).astype(int) == df.anc8plus.astype(int)).mean()
        check("anc8plus is exactly the contact count thresholded at 8",
              agree > 0.9999, f"{agree:.6f} agreement")
    return df


def test_split(df):
    section("2. THE SPLIT (everything downstream depends on this)")
    if df is None:
        skip("split reproduces", "no dataset")
        return
    try:
        from anc8 import design
    except Exception as exc:
        skip("split reproduces", f"cannot import anc8.design: {exc}")
        return
    train_psus, test_psus = design.make_psu_holdout(df)
    dev = df[df.v021.isin(train_psus)]
    held = df[df.v021.isin(test_psus)]
    check(f"development set has {EXPECTED_DEV} women", len(dev) == EXPECTED_DEV, f"{len(dev)}")
    check(f"held-out set has {EXPECTED_HELDOUT} women", len(held) == EXPECTED_HELDOUT,
          f"{len(held)}")
    check("no PSU appears on both sides",
          not (set(dev.v021) & set(held.v021)))

    part = find("partition.csv", CANDIDATE_DATA)
    if part is None:
        skip("split matches the shipped partition", "partition.csv absent")
    else:
        p = pd.read_csv(part)
        want = set(p[p.partition == "held-out"].caseid.astype(str))
        got = set(held.caseid.astype(str))
        check("split matches the shipped partition, caseid for caseid",
              want == got, f"{len(want & got)} of {len(want)} shared")

    # The folds must respect the clusters too, or cross-validated scores are
    # optimistic for the same reason an ungrouped split would be.
    folds = design.make_psu_stratum_folds(dev.reset_index(drop=True))
    leak = []
    for k in sorted(set(folds)):
        inside = set(dev.reset_index(drop=True).v021[folds == k])
        outside = set(dev.reset_index(drop=True).v021[folds != k])
        if inside & outside:
            leak.append(k)
    check("no PSU spans two cross-validation folds", not leak, str(leak))


# The 2024-25 EDHS key indicators report, Table 9: percentage of women with a
# live birth in the 2 years before the survey who had 4+ ANC visits.
from anc8.reference import EDHS_ANC4_BY_REGION  # noqa: E402


def test_official_indicator():
    section("2b. THE RECENT-BIRTH COHORT REPRODUCES THE OFFICIAL INDICATOR")
    try:
        from anc8 import cohorts
        rec = cohorts.load("recent")
    except Exception as exc:
        skip("recent cohort", f"cannot build it here: {type(exc).__name__}")
        return
    w = rec.v005 / 1e6
    national = float(np.average(rec.anc4plus, weights=w)) * 100
    check("national ANC4+ matches the EDHS report (53.0%) within 1 point",
          abs(national - 53.0) <= 1.0, f"{national:.1f}%")
    diffs = {str(r): float(np.average(g.anc4plus, weights=g.v005)) * 100
             - EDHS_ANC4_BY_REGION[str(r)]
             for r, g in rec.groupby("region", observed=True)}
    worst = max(diffs, key=lambda k: abs(diffs[k]))
    # 1.5 points rather than 1: Addis Ababa sits at +1.4 (96.2 vs 94.8), where
    # a handful of "don't know" counts -- kept in the report's denominator,
    # excluded from ours -- move a small sample's rate by that much.
    check("every region's ANC4+ matches the report within 1.5 points",
          abs(diffs[worst]) <= 1.5, f"largest gap {worst} {diffs[worst]:+.1f}")
    check("recent cohort includes stillbirths, as the DHS-8 definition does",
          int((rec.pregnancy_outcome == "stillbirth").sum()) > 0,
          f"{int((rec.pregnancy_outcome == 'stillbirth').sum())} stillbirths")


def test_artifacts():
    section("3. RESULT ARTIFACTS")
    base = first(CANDIDATE_ARTIFACTS)
    if base is None:
        skip("artifacts present", "no artifacts directory")
        return
    for rung in ("anc1plus", "anc4plus", "anc8plus"):
        d = base / rung
        if not d.exists():
            skip(f"{rung} artifacts", "rung not run")
            continue
        wanted = ["best_hyperparameters.json", "development_oof_performance.csv",
                  "heldout_performance.csv", "heldout_locked_predictions_v2.csv"]
        missing = [w for w in wanted if not (d / w).exists()]
        if len(missing) == len(wanted):
            # The directory exists but nothing is in it: the stage has not run
            # or is still running. Not a failure of what is there.
            skip(f"{rung} artifacts", "rung directory is empty -- stage not run")
            continue
        check(f"{rung} artifacts complete", not missing, str(missing) if missing else "")

    p = base / "anc8plus" / "heldout_performance.csv"
    if p.exists():
        d = pd.read_csv(p)
        v2 = d[d.generation.astype(str).str.startswith("V2")]
        check("held-out AP beats the prevalence floor for every full-pool model",
              bool((v2.AP > EXPECTED_PREVALENCE["anc8plus"]).all()),
              f"lowest {v2.AP.min():.4f} vs floor {EXPECTED_PREVALENCE['anc8plus']:.4f}")
        check("held-out AUROC is above chance for every full-pool model",
              bool((v2.AUROC > 0.5).all()), f"lowest {v2.AUROC.min():.4f}")


def test_claims():
    section("4. THE HEADLINE NUMBERS MATCH THEIR ARTIFACTS")
    base = first(CANDIDATE_ARTIFACTS)
    if base is None:
        skip("headline numbers", "no artifacts")
        return

    s = base / "anc8plus" / "stability_summary.json"
    if s.exists():
        js = json.loads(s.read_text())
        check("the full pool beats the 21 on every repeated split",
              js["AP"]["seeds_enhanced_better"] == js["n_seeds"],
              f"{js['AP']['seeds_enhanced_better']}/{js['n_seeds']}, "
              f"mean {js['AP']['delta_mean']:+.4f} AP")
    else:
        skip("repeated-split claim", "stability_summary.json absent")

    c = base / "anc8plus" / "paired_bootstrap_ci.json"
    if c.exists():
        js = json.loads(c.read_text())
        lo, hi = js["d_AP"]["lo"], js["d_AP"]["hi"]
        # Not a failure -- the honest finding IS that this interval spans zero,
        # and the write-ups say so. The test guards against a document that
        # quietly claims significance the artifact does not support.
        check("the held-out AP interval is reported as spanning zero",
              (lo < 0 < hi) == (not js.get("d_AP_excludes_zero", False)),
              f"[{lo:+.4f}, {hi:+.4f}]")
    else:
        skip("held-out interval", "paired_bootstrap_ci.json absent")

    r = base / "redundancy" / "redundancy_summary.json"
    if r.exists():
        js = json.loads(r.read_text())
        check("duplicated predictors were found and counted",
              js["n_predictors"] > js["n_after_deduplication"],
              f"{js['n_predictors']} columns -> {js['n_after_deduplication']} "
              f"distinct variables")
    else:
        skip("redundancy analysis", "not run")


def test_figures():
    section("5. FIGURES")
    base = first(CANDIDATE_FIGURES)
    if base is None:
        skip("figures present", "no figures directory")
        return
    man = base / "figures_manifest.csv"
    if not man.exists():
        skip("figure manifest", "figures_manifest.csv absent")
        return
    d = pd.read_csv(man)
    missing = [r.figure for r in d.itertuples() if not (base / f"{r.figure}.png").exists()]
    check("every figure in the manifest exists", not missing, str(missing))
    check("every figure has a caption naming its sources",
          bool(d.caption.notna().all() and d.inputs.notna().all()),
          f"{len(d)} figures")


def test_scorer():
    section("6. THE DEPLOYED SCORER")
    # Delegates to the existing parity scripts, which compare the numpy scorer
    # and the TypeScript port against the fitted pipelines' own probabilities.
    # They read the app's own source tree, which the release package does not
    # carry -- there, the bundles are checked structurally instead (section 7).
    if not (ROOT / "app").exists():
        skip("scorer parity scripts", "app/ not in this layout; see section 7")
        return
    for name in ("test_scorer.py", "check_ts_parity.py"):
        p = find(name, [ROOT / "scripts", ROOT / "tests"])
        if p is None:
            skip(name, "not present")
            continue
        try:
            r = subprocess.run([sys.executable, str(p)], capture_output=True,
                               text=True, timeout=900, cwd=str(ROOT))
        except Exception as exc:
            skip(name, f"{type(exc).__name__}: {exc}")
            continue
        tail = [ln for ln in (r.stdout or "").strip().splitlines() if ln.strip()]
        check(f"{name} passes", r.returncode == 0,
              tail[-1][:100] if tail else f"exit {r.returncode}")


def test_app_payload():
    section("7. WHAT THE WEB APP READS")
    base = first([ROOT / "app_payload", ROOT / "app" / "public"])
    if base is None:
        skip("app payload", "not present")
        return
    for name in ("insights.json", "ebm_bundle.json", "form_schema.json", "browser_models.json",
                 "model_performance.json"):
        p = base / name
        if not p.exists():
            skip(name, "absent")
            continue
        try:
            js = json.loads(p.read_text(encoding="utf-8"))
            check(f"{name} is valid JSON", True, f"{len(js)} top-level keys")
        except Exception as exc:
            check(f"{name} is valid JSON", False, str(exc))

    # The app is typed against these shapes, but TypeScript checks the
    # declaration and not the file. A field the analysis stopped writing would
    # compile cleanly and blow up in the browser, so the contract is asserted
    # here against the real artifact.
    CONTRACT = {
        "analysis.json": {
            "outcomes": dict, "rungs": list, "leaderboard": dict,
            "calibration": dict, "stability": dict, "bootstrap": dict,
            "subgroups": dict, "decision_curve": dict, "hyperparameters": dict,
        },
        "policy.json": {
            "cascade": dict, "regional_cascade": list,
            "continuation_equity": dict,
        },
    }
    ROW_FIELDS = {
        ("analysis.json", "leaderboard"): {"model", "dev_AP", "held_AP", "generation"},
        ("policy.json", "regional_cascade"): {
            "region", "reach8", "never", "start_lt4", "four_lt8", "biggest_loss"},
    }
    for fname, fields in CONTRACT.items():
        p = base / fname
        if not p.exists():
            skip(f"{fname} contract", "absent")
            continue
        js = json.loads(p.read_text(encoding="utf-8"))
        missing = [k for k, t in fields.items()
                   if k not in js or not isinstance(js[k], t)]
        check(f"{fname} has every field the app reads", not missing,
              str(missing) if missing else f"{len(fields)} keys")

        for (f, key), want in ROW_FIELDS.items():
            if f != fname or key not in js:
                continue
            sample = js[key]
            if isinstance(sample, dict):
                sample = next(iter(sample.values()), [])
            if not sample:
                skip(f"{fname}:{key} row shape", "no rows")
                continue
            absent = want - set(sample[0])
            check(f"{fname}:{key} rows carry the expected fields",
                  not absent, str(sorted(absent)) if absent else "")

        # Empty collections are the other silent failure: a panel that renders
        # a frame with nothing in it looks like a bug to the reader.
        empties = [k for k, v in js.items()
                   if isinstance(v, (list, dict)) and not v and k not in
                   ("ablation", "ladder", "tuning_gain")]
        check(f"{fname} has no empty sections that would render blank",
              not empties, str(empties) if empties else "")

    ins = base / "insights.json"
    if ins.exists():
        js = json.loads(ins.read_text(encoding="utf-8"))
        shapes = js.get("shape_functions", {})
        bad = [k for k, s in shapes.items()
               if s.get("kind") == "continuous"
               and len(s.get("scores", [])) != len(s.get("cuts", [])) + 1]
        check("every continuous shape function has one score per bin",
              not bad, f"{len(bad)} malformed" if bad else f"{len(shapes)} checked")
        nominal = {k: s for k, s in shapes.items() if s.get("kind") == "nominal"}
        bad = [k for k, s in nominal.items()
               if len(s.get("values", [])) != len(s.get("scores", []))]
        check("every categorical shape function has one score per level",
              not bad, f"{len(bad)} malformed" if bad else f"{len(nominal)} checked")


CANDIDATE_FV = [ROOT / "artifacts" / "feature_value", ROOT / "outputs" / "feature_value"]
CANDIDATE_HOR = [ROOT / "artifacts" / "horizons", ROOT / "outputs" / "horizons"]
CANDIDATE_PV = [ROOT / "artifacts" / "predictor_value", ROOT / "outputs" / "predictor_value"]
RUNGS = ("anc1plus", "anc4plus", "anc8plus")


def test_study():
    section("8. THE THREE ANALYSES")
    # The ANC-entry horizon must sit on the same split as everything else.
    try:
        from anc8 import cohorts
        e = cohorts.load("entry")
        check("ANC-entry cohort: 5,001 women on the full split (4,017 / 984)",
              len(e) == 5001 and (e.partition == "development").sum() == 4017,
              f"{len(e)} women, {(e.partition == 'held-out').sum()} held out")
    except Exception as exc:
        skip("ANC-entry cohort", f"{type(exc).__name__}: {exc}")

    fv = first(CANDIDATE_FV)
    if fv is None:
        skip("predictor-value outputs", "absent")
    else:
        for r in RUNGS:
            d = fv / "full" / r
            need = ["drop_one_within_21.csv", "forward_within_21.csv", "drop_group_21.csv",
                    "forward_steps.csv", "heldout.csv", "why21_heldout.csv"]
            missing = [n for n in need if not (d / n).exists()]
            check(f"{r}: stage 0 and the held-out ablation are present", not missing,
                  str(missing) if missing else "")
            if not missing:
                drop = pd.read_csv(d / "drop_one_within_21.csv")
                check(f"{r}: the drop study covers all 21", len(drop) == 21, f"{len(drop)}")
        for r in ("anc4plus", "anc8plus"):
            d = fv / "entry" / r
            ok = (d / "summary.json").exists() and (d / "heldout.csv").exists()
            if ok:
                js = json.loads((d / "summary.json").read_text())
                check(f"ANC-entry {r}: early ANC is a candidate", js.get("n_candidates") == 89,
                      f"{js.get('n_candidates')} candidates")
            else:
                skip(f"ANC-entry {r}", "run not complete")

    hz = first(CANDIDATE_HOR)
    if hz is None:
        skip("horizon outputs", "absent")
    else:
        need = ["early_anc_development.csv", "heldout_entry.csv", "cross_horizon.csv",
                "tiers_by_horizon.csv", "heldout_bootstrap.json"]
        missing = [n for n in need if not (hz / n).exists()]
        check("horizon comparison outputs are present", not missing, str(missing))

    pv = first(CANDIDATE_PV)
    if pv is None or not (pv / "full" / "matrix.csv").exists():
        skip("predictor x rung matrix", "absent")
    else:
        m = pd.read_csv(pv / "full" / "matrix.csv")
        check("predictor x rung matrix covers 88 predictors at 3 rungs",
              m.predictor.nunique() == 88 and m.rung.nunique() == 3,
              f"{m.predictor.nunique()} x {m.rung.nunique()}")


def _norm(text):
    return " ".join(text.split())


def test_record():
    section("9. THE ANALYSIS RECORD AND THE GLOSSARY")
    doc = find("ANALYSIS_RECORD.md", [ROOT / "docs"])
    if doc is None:
        skip("analysis record", "docs/ANALYSIS_RECORD.md absent")
        return
    text = _norm(doc.read_text(encoding="utf-8"))

    # The record quotes numbers by hand. Each is recomputed here from the file
    # it came from, so the record cannot drift from the results.
    quoted = []
    art = first(CANDIDATE_ARTIFACTS)
    if art is not None and (art / "anc8plus" / "stability_summary.json").exists():
        st = json.loads((art / "anc8plus" / "stability_summary.json").read_text())
        s = st["AP"]
        quoted += [("repeated-split gain", f"+{s['delta_mean']:.3f} AP"),
                   ("splits won", f"{s['seeds_enhanced_better']} of {st['n_seeds']}")]
        b = json.loads((art / "anc8plus" / "paired_bootstrap_ci.json").read_text())["d_AP"]
        quoted.append(("held-out paired bootstrap",
                       f"+{b['point']:.3f} AP [{b['lo']:.3f}, +{b['hi']:.3f}]".replace("-", "−")))
    lp = find("ladder_performance.csv", CANDIDATE_LADDER)
    if lp is not None:
        au = [f"{r.AUROC:.2f}" for r in pd.read_csv(lp).itertuples()]
        quoted.append(("AUROC up the ladder", " → ".join(au)))
    fv = first(CANDIDATE_FV)
    if fv is not None:
        drops = []
        for r in RUNGS:
            d = fv / "full" / r / "drop_one_within_21.csv"
            if d.exists():
                drops.append(int((pd.read_csv(d).loss <= 0).sum()))
        if len(drops) == 3:
            quoted.append(("non-contributors per rung",
                           f"{drops[0]} of 21 for ANC1+, {drops[1]} for ANC4+, {drops[2]} for ANC8+"))
        h = fv / "full" / "anc8plus" / "why21_heldout.csv"
        if h.exists():
            h = pd.read_csv(h).set_index("set")
            quoted += [("ANC8+ held-out AP, the 21", f"all 21 ({h.loc['21-predictor set', 'AP']:.3f})"),
                       ("ANC8+ held-out AP, full pool", f"full pool ({h.loc['full pool', 'AP']:.3f})")]
    did = find("tigray_difference_in_differences.csv",
               [ROOT / "outputs" / "wartime", ROOT / "artifacts" / "wartime"])
    if did is not None:
        d = pd.read_csv(did)
        d = d[(d.window_shift_months == 0) & (d.controls == "peaceful regions")].set_index("measure")
        quoted += [("wartime no-ANC share", f"{d.loc['never', 'tigray_during'] * 100:.1f}% → "
                                            f"{d.loc['never', 'tigray_after'] * 100:.1f}%"),
                   ("wartime no-ANC interval", f"[{d.loc['never', 'lo'] * 100:.1f}, "
                                               f"{d.loc['never', 'hi'] * 100:.1f}]".replace("-", "−"))]
    if not quoted:
        skip("record numbers match their sources", "result files absent")
    else:
        wrong = [f"{n}: '{v}'" for n, v in quoted if v not in text]
        check("every number the record quotes matches its result file", not wrong,
              "; ".join(wrong) if wrong else f"{len(quoted)} numbers checked")

    base = first([ROOT / "app_payload", ROOT / "app" / "public"])
    jp = base / "journey.json" if base else None
    if jp is None or not jp.exists():
        skip("journey.json", "absent")
        return
    js = json.loads(jp.read_text(encoding="utf-8"))
    entries = [e for p in js["phases"] for e in p["entries"]]
    check("the record parses into sections and entries",
          len(js["phases"]) >= 5 and len(entries) >= 20,
          f"{len(js['phases'])} sections, {len(entries)} entries")
    check("no record entry carries a date or time",
          not any("when" in e for e in entries) and not any("dates" in p for p in js["phases"]))
    ids = {t["id"] for g in js["glossary"]["groups"] for t in g["terms"]}
    dead = sorted({t for e in entries for t in e["terms"]} - ids)
    check("every term the record links to is in the glossary", not dead, str(dead))
    figdir = first(CANDIDATE_FIGURES)
    if figdir is not None and (figdir / "figures_manifest.csv").exists():
        figs = set(pd.read_csv(figdir / "figures_manifest.csv").figure)
        unguided = sorted(figs - set(js["figures"]))
        check("every figure has a plain-language reading guide", not unguided,
              str(unguided) if unguided else f"{len(figs)} figures")
        deadf = sorted({f for e in entries for f in e["figures"]} - figs)
        check("every figure the record links to exists", not deadf, str(deadf))


# Words that belong to a two-generation, already-published framing, and clock
# times from a dated log. None should appear in the documents. File and
# directory names (outputs/enhanced/, ANC8_analysis_frozen_v2) are exempt.
BANNED = [
    (r"\bpublished\b", "published"),
    (r"(?<![/_\w])frozen\b(?![_/])", "frozen"),
    (r"\bV1\b|\bV2\b", "V1/V2"),
    (r"original study", "original study"),
    (r"(?<![/_\w])enhanced\b(?![_/])", "enhanced"),
    (r"\bPhase [0-9]", "phase"),
    (r"\b\d{1,2}:\d{2}\b", "clock time"),
    (r"\bSep(tember)? 2026\b", "date"),
]


def test_wording():
    section("10. WORDING")
    import re
    docs = [ROOT / n for n in ("README.md", "FINDINGS.md", "INSIGHTS.md")] + \
        sorted((ROOT / "docs").glob("*.md"))
    docs = [d for d in docs if d.exists()]
    if not docs:
        skip("wording", "no documents")
        return
    hits = []
    for d in docs:
        for i, line in enumerate(d.read_text(encoding="utf-8").splitlines(), 1):
            for pat, name in BANNED:
                if re.search(pat, line):
                    hits.append(f"{d.name}:{i} {name}")
    check("no document uses the old framing or carries a clock time or date",
          not hits, "; ".join(hits[:12]) + (" ..." if len(hits) > 12 else "")
          if hits else f"{len(docs)} documents")

    # The studio's own screens carry the same rule: what a reader sees on screen must
    # frame the work the way the documents do.
    src = ROOT / "app" / "src"
    if not src.exists():
        skip("studio wording", "app/ not in this layout")
        return
    files = sorted((src / "app").rglob("*.tsx")) + [src / "lib" / "nav.ts"] + sorted((src / "lib" / "help").glob("*.ts"))
    for d in ("studio", "shell", "charts", "map", "planner", "war", "upload", "lab", "explore", "models", "predict", "help"):
        files += sorted((src / "components" / d).rglob("*.tsx"))
    hits = []
    for f in files:
        if not f.exists():
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("import "):
                continue
            for pat, name in BANNED:
                if re.search(pat, line):
                    hits.append(f"{f.relative_to(src)}:{i} {name}")
    check("no studio screen uses the old framing or carries a clock time or date",
          not hits, "; ".join(hits[:12]) if hits else f"{len(files)} files")


HOUSE_SPACING = set(
    "0 0.5 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 18 19 20 21 22 23 24 25 26 28 30 32 36 38 "
    "40 44 46 52 56 60 64 70 78 88 90 96 120 130 140 150 160 180 186 190 196 200 220 230 236 "
    "250 260 280 300 320 330 340 375 420 560 620 640 700 720 760 820 950 1000 1100 1120".split())


def test_studio():
    section("11. THE STUDIO (maps, regions, design)")
    import re
    base = first([ROOT / "app_payload", ROOT / "app" / "public"])
    if base is None:
        skip("studio data", "no app payload")
        return

    geo = base / "geo" / "regions.geojson"
    if geo.exists():
        g = json.loads(geo.read_text(encoding="utf-8"))
        codes = [f["properties"]["pcode"] for f in g["features"]]
        want = {"ET01", "ET02", "ET03", "ET04", "ET05", "ET06", "ET07", "ET08", "ET11",
                "ET12", "ET13", "ET14", "ET15", "ET16"}
        check("every survey region has exactly one map polygon",
              all(codes.count(c) == 1 for c in want) and set(codes) <= want | {"ET99"},
              f"{len(codes)} polygons")
    else:
        skip("map boundaries", "geo/regions.geojson absent; run scripts/build_geo.py")

    rp = base / "data" / "regions.json"
    if not rp.exists():
        skip("regions.json", "absent; run scripts/run_regional_eda.py and export_viz_data.py")
        return
    d = json.loads(rp.read_text(encoding="utf-8"))
    ok = all(len(d["cohorts"][c]["regions"]) == 14 for c in ("full", "entry", "recent"))
    check("regions.json has all 14 regions in all three cohorts", ok)
    nat = d["cohorts"]["full"]["national"]
    got = {"anc1plus": nat["reach1"], "anc4plus": nat["reach4"], "anc8plus": nat["reach8"]}
    bad = {k: v for k, v in got.items() if abs(v - EXPECTED_PREVALENCE[k]) > 6e-4}
    check("the map's national cascade equals the study's weighted prevalence", not bad, str(bad) if bad else "")
    outside = [(c, r) for c, blk in d["cohorts"].items() for r, x in blk["regions"].items()
               if not (x["reach8_ci"][0] - 1e-9 <= x["reach8"] <= x["reach8_ci"][1] + 1e-9)]
    check("every regional interval contains its estimate", not outside, str(outside[:4]))
    concepts = {c["key"] for c in d["concepts"]}
    missing = [(rung, r) for rung, blk in d["drivers"].items() for r, x in blk["regions"].items()
               if set(x["concepts"]) - concepts]
    check("every region's driver split uses only known concepts", not missing, str(missing[:3]))

    ep = base / "data" / "explore.json"
    if ep.exists():
        e = json.loads(ep.read_text(encoding="utf-8"))
        sums = [abs(sum(v["share"]) - 1) for blk in e.get("contacts", {}).values() for v in blk.values()]
        check("every contact-count distribution sums to one",
              bool(sums) and max(sums) < 1e-3, f"worst {max(sums):.2e}" if sums else "no distributions")
        check("the EDHS comparison table covers all 14 regions", len(e["edhs_anc4"]["regions"]) == 14)
        nets = e.get("networks")
        if nets:
            check("both networks are scored at every rung on the held-out women",
                  len({(r["model"], r["rung"]) for r in nets["heldout"] if r["model"] in (
                      "Ladder transformer", "Contact-sequence encoder-decoder")}) == 6)
    else:
        skip("explore.json", "absent; run scripts/export_viz_data.py")

    wp = base / "data" / "war.json"
    if wp.exists():
        wj = json.loads(wp.read_text(encoding="utf-8"))
        dc = wj["did_check"]
        outside = {k: v for k, v in dc.items() if not (v["lo"] <= v["model"] <= v["hi"])}
        check("the conflict model, run on Tigray, reproduces the difference-in-differences",
              not outside, str(outside) if outside else
              ", ".join(f"{k} {v['model']:+.3f} in [{v['lo']:+.3f}, {v['hi']:+.3f}]" for k, v in dc.items()))
        prof = wj["fit"]["profile"]
        check("every recovery lag carries a shock that lowers first contact",
              all(p["anc1"] < 0 for p in prof), f"{len(prof)} lags")
        bt = wj["backtest"]
        check("the Amhara backtest is reported, predicted against observed, by half-year",
              len(bt["rows"]) >= 4 and all("observed_anc1" in r and "full_anc1" in r for r in bt["rows"]),
              f"intensity {bt['intensity_fit']:.2f}, adaptation {bt['kappa_fit']} months")
        check("the simulator's bands rest on the bootstrap draws",
              len(wj["draws"]) >= 100, f"{len(wj['draws'])} draws")
    else:
        skip("war.json", "absent; run scripts/run_war_model.py and export_viz_data.py")

    sp = base / "data" / "scenarios.json"
    if sp.exists():
        sj = json.loads(sp.read_text(encoding="utf-8"))
        n_lev = len(sj["levers"])
        check("the planner has every on/off combination of its levers",
              len(sj["subsets"]) == 2 ** n_lev and len(set(sj["subsets"])) == 2 ** n_lev, f"{len(sj['subsets'])} combinations")
        # g-computation sanity: a lever's single-lever gain is its combination's mean
        # minus the no-lever mean, in every region and rung.
        worst = 0.0
        for r, blk in sj["rungs"].items():
            for ri, row in enumerate(blk["means"]):
                for i in range(n_lev):
                    j = sj["subsets"].index("".join("1" if k == i else "0" for k in range(n_lev)))
                    worst = max(worst, abs((row[j] - row[0]) - blk["gain"][ri][i]))
        # both numbers are written to four decimals, so they can differ by one unit in the last
        check("each lever's weight equals its re-scored average minus the unchanged one", worst <= 1.5e-4, f"worst {worst:.1e}")
        elig_ok = all(0 <= v <= 1 for vals in sj["eligible"].values() for v in vals)
        check("every lever's eligible share is a share", elig_ok)
        check("at least one lever is supported by the data at every rung",
              any(l["supported"] for l in sj["levers"]), ", ".join(l["key"] for l in sj["levers"] if l["supported"]))
    else:
        skip("scenarios.json", "absent; run scripts/run_scenarios.py and export_viz_data.py")

    mp = base / "data" / "models.json"
    if mp.exists():
        mj = json.loads(mp.read_text(encoding="utf-8"))
        an = json.loads((base / "analysis.json").read_text(encoding="utf-8")) if (base / "analysis.json").exists() else None
        fams, cards = mj["families"], mj["cards"]
        if an:
            import re as _re
            name_key = {f["name"]: k for k, f in fams.items()}
            worst, n_cmp = 0.0, 0
            for rung, rows in an["leaderboard"].items():
                short = "anc" + rung[3]
                for r in rows:
                    if r.get("held_AP") is None:
                        continue
                    nm = _re.sub(r"^V1 (.+)$", r" · 21 predictors", r["model"])
                    k = name_key.get(nm)
                    if k and short in cards.get(k, {}):
                        worst = max(worst, abs(cards[k][short]["ap"] - r["held_AP"]))
                        n_cmp += 1
            check("every leaderboard model has a card that matches its held-out AP", n_cmp > 30 and worst < 1e-4,
                  f"{n_cmp} cards, worst gap {worst:.1e}")
        bad_g = [f"{k}/{r}" for k, by in cards.items() for r, c in by.items()
                 if abs(c["gains"][0]) > 1e-9 or abs(c["gains"][-1] - 1) > 1e-3
                 or any(b < a - 1e-9 for a, b in zip(c["gains"], c["gains"][1:]))]
        check("every gains curve starts at 0, ends at 1 and never falls", not bad_g, "; ".join(bad_g[:4]))
        bad_r = [f"{k}/{r}" for k, by in cards.items() for r, c in by.items()
                 if abs(c["roc"][0][-1] - 1) > 1e-6 or abs(c["roc"][1][-1] - 1) > 1e-6]
        check("every ROC curve ends at (1, 1)", not bad_r, "; ".join(bad_r[:4]))
        small = [f"{k}/{r}/{d}" for k, by in cards.items() for r, c in by.items()
                 for d, rows in c["subgroups"].items() for x in rows if x["n"] < 25]
        check("no subgroup cell has fewer than 25 women", not small, "; ".join(small[:4]))
        nets = [k for k in ("ladder-transformer", "contact-sequence-encoder-decoder")
                if all(r in cards.get(k, {}) for r in ("anc1", "anc4", "anc8"))]
        check("both networks have a card at all three rungs", len(nets) == 2)
        check("each card carries a tuning or how-built block",
              all("tuning" in c for by in cards.values() for c in by.values()))
    else:
        skip("models.json", "absent; run scripts/run_model_cards.py and export_viz_data.py")

    # The house design system: spacing utilities outside its scale silently fall back
    # to Tailwind's default (e.g. h-54 = 216px), so they are refused here.
    src = ROOT / "app" / "src"
    if src.exists():
        pat = re.compile(r'(?<![\w-])-?(?:[mp][xytrbl]?|gap(?:-[xy])?|[wh]|size|top|left|right|bottom|'
                         r'inset(?:-[xy])?|space-[xy]|min-[wh]|max-[wh]|translate-[xy]|scroll-mt)-'
                         r'(\d+(?:\.\d+)?)(?![\w.\[])')
        dirs = ["app", "components/studio", "components/shell", "components/charts", "components/map",
                "components/planner", "components/war", "components/upload", "components/lab",
                "components/explore", "components/models", "components/predict", "components/help"]
        hits = []
        for dname in dirs:
            for f in sorted((src / dname).rglob("*.tsx")) if (src / dname).exists() else []:
                for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                    hits += [f"{f.relative_to(src)}:{i} {m.group(0)}" for m in pat.finditer(line)
                             if m.group(1) not in HOUSE_SPACING]
        check("studio screens use only the house spacing scale", not hits, "; ".join(hits[:6]))

        # Font sizes likewise: text-9 is not a house size and silently renders at the
        # inherited 13px, larger than the label it was meant to sit under.
        sizes = set(re.findall(r"--text-(\d+(?:-\d)?):", (src / "app" / "globals.css").read_text(encoding="utf-8")))
        sizes = {x.replace("-", ".") for x in sizes}
        tpat = re.compile(r'(?<![\w-])text-(\d+(?:\.\d+)?)(?![\w.\[])')
        hits = []
        for dname in dirs:
            for f in sorted((src / dname).rglob("*.tsx")) if (src / dname).exists() else []:
                for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                    hits += [f"{f.relative_to(src)}:{i} {m.group(0)}" for m in tpat.finditer(line)
                             if m.group(1) not in sizes]
        check("studio screens use only the house type sizes", not hits, "; ".join(hits[:6]))

        # Corner radius is 1-3px everywhere. The Tailwind defaults (rounded, rounded-md,
        # rounded-lg ...) are 4px and up and came from the previous build; rounded-full
        # stays for dots and thin bars.
        rpat = re.compile(r'(?<![\w-])rounded(?:-(?:sm|md|lg|xl|2xl|3xl))?(?![\w-])')
        bpat = re.compile(r"borderRadius\s*:\s*[\"']?(\d+(?:\.\d+)?)")
        cpat = re.compile(r"className=[\"'`{ ]*(?:[^\"'`]*\s)?card(?:\s|[\"'`])")
        hits = []
        for f in sorted(src.rglob("*.tsx")):
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if line.lstrip().startswith(("import ", "//", "*", "/*")):
                    continue
                hits += [f"{f.relative_to(src)}:{i} {m.group(0)}" for m in rpat.finditer(line)]
                hits += [f"{f.relative_to(src)}:{i} borderRadius {m.group(1)}" for m in bpat.finditer(line)
                         if float(m.group(1)) > 3]
                if cpat.search(line):
                    hits.append(f"{f.relative_to(src)}:{i} .card")
        check("no screen uses a corner radius above 3px or the old card class", not hits, "; ".join(hits[:6]))

    test_browser_ports()


def _compile_ts(names: list[str], tmp: Path) -> bool:
    import subprocess
    r = subprocess.run(["npx", "tsc", *[str(ROOT / "app" / "src" / "lib" / n) for n in names],
                        "--outDir", str(tmp), "--module", "commonjs", "--target", "es2019",
                        "--skipLibCheck", "--esModuleInterop"],
                       capture_output=True, text=True, shell=sys.platform == "win32", cwd=ROOT / "app")
    return r.returncode == 0


def test_browser_ports():
    """The screener and the forecasters run in the browser: check them there."""
    import subprocess
    import tempfile
    cases = ROOT / "outputs" / "screener" / "parity_cases.json"
    sj = ROOT / "outputs" / "screener" / "screener.json"
    if not (cases.exists() and sj.exists()):
        skip("screener parity", "run scripts/run_clinic_screener.py first")
        return
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        if not _compile_ts(["screener.ts", "forecast.ts"], tmp):
            skip("browser ports", "TypeScript compiler not available")
            return
        runner = tmp / "run.js"
        runner.write_text(r"""
const fs = require('fs');
const { score } = require('./screener.js');
const f = require('./forecast.js');
const s = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const c = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const p = {};
for (const r of ['anc4', 'anc8']) p[r] = c.records.map(rec => score(s, r, rec).p);
// forecasters: a seasonal series with a trend; the seasonal model should beat the
// last-value model, and two runs must agree exactly
const y = Array.from({length: 48}, (_, t) => 100 + 0.8 * t + 12 * Math.sin(2 * Math.PI * t / 12));
const a = f.backtest(y, 12, 6), b = f.backtest(y, 12, 6);
fs.writeFileSync(process.argv[4], JSON.stringify({p, best: a[0].key,
  naive: a.find(x => x.key === 'naive').mae, top: a[0].mae, same: JSON.stringify(a) === JSON.stringify(b)}));
""", encoding="utf-8")
        outp = tmp / "out.json"
        r = subprocess.run(["node", str(runner), str(sj), str(cases), str(outp)], capture_output=True, text=True, cwd=tmp)
        if r.returncode != 0:
            check("the browser screener runs", False, r.stderr[-300:])
            return
        res = json.loads(outp.read_text(encoding="utf-8"))
        ref = json.loads(cases.read_text(encoding="utf-8"))["p"]
        worst = max(abs(a - b) for rung in ("anc4", "anc8") for a, b in zip(res["p"][rung], ref[rung]))
        check("the browser screener matches the fitted model on held-out women", worst < 1e-9,
              f"worst difference {worst:.1e} over {2 * len(ref['anc4'])} predictions")
        check("the forecasters find the season in a seasonal series",
              res["best"] in ("hw", "snaive") and res["top"] < res["naive"],
              f"best {res['best']}, error {res['top']:.2f} against last-value {res['naive']:.2f}")
        check("the forecast backtest is reproducible", res["same"])

    # The two networks' browser forward pass against PyTorch, on held-out women.
    par = ROOT / "outputs" / "deep" / "parity_heldout.npy"
    wts = ROOT / "outputs" / "deep" / "weights.json"
    if not (par.exists() and wts.exists()):
        skip("network parity", "run scripts/run_deep_models.py first")
        return
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import run_deep_models as rdm
        _, _, held, _, _, _ = rdm.load()
    except Exception as exc:  # the per-woman data is not in every layout
        skip("network parity", f"held-out women not available: {type(exc).__name__}")
        return
    prep = json.loads(wts.read_text(encoding="utf-8"))["ladder"]["prep"]
    n = 200
    recs = []
    for _, row in held.head(n).iterrows():
        rec = {c: (None if pd.isna(pd.to_numeric(row[c], errors="coerce")) else float(pd.to_numeric(row[c], errors="coerce")))
               for c in prep["numeric"]}
        rec.update({c: (None if pd.isna(row[c]) else str(row[c])) for c in prep["categorical"]})
        recs.append(rec)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        if not _compile_ts(["nets.ts"], tmp):
            skip("network parity", "TypeScript compiler not available")
            return
        (tmp / "recs.json").write_text(json.dumps(recs), encoding="utf-8")
        (tmp / "run.js").write_text(r"""
const fs = require('fs'); const n = require('./nets.js');
const nets = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const recs = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
fs.writeFileSync(process.argv[4], JSON.stringify(recs.map(r => [n.ladder(nets, r).p, n.sequence(nets, r).p])));
""", encoding="utf-8")
        r = subprocess.run(["node", str(tmp / "run.js"), str(wts), str(tmp / "recs.json"), str(tmp / "out.json")],
                           capture_output=True, text=True, cwd=tmp)
        if r.returncode != 0:
            check("the browser networks run", False, r.stderr[-300:])
            return
        got = np.array(json.loads((tmp / "out.json").read_text(encoding="utf-8")))  # (n, 2, 3)
    ref = np.load(par)[:, :n, :].transpose(1, 0, 2)
    worst = float(np.abs(got - ref).max())
    # the weights are stored to six decimals, so agreement is to about 1e-5
    check("the browser networks match PyTorch on held-out women", worst < 1e-4,
          f"worst difference {worst:.1e} over {n} women, both networks, three rungs")



def _help_cards(src: Path) -> dict[str, str | None]:
    """Every Help card as "<topic>.<card>" -> the screenshot it shows (None for none).

    Reads lib/help/{basics,plan,explore,models}.ts by their layout: a topic's `key:` is
    indented four spaces, and a card's `id:` and optional `shot:` eight.
    """
    import re
    cards: dict[str, str | None] = {}
    for name in ("basics", "plan", "explore", "models"):
        topic, card = None, None
        for line in (src / "lib" / "help" / f"{name}.ts").read_text(encoding="utf-8").splitlines():
            if m := re.match(r'^ {4}key: "([^"]+)"', line):
                topic = m.group(1)
            elif topic and (m := re.match(r'^ {8}id: "([^"]+)"', line)):
                card = f"{topic}.{m.group(1)}"
                cards[card] = card
            elif card and (m := re.match(r'^ {8}shot: (false|"([^"]+)")', line)):
                cards[card] = None if m.group(1) == "false" else m.group(2)
    return cards


def test_help():
    section("12. THE HELP")
    import re
    src = ROOT / "app" / "src"
    if not (src / "lib" / "help").exists():
        skip("help", "app/src/lib/help not in this layout")
        return
    cards = _help_cards(src)
    check("the Help has a card for every panel it explains", len(cards) > 80, f"{len(cards)} cards")

    # Every help id a screen carries opens a real card.
    used, missing, bare = set(), [], []
    for f in sorted(src.rglob("*.tsx")):
        rel = f.relative_to(src).as_posix()
        if rel.startswith("components/help/"):
            continue
        text = f.read_text(encoding="utf-8")
        for m in re.finditer(r'(?:data-)?help="([a-z0-9-]+\.[a-z0-9-]+)"', text):
            used.add(m.group(1))
            if m.group(1) not in cards:
                missing.append(f"{rel}: {m.group(1)}")
        # every panel or region section with a how-to-read hint links to its card
        for m in re.finditer(r"\bhow=", text):
            start = max(text.rfind("<Panel", 0, m.start()), text.rfind("<Section", 0, m.start()))
            if start >= 0 and "help=" not in text[start:m.start()]:
                bare.append(f"{rel}:{text.count(chr(10), 0, m.start()) + 1}")
    check("every help id on a screen opens a Help card", not missing, "; ".join(missing[:6]))
    check("every panel with a how-to-read hint links to the Help", not bare, "; ".join(bare[:6]))

    # Every screenshot the Help shows was captured.
    shots_dir = ROOT / "app" / "public" / "help" / "shots"
    idx = shots_dir / "index.json"
    if not idx.exists():
        skip("help screenshots", "run scripts/capture_help_shots.mjs against the dev server")
        return
    have = set(json.loads(idx.read_text(encoding="utf-8"))["shots"])
    wanted = {s for s in cards.values() if s}
    absent = sorted(s for s in wanted if s not in have or not (shots_dir / f"{s}.jpg").exists())
    check("every screenshot the Help shows was captured", not absent, "; ".join(absent[:8]) + (" ..." if len(absent) > 8 else ""))
    orphans = sorted(u for u in used if u not in have)
    check("every tagged panel has a screenshot", not orphans, "; ".join(orphans[:8]))


def main():
    print("=" * 74)
    print("ANC ATTAINMENT -- CHECK SUITE")
    print("=" * 74)
    print(f"root: {ROOT}")

    df = test_dataset()
    test_split(df)
    test_official_indicator()
    test_artifacts()
    test_claims()
    test_figures()
    test_scorer()
    test_app_payload()
    test_study()
    test_record()
    test_wording()
    test_studio()
    test_help()

    print("\n" + "=" * 74)
    passed = sum(1 for k, _ in RESULTS if k == "PASS")
    failed = [n for k, n in RESULTS if k == "FAIL"]
    skipped = [n for k, n in RESULTS if k == "SKIP"]
    print(f"{passed} passed, {len(failed)} failed, {len(skipped)} skipped")
    if skipped:
        print("\nSkipped (inputs absent -- not a pass):")
        for n in skipped:
            print(f"  - {n}")
    if failed:
        print("\nFAILED:")
        for n in failed:
            print(f"  - {n}")
        sys.exit(1)
    print("\nEverything that could be checked, checked out.")


if __name__ == "__main__":
    main()
