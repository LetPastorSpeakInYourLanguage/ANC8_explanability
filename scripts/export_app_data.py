"""Publish the analysis itself to the web app, not just its conclusions.

    python scripts/export_app_data.py

Writes app/public/analysis.json and app/public/policy.json. Everything is read
from the artifacts the pipeline produced, so the app cannot display a number
the analysis did not compute -- including the unflattering ones. The tuning
view shows what the search bought over library defaults, the evidence view
shows the confidence interval that spans zero, and the subgroup table shows
where the model is at chance.

Rungs and analyses that have not run yet are simply absent, and the app hides
those panels rather than inventing content.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from anc8 import outcomes  # noqa: E402

ENHANCED = ROOT / "outputs" / "enhanced"
LADDER = ROOT / "outputs" / "ladder"
POLICY = ROOT / "outputs" / "policy"
PUBLIC = ROOT / "app" / "public"

RUNGS = list(outcomes.LADDER)

# Which predictors a ministry could plausibly act on. Kept here as well as in
# the policy script so the app can label a predictor without a second lookup.
MODIFIABLE_HINT = {
    "travel_hospital_log", "travel_healthpost_log", "s1101", "s1101b", "s1101a",
    "transport_mode_group", "health_insurance", "v481", "healthpost_time_missing",
    "internet_exposure", "v171a", "v157", "v158", "v159", "v113", "v116",
}


def rows(path: Path):
    return pd.read_csv(path).to_dict("records") if path.exists() else None


def blob(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def clean(obj):
    """JSON cannot carry NaN; the app would rather see null."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return None if not np.isfinite(obj) else round(float(obj), 6)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def wmean(x, w):
    x, w = np.asarray(x, float), np.asarray(w, float)
    return float((x * w).sum() / w.sum())


# --------------------------------------------------------------- leaderboard
def leaderboard(rung: str):
    dev_p = ENHANCED / rung / "development_oof_performance.csv"
    held_p = ENHANCED / rung / "heldout_performance.csv"
    if not dev_p.exists():
        return None
    dev = pd.read_csv(dev_p).set_index("model")
    held = pd.read_csv(held_p) if held_p.exists() else pd.DataFrame()

    out = []
    seen = set()
    if len(held):
        for r in held.itertuples():
            d = dev.loc[r.model] if r.model in dev.index else None
            seen.add(r.model)
            out.append({
                "model": r.model,
                "generation": getattr(r, "generation", "V2 (enhanced)"),
                "held_AP": r.AP, "held_AUROC": r.AUROC, "held_Brier": r.Brier,
                "held_slope": getattr(r, "Calibration_slope", None),
                "held_CITL": getattr(r, "CITL", None),
                "sensitivity": getattr(r, "Sensitivity", None),
                "specificity": getattr(r, "Specificity", None),
                "threshold": getattr(r, "Threshold", None),
                "dev_AP": float(d.AP) if d is not None else None,
                "dev_AUROC": float(d.AUROC) if d is not None else None,
                "dev_Brier": float(d.Brier) if d is not None else None,
                "dev_slope": float(d.Calibration_slope) if d is not None else None,
                "n_trials": int(d.n_trials) if d is not None else None,
                "seconds": float(d.seconds) if d is not None else None,
                "optimism": (float(d.AP) - r.AP) if d is not None else None,
            })
    for model, d in dev.iterrows():
        if model in seen:
            continue
        out.append({
            "model": model, "generation": "V2 (enhanced)",
            "held_AP": None, "held_AUROC": None, "held_Brier": None,
            "held_slope": None, "held_CITL": None,
            "sensitivity": None, "specificity": None, "threshold": None,
            "dev_AP": float(d.AP), "dev_AUROC": float(d.AUROC),
            "dev_Brier": float(d.Brier), "dev_slope": float(d.Calibration_slope),
            "n_trials": int(d.n_trials), "seconds": float(d.seconds),
            "optimism": None,
        })
    out.sort(key=lambda r: -(r["dev_AP"] or 0))
    return out


def calibration_curves(rung: str, bins: int = 10):
    """Weighted decile means, for the calibration panel.

    Computed here rather than in the browser because it needs the locked
    held-out predictions, which are far larger than the numbers they reduce to.
    """
    p = ENHANCED / rung / "heldout_locked_predictions_v2.csv"
    if not p.exists():
        return None
    d = pd.read_csv(p)
    y, w = d.y.to_numpy(), d.w.to_numpy()
    out = {}
    for col in [c for c in d.columns if c.startswith("prob::")]:
        pr = d[col].to_numpy()
        q = np.quantile(pr, np.linspace(0, 1, bins + 1))
        idx = np.clip(np.digitize(pr, q[1:-1]), 0, bins - 1)
        pts = []
        for b in range(bins):
            sel = idx == b
            if sel.sum() < 10:
                continue
            pts.append({"predicted": wmean(pr[sel], w[sel]),
                        "observed": wmean(y[sel], w[sel]),
                        "n": int(sel.sum())})
        if pts:
            out[col.removeprefix("prob::")] = pts
    return out


def ablation(rung: str):
    p = ENHANCED / rung / "hyperparameter_ablation.csv"
    if not p.exists():
        return None
    d = pd.read_csv(p)
    per_model = {}
    for model in d.model.unique():
        sub = d[d.model == model]
        dflt = sub[sub.parameter == "(library defaults)"]
        tuned = sub[sub.parameter == "(tuned optimum)"]
        real = sub[~sub.parameter.astype(str).str.startswith("(")]
        sens = (real.groupby("parameter")
                .agg(worst_AP_drop=("AP_vs_tuned", "min"),
                     best_AP_gain=("AP_vs_tuned", "max"),
                     n_perturbations=("AP_vs_tuned", "size"))
                .sort_values("worst_AP_drop").reset_index())
        per_model[model] = {
            "defaults_AP": float(dflt.AP.iloc[0]) if len(dflt) else None,
            "tuned_AP": float(tuned.AP.iloc[0]) if len(tuned) else None,
            "gain": (float(tuned.AP.iloc[0]) - float(dflt.AP.iloc[0]))
                    if len(tuned) and len(dflt) else None,
            "parameters": sens.to_dict("records"),
            "trials": real.to_dict("records"),
        }
    return per_model


def ladder_block():
    out = {}
    for name, key in (("patterns", "ladder_patterns.csv"),
                      ("predictor_shares", "predictor_shares.csv"),
                      ("domain_shares", "domain_shares.csv"),
                      ("performance", "ladder_performance.csv"),
                      ("agreement", "method_agreement.csv")):
        r = rows(LADDER / key)
        if r is not None:
            out[name] = r
    roll = LADDER / "domain_rollup.csv"
    if roll.exists():
        out["domain_rollup"] = pd.read_csv(roll).to_dict("records")
    return out or None


def policy_block():
    out = {}
    df_path = ENHANCED / "ANC8_analysis_frozen_v2.pkl"
    if df_path.exists():
        df = pd.read_pickle(df_path)
        w = (df.v005 / 1e6).to_numpy()
        n = df.anc_contacts.fillna(0).to_numpy()
        started, at4 = n >= 1, n >= 4
        out["cascade"] = {
            "reach1": wmean(n >= 1, w), "reach4": wmean(n >= 4, w),
            "reach8": wmean(n >= 8, w),
            "never": wmean(n < 1, w),
            "start_lt4": wmean(started & (n < 4), w),
            "four_lt8": wmean(at4 & (n < 8), w),
            "continue_1_to_4": wmean(n[started] >= 4, w[started]),
            "continue_4_to_8": wmean(n[at4] >= 8, w[at4]),
            "n": int(len(df)),
        }

        reg = []
        for region, g in df.groupby("region", observed=True):
            i = df.index.get_indexer(g.index)
            ni, wi = n[i], w[i]
            st, f4 = ni >= 1, ni >= 4
            reg.append({
                "region": str(region), "n": len(i),
                "reach8": wmean(ni >= 8, wi),
                "never": wmean(ni < 1, wi),
                "start_lt4": wmean(st & (ni < 4), wi),
                "four_lt8": wmean(f4 & (ni < 8), wi),
                "continue_1_to_4": wmean(ni[st] >= 4, wi[st]) if st.sum() else None,
                "continue_4_to_8": wmean(ni[f4] >= 8, wi[f4]) if f4.sum() else None,
            })
        for r in reg:
            losses = {"never starting": r["never"],
                      "stopping before the 4th contact": r["start_lt4"],
                      "stopping between the 4th and 8th": r["four_lt8"]}
            r["biggest_loss"] = max(losses, key=losses.get)
            r["biggest_loss_share"] = losses[r["biggest_loss"]]
        out["regional_cascade"] = sorted(reg, key=lambda r: r["reach8"])

        # Equity among women who have already demonstrated engagement.
        eq = {}
        sub = df[at4]
        nn, ww = n[at4], w[at4]
        for var in ("wealth_quintile", "residence", "maternal_education"):
            if var not in sub:
                continue
            levels = []
            for lev, g in sub.groupby(var, observed=True):
                i = sub.index.get_indexer(g.index)
                if len(i) < 25:
                    continue
                levels.append({"level": str(lev), "n": int(len(i)),
                               "continue_4_to_8": wmean(nn[i] >= 8, ww[i])})
            if levels:
                eq[var] = sorted(levels, key=lambda r: r["continue_4_to_8"])
        out["continuation_equity"] = eq

    for name, key in (("regional_gap", "regional_performance.csv"),
                      ("modifiable", "modifiable_vs_fixed.csv"),
                      ("risk_bands", "risk_bands.csv"),
                      ("continuation_profile", "continuation_profile.csv")):
        r = rows(POLICY / key)
        if r is not None:
            out[name] = r
    return out


def feature_value_block():
    """Which predictors pay their way, per cohort and outcome.

    Only the parts the app shows: the add-one distribution, the cumulative
    curve, the forward-selection tiers, the bootstrap selection frequency and
    the held-out comparison. Everything else stays in outputs/feature_value/.
    """
    base = ROOT / "outputs" / "feature_value"
    if not base.exists():
        return None
    out = {}
    for cohort_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        for rung_dir in sorted(p for p in cohort_dir.iterdir() if p.is_dir()):
            summary = blob(rung_dir / "summary.json")
            if not summary or "tier1" not in summary:
                continue
            entry = {"summary": summary}
            for key, name in (("add_one", "add_one_to_21.csv"),
                              ("cumulative", "cumulative_from_21.csv"),
                              ("steps", "forward_steps.csv"),
                              ("frequency", "selection_frequency.csv"),
                              ("heldout", "heldout.csv"),
                              ("lightgbm_check", "lightgbm_check.csv"),
                              ("original21_placement", "original21_placement.csv"),
                              ("drop_within_21", "drop_one_within_21.csv"),
                              ("path_within_21", "forward_within_21.csv"),
                              ("drop_group_21", "drop_group_21.csv")):
                r = rows(rung_dir / name)
                if r is not None:
                    entry[key] = r
            entry["heldout_bootstrap"] = blob(rung_dir / "heldout_bootstrap.json")
            # The 21 under random forest and XGBoost as well as logistic
            # regression (scripts/run_21_models_heldout.py). The logistic row
            # is already in heldout.csv, so only the other two are added.
            fam = rows(rung_dir / "heldout_21_models.csv")
            if fam:
                entry["heldout"] = (entry.get("heldout") or []) + [
                    {k: v for k, v in r.items() if k not in ("params", "best_of_three")}
                    for r in fam if r["model"] != "Logistic regression"]
                entry["best_21_model"] = next(
                    (r["model"] for r in fam if r.get("best_of_three")), None)
                entry["heldout_bootstrap"] = {
                    **(entry["heldout_bootstrap"] or {}),
                    **(blob(rung_dir / "heldout_21_models_bootstrap.json") or {})}
            out.setdefault(cohort_dir.name, {})[rung_dir.name] = entry
    return out or None


def horizons_block():
    """The two prediction horizons: before ANC and at ANC entry."""
    base = ROOT / "outputs" / "horizons"
    if not base.exists():
        return None
    out = {}
    for key, name in (("early_anc", "early_anc_development.csv"),
                      ("heldout", "heldout_entry.csv"),
                      ("cross", "cross_horizon.csv"),
                      ("tiers", "tiers_by_horizon.csv")):
        r = rows(base / name)
        if r is not None:
            out[key] = r
    out["bootstrap"] = blob(base / "heldout_bootstrap.json")
    return out or None


def predictor_matrix_block():
    """Each predictor's value relative to the 21, per rung (full cohort)."""
    return rows(ROOT / "outputs" / "predictor_value" / "full" / "matrix.csv")


def wartime_block():
    base = ROOT / "outputs" / "wartime"
    if not base.exists():
        return None
    out = {}
    for key, name in (("did", "tigray_difference_in_differences.csv"),
                      ("by_period", "anc_by_region_period.csv"),
                      ("exposure_counts", "exposure_counts.csv"),
                      ("interactions", "exposure_interactions.csv"),
                      ("regional_gap", "regional_gap_by_cohort.csv"),
                      ("by_war_period", "region_by_war_period.csv")):
        r = rows(base / name)
        if r is not None:
            out[key] = r
    w = ROOT / "docs" / "conflict_windows.csv"
    if w.exists():
        out["windows"] = pd.read_csv(w).to_dict("records")
    return out or None


# The documents the Reports view renders, in reading order, with the reader
# each is written for. The files themselves are copied verbatim, so the app
# shows exactly the text and generated tables that are in the repository.
DOCUMENTS = [
    ("brief", "docs/POLICY_BRIEF.md", "Policy brief",
     "Ministry of Health", "Findings and recommendations, in ten minutes"),
    ("record", "docs/ANALYSIS_RECORD.md", "Analysis record", "Everyone",
     "Every analysis in order: the question, the test, the result"),
    ("glossary", "docs/GLOSSARY.md", "Understanding the numbers", "Everyone",
     "Every term, score and figure explained in plain language"),
    ("insights", "INSIGHTS.md", "Insights", "General reader",
     "The findings in plain language"),
    ("findings", "FINDINGS.md", "Technical findings", "Researchers",
     "The hub: what held up, what did not, and why"),
    ("predictors", "docs/PREDICTOR_VALUE.md", "Predictor value",
     "Researchers", "2 / 8 / 21 / 88, the drop study, why 21, across ANC1+/4+/8+"),
    ("horizons", "docs/HORIZONS.md", "Two prediction horizons", "Researchers",
     "Before ANC starts vs at ANC entry, and what early ANC adds"),
    ("wartime", "docs/WARTIME.md", "The Tigray war", "Researchers",
     "Antenatal care during and after the conflict"),
    ("data", "docs/DATA_AND_COHORT.md", "Data and cohort", "Researchers",
     "The population, the official window, when predictors were measured"),
    ("methods", "docs/METHODS.md", "Methods", "Researchers",
     "Design, splitting, models, metrics, supporting analyses, deployment"),
    ("limitations", "docs/LIMITATIONS.md", "Limitations", "Everyone",
     "What this analysis cannot support"),
    ("decisions", "docs/DECISION_LOG.md", "Decision log", "Reviewers",
     "Every significant decision and why it was made"),
]


def publish_documents():
    """Copy the documents and figures into app/public for the Reports view."""
    import shutil

    docs_out = PUBLIC / "docs"
    figs_out = PUBLIC / "figures"
    docs_out.mkdir(parents=True, exist_ok=True)
    figs_out.mkdir(parents=True, exist_ok=True)

    index = []
    for key, rel, title, audience, blurb in DOCUMENTS:
        src = ROOT / rel
        if not src.exists():
            continue
        shutil.copy2(src, docs_out / f"{key}.md")
        index.append({"key": key, "title": title, "audience": audience,
                      "blurb": blurb, "source": rel,
                      "file": Path(rel).name})

    figs = []
    man = ROOT / "outputs" / "figures" / "figures_manifest.csv"
    if man.exists():
        for r in pd.read_csv(man).sort_values("figure").itertuples():
            png = ROOT / "outputs" / "figures" / f"{r.figure}.png"
            if png.exists():
                shutil.copy2(png, figs_out / png.name)
                figs.append({"figure": r.figure, "title": r.title,
                             "caption": r.caption, "file": f"/figures/{png.name}"})

    (PUBLIC / "documents.json").write_text(
        json.dumps({"documents": index, "figures": figs}, indent=1), encoding="utf-8")
    mb = sum(f.stat().st_size for f in figs_out.glob("*.png")) / 1e6
    print(f"published {len(index)} documents and {len(figs)} figures ({mb:.1f} MB)")


# ---------------------------------------------------------------------------
# The "Analysis record" view: the record and the glossary, parsed from their
# markdown so the documents stay the only source. Both files follow a fixed
# shape (see the files themselves); a malformed entry fails loudly here rather
# than rendering half-empty in the app.

JOURNEY_FIELDS = {
    "Question": "question", "What we did": "did", "How we tested it": "tested",
    "What we found": "found", "What changed": "changed", "Source": "source",
}
GLOSSARY_FIELDS = {
    "In plain words": "plain", "In this analysis": "here",
    "A good value looks like": "good",
}
FIGURE_FIELDS = {
    "What it shows": "shows", "How to read it": "read", "Takeaway": "takeaway",
}


def _meta(lines) -> dict:
    """First '<!-- a: x | b: y, z -->' line -> {'a': 'x', 'b': 'y, z'}"""
    line = next((l for l in lines if l.strip().startswith("<!--")), "")
    body = line.strip()[4:-3].strip()
    out = {}
    for part in body.split("|"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def _fields(lines, names: dict) -> dict:
    """Split an entry body on '**Label.**' openers into named markdown fields."""
    import re

    pat = re.compile(r"^\*\*(" + "|".join(re.escape(k) for k in names) + r")\.\*\*\s*(.*)$")
    out, key, buf = {}, None, []
    for line in lines:
        if line.strip() == "---":
            continue
        m = pat.match(line)
        if m:
            if key:
                out[key] = "\n".join(buf).strip()
            key, buf = names[m.group(1)], [m.group(2)]
        elif key:
            buf.append(line)
    if key:
        out[key] = "\n".join(buf).strip()
    return out


def _sections(text: str, level: str):
    """(preamble, [(heading, body_lines), ...]) for headings of one level."""
    pre, secs = [], []
    for line in text.splitlines():
        if line.startswith(level + " "):
            secs.append((line[len(level) + 1:].strip(), []))
        elif secs:
            secs[-1][1].append(line)
        else:
            pre.append(line)
    return pre, secs


def _clean(lines) -> str:
    """Drop horizontal rules and metadata comments; keep the markdown."""
    return "\n".join(l for l in lines
                     if l.strip() != "---" and not l.strip().startswith("<!--")).strip()


def parse_glossary(text: str):
    start, groups, guides = "", [], {}
    _, secs = _sections(text, "##")
    for title, body in secs:
        if title.lower().startswith("start here"):
            start = _clean(body)
            continue
        is_figs = title.lower().startswith("reading the figures")
        pre, subs = _sections("\n".join(body), "###")
        terms = []
        for sub, sbody in subs:
            if is_figs:
                f = _fields(sbody, FIGURE_FIELDS)
                missing = set(FIGURE_FIELDS.values()) - set(f)
                if missing:
                    raise ValueError(f"figure guide {sub} lacks {sorted(missing)}")
                guides[sub] = f
                continue
            m = _meta(sbody)
            if "id" not in m:
                raise ValueError(f"glossary term '{sub}' has no id")
            f = _fields(sbody, GLOSSARY_FIELDS)
            if "plain" not in f:
                raise ValueError(f"glossary term '{sub}' lacks 'In plain words'")
            terms.append({"id": m["id"], "name": sub,
                          "aka": [a.strip() for a in m.get("aka", "").split(",") if a.strip()],
                          **f})
        if not is_figs:
            groups.append({"title": title, "intro": _clean(pre), "terms": terms})
    return start, groups, guides


def parse_journey(text: str):
    intro, secs = _sections(text, "##")
    phases = []
    for title, body in secs:
        meta = _meta(body)
        pre, subs = _sections("\n".join(body), "###")
        entries = []
        for sub, sbody in subs:
            m = _meta(sbody)
            # Entries are titled by what was tested; no dates or times.
            name = sub
            f = _fields(sbody, JOURNEY_FIELDS)
            missing = set(JOURNEY_FIELDS.values()) - set(f)
            if missing:
                raise ValueError(f"timeline entry '{sub}' lacks {sorted(missing)}")
            correction = name.startswith("*Correction:*")
            entries.append({
                "id": f"{meta['phase']}-{len(entries) + 1}",
                "title": name.replace("*Correction:*", "").strip(),
                "kind": "correction" if correction else m.get("kind", "step"),
                "figures": [x.strip() for x in m.get("figures", "").split(",") if x.strip()],
                "terms": [x.strip() for x in m.get("terms", "").split(",") if x.strip()],
                **f,
            })
        phases.append({"id": meta["phase"], "title": meta.get("title", title),
                       "intro": _clean(pre),
                       "entries": entries})
    # the document title line is shown by the app itself
    return _clean([l for l in intro if not l.startswith("# ")]), phases


def publish_journey():
    """Parse ANALYSIS_RECORD.md and GLOSSARY.md into app/public/journey.json."""
    jpath, gpath = ROOT / "docs" / "ANALYSIS_RECORD.md", ROOT / "docs" / "GLOSSARY.md"
    if not (jpath.exists() and gpath.exists()):
        print("record: ANALYSIS_RECORD.md or GLOSSARY.md missing, skipped")
        return
    intro, phases = parse_journey(jpath.read_text(encoding="utf-8"))
    start, groups, guides = parse_glossary(gpath.read_text(encoding="utf-8"))

    # Every reference must resolve, or the app would show a dead link.
    ids = {t["id"] for g in groups for t in g["terms"]}
    man = ROOT / "outputs" / "figures" / "figures_manifest.csv"
    figs = set(pd.read_csv(man).figure) if man.exists() else set(guides)
    problems = []
    for ph in phases:
        for e in ph["entries"]:
            problems += [f"{e['id']}: unknown term '{t}'" for t in e["terms"] if t not in ids]
            problems += [f"{e['id']}: unknown figure '{f}'" for f in e["figures"] if f not in figs]
    problems += [f"figure without a reading guide: {f}" for f in sorted(figs - set(guides))]
    dup = [i for i in ids if sum(t["id"] == i for g in groups for t in g["terms"]) > 1]
    problems += [f"duplicate glossary id: {i}" for i in dup]
    if problems:
        raise ValueError("record references do not resolve:\n  " + "\n  ".join(problems))

    out = {"intro": intro, "phases": phases,
           "glossary": {"start": start, "groups": groups}, "figures": guides}
    (PUBLIC / "journey.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    n = sum(len(p["entries"]) for p in phases)
    print(f"published record: {len(phases)} sections, {n} entries, "
          f"{len(ids)} terms, {len(guides)} figure guides")


def main():
    PUBLIC.mkdir(parents=True, exist_ok=True)

    analysis = {
        "outcomes": {o: outcomes.OUTCOMES[o] for o in RUNGS},
        "rungs": [],
        "leaderboard": {},
        "calibration": {},
        "hyperparameters": {},
        "ablation": {},
        "stability": {},
        "bootstrap": {},
        "subgroups": {},
        "decision_curve": {},
        "operating_thresholds": {},
    }

    for rung in RUNGS:
        lb = leaderboard(rung)
        if lb is None:
            continue
        analysis["rungs"].append(rung)
        analysis["leaderboard"][rung] = lb
        pairs = [r for r in lb if r["optimism"] is not None]
        if pairs:
            analysis.setdefault("optimism", {})[rung] = {
                "mean_drop": float(np.mean([r["optimism"] for r in pairs])),
                "n_models": len(pairs),
            }
        for key, fn in (("calibration", calibration_curves),
                        ("ablation", ablation)):
            v = fn(rung)
            if v:
                analysis[key][rung] = v
        for key, path in (("hyperparameters", "best_hyperparameters.json"),
                          ("stability", "stability_summary.json"),
                          ("bootstrap", "paired_bootstrap_ci.json"),
                          ("operating_thresholds", "operating_thresholds.json")):
            v = blob(ENHANCED / rung / path)
            if v is not None:
                analysis[key][rung] = v
        for key, path in (("subgroups", "subgroup_performance.csv"),
                          ("decision_curve", "decision_curve.csv")):
            v = rows(ENHANCED / rung / path)
            if v is not None:
                analysis[key][rung] = v

    # Cross-rung: what the whole search bought, everywhere it was measured.
    gains = []
    for rung, per_model in analysis["ablation"].items():
        for model, d in per_model.items():
            if d["gain"] is not None:
                gains.append({"rung": rung, "model": model,
                              "defaults_AP": d["defaults_AP"],
                              "tuned_AP": d["tuned_AP"], "gain": d["gain"]})
    if gains:
        analysis["tuning_gain"] = sorted(gains, key=lambda r: r["gain"])

    # Supporting analyses shown in the Evidence view.
    v = rows(ENHANCED / "preprocessing_ablation.csv")
    if v is not None:
        analysis["preprocessing"] = v

    # Screening, summarised: the full table is 6,648 rows and the app only
    # needs the counts and the strongest candidates.
    scr = ENHANCED / "candidate_screening.csv"
    if scr.exists():
        d = pd.read_csv(scr)
        strong = d[d.weighted_auc.notna()].copy()
        strong["strength"] = (strong.weighted_auc - 0.5).abs() + 0.5
        analysis["screening"] = {
            "n_columns": int(len(d)),
            "counts": {str(k): int(v)
                       for k, v in d.screen_status.astype(str).value_counts().items()},
            "top": strong.sort_values("strength", ascending=False).head(30)[
                ["variable", "label", "weighted_auc", "screen_status",
                 "exclusion_reason"]].to_dict("records"),
        }

    red = ENHANCED / "redundancy"
    if red.exists():
        analysis["redundancy"] = {
            "summary": blob(red / "redundancy_summary.json"),
            "pairs": rows(red / "duplicate_pairs.csv"),
            "coarsening": rows(red / "coarsening_pairs.csv"),
            "grouped": (rows(red / "grouped_importance.csv") or [])[:40],
        }

    lad = ladder_block()
    if lad:
        analysis["ladder"] = lad

    analysis["modifiable_hint"] = sorted(MODIFIABLE_HINT)

    fv = feature_value_block()
    if fv:
        analysis["feature_value"] = fv
    pm = predictor_matrix_block()
    if pm:
        analysis["predictor_matrix"] = pm
    hz = horizons_block()
    if hz:
        analysis["horizons"] = hz

    (PUBLIC / "analysis.json").write_text(
        json.dumps(clean(analysis), indent=None, separators=(",", ":")),
        encoding="utf-8")

    pol = policy_block()
    war = wartime_block()
    if war:
        pol["wartime"] = war
    (PUBLIC / "policy.json").write_text(
        json.dumps(clean(pol), indent=None, separators=(",", ":")),
        encoding="utf-8")

    publish_documents()
    publish_journey()

    a = (PUBLIC / "analysis.json").stat().st_size / 1024
    p = (PUBLIC / "policy.json").stat().st_size / 1024
    print(f"wrote {PUBLIC / 'analysis.json'}  ({a:.0f} KB)")
    print(f"  rungs evaluated       {analysis['rungs']}")
    print(f"  models on the board   "
          f"{ {k: len(v) for k, v in analysis['leaderboard'].items()} }")
    print(f"  ablations             {list(analysis['ablation'])}")
    print(f"  ladder sections       {list(lad) if lad else '(not run)'}")
    print(f"wrote {PUBLIC / 'policy.json'}  ({p:.0f} KB)")
    print(f"  sections              {list(pol)}")


if __name__ == "__main__":
    main()
