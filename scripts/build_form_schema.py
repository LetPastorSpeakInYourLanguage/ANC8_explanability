"""Generate the web form schema from the model bundles and predictor registers.

The form is derived from what the models actually expect rather than hand-written,
so a field cannot silently drift away from the feature it feeds. Option lists come
straight from the fitted encoders' category lists.

Run after the bundles exist:
    python scripts/build_form_schema.py

Writes app/public/form_schema.json -- every deployed model with the outcome and
horizon it predicts, its held-out AP and AUROC and the questions it asks -- and
app/public/browser_models.json, the additive models (explainable boosting and
logistic regression) that the Predict tab scores in the browser.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "app" / "models"
ENHANCED = ROOT / "outputs" / "enhanced"

# Human-readable labels and help text. Anything not listed falls back to the
# register description, so an unlabelled field is still usable.
LABELS = {
    "v012": ("Mother's age", "Age in completed years at interview", "years"),
    "v133": ("Mother's years of education", "Total completed years of schooling", "years"),
    "v715": ("Partner's years of education", "Total completed years of schooling", "years"),
    "v730": ("Partner's age", "Age in completed years", "years"),
    "v191": ("Household wealth score", "DHS wealth index factor score", ""),
    "v191a": ("Household wealth score (urban/rural)", "Urban/rural-specific wealth score", ""),
    "household_size": ("Household size", "Number of people living in the household", "people"),
    "v136": ("Household size", "Number of people listed in the household", "people"),
    "v137": ("Children under 5 in household", "", "children"),
    "v138": ("Eligible women in household", "", "women"),
    "v152": ("Age of household head", "", "years"),
    "v115": ("Time to water source", "One-way travel time", "minutes"),
    "v201": ("Total children ever born", "", "children"),
    "v212": ("Age at first birth", "", "years"),
    "v218": ("Number of living children", "", "children"),
    "v511": ("Age at first marriage/union", "", "years"),
    "v613": ("Ideal number of children", "Number the respondent considers ideal", "children"),
    "s1101": ("Travel time to hospital / health centre", "One-way travel time", "minutes"),
    "s1101b": ("Travel time to nearest health post", "Leave blank if there is none nearby", "minutes"),
    "travel_time_min": ("Travel time to hospital / health centre", "One-way travel time", "minutes"),
    "traditional_media_weekly_count": (
        "Traditional media accessed weekly",
        "Count of newspaper, radio and television accessed at least weekly (0-3)",
        "",
    ),
    "early_anc": (
        "First ANC contact in the first trimester",
        "1 if the first antenatal contact was at or before 12 weeks / 3 months",
        "",
    ),
}

# Ordered value labels for DHS coded variables, so the form shows meaning
# rather than raw integer codes.
CODED = {
    "v106": {"0": "No education", "1": "Primary", "2": "Secondary", "3": "Higher"},
    "v155": {"0": "Cannot read at all", "1": "Able to read only parts of sentence",
             "2": "Able to read whole sentence", "3": "No card with required language",
             "4": "Blind / visually impaired"},
    "v157": {"0": "Not at all", "1": "Less than once a week", "2": "At least once a week"},
    "v158": {"0": "Not at all", "1": "Less than once a week", "2": "At least once a week"},
    "v159": {"0": "Not at all", "1": "Less than once a week", "2": "At least once a week"},
    "v171a": {"0": "Never used", "1": "Used in last 12 months", "2": "Used before last 12 months"},
    "v190": {"1": "Poorest", "2": "Poorer", "3": "Middle", "4": "Richer", "5": "Richest"},
    "v190a": {"1": "Poorest", "2": "Poorer", "3": "Middle", "4": "Richer", "5": "Richest"},
    "v025": {"1": "Urban", "2": "Rural"},
    "v130": {"1": "Orthodox", "2": "Catholic", "3": "Protestant", "4": "Muslim",
             "5": "Traditional", "96": "Other"},
    "v024": {"1": "Tigray", "2": "Afar", "3": "Amhara", "4": "Oromia", "5": "Somali",
             "6": "Benishangul-Gumuz", "7": "Central Ethiopia", "8": "Sidama",
             "9": "South West Ethiopia", "10": "South Ethiopia", "12": "Gambella",
             "13": "Harari", "14": "Addis Ababa", "15": "Dire Dawa"},
    "v151": {"1": "Male", "2": "Female"},
    "v119": {"0": "No", "1": "Yes"},
    "v120": {"0": "No", "1": "Yes"},
    "v121": {"0": "No", "1": "Yes"},
    "v123": {"0": "No", "1": "Yes"},
    "v169a": {"0": "No", "1": "Yes"},
    "v170": {"0": "No", "1": "Yes"},
    "v481": {"0": "No", "1": "Yes"},
    "v731": {"0": "No", "1": "Yes"},
    "v467b": {"1": "Big problem", "2": "Not a big problem"},
    "v467c": {"1": "Big problem", "2": "Not a big problem"},
    "v467d": {"1": "Big problem", "2": "Not a big problem"},
    "v467f": {"1": "Big problem", "2": "Not a big problem"},
    "v744a": {"0": "No", "1": "Yes", "8": "Don't know"},
    "v744b": {"0": "No", "1": "Yes", "8": "Don't know"},
    "v744c": {"0": "No", "1": "Yes", "8": "Don't know"},
    "v744d": {"0": "No", "1": "Yes", "8": "Don't know"},
    "v744e": {"0": "No", "1": "Yes", "8": "Don't know"},
    "v745a": {"0": "Does not own", "1": "Alone only", "2": "Jointly only",
              "3": "Both alone and jointly"},
    "v745b": {"0": "Does not own", "1": "Alone only", "2": "Jointly only",
              "3": "Both alone and jointly"},
}

DOMAIN_ORDER = [
    "Maternal and sociodemographic",
    "Household and socioeconomic",
    "Geographic",
    "Partner and empowerment",
    "Pregnancy and obstetric",
    "Health service and access",
    "Other",
]


def load(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def field_for(name, spec, register_row):
    """Build one form field from what the model expects."""
    label, helptext, unit = LABELS.get(name, (None, "", ""))
    if label is None:
        desc = register_row["description"] if register_row is not None else name
        label = str(desc)[:70]

    numeric = name in spec.get("numeric", [])
    field = {
        "name": name,
        "label": label,
        "help": helptext,
        "unit": unit,
        "domain": (register_row or {}).get("domain", "Other"),
    }

    if numeric:
        field["type"] = "number"
        field["default"] = spec["numeric_impute"].get(name)
        return field

    cats = spec["categories"].get(name, [])
    field["type"] = "select"
    coded = CODED.get(name)
    field["options"] = [
        {"value": c, "label": (coded.get(str(c).replace(".0", ""), c) if coded else c)}
        for c in cats
    ]
    field["default"] = (
        spec.get("categorical_impute", {}).get(name)
        or spec.get("binary_impute", {}).get(name)
    )
    return field


OUTCOMES = {"anc1plus": "ANC1+", "anc4plus": "ANC4+", "anc8plus": "ANC8+"}
HORIZONS = {"before": "Before ANC starts", "entry": "At the first ANC visit"}

# Which model the study points to for each outcome and horizon (FINDINGS.md,
# docs/PREDICTOR_VALUE.md, docs/HORIZONS.md). For ANC8+, and for both rungs
# at ANC entry, a small set does as well as the larger ones, so the small
# logistic model is the recommendation; for ANC1+ and ANC4+ before ANC the
# full pool beats the 21, so the full pool's headline model is.
RECOMMENDED = {
    ("anc1plus", "before"): ("pool_anc1plus", None),
    ("anc4plus", "before"): ("pool_anc4plus", None),
    ("anc8plus", "before"): ("small", "anc8plus · before · "),
    ("anc4plus", "entry"): ("small", "anc4plus · entry · "),
    ("anc8plus", "entry"): ("small", "anc8plus · entry · "),
}

# Additive models are scored in the browser, so they respond as answers change
# and their contributions are exact; everything else goes to the service.
BROWSER_KINDS = {"ebm", "logistic"}


def bundle_fields(pre):
    return (pre["numeric"] + pre.get("binary", []) + pre["categorical"]
            + pre.get("extra", []))


def main():
    reg1 = pd.read_csv(ROOT / "outputs" / "ANC8_predictor_register_final.csv")
    reg2 = pd.read_csv(ENHANCED / "predictor_register_v2.csv")
    register = {r.final_variable: {"domain": r.domain, "description": r.description}
                for r in reg2.itertuples()}
    register.update({r.final_variable: {"domain": r.domain, "description": r.construct}
                     for r in reg1.itertuples()})

    held = {o: pd.read_csv(ENHANCED / o / "heldout_performance.csv") for o in OUTCOMES}
    t1 = pd.read_csv(ROOT / "outputs/publication_results/main_tables"
                            "/Table_1_full_cohort_heldout_performance.csv").set_index("Model")
    t2 = pd.read_csv(ROOT / "outputs/publication_results/main_tables"
                            "/Table_2_anc_entry_probability_performance.csv").set_index("Algorithm")
    insights = json.loads((ROOT / "app" / "public" / "insights.json").read_text(encoding="utf-8"))

    fields, models = {}, []
    browser = {"preprocessors": {}, "models": {}}
    prevalence = {(o, "before"): insights["outcomes"][o]["weighted_prevalence"]
                  for o in OUTCOMES if o in insights.get("outcomes", {})}

    def add(bundle_key, bundle, name, *, outcome, horizon, set_label, algorithm,
            ap, auroc, predictors=None, note=""):
        m = bundle["models"][name]
        pre = bundle["preprocessors"][m["preprocessor"]]
        asked = bundle_fields(pre)
        for n in asked:
            if n not in fields:
                f = field_for(n, pre, register.get(n))
                if n == "early_anc":
                    f["type"] = "select"
                    f["options"] = [
                        {"value": "0", "label": "No -- first contact after 12 weeks"},
                        {"value": "1", "label": "Yes -- first contact at or before 12 weeks"}]
                    f["domain"] = "Health service and access"
                    f["default"] = None
                fields[n] = f
        mid = f"{bundle_key}::{name}"
        rec = RECOMMENDED.get((outcome, horizon))
        recommended = bool(rec) and rec[0] == bundle_key and (
            name.startswith(rec[1]) if rec[1] else name == bundle.get("champion"))
        in_browser = m["kind"] in BROWSER_KINDS
        if in_browser:
            browser["preprocessors"][mid] = pre
            browser["models"][mid] = {**m, "preprocessor": mid}
        models.append({
            "id": mid, "bundle": bundle_key, "model": name,
            "outcome": outcome, "horizon": horizon,
            "set": set_label, "algorithm": algorithm,
            "n_predictors": len(predictors or asked), "fields": asked,
            "heldout_AP": None if ap is None or pd.isna(ap) else float(ap),
            "heldout_AUROC": None if auroc is None or pd.isna(auroc) else float(auroc),
            "threshold": m.get("threshold"),
            "browser": in_browser, "recommended": recommended,
            "headline": name == bundle.get("champion"),
            "note": note,
        })

    # ---- the 21-predictor models -----------------------------------------
    v1 = load(MODELS / "v1_bundle.json.gz")
    for name in v1["models"]:
        r = t1.loc[name]
        add("v1", v1, name, outcome="anc8plus", horizon="before",
            set_label="21 predictors", algorithm=name,
            ap=r.Weighted_AP, auroc=r.Weighted_AUROC)
    ve = load(MODELS / "v1_anc_entry_bundle.json.gz")
    for name in ve["models"]:
        algo, spec = name.rsplit(" (", 1)
        spec = spec.rstrip(")")
        r = t2.loc[algo]
        add("v1_anc_entry", ve, name, outcome="anc8plus", horizon="entry",
            set_label="21 predictors" + (" + early ANC" if spec == "Extended" else ""),
            algorithm=algo, ap=r[f"{spec}_Weighted_AP"],
            auroc=r[f"{spec}_Weighted_AUROC"])

    # ---- the full-pool models, one bundle per outcome -----------------------
    not_deployed = {}
    for outcome, key in (("anc1plus", "pool_anc1plus"), ("anc4plus", "pool_anc4plus"),
                         ("anc8plus", "v2")):
        path = MODELS / f"{key}_bundle.json.gz"
        if not path.exists():
            continue
        b = load(path)
        h = held[outcome]
        h = h[~h.generation.astype(str).str.startswith("V1")].set_index("model")
        for name in b["models"]:
            add(key, b, name, outcome=outcome, horizon="before",
                set_label="Full pool", algorithm=name,
                ap=h.AP.get(name), auroc=h.AUROC.get(name),
                note=("a short list of the full pool's strongest predictors"
                      if name == "Parsimonious" else ""))
        if b.get("not_deployed"):
            not_deployed[outcome] = b["not_deployed"]

    # ---- the study's best small sets ---------------------------------------
    small_path = MODELS / "small_bundle.json.gz"
    if small_path.exists():
        sb = load(small_path)
        for c in sb["catalog"]:
            label = c["set"]
            label = ("Best " + label.removeprefix("best ")) if label.startswith("best ") \
                else label[0].upper() + label[1:]
            add("small", sb, c["model"], outcome=c["outcome"], horizon=c["horizon"],
                set_label=label, algorithm="Logistic regression",
                ap=c["heldout_AP"], auroc=c["heldout_AUROC"],
                predictors=c["predictors"])
            prevalence.setdefault((c["outcome"], c["horizon"]), c["prevalence"])

    order = {k: i for i, k in enumerate(DOMAIN_ORDER)}
    ordered = sorted(fields.values(),
                     key=lambda f: (order.get(f["domain"], len(DOMAIN_ORDER)), f["label"]))

    schema = {
        "outcomes": OUTCOMES,
        "horizons": HORIZONS,
        "prevalence": {f"{o}|{h}": p for (o, h), p in prevalence.items()},
        "fields": ordered,
        "models": models,
        "not_deployed": not_deployed,
    }
    out = ROOT / "app" / "public" / "form_schema.json"
    out.write_text(json.dumps(schema, indent=1, ensure_ascii=False), encoding="utf-8")
    bout = ROOT / "app" / "public" / "browser_models.json"
    bout.write_text(json.dumps(browser, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out}: {len(ordered)} fields, {len(models)} models")
    print(f"wrote {bout}: {len(browser['models'])} models scored in the browser "
          f"({bout.stat().st_size / 1024:.0f} KB)")
    for m in models:
        ap = m["heldout_AP"]
        print(f"  {m['outcome']:8s} {m['horizon']:6s} {m['set']:28s} {m['algorithm']:22s} "
              f"AP {'  -  ' if ap is None else f'{ap:.3f}'}"
              f"{'  browser' if m['browser'] else ''}"
              f"{'  RECOMMENDED' if m['recommended'] else ''}")

if __name__ == "__main__":
    main()
