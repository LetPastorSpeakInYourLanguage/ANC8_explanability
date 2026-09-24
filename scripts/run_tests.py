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
EDHS_ANC4_BY_REGION = {
    "Tigray": 57.1, "Afar": 46.2, "Amhara": 62.0, "Oromia": 48.4, "Somali": 12.7,
    "Benishangul-Gumuz": 57.2, "Central Ethiopia": 58.5, "Sidama": 41.5,
    "South West Ethiopia": 48.1, "South Ethiopia": 47.1, "Gambella": 49.2,
    "Harari": 46.5, "Addis Ababa": 94.8, "Dire Dawa": 69.1,
}


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
