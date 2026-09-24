"""Generate the web form schema from the model bundles and predictor registers.

The form is derived from what the models actually expect rather than hand-written,
so a field cannot silently drift away from the feature it feeds. Option lists come
straight from the fitted encoders' category lists.

Run after both bundles exist:
    python scripts/build_form_schema.py
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


def main():
    v1 = load(MODELS / "v1_bundle.json.gz")
    v1_pre = v1["preprocessors"][v1["models"]["XGBoost"]["preprocessor"]]

    reg1 = pd.read_csv(ROOT / "outputs" / "ANC8_predictor_register_final.csv")
    reg1_map = {r.final_variable: {"domain": r.domain, "description": r.construct}
                for r in reg1.itertuples()}

    v1_fields = [
        field_for(n, v1_pre, reg1_map.get(n))
        for n in v1_pre["numeric"] + v1_pre.get("binary", []) + v1_pre["categorical"]
    ]

    schema = {
        "v1": {
            "title": "21-predictor models, before ANC",
            "subtitle": "logistic regression, random forest, XGBoost",
            "fields": v1_fields,
            "models": list(v1["models"]),
        }
    }

    # ---- ANC-entry horizon ------------------------------------------------
    entry_path = MODELS / "v1_anc_entry_bundle.json.gz"
    if entry_path.exists():
        ve = load(entry_path)
        first = list(ve["models"])[0]
        ve_pre = ve["preprocessors"][ve["models"][first]["preprocessor"]]
        # The Extended specification carries early_anc in its own block, so its
        # preprocessor is the one that describes every field the horizon needs.
        for mname, m in ve["models"].items():
            pre = ve["preprocessors"][m["preprocessor"]]
            if pre.get("extra"):
                ve_pre = pre
                break

        entry_fields = []
        for n in (ve_pre["numeric"] + ve_pre.get("binary", [])
                  + ve_pre["categorical"] + ve_pre.get("extra", [])):
            f = field_for(n, ve_pre, reg1_map.get(n))
            if n == "early_anc":
                f["type"] = "select"
                f["options"] = [{"value": "0", "label": "No -- first contact after 12 weeks"},
                                {"value": "1", "label": "Yes -- first contact at or before 12 weeks"}]
                f["domain"] = "Health service and access"
                f["default"] = None
            entry_fields.append(f)

        schema["v1_anc_entry"] = {
            "title": "21-predictor models, at ANC entry",
            "subtitle": "for women who have already started ANC",
            "fields": entry_fields,
            "models": list(ve["models"]),
            "gating_field": "early_anc",
        }

    v2_path = MODELS / "v2_bundle.json.gz"
    if v2_path.exists():
        v2 = load(v2_path)
        reg2 = pd.read_csv(ENHANCED / "predictor_register_v2.csv")
        reg2_map = {r.final_variable: {"domain": r.domain, "description": r.description}
                    for r in reg2.itertuples()}

        champ = v2.get("champion") or list(v2["models"])[0]
        if champ not in v2["models"]:
            champ = list(v2["models"])[0]
        v2_pre = v2["preprocessors"][v2["models"][champ]["preprocessor"]]

        pars = json.loads((ENHANCED / "anc8plus" / "parsimonious_spec.json").read_text())
        core = set(pars["predictors"])

        v2_fields = []
        for n in v2_pre["numeric"] + v2_pre.get("binary", []) + v2_pre["categorical"]:
            f = field_for(n, v2_pre, reg2_map.get(n))
            f["core"] = n in core
            v2_fields.append(f)

        schema["v2"] = {
            "title": "Full-pool model",
            "subtitle": f"{len(v2_fields)} predictors",
            "fields": v2_fields,
            "models": list(v2["models"]),
            "champion": champ,
            "core_predictors": pars["predictors"],
        }

    # Order fields by domain so the form reads like a questionnaire.
    for gen in schema.values():
        gen["fields"].sort(
            key=lambda f: (DOMAIN_ORDER.index(f["domain"]) if f["domain"] in DOMAIN_ORDER
                           else len(DOMAIN_ORDER), f["label"])
        )

    out = ROOT / "app" / "public" / "form_schema.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(schema, indent=1), encoding="utf-8")
    print(f"wrote {out}")
    for k, g in schema.items():
        print(f"  {k}: {len(g['fields'])} fields, models: {g['models']}")


if __name__ == "__main__":
    main()
