# UCI dataset attribution

The included `backend/artifacts/model_bundle.joblib`, `metrics.json`, and `feature_manifest.json` were derived from the **extension of the Z-Alizadeh Sani dataset** in the UCI Machine Learning Repository. The original dataset is licensed CC BY 4.0. The raw data file is not included in this project bundle.

**Attribution:** Alizadehsani, Roohallah; Roshanzamir, Mohamad; Sani, Zahra. *extention of Z-Alizadeh sani dataset*. UCI Machine Learning Repository. DOI: [10.24432/C5461K](https://doi.org/10.24432/C5461K). Dataset page: <https://archive.ics.uci.edu/dataset/411/extention+of+z+alizadeh+sani+dataset>. License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

**Changes made:** The local model bundle was trained using a curated 22-field feature subset and scikit-learn logistic-regression pipelines. The official `.xlsx` has no separate `CAD` column, so its `Cath` field (`CAD`/`Normal`) is used as the overall-label target. `Cath`, `LAD`, `LCX`, `RCA` and any `CAD` column are excluded from every predictor matrix. CV metrics and the feature mapping are included next to the model bundle. The artifact is an uncalibrated research baseline, not a medical product or validated clinical predictor.
