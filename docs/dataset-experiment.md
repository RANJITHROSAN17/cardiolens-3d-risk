# Exploratory dataset experiment: 10-year CHD label

**Not for patient care.** This is a single random train/test split of one publicly mirrored dataset, not external, temporal or prospective validation. It does not evaluate the current deployed CAD model or provide a clinical risk calculator. The dataset label is 10-year **coronary heart disease (CHD)**, not a 10-year heart-attack-or-stroke composite. Do not interpret the results as accuracy for India or any clinical population.

## Data, provenance and limitations

We examined the CSV publicly hosted at [this GitHub mirror](https://github.com/plaguedoc000/framingham-heart-study-dataset/blob/main/framingham.csv), whose README attributes it to a Kaggle Framingham dataset. The mirror describes the outcome as `TenYearCHD`. The chain from the original Framingham Heart Study, complete outcome definitions, selection, follow-up/censoring and permission to redistribute are **not independently verified**. A CC0 label on a different Kaggle listing is not proof of rights for this exact mirror. The raw data and fitted model are not included. Anyone reproducing must independently verify authorization, permitted use and applicable ethics/privacy requirements; public accessibility is not a license.

File SHA-256: `2c0e57dc0361b420becf1facec0a054af06c420eae0ae2faf0fdc8591fadb018`. This hash identifies the examined bytes, not provenance or permission.

The CSV lacks a reliable patient identifier, event dates, censoring, full cardiovascular history and documented source population. Thus we cannot establish patient independence or truly restrict the analysis to adults without prior CVD, and we cannot evaluate survival or censoring correctly. A previous-stroke flag exists: 25 flagged rows are excluded, but other pre-existing CVD may remain. No exact duplicate full rows were found; that does not prove unique individuals. Risk predictions and outcomes depend on historical population and care, and transportability to India is unknown.

## Method

The independent offline experiment uses nine pre-specified fields: male, age, currentSmoker, BPMeds, diabetes, totChol, sysBP, BMI and glucose. No target or stroke flag is used as a predictor. A stratified random 80/20 split, seed 42, is followed by training-only median imputation, standardization and logistic regression. There is no hyperparameter search, calibration fit, threshold selection or model export. Missing values were imputed for this exploratory analysis, not as a recommendation for clinical use. The test set is from the **same source** and was used for this report; it is not a locked independent external dataset. Baseline predicts the training event fraction for all test rows.

Python 3.13.16, NumPy 2.3.5, pandas 2.2.3 and scikit-learn 1.6.1 were used. Reproducibility across dependency versions is not guaranteed. Aggregate output is in `src/research-results.json`. No per-person values or predictions are saved by this script.

## Held-out results

| Metric | Result |
| --- | ---: |
| Source rows | 4,240 |
| Rows after prior-stroke exclusion | 4,215 |
| Train / test rows | 3,372 / 843 |
| Test positive outcomes | 127 (15.1%) |
| ROC-AUC | 0.724 |
| Average precision | 0.322 |
| Brier score (lower better) | 0.117 |
| Constant training-event-rate baseline Brier | 0.128 |

The AUC reflects ranking within this particular test split; the average precision is influenced by the outcome fraction. Brier compares predicted probabilities with the binary label, but unknown censoring and label definitions matter. The five grouped observed-versus-predicted values appear in the app and JSON; they are descriptive, do not show uncertainty, and do **not** establish calibration. No confidence intervals, subgroup evaluation, sensitivity/specificity at a clinically justified threshold, external validation or impact study were performed. Results are vulnerable to sampling noise and possible leakage through unidentified participants.

## Reproduce (only with authorized data)

From repository root, create and activate a Python environment and install `backend/requirements.txt`. Obtain the exact CSV through an authorized source and keep it in ignored `backend/data/` (never commit individual records). Then:

```bash
python research/framingham_experiment.py --data backend/data/framingham.csv --out /tmp/cardiolens-experiment.json
```

On Windows use an appropriate local output path instead of `/tmp`. The script prints and writes aggregate results only. The app displays the checked-in result JSON; running the experiment elsewhere does not automatically change the website. Review results before intentionally replacing the JSON. Do not use external patient records without approved governance or publish identifying or small-cell outputs.

## Next evidence gate

Specify the intended composite outcome and study protocol; obtain rights and representative longitudinal Indian cohort(s), complete eligibility and event definitions, patient IDs, follow-up and censoring. Compare suitable existing models to standard care with frozen model implementations, external site/time validation, calibration and uncertainty, prespecified subgroups and meaningful clinical utility; then pursue ethics-approved prospective studies. This experiment does not satisfy those gates.
