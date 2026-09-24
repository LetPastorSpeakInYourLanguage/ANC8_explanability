"""Fill the numeric tables in the documentation from the result files.

    python scripts/build_docs.py

The prose in the documents is written by hand. The numbers are not: each
table lives between a pair of markers,

    <!-- AUTO:name -->
    ...generated table...
    <!-- /AUTO:name -->

and this script regenerates everything between them from outputs/. Re-run it
after any analysis finishes and every document picks up the new results; a
table whose inputs do not exist yet says so rather than showing stale or
invented numbers. Nothing outside the markers is touched.

Tables about predictor sets exist per cohort: the plain name is the full
cohort (the main analysis), `_entry` the ANC-entry horizon and `_recent` the
24-month sensitivity window -- e.g. `sets_heldout`, `sets_heldout_entry`,
`sets_heldout_recent`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "outputs"
FV = OUT / "feature_value"
WAR = OUT / "wartime"
ENH = OUT / "enhanced"
HOR = OUT / "horizons"
PV = OUT / "predictor_value"
LAD = OUT / "ladder"
DOCS = [ROOT / "docs" / n for n in (
    "POLICY_BRIEF.md", "DATA_AND_COHORT.md", "PREDICTOR_VALUE.md", "HORIZONS.md",
    "WARTIME.md", "DECISION_LOG.md", "ANALYSIS_RECORD.md", "METHODS.md")] + \
    [ROOT / "FINDINGS.md", ROOT / "INSIGHTS.md", ROOT / "README.md"]

RUNGS = ["anc1plus", "anc4plus", "anc8plus"]
RUNG = {"anc1plus": "ANC1+", "anc4plus": "ANC4+", "anc8plus": "ANC8+"}
COHORT = {"full": "Before ANC (6,893)", "entry": "ANC entry (5,001)",
          "recent": "Last 24 months (5,037)"}
SET = {"tier 1": "Tier 1", "tier 1+2": "Tier 1+2", "original 21": "21-predictor set",
       "all 88": "Full pool", "21 + early ANC": "21 + early ANC"}
PENDING = "_Not yet produced -- this table fills in when the analysis finishes._"


# ------------------------------------------------------------------ helpers
_LABELS = None


def lab(code: str) -> str:
    global _LABELS
    if _LABELS is None:
        p = ROOT / "app" / "src" / "lib" / "labels.ts"
        _LABELS = dict(re.findall(r'^\s+([A-Za-z0-9_]+): "([^"]+)"',
                                  p.read_text(encoding="utf-8"), flags=re.M)) if p.exists() else {}
        _LABELS.update({"age_at_birth": "Mother's age at the birth",
                        "travel_time_min": "Travel time to hospital or health centre",
                        "household_size": "Household size",
                        "traditional_media_weekly_count": "Weekly media count (0-3)",
                        "early_anc": "First ANC contact by 3 months"})
    return _LABELS.get(code, code)


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def isnan(v):
    return v is None or (isinstance(v, float) and np.isnan(v))


def f3(v):
    return "—" if isnan(v) else f"{v:.3f}"


def f4s(v):
    return "—" if isnan(v) else f"{v:+.4f}"


def pct(v, d=1):
    return "—" if isnan(v) else f"{v * 100:.{d}f}%"


def ci(b, key="AP", d=3):
    return (f"{b[f'd_{key}']:+.{d}f} [{b[f'd_{key}_lo']:+.{d}f}, {b[f'd_{key}_hi']:+.{d}f}]"
            if b else "—")


def runs(cohort):
    """Every completed (rung, summary) feature-value run for one cohort."""
    out = []
    for r in RUNGS:
        s = FV / cohort / r / "summary.json"
        if s.exists():
            js = json.loads(s.read_text())
            if "tier1" in js:
                out.append((r, js))
    return out


def csv(c, r, name):
    p = FV / c / r / name
    return pd.read_csv(p) if p.exists() else None


def lift_share(ap, js):
    a = js["anchors"]
    return (ap - a["prevalence"]) / (a["all88"] - a["prevalence"])


# ------------------------------------------------ predictor sets, per cohort
def t_sets_dev(cohort):
    rows = []
    for r, js in runs(cohort):
        a = js["anchors"]
        steps = csv(cohort, r, "forward_steps.csv")
        t1 = steps[steps.tier == "tier 1"] if steps is not None else None
        t2 = steps[steps.tier.isin(["tier 1", "tier 2"])] if steps is not None else None
        rows.append([RUNG[r], f3(a["prevalence"]),
                     f"{len(js['tier1'])} → {f3(t1.AP.iloc[-1]) if t1 is not None and len(t1) else '—'}",
                     f"{len(js['tier1']) + len(js['tier2'])} → {f3(t2.AP.iloc[-1]) if t2 is not None and len(t2) else '—'}",
                     f3(a["original21"]), f"{js.get('n_candidates', 88)} → {f3(a['all88'])}"])
    if not rows:
        return PENDING
    return md_table(["Outcome", "Prevalence (no-information AP)", "Tier 1: n → AP",
                     "Tier 1+2: n → AP", "21-predictor set", "Full pool: n → AP"], rows) + (
        "\n\nDevelopment out-of-fold AP, logistic regression, each set at its own best "
        "regularisation. The tier columns are optimistic because those sets were chosen on "
        "these same folds; the held-out table is the fair comparison.")


def t_sets_heldout(cohort):
    rows = []
    extra = cohort == "entry"
    for r, js in runs(cohort):
        h = csv(cohort, r, "heldout.csv")
        if h is None:
            continue
        bp = FV / cohort / r / "heldout_bootstrap.json"
        boot = json.loads(bp.read_text()) if bp.exists() else {}
        for model in ("Logistic regression", "LightGBM"):
            sub = h[h.model == model].set_index("set")
            cells = []
            names = ["tier 1", "tier 1+2", "original 21"] + \
                (["21 + early ANC"] if extra else []) + ["all 88"]
            for s in names:
                if s not in sub.index:
                    cells.append("—")
                    continue
                b = boot.get(f"{model} | {s} vs original 21")
                cells.append(f"{sub.loc[s, 'AP']:.3f}" + (f" ({ci(b)})" if b else ""))
            rows.append([RUNG[r], "logistic" if model.startswith("Log") else model, *cells])
    if not rows:
        return PENDING
    head = ["Outcome", "Model", "Tier 1", "Tier 1+2", "21-predictor set"] + \
        (["21 + early ANC"] if extra else []) + ["Full pool"]
    return md_table(head, rows) + (
        "\n\nHeld-out AP, each set fitted on development women and scored once on women it "
        "never saw. In brackets: the difference from the 21-predictor set and its 95% paired "
        "stratified-PSU bootstrap interval. An interval containing 0 means the held-out set "
        "cannot tell the two apart.")


def t_tiers(cohort):
    blocks = []
    for r, js in runs(cohort):
        steps = csv(cohort, r, "forward_steps.csv")
        if steps is None:
            continue
        freq = csv(cohort, r, "selection_frequency.csv")
        fmap = dict(zip(freq.predictor, freq.selected_share)) if freq is not None else {}
        rows = []
        for s in steps.itertuples():
            flag = " ⚑" if isinstance(s.at_interview, str) and s.at_interview else ""
            rows.append([s.tier, f"{lab(s.predictor)}{flag}", f"`{s.predictor}`", f3(s.AP),
                         f4s(s.gain), f"{s.seeds_positive}/5",
                         pct(fmap.get(s.predictor), 0) if fmap else "—",
                         "yes" if s.in_original_21 else ""])
        blocks.append(f"**{RUNG[r]}**\n\n" + md_table(
            ["Tier", "Variable", "Code", "AP after adding", "Gain", "Splits", "Re-selected",
             "In the 21"], rows))
    if not blocks:
        return PENDING
    return "\n\n".join(blocks) + (
        "\n\n⚑ measured at interview rather than during the pregnancy (see "
        "DATA_AND_COHORT.md). \"Re-selected\" is the share of 10 bootstrap resamples in which "
        "the same variable was chosen again (ANC8+ only); the last row of each table is the "
        "first step that failed the threshold.")


def t_add_one(cohort):
    rows = []
    for r, js in runs(cohort):
        add = csv(cohort, r, "add_one_to_21.csv")
        cum = csv(cohort, r, "cumulative_from_21.csv")
        if add is None or cum is None:
            continue
        total = cum.AP.iloc[-1] - cum.AP.iloc[0]
        # A share of a near-zero total is noise, not information.
        share = lambda k: ((cum.AP.iloc[k] - cum.AP.iloc[0]) / total
                           if total >= 0.005 and k < len(cum) else np.nan)
        peak = int(cum.AP.idxmax())
        rows.append([RUNG[r], f"{int(add.clears_threshold.sum())} of {len(add)}",
                     f4s(add.gain.median()), f4s(total), pct(share(5), 0), pct(share(10), 0),
                     f"{int(cum.n_added[peak])} (+{cum.AP[peak] - cum.AP.iloc[0]:.4f})"])
    if not rows:
        return PENDING
    return md_table(["Outcome", "Clear +0.005 alone", "Median gain", "All added",
                     "Best 5 carry", "Best 10 carry", "Peak at n added"], rows) + (
        "\n\n\"All added\" is the AP of the 21 plus every other candidate, minus the 21 "
        "alone. A share above 100% means the remaining additions, taken together, made the "
        "model worse.")


def t_top_additions(cohort, n=8):
    blocks = []
    for r, js in runs(cohort):
        add = csv(cohort, r, "add_one_to_21.csv")
        if add is None:
            continue
        rows = [[lab(x.predictor), f"`{x.predictor}`", f4s(x.gain), f"{x.seeds_positive}/5",
                 "yes" if x.clears_threshold else ""] for x in add.head(n).itertuples()]
        blocks.append(f"**{RUNG[r]}**\n\n" + md_table(
            ["Addition to the 21", "Code", "Gain", "Splits", "Clears"], rows))
    return "\n\n".join(blocks) if blocks else PENDING


def t_placement(cohort):
    data = {}
    for r, js in runs(cohort):
        p = csv(cohort, r, "original21_placement.csv")
        if p is not None:
            data[RUNG[r]] = dict(zip(p.predictor, p.placement))
    if not data:
        return PENDING
    names = list(next(iter(data.values())).keys())
    short = {"tier 1": "T1", "tier 2": "T2", "not selected": "·"}
    rows = [[lab(n)] + [short.get(v.get(n, ""), "") for v in data.values()] for n in names]
    counts = ["**selected**"] + [str(sum(1 for x in v.values() if x != "not selected"))
                                 for v in data.values()]
    return md_table(["Member of the 21"] + list(data.keys()), rows + [counts]) + (
        "\n\nT1 / T2 = chosen in tier 1 / tier 2 when selecting from the full pool; "
        "· = not chosen. Age enters as age at the birth.")


# --------------------------------------------------- the 21 on their own
def t_drop_within_21(cohort="full"):
    loss, n21 = {}, None
    for r, js in runs(cohort):
        d = csv(cohort, r, "drop_one_within_21.csv")
        if d is not None:
            loss[r] = d.set_index("predictor")
    if not loss:
        return PENDING
    rungs = [r for r in RUNGS if r in loss]
    order = loss[rungs[-1]].loss.sort_values(ascending=False).index
    rows = []
    for c in order:
        cells = []
        for r in rungs:
            v = loss[r].loss.get(c)
            s = loss[r].seeds_positive.get(c)
            cells.append(f"{v:+.4f}" + ("" if v > 0 else " ·") + f" ({s}/5)")
        rows.append([lab(c)] + cells)
    foot = ["**non-contributors**"] + [str(int((loss[r].loss <= 0).sum())) for r in rungs]
    return md_table(["Removed from the 21"] + [RUNG[r] for r in rungs], rows + [foot]) + (
        "\n\nDevelopment AP lost when the predictor is removed from the 21 (logistic "
        "regression, each set at its own best regularisation, 5 split seeds; in brackets the "
        "seeds on which removing it hurt). · = removing it costs nothing or helps.")


def t_why21(cohort="full"):
    rows = []
    for r, js in runs(cohort):
        a = js["anchors"]
        s0 = js.get("stage0")
        path = csv(cohort, r, "forward_within_21.csv")
        steps = csv(cohort, r, "forward_steps.csv")
        grp = csv(cohort, r, "drop_group_21.csv")
        if s0 is None or path is None or steps is None:
            continue
        sel_ = steps[steps.tier.isin(["tier 1", "tier 2"])]
        cell = lambda n, ap: f"{n} → {ap:.3f} ({lift_share(ap, js) * 100:.0f}%)"
        top3 = path.head(3)
        rows.append([
            RUNG[r], f3(a["prevalence"]),
            cell(len(sel_), sel_.AP.iloc[-1]) if len(sel_) else "—",
            cell(3, top3.AP.iloc[-1]),
            cell(s0["best_k_within_21"], s0["best_AP_within_21"]),
            cell(len(grp) and int(grp.n.iloc[1]), s0["AP_21_minus_non_contributors"]),
            cell(21, a["original21"]),
            cell(js.get("n_candidates", 88), a["all88"])])
    if not rows:
        return PENDING
    return md_table(["Outcome", "Prevalence", "Selected from the pool", "Best 3 of the 21",
                     "Best k of the 21", "21 minus non-contributors", "All 21", "Full pool"],
                    rows) + (
        "\n\nDevelopment AP, n → AP (share of the full pool's lift over prevalence). "
        "\"Best 3 / best k of the 21\" follow the greedy path within the 21; the selected "
        "sets and the path are chosen on these folds and so are optimistic -- the held-out "
        "table is the fair comparison.")


def t_path_within_21(cohort="full"):
    blocks = []
    for r, js in runs(cohort):
        path = csv(cohort, r, "forward_within_21.csv")
        if path is None:
            continue
        rows = [[p.step, lab(p.predictor), f3(p.AP), f4s(p.gain), f"{p.seeds_positive}/5",
                 pct(p.lift_share_of_88, 0)] for p in path.head(8).itertuples()]
        blocks.append(f"**{RUNG[r]}**\n\n" + md_table(
            ["Step", "Added", "AP", "Gain", "Splits", "Share of full-pool lift"], rows))
    return "\n\n".join(blocks) + (
        "\n\nThe first eight steps of the greedy path within the 21; the rest add nothing "
        "or lose AP.") if blocks else PENDING


# ------------------------------------------------- across the ANC ladder
def t_predictor_matrix(n=20):
    p = PV / "full" / "matrix.csv"
    if not p.exists():
        return PENDING
    m = pd.read_csv(p)
    wide = m.pivot(index="predictor", columns="rung", values="marginal_share")
    tier = m.pivot(index="predictor", columns="rung", values="tier").fillna("")
    in21 = m.groupby("predictor").in_21.first()
    rungs = [r for r in RUNGS if r in wide.columns]
    top = wide[rungs].max(axis=1).sort_values(ascending=False).head(n).index
    short = {"tier 1": " T1", "tier 2": " T2", "": ""}
    rows = []
    for c in top:
        cells = [f"{wide.loc[c, r] * 100:+.1f}%{short[tier.loc[c, r]]}" for r in rungs]
        shift = wide.loc[c, rungs[-1]] - wide.loc[c, rungs[0]]
        rows.append([lab(c), "yes" if in21[c] else "", *cells, f"{shift * 100:+.1f}"])
    return md_table(["Predictor", "In the 21", *[RUNG[r] for r in rungs],
                     f"Shift {RUNG[rungs[0]]} → {RUNG[rungs[-1]]} (pts)"], rows) + (
        "\n\nMarginal value relative to the 21-predictor set, as a share of each rung's "
        "ceiling (full-pool AP minus prevalence): for members of the 21 the AP lost when "
        "dropped from it, for the rest the AP gained when added to it. T1 / T2 = selected in "
        "tier 1 / tier 2 at that rung. The top predictors by their largest value on any rung.")


def t_ladder_patterns(n=10):
    p = LAD / "ladder_patterns.csv"
    if not p.exists():
        return PENDING
    d = pd.read_csv(p)
    blocks = []
    for kind, title in (("engagement-limited", "Matter more for completing the schedule"),
                        ("access-limited", "Matter more for reaching care at all")):
        sub = d[d.pattern == kind].reindex(
            d[d.pattern == kind].mean_share_shift.abs().sort_values(ascending=False).index).head(n)
        rows = [[lab(r.predictor), r.domain, f"{r.mean_share_shift:+.3f}",
                 f"{r.methods_agreeing}/{r.methods_total}"] for r in sub.itertuples()]
        blocks.append(f"**{title}**\n\n" + md_table(
            ["Predictor", "Domain", "Share shift ANC1+ → ANC8+", "Methods agreeing"], rows))
    return "\n\n".join(blocks)


def t_domain_rollup():
    p = LAD / "domain_rollup.csv"
    if not p.exists():
        return PENDING
    d = pd.read_csv(p).groupby("domain")[["anc1plus", "anc4plus", "anc8plus"]].mean()
    d["shift"] = d.anc8plus - d.anc1plus
    d = d.sort_values("anc8plus", ascending=False)
    rows = [[dom, pct(r.anc1plus, 0), pct(r.anc4plus, 0), pct(r.anc8plus, 0),
             f"{r['shift'] * 100:+.1f} pts"] for dom, r in d.iterrows()]
    return md_table(["Domain", "ANC1+", "ANC4+", "ANC8+", "Shift"], rows) + (
        "\n\nShare of total predictor importance within each outcome, averaged over "
        "EBM, SHAP and drop-one, with duplicate variables counted once.")


def t_method_agreement():
    p = LAD / "method_agreement.csv"
    if not p.exists():
        return PENDING
    d = pd.read_csv(p)
    rows = [[RUNG.get(r.rung, r.rung), f"{r.method_a} vs {r.method_b}",
             f"{r.spearman_predictor:.2f}", f"{r.spearman_domain:.2f}"] for r in d.itertuples()]
    return md_table(["Outcome", "Methods", "Rank agreement, predictors",
                     "Rank agreement, domains"], rows)


def t_ladder_performance():
    rows = []
    try:
        from anc8 import outcomes as oc
    except Exception:
        return PENDING
    for r in RUNGS:
        dp = ENH / r / "development_oof_performance.csv"
        hp = ENH / r / "heldout_performance.csv"
        if not (dp.exists() and hp.exists()):
            continue
        dev = pd.read_csv(dp).dropna(subset=["AP"]).sort_values("AP", ascending=False)
        held = pd.read_csv(hp)
        held = held[held.generation.astype(str).str.startswith("V2")].set_index("model")
        champ = next((m for m in dev.model if m in held.index), None)
        if champ is None:
            continue
        h = held.loc[champ]
        prev = oc.OUTCOMES[r]["weighted_prevalence"]
        rows.append([RUNG[r], pct(prev), champ, f3(h.AUROC), f3(h.AP), f"+{h.AP - prev:.3f}",
                     f"{(h.AP - prev) / (1 - prev):.2f}"])
    if not rows:
        return PENDING
    return md_table(["Rung", "Attain it", "Model (development champion)", "AUROC", "AP",
                     "AP lift", "Share of possible lift"], rows) + (
        "\n\nHeld-out women, full candidate pool. The model is the one ranked first on "
        "development folds, so the held-out set is not used to choose it. \"Share of possible "
        "lift\" is AP lift divided by its maximum (1 minus prevalence).")


# ------------------------------------------------------ the two horizons
def t_horizon_tiers():
    p = HOR / "tiers_by_horizon.csv"
    if not p.exists():
        return PENDING
    d = pd.read_csv(p)
    rows = []
    for r in ("anc4plus", "anc8plus"):
        for h in ("before ANC", "ANC entry"):
            s = d[(d.outcome == r) & (d.horizon == h)].sort_values("step")
            if not len(s):
                continue
            t1 = ", ".join(lab(x) for x in s[s.tier == "tier 1"].predictor)
            t2 = ", ".join(lab(x) for x in s[s.tier == "tier 2"].predictor) or "—"
            rows.append([RUNG[r], h, t1, t2, f3(s.prevalence.iloc[0]),
                         f3(s.set21_AP.iloc[0]), f3(s.all_pool_AP.iloc[0])])
    return md_table(["Outcome", "Horizon", "Tier 1", "Tier 2", "Prevalence",
                     "21-predictor set", "Full pool"], rows) + (
        "\n\nForward selection at each horizon, in order. Development AP; the ANC-entry "
        "pool adds the timing of the first contact.")


def t_early_anc():
    dp, bp = HOR / "early_anc_development.csv", HOR / "heldout_bootstrap.json"
    if not (dp.exists() and bp.exists()):
        return PENDING
    d = pd.read_csv(dp)
    boot = json.loads(bp.read_text())
    rows = []
    for x in d.itertuples():
        b = boot.get(f"{x.outcome} | {x.base} + early ANC vs {x.base}")
        rows.append([RUNG[x.outcome], x.base, f"{x.AP_without:.3f} → {x.AP_with:.3f}",
                     f"{x.gain:+.4f} ({x.seeds_positive}/5)", ci(b), ci(b, "AUROC")])
    return md_table(["Outcome", "Added to", "Development AP", "Development gain",
                     "Held-out ΔAP [95% CI]", "Held-out ΔAUROC [95% CI]"], rows) + (
        "\n\nWhat knowing that the first contact came by 3 months adds, among women who "
        "started ANC. Held-out: 984 women, paired stratified-PSU bootstrap.")


def t_cross_horizon():
    p, bp = HOR / "cross_horizon.csv", HOR / "heldout_bootstrap.json"
    if not (p.exists() and bp.exists()):
        return PENDING
    d = pd.read_csv(p)
    boot = json.loads(bp.read_text())
    rows = []
    for (r, s), g in d.groupby(["outcome", "set"], sort=False):
        g = g.set_index("trained_on")
        e, f = g.loc["ANC-entry development"], g.loc["full-cohort development"]
        b = boot.get(f"{r} | {s}: entry-trained vs full-cohort-trained")
        rows.append([RUNG[r], "21-predictor set" if s == "21" else "Full pool",
                     f"{f.AP:.3f} / {f.AUROC:.3f}", f"{e.AP:.3f} / {e.AUROC:.3f}",
                     ci(b), ci(b, "AUROC")])
    return md_table(["Outcome", "Set", "Trained before ANC: AP / AUROC",
                     "Trained at ANC entry: AP / AUROC", "ΔAP [95% CI]", "ΔAUROC [95% CI]"],
                    rows) + (
        "\n\nBoth scored on the same 984 held-out women who started ANC. Neither uses the "
        "timing of the first contact; the question is only whether fitting on the entry "
        "population itself changes the model.")


def t_entry_heldout():
    p = HOR / "heldout_entry.csv"
    if not p.exists():
        return PENDING
    d = pd.read_csv(p)
    rows = [[RUNG[x.outcome], x.set, "yes" if x.early_anc else "", x.n_predictors, f3(x.AP),
             f3(x.AUROC), f3(x.Calibration_slope)] for x in d.itertuples()]
    return md_table(["Outcome", "Set", "+ early ANC", "Predictors", "AP", "AUROC",
                     "Calibration slope"], rows)


# ------------------------------------------------------------ wartime
def t_wartime():
    p = WAR / "tigray_difference_in_differences.csv"
    if not p.exists():
        return PENDING
    d = pd.read_csv(p)
    m = d[(d.window_shift_months == 0) & (d.controls == "peaceful regions")].set_index("measure")
    names = {"never": "Received no antenatal care", "anc1plus": "Any ANC (ANC1+)",
             "anc4plus": "Four or more (ANC4+)", "four_lt8": "Reached 4, stopped before 8",
             "start_lt4": "Started, stopped before 4", "anc8plus": "Eight or more (ANC8+)"}
    rows = [[names[k], pct(m.loc[k, "tigray_during"]), pct(m.loc[k, "tigray_after"]),
             f"{m.loc[k, 'control_change_within_region'] * 100:+.1f}",
             f"**{m.loc[k, 'did'] * 100:+.1f}**",
             f"{m.loc[k, 'lo'] * 100:+.1f} to {m.loc[k, 'hi'] * 100:+.1f}"]
            for k in names if k in m.index]
    n1, n2 = int(m.tigray_during_n.iloc[0]), int(m.tigray_after_n.iloc[0])
    rob = d[d.measure == "anc4plus"]
    return md_table(["Tigray", f"Wartime pregnancy (n={n1})", f"Post-war pregnancy (n={n2})",
                     "Other regions, same periods (pts)", "Difference-in-differences (pts)",
                     "95% interval"], rows) + (
        f"\n\nRobustness: across window shifts of ±3 months and both comparison groups, the "
        f"ANC4+ effect ranges from {rob['did'].min() * 100:+.1f} to {rob['did'].max() * 100:+.1f} points.")


def t_tigray_regions():
    p = WAR / "region_by_war_period.csv"
    if not p.exists():
        return PENDING
    d = pd.read_csv(p)
    w = d.pivot(index="region", columns="period")
    order = (w[("anc4plus", "after")] - w[("anc4plus", "during")]).sort_values(ascending=False)
    rows = []
    for reg in order.index:
        r = w.loc[reg]
        name = f"**{reg}**" if reg == "Tigray" else reg
        rows.append([name, f"{int(r[('n', 'during')])} / {int(r[('n', 'after')])}"] + [
            f"{r[(m, 'during')] * 100:.0f} → {r[(m, 'after')] * 100:.0f}"
            for m in ("never", "anc1plus", "anc4plus", "anc8plus")] + [
            f"{(r[('anc4plus', 'after')] - r[('anc4plus', 'during')]) * 100:+.1f}"])
    return md_table(["Region", "n wartime / post-war", "No ANC (%)", "ANC1+ (%)", "ANC4+ (%)",
                     "ANC8+ (%)", "ANC4+ change (pts)"], rows) + (
        "\n\nEvery region over the same two calendar periods: pregnancies with at least 3 "
        "months inside the Tigray war window (Nov 2020 - Nov 2022), and pregnancies conceived "
        "after the ceasefire. Survey-weighted. Sorted by the ANC4+ change.")


def t_regional_gap():
    p = WAR / "regional_gap_by_cohort.csv"
    if not p.exists():
        return PENDING
    d = pd.read_csv(p)
    d = d[d.outcome == "anc8plus"].pivot(index="region", columns="cohort", values="gap")
    d = d.sort_values("full", ascending=False)
    rows = [[reg] + [f"{r[c] * 100:+.1f}" if c in r and not pd.isna(r[c]) else "—"
                     for c in ("full", "post-war pregnancies", "recent")]
            for reg, r in d.iterrows()]
    return md_table(["Region", "All births", "Post-war pregnancies only",
                     "Last 24 months (sensitivity)"], rows) + (
        "\n\nANC8+ attainment minus what the region's population profile implies (predicted "
        "with region withheld), percentage points.")


# ------------------------------------------------------- data and cohort
def t_cohort_validation():
    edhs = {"Tigray": 57.1, "Afar": 46.2, "Amhara": 62.0, "Oromia": 48.4, "Somali": 12.7,
            "Benishangul-Gumuz": 57.2, "Central Ethiopia": 58.5, "Sidama": 41.5,
            "South West Ethiopia": 48.1, "South Ethiopia": 47.1, "Gambella": 49.2,
            "Harari": 46.5, "Addis Ababa": 94.8, "Dire Dawa": 69.1}
    try:
        from anc8 import cohorts
        full, rec = cohorts.load("full"), cohorts.load("recent")
    except Exception as exc:
        return f"_Could not build the cohorts here ({type(exc).__name__})._"
    rows = []
    for reg in sorted(edhs):
        f = full[full.region.astype(str) == reg]
        r = rec[rec.region.astype(str) == reg]
        vf = np.average(f.anc4plus, weights=f.v005) * 100
        vr = np.average(r.anc4plus, weights=r.v005) * 100
        rows.append([reg, f"{edhs[reg]:.1f}", f"{vr:.1f}", f"{vr - edhs[reg]:+.1f}",
                     f"{vf:.1f}", f"{vf - edhs[reg]:+.1f}"])
    nf = np.average(full.anc4plus, weights=full.v005) * 100
    nr = np.average(rec.anc4plus, weights=rec.v005) * 100
    rows.append(["**National**", "53.0", f"{nr:.1f}", f"{nr - 53.0:+.1f}", f"{nf:.1f}",
                 f"{nf - 53.0:+.1f}"])
    return md_table(["Region", "EDHS report", "Last 24 months", "diff", "All births", "diff"],
                    rows) + ("\n\nANC4+ among women with a recent birth. EDHS figures: "
                             "2024-25 EDHS key indicators report, Table 9.")


def t_cohorts():
    try:
        from anc8 import cohorts
    except Exception:
        return PENDING
    rows = []
    for c, use in (("full", "Main analysis; horizon 1 (before ANC)"),
                   ("entry", "Horizon 2 (at ANC entry)"),
                   ("recent", "Sensitivity (DHS-8 24-month window)")):
        d = cohorts.load(c)
        w = (d.v005 / 1e6).to_numpy()
        part = d.partition.value_counts()
        rows.append([COHORT[c].split(" (")[0], len(d), int(part.get("development", 0)),
                     int(part.get("held-out", 0)),
                     pct(float(np.average(d.anc4plus, weights=w))),
                     pct(float(np.average(d.anc8plus, weights=w))), use])
    return md_table(["Cohort", "Women", "Development", "Held out", "ANC4+", "ANC8+", "Use"],
                    rows) + ("\n\nOne development / held-out split, drawn once by survey "
                             "cluster on the full cohort and restricted to each cohort.")


def t_recent_cascade():
    try:
        from anc8 import cohorts
    except Exception:
        return PENDING
    rows = []
    for name, c in (("All births", "full"), ("Last 24 months", "recent")):
        d = cohorts.load(c)
        n = d.anc_contacts.fillna(0).to_numpy()
        w = (d.v005 / 1e6).to_numpy()
        st, f4 = n >= 1, n >= 4
        wm = lambda x, ww=w: float(np.average(x, weights=ww))
        rows.append([name, len(d), pct(wm(n >= 1)), pct(wm(n >= 4)), pct(wm(n >= 8)),
                     pct(float(np.average(n[st] >= 4, weights=w[st])), 0),
                     pct(float(np.average(n[f4] >= 8, weights=w[f4])), 0)])
    return md_table(["Window", "Women", "ANC1+", "ANC4+", "ANC8+", "Starters reaching 4",
                     "Those at 4 reaching 8"], rows)


# ------------------------------------------------ from 6,648 columns to a set
def _module(v: str) -> str:
    import re as _re
    for pat, name in ((r"^v4", "breastfeeding, nutrition and child health (after the birth)"),
                      (r"^v3", "contraception (measured at interview)"),
                      (r"^(b\d|bidx|bord)", "other children's birth history"),
                      (r"^(p\d|pidx|pord)", "pregnancy-history index columns"),
                      (r"^v8", "HIV/AIDS knowledge"),
                      (r"^mm", "sibling mortality"),
                      (r"^v2", "reproductive counts and history"),
                      (r"^v5", "marriage and sexual activity"),
                      (r"^v6", "fertility preferences"),
                      (r"^v7", "partner, work and empowerment"),
                      (r"^v[01]", "respondent and household")):
        if _re.match(pat, v):
            return name
    return "other modules"


def t_funnel():
    scr = ENH / "candidate_screening.csv"
    reg = ENH / "predictor_register_v2.csv"
    spec = ENH / "feature_spec_v2.json"
    if not (scr.exists() and reg.exists() and spec.exists()):
        return PENDING
    d = pd.read_csv(scr)
    r = pd.read_csv(reg)
    refused = set(json.loads(spec.read_text())["temporal_exclusions"])
    reason = d.exclusion_reason.fillna("")
    groups = [
        ("Not collected in this survey round", reason.str.startswith("not collected")),
        ("Entirely missing in the cohort", reason.str.startswith("entirely missing")),
        ("Measured at or after the delivery (leakage by design)",
         reason.str.contains("measured at or after delivery")),
        ("Survey design or administrative", reason.str.contains("administrative")),
        ("Observed for under half the cohort", reason.str.startswith("observed for only")),
    ]
    rows, used = [], pd.Series(False, index=d.index)
    for name, m in groups:
        m = m & ~used
        used |= m
        rows.append([name, f"{int(m.sum()):,}", "—"])
    cand = d.screen_status == "candidate"
    other = ~used & ~cand
    if other.any():
        rows.append(["Other automated exclusions", f"{int(other.sum()):,}", "—"])
    c = d[cand]
    admitted = set(r[r.provenance == "Newly admitted EDHS source variable"].final_variable)
    n_ref = int(c.variable.isin(refused).sum())
    rest = c[~c.variable.isin(admitted) & ~c.variable.isin(refused)]
    mods = rest.variable.map(_module).value_counts()
    top = ", ".join(f"{k} {v}" for k, v in mods.head(5).items())
    rows += [
        ["**Rankable candidates** (at least half the cohort observed)", f"**{int(cand.sum()):,}**", ""],
        ["Refused on timing: they record the care itself or life after it", str(n_ref),
         "e.g. facility visit in the last 12 months, HIV testing, contraception"],
        ["Not admitted: no plausible link before the pregnancy, or near-zero signal",
         f"{len(rest):,}", f"median univariate AUC {rest.weighted_auc.median():.3f}; {top}"],
        ["**Admitted survey variables**", f"**{len(admitted)}**", ""],
        ["+ constructs of the 21-predictor set, and derived measures",
         str(int((r.provenance != 'Newly admitted EDHS source variable').sum())),
         "e.g. log travel times, separate media channels, spousal gaps"],
        ["**Full candidate pool (columns)**", f"**{len(r)}**", ""],
        ["Distinct variables once copies are merged", "85", "10 columns were the same variable twice"],
        ["**Predictor-value study pool**", "**88**",
         "the 85 plus three constructs only the 21-predictor set had"],
    ]
    return md_table(["Step", "Columns", "Note"], rows) + (
        f"\n\nFrom the {len(d):,} columns of the Individual Recode to the pool the "
        "predictor-value study selects from. The automated rows are exclusive, applied "
        "top to bottom.")


def t_ablation(cohort="full"):
    """Every predictor set tried, development and held-out, per rung."""
    blocks = []
    for r, js in runs(cohort):
        a = js["anchors"]
        s0 = js.get("stage0") or {}
        h = csv(cohort, r, "why21_heldout.csv")
        steps = csv(cohort, r, "forward_steps.csv")
        path = csv(cohort, r, "forward_within_21.csv")
        held = csv(cohort, r, "heldout.csv")
        if h is None or steps is None or path is None:
            continue
        bp = FV / cohort / r / "why21_bootstrap.json"
        boot = json.loads(bp.read_text()) if bp.exists() else {}
        hb = FV / cohort / r / "heldout_bootstrap.json"
        hboot = json.loads(hb.read_text()) if hb.exists() else {}
        h = h.set_index("set")
        sel_ = steps[steps.tier.isin(["tier 1", "tier 2"])]
        t1 = steps[steps.tier == "tier 1"]
        k = s0.get("best_k_within_21")
        prev = float(h.prevalence.iloc[0])
        rows = []

        def row(name, n, dev, hap, hauc, b):
            rows.append([name, n, f3(dev), f"{lift_share(dev, js) * 100:.0f}%" if dev is not None else "—",
                         f3(hap), f3(hauc), ci(b) if b else ("reference" if b is None else "—"),
                         ci(b, "AUROC") if b else ""])

        if len(t1) and held is not None:
            lr = held[(held.model == "Logistic regression") & (held.set == "tier 1")]
            if len(lr):
                row("Tier 1 (selected from the pool)", len(t1), float(t1.AP.iloc[-1]),
                    float(lr.AP.iloc[0]), float(lr.AUROC.iloc[0]),
                    hboot.get("Logistic regression | tier 1 vs original 21", {}))
        if "selected from the pool" in h.index and len(sel_) > len(t1):
            x = h.loc["selected from the pool"]
            row("Tier 1+2 (selected from the pool)", int(x.n_predictors), float(sel_.AP.iloc[-1]),
                x.AP, x.AUROC, boot.get("selected from the pool", {}))
        name_k = f"best {k} of the 21"
        if name_k in h.index:
            x = h.loc[name_k]
            row(f"Best {k} of the 21", int(x.n_predictors), s0["best_AP_within_21"], x.AP,
                x.AUROC, boot.get(name_k, {}))
        if "21 minus non-contributors" in h.index:
            x = h.loc["21 minus non-contributors"]
            row("The 21 minus its non-contributors", int(x.n_predictors),
                s0["AP_21_minus_non_contributors"], x.AP, x.AUROC,
                boot.get("21 minus non-contributors", {}))
        x = h.loc["21-predictor set"]
        rows.append(["**The 21-predictor set**", 21, f3(a["original21"]),
                     f"{lift_share(a['original21'], js) * 100:.0f}%", f3(x.AP), f3(x.AUROC),
                     "reference", ""])
        x = h.loc["full pool"]
        row("Full pool", int(x.n_predictors), a["all88"], x.AP, x.AUROC,
            boot.get("full pool", {}))
        blocks.append(f"**{RUNG[r]}** (held-out prevalence {prev:.3f})\n\n" + md_table(
            ["Set", "Predictors", "Development AP", "Share of pool's lift", "Held-out AP",
             "Held-out AUROC", "ΔAP vs the 21 [95%]", "ΔAUROC vs the 21 [95%]"], rows))
    if not blocks:
        return PENDING
    return "\n\n".join(blocks) + (
        "\n\nLogistic regression throughout, each set at the regularisation it earned on "
        "development folds. Development scores of the searched sets (the tiers and the "
        "reduced 21) are optimistic, because they were chosen on those folds; the held-out "
        "columns are the fair comparison. Intervals: paired stratified-PSU bootstrap on the "
        "held-out women.")


TABLES = {
    "funnel": t_funnel,
    "ablation": t_ablation,
    "why21": t_why21, "drop_within_21": t_drop_within_21, "path_within_21": t_path_within_21,
    "predictor_matrix": t_predictor_matrix, "ladder_patterns": t_ladder_patterns,
    "domain_rollup": t_domain_rollup, "method_agreement": t_method_agreement,
    "ladder_performance": t_ladder_performance,
    "horizon_tiers": t_horizon_tiers, "early_anc": t_early_anc,
    "cross_horizon": t_cross_horizon, "entry_heldout": t_entry_heldout,
    "wartime": t_wartime, "tigray_regions": t_tigray_regions, "regional_gap": t_regional_gap,
    "cohort_validation": t_cohort_validation, "cohorts": t_cohorts,
    "recent_cascade": t_recent_cascade,
}
for _c, _sfx in (("full", ""), ("entry", "_entry"), ("recent", "_recent")):
    for _name, _fn in (("sets_dev", t_sets_dev), ("sets_heldout", t_sets_heldout),
                       ("tiers", t_tiers), ("add_one", t_add_one),
                       ("top_additions", t_top_additions), ("placement", t_placement)):
        TABLES[_name + _sfx] = (lambda f=_fn, c=_c: f(c))


def main():
    cache = {}
    pattern = re.compile(r"(<!-- AUTO:(\w+) -->)(.*?)(<!-- /AUTO:\2 -->)", re.S)
    unknown = set()
    for doc in DOCS:
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8")

        def fill(m):
            name = m.group(2)
            if name not in TABLES:
                unknown.add(name)
                return m.group(0)
            if name not in cache:
                cache[name] = TABLES[name]()
            return f"{m.group(1)}\n{cache[name]}\n{m.group(4)}"

        new, n = pattern.subn(fill, text)
        if n:
            doc.write_text(new, encoding="utf-8")
            print(f"  {doc.relative_to(ROOT)}: {n} table(s)")
    if unknown:
        print(f"  unknown table names left untouched: {sorted(unknown)}")
    print("predictor-value runs: " + ", ".join(
        f"{c} {len(runs(c))}/{3 if c != 'entry' else 2}" for c in ("full", "entry", "recent")))


if __name__ == "__main__":
    main()
