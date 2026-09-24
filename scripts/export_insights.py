"""Export the explainability artifacts the web app consumes.

    python scripts/export_insights.py

Writes to app/public/. Everything here is derived from the frozen analysis
artifacts, so the app cannot show a number the analysis did not produce.

  insights.json   global importance per rung, the ladder comparison, domain
                  roll-up, fitted shape functions, and sensible slider ranges
  examples.json   one synthetic typical profile with its exact decomposition
"""

from __future__ import annotations

import gzip
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app" / "api" / "_lib"))

from anc8 import design, ladder, outcomes  # noqa: E402

ENHANCED = ROOT / "outputs" / "enhanced"
LADDER_DIR = ROOT / "outputs" / "ladder"
PUBLIC = ROOT / "app" / "public"

# How many predictors the what-if view offers. Enough to explore, few enough
# that the page stays legible.
N_SLIDERS = 14


def load_bundle():
    with gzip.open(ROOT / "app" / "models" / "v2_bundle.json.gz", "rt",
                   encoding="utf-8") as fh:
        return json.load(fh)


def shape_functions(bundle, model_name):
    """The fitted response curve for every predictor of the additive model.

    This is what makes a slider informative rather than decorative: the user
    sees the shape the model learned across the whole range, not just the value
    they happen to have selected.
    """
    model = bundle["models"][model_name]
    spec = bundle["preprocessors"][model["preprocessor"]]
    names = (spec["numeric"] + spec.get("binary", [])
             + spec["categorical"] + spec.get("extra", []))
    categories = spec.get("categories", {})

    out = {}
    for term in model["terms"]:
        f = term["feature"]
        if f >= len(names):
            continue
        name = names[f]
        scores = term["scores"]

        if term["kind"] == "nominal":
            mapping = term.get("mapping", {})
            out[name] = {
                "kind": "nominal",
                "values": list(mapping),
                "scores": [scores[min(i, len(scores) - 1)] for i in mapping.values()],
            }
            continue

        # A continuous term with C cut points has C+1 real bins, and the score
        # table carries two extra entries around them: index 0 is the missing
        # bin and the last is "unseen". Bin i therefore lives at scores[i+1],
        # for i in 0..C -- taking only 0..C-1 would silently drop the topmost
        # bin, which for an ordinal-coded categorical is a whole level.
        cuts = list(term.get("cuts", []))
        bins = [scores[min(i + 1, len(scores) - 1)] for i in range(len(cuts) + 1)]

        # Categoricals reach the additive model as integer codes, so their
        # "cuts" are just 0.5, 1.5, ... Reporting them as a step function over
        # those codes is unreadable; with the encoder's own level names it
        # becomes a bar per level.
        levels = list(categories.get(name, []))
        if name in spec.get("categorical", []) and len(levels) == len(bins):
            out[name] = {"kind": "nominal", "values": levels, "scores": bins}
            continue

        out[name] = {
            "kind": "continuous",
            "cuts": cuts,
            "scores": bins,
            "range": [float(min(cuts)), float(max(cuts))] if cuts else None,
        }
    return out, names


def observed_ranges(held, names, spec):
    """Slider bounds taken from what was actually observed.

    Letting a slider run past the data would invite extrapolation the model
    cannot support -- the shape function is flat outside its bins, so the UI
    would imply a confident prediction where there is no evidence.
    """
    ranges = {}
    for n in names:
        if n not in held.columns:
            continue
        if n in spec["numeric"]:
            v = pd.to_numeric(held[n], errors="coerce").dropna()
            if len(v):
                ranges[n] = {
                    "kind": "continuous",
                    "min": float(v.min()), "max": float(v.max()),
                    "median": float(v.median()),
                    "p05": float(v.quantile(0.05)), "p95": float(v.quantile(0.95)),
                }
        else:
            cats = spec["categories"].get(n, [])
            ranges[n] = {"kind": "categorical", "options": list(cats)}
    return ranges


def main():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    bundle = load_bundle()

    model_name = "Explainable Boosting"
    if model_name not in bundle["models"]:
        print("the additive model is not in the bundle; run export_serving.py --v2")
        sys.exit(1)

    shapes, names = shape_functions(bundle, model_name)
    spec = bundle["preprocessors"][bundle["models"][model_name]["preprocessor"]]

    df = pd.read_pickle(ENHANCED / "ANC8_analysis_frozen_v2.pkl")
    _, test_psus = design.make_psu_holdout(df)
    held = df[df.v021.isin(test_psus)].reset_index(drop=True)

    insights = {
        "model": model_name,
        "outcomes": {o: outcomes.OUTCOMES[o] for o in outcomes.LADDER},
        "shape_functions": shapes,
        "ranges": observed_ranges(held, names, spec),
        "domains": {p: ladder.domain_of(p) for p in names},
    }

    # ---- global importance, per rung ---------------------------------------
    # Mean |contribution| across held-out women: how much each predictor
    # actually moves predictions in this population.
    import scorer

    X = held[spec["numeric"] + spec["categorical"]].copy()
    for c in spec["categorical"]:
        X[c] = X[c].astype(str)
    rows = X.astype(object).where(pd.notna(X), None).to_dict("records")

    # Every term for every woman. `scorer.predict` truncates its contribution
    # list to the top few per row for display; averaging over THAT would rank a
    # rare indicator with an occasional huge value above a predictor that moves
    # every prediction a little, because the latter's small contributions never
    # make the cut. Global importance has to see the whole matrix.
    model = bundle["models"][model_name]
    contrib_sum = {}
    for r in rows:
        x = scorer.apply_preprocessor(spec, r)
        for term in model["terms"]:
            f = term["feature"]
            if f >= len(names):
                continue
            c = abs(scorer._ebm_term_contribution(term, x))
            contrib_sum[names[f]] = contrib_sum.get(names[f], 0.0) + c
    global_imp = {k: v / len(rows) for k, v in contrib_sum.items()}

    # Direction: does a higher value push towards or away from attainment?
    #
    # Only meaningful where the values are ordered. A categorical predictor
    # reaches the model as an arbitrary integer code, so "higher increases"
    # would be an artefact of alphabetical ordering; for those, name the levels
    # at each end of the fitted effect instead.
    direction = {}
    extremes = {}
    for n, sh in shapes.items():
        s = np.asarray(sh["scores"], dtype=float)
        if len(s) < 2:
            continue
        if sh["kind"] == "nominal":
            vals = sh.get("values") or []
            direction[n] = "varies by level"
            if len(vals) == len(s):
                extremes[n] = {"raises_most": str(vals[int(np.argmax(s))]),
                               "lowers_most": str(vals[int(np.argmin(s))])}
        else:
            # Sign of the trend across bins, not just the two endpoints: a
            # step function can end lower than it starts while rising over
            # almost all of its range.
            idx = np.arange(len(s))
            slope = float(np.polyfit(idx, s, 1)[0])
            direction[n] = "higher increases" if slope > 0 else "higher decreases"

    insights["global_importance"] = (
        pd.Series(global_imp).sort_values(ascending=False).to_dict()
    )
    insights["direction"] = direction
    insights["level_extremes"] = extremes
    insights["top_predictors"] = list(
        pd.Series(global_imp).sort_values(ascending=False).head(N_SLIDERS).index
    )

    # ---- the ladder comparison, when it exists -----------------------------
    patterns_path = LADDER_DIR / "ladder_patterns.csv"
    if patterns_path.exists():
        pat = pd.read_csv(patterns_path)
        insights["ladder_patterns"] = pat.to_dict("records")

        roll = pd.read_csv(LADDER_DIR / "domain_rollup.csv", index_col=0)
        rungs = [r for r in outcomes.LADDER if r in roll.columns]
        insights["domain_rollup"] = (
            roll.groupby(level=0)[rungs].mean().to_dict("index")
        )

        perf = pd.read_csv(LADDER_DIR / "ladder_performance.csv")
        insights["ladder_performance"] = perf.to_dict("records")
    else:
        insights["ladder_patterns"] = []
        print("  (ladder analysis not run yet -- app will hide that view)")

    (PUBLIC / "insights.json").write_text(json.dumps(insights, indent=1),
                                          encoding="utf-8")

    # ---- the browser's copy of the model -----------------------------------
    # Only the additive model and its preprocessor: 82 KB raw against 11 MB for
    # the full bundle, because the tree models carry every split of every tree.
    # This is what makes the what-if view instant -- it never calls the API.
    ebm_only = {
        "generation": bundle["generation"],
        "predictors": bundle["predictors"],
        "preprocessors": {k: v for k, v in bundle["preprocessors"].items()
                          if k.startswith(model_name)},
        "models": {k: v for k, v in bundle["models"].items()
                   if v.get("kind") == "ebm"},
    }
    (PUBLIC / "ebm_bundle.json").write_text(json.dumps(ebm_only),
                                            encoding="utf-8")
    kb = (PUBLIC / "ebm_bundle.json").stat().st_size / 1024
    print(f"wrote {PUBLIC / 'ebm_bundle.json'} ({kb:.0f} KB, served to the browser)")

    # ---- worked example ------------------------------------------------------
    # One SYNTHETIC profile -- every predictor at its median (numeric) or most
    # common level (categorical) among held-out women -- so the what-if view has
    # a concrete starting point. It is not any real woman: survey records are
    # not redistributable, and the app is published.
    typical = {}
    for c in spec["numeric"]:
        v = pd.to_numeric(X[c], errors="coerce").median()
        typical[c] = None if pd.isna(v) else str(float(v))
    for c in spec["categorical"]:
        m = X[c].dropna().mode()
        typical[c] = None if m.empty else str(m.iloc[0])
    s = scorer.predict(bundle, model_name, typical)
    examples = [{
        "label": "typical",
        "synthetic": True,
        "answers": typical,
        "probability": s["probability"],
        "contributions": s["contributions"],
        "observed": {},
    }]
    (PUBLIC / "examples.json").write_text(json.dumps(examples, indent=1),
                                          encoding="utf-8")

    print(f"wrote {PUBLIC / 'insights.json'}")
    print(f"  {len(shapes)} shape functions, {len(insights['top_predictors'])} sliders")
    print(f"  ladder patterns: {len(insights['ladder_patterns'])}")
    print(f"wrote {PUBLIC / 'examples.json'} (1 synthetic profile)")
    print("\nTOP 15 PREDICTORS (mean |log-odds contribution|, held-out)")
    for k, v in list(insights["global_importance"].items())[:15]:
        print(f"  {k:34s} {v:.4f}   {direction.get(k, '')}")


if __name__ == "__main__":
    main()
