# Model card — CardioLens research baseline

**Artifact:** `backend/artifacts/model_bundle.joblib`  
**Version:** `research-1.1.0`  
**Training/runtime scikit-learn:** `1.6.1` (pinned; retrain and regression-test before changing)  
**Status:** Research demonstration only; not clinically validated, not calibrated, not for patient care.

## Intended use and non-use

The four independent logistic-regression heads estimate the source-cohort labels for prevalent CAD (`Cath` used as the overall CAD label because the official UCI workbook has no separate `CAD` column) and ≥50%-stenosis labels for LAD, LCX and RCA. The scores are not a future-event risk estimate, do not locate a lesion and do not support diagnosis, triage or treatment.

## Training data and labels

- Source: UCI extension of the Z-Alizadeh Sani dataset; 303 records; 22 curated input fields selected from its demographic, history/examination, ECG, lab and echo groups.
- The source `Cath` label has 216 CAD / 87 Normal records. Vessel positives: LAD 177, LCX 119, RCA 114.
- The source CAD label agrees with the OR of LAD/LCX/RCA in 302/303 rows (99.67%); the one disagreement is retained as supplied and noted in `feature_manifest.json`.
- The data file itself is not bundled. Attribution and license information: [`DATA_ATTRIBUTION.md`](../DATA_ATTRIBUTION.md).
- Predictors: age, sex, BMI, diabetes, hypertension, current/ex-smoking, family history, BP, pulse, typical chest pain, ST elevation/depression, T inversion, LVH, fasting glucose, TG, LDL, HDL, EF-TTE, region-RWMA source code and VHD.
- Leakage firewall: CAD, Cath, LAD, LCX and RCA are labels/diagnostic fields and never predictors.

## Model and evaluation

Each target uses a scikit-learn pipeline: fold-fitted median/mode imputation, scaling of continuous fields, one-hot encoding of categorical fields, and class-weighted logistic regression (`C=0.5`). Evaluation is **fixed-model repeated stratified 5-fold internal CV** (five repeats; threshold 0.5); the table shows mean ± SD across folds, not confidence intervals. No hyperparameter tuning or post-hoc calibration was performed.

| Target | Accuracy | Precision | Sensitivity | Specificity | F1 | ROC-AUC | PR-AUC | Brier |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CAD (`Cath`) | 0.853 ± 0.041 | 0.932 ± 0.030 | 0.857 ± 0.064 | 0.842 ± 0.077 | 0.891 ± 0.034 | 0.936 ± 0.025 | 0.973 ± 0.011 | 0.102 ± 0.024 |
| LAD | 0.758 ± 0.050 | 0.809 ± 0.050 | 0.772 ± 0.082 | 0.740 ± 0.086 | 0.787 ± 0.049 | 0.848 ± 0.044 | 0.881 ± 0.042 | 0.160 ± 0.023 |
| LCX | 0.674 ± 0.047 | 0.573 ± 0.056 | 0.680 ± 0.094 | 0.669 ± 0.068 | 0.619 ± 0.060 | 0.727 ± 0.046 | 0.592 ± 0.062 | 0.215 ± 0.021 |
| RCA | 0.641 ± 0.046 | 0.522 ± 0.050 | 0.642 ± 0.090 | 0.641 ± 0.087 | 0.572 ± 0.052 | 0.709 ± 0.058 | 0.585 ± 0.085 | 0.220 ± 0.027 |

Full per-fold details are in `backend/artifacts/metrics.json`; exact source/canonical mappings and the dataset hash are in `backend/artifacts/feature_manifest.json`.

## Limitations and required next evidence

Small, single-source cohort; likely spectrum and population shift; modest vessel-specific performance; one CAD/vessel-label inconsistency; no external or prospective validation; no calibration or clinically selected operating thresholds; no fairness analysis; no time-to-event outcomes; no patient-specific imaging/segment labels. Scores shown in the app are uncalibrated research model outputs, not calibrated clinical probabilities. Obtain independent, representative validation, calibration, clinical thresholds, human-factors review, privacy/security approval and regulatory determination before any clinical pilot or claim.
