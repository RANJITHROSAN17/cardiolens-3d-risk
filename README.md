# CardioLens — 3D Coronary Model Explorer

An interactive **research prototype** for the Multimodal AI Hackathon 2026 Track A. It connects an editable synthetic clinical snapshot to four logistic-regression baseline heads trained on the UCI Z-Alizadeh Sani extension and colors a procedural 3D heart/coronary schematic. A fallback synthetic scorer is available if the local model bundle is removed. The app runs without external anatomy downloads or a dedicated GPU.

> **Safety:** The bundled model is a small-cohort, uncalibrated internal research baseline—not a clinically validated model. Default inputs are synthetic; outputs must not be used for diagnosis, screening, triage, treatment, or patient care. The 3D geometry is illustrative and whole-vessel colors do not indicate a lesion.

## What works in this prototype

- Three synthetic presets plus a blank, single-case manual demo form for the 22 supported features. All fields must be entered explicitly; blanks are not silently turned into zero/normal values.
- FastAPI prediction endpoint. Default mode is `trained_research` (the bundled local baseline); if its model bundle is removed, a fabricated `synthetic_demo` scorer remains available for UI testing.
- Interactive Three.js model: drag to rotate, wheel to zoom, click a coronary vessel or select LAD/LCX/RCA cards.
- Per-vessel score/color updates, linear-model log-odds contribution panel and a persistent research-use warning.
- A local training pipeline with target leakage exclusions, repeated stratified CV, feature manifest and reproducible model bundle.

## Prerequisites

- Node.js 20.19+ or 22.12+, and npm 10+.
- Python 3.12 64-bit is recommended, especially on Windows (the bundled model pins scikit-learn 1.6.1 to match its artifact).
- A modern browser with WebGL enabled. No dedicated GPU is required.

## Run locally

### Option A — one command (macOS/Linux)

From this directory:

```bash
chmod +x dev.sh
./dev.sh
```

The script creates `backend/.venv` if needed, starts the API on `127.0.0.1:8000`, and Vite on `0.0.0.0:5173`. Open **http://localhost:5173**. The web app uses the same-origin `/api` proxy; browser code does not call a hard-coded localhost API.

### Option B — two terminals

**Terminal 1 — API**

```bash
cd backend
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — web app**

```bash
npm install
npm run dev -- --host 0.0.0.0
```

Open **http://localhost:5173**. The Vite proxy forwards `/api/*` to FastAPI. Local API docs: `http://127.0.0.1:8000/docs`.

## Try the prototype

1. Choose **Balanced demo**, **Lower-factor demo**, or **Higher-factor demo** for synthetic scenarios, or select **New manual case** for a blank one-case demo entry.
2. In manual mode, complete every field, explicitly choose Yes/No for each flag, then select **Run research estimate**. Missing or unsupported values return `not_estimable`; input is not saved between cases.
3. Changes clear the previous output until you rerun the estimate.
4. Drag the heart to rotate, use the mouse wheel to zoom, and select LAD, LCX or RCA on the mesh or vessel cards.
5. Review the model version, calibration status and factors. Explanations are not SHAP and are not causal. Manual mode is demo/research only—never enter names, identifiers, or PHI.

## Bundled research model and training

The project includes `backend/artifacts/model_bundle.joblib`, `metrics.json` and `feature_manifest.json`, derived from the official UCI extension under CC BY 4.0. The original dataset file is **not** included; see [`DATA_ATTRIBUTION.md`](DATA_ATTRIBUTION.md) and [`docs/model-card.md`](docs/model-card.md).

To retrain locally, download the **extension of Z-Alizadeh Sani** from UCI, review its license/data dictionary, and place the `.xlsx` or `.csv` in `backend/data/`. Do not commit patient-level source data to a public repository.

```bash
cd backend
python -m pip install -r requirements.txt
python -m ml.train --data data/z_alizadeh_extension.xlsx --out artifacts
```

Optional Excel worksheet:

```bash
python -m ml.train --data data/z_alizadeh_extension.xlsx --sheet Sheet1 --out artifacts
```

The trainer uses `CAD` as the overall label if present; otherwise it uses the official workbook's `Cath` (`CAD`/`Normal`) column as the overall CAD label. `LAD`, `LCX` and `RCA` are the vessel targets. **CAD, Cath, LAD, LCX and RCA are excluded from all predictor matrices**; unrecognized labels fail closed. The default curated 22-feature map aligns with the UI form and spans demographics, history/examination, ECG, labs and echo. The model pipeline uses fixed class-weighted logistic regression and repeated stratified internal CV; it does not calibrate the outputs or perform external validation.

The output bundle loads on API startup. Restart the API after retraining. The front-end form sends the same canonical feature schema; if a custom bundle requires other columns, the API returns `not_estimable` with missing field names instead of silently inventing values. The requirements pin scikit-learn 1.6.1 to match the bundled joblib artifact; do not upgrade sklearn without retraining/testing the artifact. Only load trusted locally generated model bundles; joblib/pickle files can execute code when loaded.

## API

### `GET /api/health`

Returns service status and mode (`trained_research` or `synthetic_demo`).

### `GET /api/model-info`

Returns model id/version, training row count (when available), feature count, calibration status, label-consistency QA and future-risk availability (`false`).

### `GET /api/sample-case`

Returns an editable synthetic input case. No real patient rows or identifiers are served.

### `POST /api/predict`

Example body matching the included 22-feature model:

```json
{
  "schema_version": "0.2",
  "features": {
    "age": 58, "sex": "Female", "bmi": 27.4,
    "systolic_bp": 138, "pulse_rate": 74,
    "smoking": false, "ex_smoker": false, "diabetes": false,
    "hypertension": true, "family_history": true,
    "typical_chest_pain": false, "st_elevation": false,
    "st_depression": false, "t_inversion": true, "lvh": false,
    "fbs": 96, "ldl": 122, "hdl": 48, "tg": 154,
    "ef_tte": 55, "region_rwma": 0, "vhd": "N"
  }
}
```

Research responses use `uncalibrated_research_model_score`; the fallback uses `synthetic_demo_score`. The future-event risk module is explicitly unavailable.

## Project structure

```text
src/                         React dashboard and procedural Three.js scene
backend/app/main.py          FastAPI API; trained bundle / synthetic fallback
backend/ml/train.py          Leakage-controlled Track A training pipeline
backend/artifacts/            Research model, internal CV metrics, feature manifest
backend/tests/                Smoke and leakage tests
docs/project-spec.md          Six-page implementation specification
docs/model-card.md            Dataset, metrics and limitations
DATA_ATTRIBUTION.md           UCI dataset attribution/license note
README.md                     Setup, API, training and safety instructions
```

## Model semantics and limitations

- The outputs estimate source-cohort **prevalent CAD/vessel labels**, not 10-year or 30-year future-event risk. No longitudinal model is included.
- The official UCI workbook has 303 records and no separate `CAD` field; this implementation uses `Cath` as the overall CAD target if needed. CAD/Cath/LAD/LCX/RCA are never predictors. CAD and the OR of vessel targets disagree in one source record; the supplied label is retained and the issue is recorded.
- The model is a small single-source logistic baseline. The included repeated CV metrics are internal only—not independent validation or confidence intervals. Vessel-specific performance is weaker than overall CAD; consult the model card and `metrics.json`.
- Scores are uncalibrated and must not be described as clinical probabilities or risk strata. No independent external validation, prospective evaluation, clinical threshold, fairness analysis, regulatory review or clinical-use approval has been completed.
- A vessel score colors only the corresponding complete vessel. No segment location, lesion geometry, stenosis percentage or myocardium hotspot is inferred. Separate vessel heads do not form a joint probability distribution.
- The 3D heart is procedural and schematic—not an anatomically certified or patient-specific mesh. The hackathon UI supports one active case at a time (three synthetic presets or a blank manual demo entry), not a scalable patient worklist or live hospital feed. No real EHR/FHIR connector, authentication, PHI storage, patient imaging or future-risk engine is included.

Before any clinical claim/pilot: verify the actual intended use and target population; secure independent representative data; assess calibration and subgroup performance; set thresholds with clinicians; run usability/human-factors and prospective silent-mode studies; complete privacy/security and regulatory reviews; and obtain cardiology/anatomy review of the visual model.

## Tests and build

```bash
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
npm install
npm run build
npm audit
```

## References

- UCI extension of Z-Alizadeh Sani: <https://archive.ics.uci.edu/dataset/411/extention+of+z+alizadeh+sani+dataset>
- FDA Clinical Decision Support Software guidance: <https://www.fda.gov/media/109618/download>
- HL7 SMART App Launch: <https://hl7.org/fhir/smart-app-launch/>
