# CardioLens 3D

**An interactive, research-only coronary visualization prototype for hackathon demonstration.**

CardioLens 3D pairs a browser-based 3D coronary schematic with a fixed, locally loaded machine-learning baseline. It supports synthetic demo presets and manual entry of **one case at a time**, then displays uncalibrated scores for the source-cohort CAD label and the LAD, LCX, and RCA labels.

> **⚠️ Demo/research use only — not for patient care.** This prototype has not been independently or prospectively validated, is not calibrated, and must not be used for diagnosis, screening, triage, treatment, or clinical decisions. Its scores are **not clinical probabilities or future-event risk estimates**. The 3D model is schematic, not patient-specific; whole-vessel coloring does not identify a lesion. Never enter names, identifiers, or protected health information (PHI).

## At a glance

| | Current prototype |
|---|---|
| Workflow | Three synthetic presets or a blank manual form; one active case at a time |
| Model | Fixed, versioned logistic-regression research baseline; no automatic learning |
| Inputs | 22 curated fields; all required manual fields must be explicitly entered |
| Targets | Source-cohort prevalent CAD (`Cath`) and source vessel labels (`LAD`, `LCX`, `RCA`) |
| Data | 303-record UCI source cohort; raw dataset file is not included |
| Validation | Internal repeated stratified cross-validation only; no external or prospective validation |
| Anatomy | Procedural schematic; no patient imaging, lesion coordinates, or segment localization |
| Future-event risk | Not available |

## What it does

- **Interactive 3D view:** rotate and zoom the schematic; select a vessel in the scene or from the vessel cards.
- **Single-case workflow:** use a synthetic preset or start a blank manual case. Required fields and Yes/No inputs must be entered explicitly; blanks are not silently changed to normal values. Editing inputs clears the previous result.
- **Research-only outputs:** display model scores and the model's calibration status for CAD and the three vessel labels.
- **Model explanation:** show local linear-model log-odds contributions. These are not SHAP values, causal explanations, or treatment guidance.
- **Local-first demo:** React/Vite serves the interface and proxies `/api` to a local FastAPI service. There is no EHR/FHIR integration, hosted patient database, or multi-patient worklist.

The model bundle is fixed during normal app use. Retraining is a separate, explicit local workflow; the application does not learn automatically from entered cases.

## Safety, privacy, and scope

This is a hackathon research prototype, not a validated clinical decision-support system. No medical-device regulatory determination has been completed; a disclaimer alone does not establish clinical suitability or regulatory status.

- Do not use it to diagnose, screen, triage, treat, or make decisions about a person.
- Do not enter real patient data, names, identifiers, or PHI. The prototype has no authentication, clinical data governance, or privacy/security review.
- Scores are uncalibrated outputs for labels in one historical source cohort. They are not calibrated probabilities, risk strata, or 10-/30-year cardiovascular event estimates.
- CAD and vessel outputs are separate model heads; they do not form a joint probability distribution.
- The visualization colors complete schematic vessels. It does not infer a patient's anatomy, stenosis location, lesion length, or affected myocardial territory.
- No independent external validation, prospective evaluation, clinical threshold selection, fairness analysis, or clinical-use approval has been completed.

## Run locally

### Requirements

- **Node.js:** 20.19+ or 22.12+; npm 10+.
- **Python:** 3.12 64-bit recommended. The bundled model artifact requires the pinned scikit-learn version `1.6.1`.
- A modern browser with WebGL enabled. A dedicated GPU is not required.

### Windows PowerShell

Open two PowerShell terminals. In both, start from the project root—the folder containing `package.json` and `backend`.

**Terminal 1 — install and start the API** (first two commands are needed only once):

```powershell
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If `py -3.12` is not recognized but `python --version` reports Python 3.12, use `python -m venv backend\.venv` for the first command. The commands call the virtual-environment Python directly, so activation is not required.

**Terminal 2 — install and start the web app** (from the project root, not `backend`):

```powershell
npm ci
npm run dev
```

Open **http://localhost:5173**. The Vite development server forwards `/api` requests to the local API on port `8000`. Stop each service with **Ctrl+C** in its terminal.

### macOS or Linux

From the project root:

```bash
chmod +x ./dev.sh
./dev.sh
```

The script creates the Python virtual environment and installs dependencies when needed, then starts the API and Vite. Open **http://localhost:5173**.

## Try the prototype

1. Start with **Balanced demo**, **Lower-factor demo**, or **Higher-factor demo** to load synthetic example inputs, or choose **New manual case** for a blank form.
2. In manual mode, enter all required fields and explicitly choose Yes or No for every binary field.
3. Select **Run research estimate**. Incomplete cases are not estimated; unsupported or out-of-range values are rejected.
4. Rotate the 3D schematic, zoom, and select LAD, LCX, or RCA to inspect the corresponding whole-vessel display.
5. Review the model version, calibration status, score, and local explanation. Treat all outputs as research-demo values only.

The app is designed for one active case and does not provide a patient worklist or longitudinal history. Do not enter real patient information.

## Model and evaluation

The bundled artifact is `backend/artifacts/model_bundle.joblib` (`z-alizadeh-logistic-baseline`, version `research-1.1.0`). It contains four independent logistic-regression heads, using 22 curated fields from demographic, history/examination, ECG, laboratory, and echocardiography groups. The runtime pins scikit-learn to `1.6.1` to match the artifact.

The source is the UCI **extension of the Z-Alizadeh Sani dataset** (303 records). The official workbook has no separate `CAD` column, so this implementation uses `Cath` (`CAD`/`Normal`) as the overall CAD label; `LAD`, `LCX`, and `RCA` are the vessel labels. Outcome/diagnostic fields `CAD`, `Cath`, `LAD`, `LCX`, and `RCA` are excluded from the predictors. The source CAD label differs from the OR of the three vessel labels in one of 303 records; the supplied source label is retained and the discrepancy is documented.

### Internal cross-validation summary

These are internal repeated stratified 5-fold cross-validation summaries (five repeats). Values are **mean ± standard deviation across folds**, not confidence intervals and not independent validation results.

| Target | Accuracy | F1 | ROC-AUC |
|---|---:|---:|---:|
| CAD (`Cath`) | 0.853 ± 0.041 | 0.891 ± 0.034 | 0.936 ± 0.025 |
| LAD | 0.758 ± 0.050 | 0.787 ± 0.049 | 0.848 ± 0.044 |
| LCX | 0.674 ± 0.047 | 0.619 ± 0.060 | 0.727 ± 0.046 |
| RCA | 0.641 ± 0.046 | 0.572 ± 0.052 | 0.709 ± 0.058 |

Vessel-label performance is weaker than the overall CAD-label result, particularly for LCX and RCA. The cohort is small and single-source; external generalization is unknown. Full metric details, including precision, sensitivity, specificity, PR-AUC, and Brier score, are in [`backend/artifacts/metrics.json`](backend/artifacts/metrics.json) and [`docs/model-card.md`](docs/model-card.md).

The original dataset file is **not** included. Attribution and license details are in [`DATA_ATTRIBUTION.md`](DATA_ATTRIBUTION.md). The included model artifact and metrics were derived from that source; see the attribution note for details.

## API

When the backend is running, interactive documentation is available at **http://127.0.0.1:8000/docs**.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Service status and active mode (`trained_research` or `synthetic_demo`) |
| `GET` | `/api/model-info` | Model version, feature count, calibration status, and target metadata |
| `GET` | `/api/sample-case` | Synthetic example inputs; no real patient rows are served |
| `POST` | `/api/predict` | Estimate the CAD and vessel-label scores for one case |

The prediction request uses schema version `0.2` and a `features` object containing the complete feature set. Missing values are not silently imputed at request time; incomplete inputs return `not_estimable`. Outcome/diagnostic fields cannot be submitted as predictors. Future-event risk is always reported as unavailable.

## Tests and production build

From the project root, after the backend virtual environment and Node dependencies are installed:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements-dev.txt
.\backend\.venv\Scripts\python.exe -m pytest .\backend\tests -q
npm run build
```

The backend tests cover input validation, synthetic-mode behavior, label handling, and exclusion of outcome/diagnostic fields from predictors.

## Optional: retrain locally

Retraining is an explicit offline action; it is **not** part of normal app use. Obtain the source dataset from UCI, review its license and data dictionary, and place your local `.xlsx` or `.csv` file in `backend/data/`. That directory is ignored by Git; do not commit the raw source data to a public repository.

For example, from the project root in Windows PowerShell:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m ml.train --data data\z_alizadeh_extension.xlsx --out artifacts
```

Restart the API after retraining. The output bundle is a trusted local `joblib` artifact; only load bundles you created or otherwise trust, because joblib/pickle files can execute code when loaded. Review the manifest and metrics after every retraining run.

## Repository map

```text
src/                         React dashboard and Three.js coronary schematic
backend/app/main.py          FastAPI prediction API
backend/ml/train.py          Explicit, leakage-controlled training script
backend/artifacts/            Fixed model bundle, metrics, feature manifest
backend/tests/                Backend smoke and validation tests
docs/model-card.md            Model details, metrics, intended use, limitations
docs/project-spec.md          Project specification and design documentation
DATA_ATTRIBUTION.md           UCI source attribution and license note
```

## Before any clinical research or deployment

Independent validation on representative data, calibration assessment, clinically justified thresholds, subgroup/fairness evaluation, human-factors testing, privacy/security controls, review of the anatomical visualization, and jurisdiction-specific regulatory assessment would all be required. This repository does not provide those assurances.

## References

- [UCI extension of the Z-Alizadeh Sani dataset](https://archive.ics.uci.edu/dataset/411/extention+of+z+alizadeh+sani+dataset)
- [Dataset attribution and license](DATA_ATTRIBUTION.md)
- [Model card](docs/model-card.md)
- [Project specification](docs/project-spec.md)
