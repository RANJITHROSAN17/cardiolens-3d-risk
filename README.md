<div align="center">

# CardioLens 3D

### Explore the heart. Question the model. Design better prevention.

An interactive **research prototype** combining a 3D coronary schematic, transparent model experiments, and a fictional prevention follow-through workflow.

[Explore the live demo](https://ranjithrosan17.github.io/cardiolens-3d-risk/) · [Quick start](#quick-start) · [See the evidence](#what-do-the-results-mean) · [Share feedback](#share-feedback--contribute)

</div>

> **Research and software demonstration only — not for patient care.** CardioLens is not validated for diagnosis, screening, triage, treatment or any clinical decision. **Never enter real patient data, names or identifiers.** The 3D heart is a generic schematic; colors do not show a real person's arteries or lesions. No 10-year cardiovascular risk calculator is available.

---

## Why CardioLens?

Cardiovascular disease can develop quietly, and detecting risk is only one part of prevention: a person also needs access to review, an appropriate plan and follow-up. CardioLens is an experiment in making these ideas easier to explore—without pretending that a prototype can replace clinicians or established care.

Our long-term question: **Could a locally validated risk model and a thoughtfully designed follow-through workflow help a care team support cardiovascular prevention?** That question still needs clinical partners, representative longitudinal data, independent validation, usability studies and regulatory review. The current project does not answer it yet.

## Try it in a few minutes

1. **Read the safety notice** and use fictional data only.
2. Explore the **prevention research checklist**. It records no clinical evidence and resets on refresh.
3. Try the **fictional follow-through worklist**: filter by stage, move example cases forward or backward, and reset. Nothing is scheduled, sent or saved.
4. Review the **dataset experiment** and compare predicted and observed event frequencies in its held-out sample. This is a separate offline experiment—not a live risk calculator.
5. In the **coronary explorer**, select a demo preset and run an estimate; drag to rotate the heart, zoom, and select a vessel. Editing inputs clears the old result. Try a blank manual case to see the missing-input checks—use invented values only.

The public site uses a **fabricated synthetic formula** unless an API was explicitly configured at build time. The live site may reflect an older deployed commit than this branch. [Pages usage guide](docs/github-pages.md).

## What is here—and what isn't

| Area | Available now | Not available / not established |
|---|---|---|
| **3D explorer** | Interactive generic heart and selectable LAD, LCX and RCA | Patient-specific imaging, lesion location or stenosis measurement |
| **Scoring** | Fabricated browser demo; optional uncalibrated CAD/vessel research model via FastAPI | Validated patient risk, clinical probability, diagnosis or triage |
| **Prevention** | Fictional worklist and research checklist, held in memory | Patient records, scheduling, messaging, EHR/FHIR integration or 10-year risk calculator |
| **Evidence** | Internal CAD-model cross-validation; a separate exploratory CHD holdout experiment | Independent external/prospective validation, clinical utility or regulatory authorization |

The fictional follow-through examples are not patients. The CAD explorer accepts one active synthetic/manual case at a time. **Do not use any output to make decisions about a person.**

## Quick start

### Prerequisites

- Node.js **20.19+ or 22.12+**, npm and a modern browser with WebGL.
- Python **3.12** recommended for the optional API and research tests. The supplied model artifact requires scikit-learn **1.6.1**.

Clone the repository and enter it:

```bash
git clone https://github.com/RANJITHROSAN17/cardiolens-3d-risk.git
cd cardiolens-3d-risk
```

> The latest work may be on `prevention-research-upgrade` until merged. To try that branch, run `git switch prevention-research-upgrade` after cloning.

### Option A: frontend-only synthetic demo

```bash
npm ci
VITE_BASE_PATH=/ npm run dev
```

In PowerShell:

```powershell
npm ci
$env:VITE_BASE_PATH='/'
npm run dev
```

Open the local address printed by Vite, normally **http://localhost:5173/**. No backend is needed. Scores are fabricated examples, not a trained model. Stop with **Ctrl+C**.

### Option B: frontend + local research API

On macOS/Linux, run:

```bash
./dev.sh
```

This installs dependencies as needed, starts FastAPI locally on port 8000, and starts Vite with its `/api` proxy enabled. Open the Vite address shown in the terminal. Stop with **Ctrl+C**.

On Windows PowerShell, use two terminals from the repository root:

```powershell
# Terminal 1: create the environment once, install dependencies, start API
py -3.12 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2: start web app through Vite's local API proxy
npm ci
$env:VITE_BASE_PATH='/'
$env:VITE_USE_LOCAL_API='true'
npm run dev
```

Open **http://localhost:5173/**. The bundled model is selected when available; `/api/model-info` reports the active mode. If the bundle is absent, the **backend** uses an explicitly labeled synthetic demo. If a configured API fails, the frontend displays an error and does not silently substitute a result. API docs: **http://127.0.0.1:8000/docs**.

`VITE_USE_LOCAL_API=true` uses Vite's development proxy only; it is not a production API configuration. Do not expose this unauthenticated research API publicly or send real health information to it. A separately hosted API needs its own security, authorization, HTTPS and cross-origin or reverse-proxy setup. Frontend environment variables are public—not a place for secrets.

## What do the results mean?

### Coronary research model

The optional FastAPI bundle contains four fixed logistic-regression heads trained on the UCI extension of the Z-Alizadeh Sani dataset: **303 records from one source**. The heads output scores for a prevalent CAD label (`Cath`) and three vessel labels. The labels are excluded from predictors. The model is **not calibrated**, has no independent external or prospective validation, and does not estimate future heart attack or stroke risk.

The model card reports repeated stratified five-fold *internal* cross-validation. For example, the overall CAD-label ROC-AUC is **0.936 ± 0.025**, while LCX is **0.727 ± 0.046** and RCA is **0.709 ± 0.058**; values are fold mean ± SD, not confidence intervals. These figures do not establish real-world performance. See the [model card](docs/model-card.md), [full metrics](backend/artifacts/metrics.json), and [data attribution](DATA_ATTRIBUTION.md).

### Separate 10-year CHD dataset experiment

A separate offline logistic-regression experiment on a public Framingham-labeled mirror produced a same-source held-out **ROC-AUC of 0.724** and **Brier score of 0.117** on 843 test rows. A constant-rate baseline Brier score was 0.128. This is an exploratory single split, not external validation. The dataset's outcome is **CHD**, not the proposed heart-attack-or-stroke composite; its provenance, follow-up and eligibility details are insufficiently verified. Results cannot be generalized to India or patient care. Raw data and the fitted experimental model are not included. See the [experiment report](docs/dataset-experiment.md) for methods, caveats and reproduction instructions.

## Run tests and build

From the project root:

```bash
# Frontend / workflow unit tests and production build
npm ci
node --test tests/*.test.js
npm run build

# Backend and offline experiment tests (macOS/Linux)
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
backend/.venv/bin/python -m pytest backend/tests -q
backend/.venv/bin/python -m unittest discover -s research -p 'test_*.py' -v
```

On Windows, replace `backend/.venv/bin/python` with `backend\.venv\Scripts\python.exe`. Tests use synthetic inputs. CI runs these checks on pushes and pull requests. Passing tests verifies software behavior covered by the tests—not clinical safety or model validity.

## Explore the repository

```text
src/                         React UI, Three.js scene, fictional workflow & aggregate results
backend/app/                 FastAPI research/demo endpoints
backend/ml/                  Offline training for the source-cohort CAD model
backend/artifacts/           Bundled model, feature manifest and internal metrics
backend/tests/               API, input validation and leakage tests
research/                    Separate CHD experiment and synthetic tests
tests/                       Frontend validation and workflow unit tests
docs/                        Model card, experiment report, Pages guide and roadmap
```

- [Model card](docs/model-card.md) · [Dataset experiment](docs/dataset-experiment.md) · [Data attribution](DATA_ATTRIBUTION.md)
- [Prevention research plan](docs/prevention-risk-plan.md) · [Follow-through proposal](docs/prevention-follow-through.md) · [Product blueprint](docs/product-blueprint.md)
- [GitHub Pages guide](docs/github-pages.md) · [Project specification](docs/project-spec.md)

The source datasets are not bundled. The offline training script requires separately obtained, appropriately licensed data; see [data attribution](DATA_ATTRIBUTION.md). Load only trusted `joblib` artifacts: pickle-based files can execute code.

## Share feedback & contribute

We welcome feedback from clinicians, patients, designers, researchers and developers. You do **not** need to be a medical AI expert to help.

- [Open an issue](https://github.com/RANJITHROSAN17/cardiolens-3d-risk/issues/new) with a bug, usability finding, accessibility concern or research question.
- Include steps to reproduce, expected and actual behavior, browser/OS, and screenshots **containing fictional data only**. Never post patient information, credentials or sensitive records.
- For code changes, fork the repo, create a focused branch, run the tests above, and open a pull request describing the change and its limitations. Please avoid unsupported medical claims or unverified datasets.
- If you are a clinician or researcher interested in collaboration, describe your expertise and intended contribution in an issue without sharing confidential information.

Before a clinical pilot, the project needs a clearly defined intended use, representative independent validation, calibration and subgroup analysis, human-factors testing, privacy/security controls, institutional and ethics approvals as applicable, and regulatory assessment. No performance metric or disclaimer replaces those steps.

## License

Repository code is licensed under [MIT](LICENSE). Datasets and third-party materials have their own terms; see [DATA_ATTRIBUTION.md](DATA_ATTRIBUTION.md). The model and evaluation artifacts are research-only.
