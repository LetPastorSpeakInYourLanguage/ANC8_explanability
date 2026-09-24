ANC8 PUBLICATION RESULTS PACKAGE
================================

Purpose
-------
This directory contains the frozen numerical sources used to construct
manuscript tables and evaluation figures.

The CSV files are the numerical authority.
Word tables and figures should be generated from these frozen sources.

Main tables
-----------
Table 1
    Full-cohort held-out predictive performance, bootstrap confidence
    intervals, calibration, and secondary threshold measures.

Table 2
    ANC-entry baseline versus extended probability performance, including
    paired incremental differences and stratified-PSU bootstrap uncertainty.

Table 3
    ANC-entry calibration and held-out threshold-based performance.

Supplementary tables
--------------------
S1  Full-cohort development-derived thresholds.
S2  ANC-entry development-derived thresholds.
S3  Full-cohort pairwise model comparisons.
S4  ANC-entry consolidated incremental point estimates.
S5  ANC-entry model-specific bootstrap confidence intervals.
S6  ANC-entry paired-difference bootstrap confidence intervals.
S7  ANC-entry held-out survey-design audit.

Reproducibility
---------------
The reproducibility directory contains all retained bootstrap replicate
distributions underlying the reported percentile confidence intervals.

Interpretation
--------------
Primary probability-based metrics are Average Precision, AUROC, and Brier
score.

Calibration and threshold-based metrics are complementary evaluations.

For ANC-entry paired differences:
- positive Delta_AP favors the extended model;
- positive Delta_AUROC favors the extended model;
- positive Brier_improvement means lower Brier score for the extended model.

No causal interpretation is intended.