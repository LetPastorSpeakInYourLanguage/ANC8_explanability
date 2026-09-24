ANC8 NOTEBOOK 3 EXPLAINABILITY HANDOFF
======================================

Purpose
-------
This directory is the frozen input authority for Notebook 3.

Notebook 3 should load these files rather than rerun model development,
hyperparameter tuning, train/test splitting, or outcome/predictor construction.

Prediction horizons
-------------------
1. Full cohort:
   Original 21-predictor baseline prediction horizon.

2. ANC entry:
   Same 21 predictors among women who initiated ANC and had known timing
   of first ANC, with an extended 22-predictor specification adding early_anc.

Core files
----------
full_cohort_final_models.joblib
    Three fitted primary full-cohort pipelines.

anc_entry_final_models.joblib
    Six fitted ANC-entry pipelines:
    baseline and extended Logistic regression, Random Forest, and XGBoost.

full_cohort_development.pkl
full_cohort_heldout.pkl
anc_entry_development.pkl
anc_entry_heldout.pkl
    Frozen analytic populations for explanation/reference distributions.

full_cohort_locked_predictions.csv
anc_entry_locked_predictions.csv
    Held-out predictions generated before final outcome evaluation.

full_cohort_feature_lineage.csv
anc_entry_feature_lineage.csv
    Authorities for mapping transformed model features back to original
    predictor constructs.

predictor_architecture.json
    Frozen predictor lists.

selected_model_metadata.json
    Final selected hyperparameters.

handoff_metadata.json
    Prediction-horizon and governance metadata.

software_environment.json
    Software versions under which models were fitted.

SHA256_MANIFEST.csv
    Integrity hashes for all files in this directory.

Explainability governance
-------------------------
Explanation analyses describe how fitted models generate predictions.
They do not estimate causal effects.

Original predictor constructs should be the main interpretation level.
One-hot encoded components should not be treated as independent scientific
predictors without explicit justification.