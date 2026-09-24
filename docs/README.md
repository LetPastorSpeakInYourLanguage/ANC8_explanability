# Documentation map

What best predicts whether women in Ethiopia complete the eight antenatal
care contacts the WHO recommends (ANC8+), and the earlier rungs ANC1+ and
ANC4+, from the 2024-25 Ethiopia DHS. Three analyses carry the study:

1. **Predictor value** — which predictors carry the prediction, how many are
   needed, and how their value changes from ANC1+ to ANC8+;
2. **The two prediction horizons** — before ANC starts, and at ANC entry;
3. **The Tigray war** — antenatal care during and after it, against the
   other regions.

## Start here, by who you are

| You are... | Read | Length |
|---|---|---|
| A **Ministry of Health** decision-maker | [POLICY_BRIEF.md](POLICY_BRIEF.md) | 10 minutes |
| A general reader | [../INSIGHTS.md](../INSIGHTS.md) | 10 minutes |
| A researcher assessing the work | [../FINDINGS.md](../FINDINGS.md), then the deep dives below | 30 minutes |
| Someone reproducing it | [../release/GUIDE.md](../release/GUIDE.md) | step by step |
| Anyone meeting terms like AUROC, held-out or bootstrap | [GLOSSARY.md](GLOSSARY.md), which also explains every figure | look up as needed |
| Anyone asking "what exactly was tested, and how?" | [ANALYSIS_RECORD.md](ANALYSIS_RECORD.md), every analysis with its question, test and result | 20 minutes |

## The deep dives

| Document | Question it answers |
|---|---|
| [PREDICTOR_VALUE.md](PREDICTOR_VALUE.md) | From 6,648 survey columns to a candidate pool; which predictors carry the prediction of ANC1+, ANC4+ and ANC8+; how many are needed (the ablation from 1 predictor to the full pool, including the 21-predictor set); the drop study; how each predictor's value changes up the ladder |
| [HORIZONS.md](HORIZONS.md) | Does the answer change once a woman has started ANC? What does knowing her first contact was early add? |
| [WARTIME.md](WARTIME.md) | What did the Tigray war do to antenatal care, how does Tigray compare with the other regions, and does the war distort the other findings? |
| [DATA_AND_COHORT.md](DATA_AND_COHORT.md) | What population is this, and does it match the official survey report? Which predictors were measured at the wrong moment? |
| [METHODS.md](METHODS.md) | Survey design, the predictor-value study, horizons, the war analysis, supporting analyses, and deployment |
| [LIMITATIONS.md](LIMITATIONS.md) | What this analysis cannot support |
| [DECISION_LOG.md](DECISION_LOG.md) | Every significant decision and why it was made |

## How the documents stay correct

Numbers in the tables are **generated from the result files**, not typed in.
Each table sits between `<!-- AUTO:name -->` markers and is rebuilt by:

```bash
python scripts/build_docs.py
```

The analysis record quotes numbers by hand; `scripts/run_tests.py` recomputes
each one from its result file and fails if any has drifted. The app's
"Analysis record" tab is parsed from `ANALYSIS_RECORD.md` and `GLOSSARY.md` by
`scripts/export_app_data.py`, so the two cannot disagree.

A table whose inputs do not exist yet says so instead of showing a stale
number. Prose outside the markers is written by hand.

## Where the evidence lives

| | |
|---|---|
| `outputs/feature_value/` | the predictor-value study, per cohort (`full`, `entry`, `recent`) and outcome |
| `outputs/predictor_value/` | each predictor's value at each rung |
| `outputs/horizons/` | the two prediction horizons |
| `outputs/ladder/` | importance three ways, per rung |
| `outputs/wartime/` | the Tigray war analysis |
| `outputs/enhanced/` | screening, model families, tuning and supporting analyses, per outcome |
| `outputs/policy/` | cascade, regional and targeting analyses |
| `outputs/figures/` | every figure, with `figures_manifest.csv` naming each one's sources |
| `docs/conflict_windows.csv` | conflict dates with citations |
