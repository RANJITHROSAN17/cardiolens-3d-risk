# Interactive Cardiovascular Risk & Coronary Vessel Visualization
## Greenfield implementation specification — Track A aligned

**Version:** 1.0 · **Date:** 04 October 2026 · **Audience:** product, clinical, ML, engineering, security and regulatory teams

> **Architecture decision:** Treat (1) prediction of *prevalent, dataset-defined CAD / vessel stenosis* and (2) *future cardiovascular event risk over a stated time horizon* as separate functions. The Track A Z-Alizadeh Sani extension has 303 records and 59 features; it supports a research prototype for its angiography-derived labels, not a validated 10-year risk model or a clinical deployment claim. ([R1])

## 1. Product scope, intended use and safety boundary

### 1.1 Two estimands; do not conflate them

| Function | MVP definition | What the output means |
|---|---|---|
| **Prevalent CAD classifier** | Binary CAD target as defined by the source dataset (≥50% narrowing in at least one target vessel); plus separate LAD, LCX and RCA stenosis heads. | A model-estimated probability of the dataset label in the evaluated population. It is **not** a future-event probability and does not establish stenosis in an individual. |
| **Future cardiac-event risk** | Separate plug-in for an approved, population-appropriate, guideline-based calculator; otherwise unavailable. | A named outcome over a named horizon (e.g., 10-year risk), only for that calculator's supported population. The cross-sectional UCI labels cannot train this function. |

For U.S. primary prevention, AHA PREVENT may be evaluated as a separate calculator only for its stated eligible population (adults 30–79 without known CVD) and after local clinical approval; do not assume U.S. equations are calibrated for Indian or other populations. ([R9])

### 1.2 Intended-use statement for the prototype

A clinician-facing, investigational decision-support prototype that accepts a reviewed clinical feature snapshot, returns research predictions for dataset-defined CAD and LAD/LCX/RCA stenosis, and displays those vessel-level outputs on a generic 3D heart. It is not for diagnosis, screening, triage, treatment selection, emergency use, or replacement of ECG, angiography, CT, or other formal assessment. No automated order, alert, or treatment action is in scope.

**Anatomical boundary:** The model predicts at most a *whole-vessel label*. It does not produce lesion coordinates, stenosis percentage, plaque burden, artery-segment status, or patient-specific anatomy. A 3D color is a visual association to a model output—not a measured lesion. RWMA may be an input feature but is not a 3D coordinate or pixel-level lesion map.

**Visible prototype notice:** “Research prototype — not clinically validated. Model estimates do not diagnose CAD or locate a lesion. Verify the source data and use independent clinical judgment; do not use this display instead of indicated clinical evaluation or imaging.” Keep it persistently visible and on any export. A disclaimer does not settle device classification.

### 1.3 MVP acceptance outcomes

A clinician can select a patient or synthetic case, review source/time/units and missing fields, run the four predictions, inspect per-vessel probabilities and feature contributions, rotate/zoom/select LAD, LCX and RCA, and understand what is *not* being claimed. Every result is reproducible from a versioned model and input snapshot. No patient-specific output is shown when required inputs are invalid, unsupported, or out of domain.

---PAGEBREAK---

## 2. Technical architecture and data requirements

### 2.1 Logical flow

```text
UCI XLSX / synthetic cases ─┐                 ┌─ offline training + validation → signed model bundle
FHIR EHR / manual entry ────┴→ adapters → canonical feature snapshot → prediction API → JSON + attribution
                                                                  └──────────────→ React dashboard + 3D scene
```

Keep training offline and separate from inference. The EHR remains the clinical source of truth. Frontend code never connects directly to the EHR database or loads model weights; all predictions go through a versioned, authenticated API. **As built in the hackathon prototype:** one active case at a time can be selected from three synthetic presets or entered manually in a blank demo form; there is no production patient worklist or EHR connector. The scalable paginated worklist below is a production design requirement, not a current feature.

### 2.2 Sources and feature contract

- **Prototype:** UCI extension of Z-Alizadeh Sani (303 rows, 59 features; CC BY 4.0—retain attribution and dataset version/hash). The source groups fields as demographic, symptom/examination, ECG, laboratory and echo features. The released dataset reports no missing values; production EHR data will not have that property. ([R1])
- **Production candidate:** SMART-on-FHIR R4 read-only launch, with a narrow allowlist of `Patient`, `Observation`, `Condition`, `DiagnosticReport` and, only if a selected model needs them, medication resources. Add HL7 v2/CSV adapters only behind the same canonical contract. SMART App Launch 2.2 is based on FHIR R4. ([R3])
- **Candidate inputs:** age and model-required sex variable; smoking, family history, diabetes, hypertension and medication status only if present and consistently defined; systolic/diastolic BP, pulse; lipids/glucose and other available labs; symptoms/examination; ECG findings (e.g., ST changes, T inversion, LVH); echo findings including RWMA. Cardiac enzymes and acute findings require a defined prediction time and intended use. **Do not invent fields or treat unavailable values as normal.** Confirm every field against the supplied file’s data dictionary before implementation.
- **Label firewall:** `CAD`, `LAD`, `LCX`, `RCA`, and `Cath` (angiography result) are outcomes/diagnostic fields—not predictors for any head. Also exclude identifiers, post-angiography information, and any feature recorded after the intended prediction time. Use an explicit predictor allowlist; automated tests must fail if a forbidden column reaches `X`.

### 2.3 Canonical schema, validation and normalization

Represent each measurement as `{code, value, unit, effective_at, status, source, source_record_id}` plus opaque patient/encounter references and schema version. Use JSON/OpenAPI at the service boundary; ISO-8601 timestamps with timezone; UCUM units; LOINC/SNOMED CT where available. Preserve the source value and normalized value with conversion provenance (e.g., mmHg; mg/dL ↔ mmol/L). Do not silently overwrite or guess units.

Pipeline stages: (1) schema/type check and source hash; (2) terminology/unit mapping; (3) clinical plausibility and allowed-range checks; (4) duplicate/conflicting observation resolution with latest-valid timestamp rules; (5) freshness and required-feature checks; (6) missingness/out-of-range report; (7) immutable prediction snapshot. Invalid, stale, contradictory or unsupported inputs are returned to the clinician for review or cause an explicit `not_estimable` response—never silent defaulting. Manual edits are attributed and timestamped.

**Example input:** `schema_version`, `patient_ref` (opaque), `as_of`, `observations[]`; each observation carries code, value, unit, effective time and provenance. Apply identical preprocessing at training and inference from a versioned feature manifest.

### 2.4 Storage and governance

Use PostgreSQL for application metadata, consent/authorization references, input-snapshot references, predictions and audit events; encrypted object storage for the de-identified training data, data dictionary, evaluation outputs and model artifacts. Keep identity mapping separate. In a pilot, persist only the minimum necessary data; prefer the EHR as source of truth. Encrypt in transit and at rest with managed keys; enforce tenant/site isolation, role-based access, least privilege, retention/deletion policy, backup/restore tests, immutable access audit, and no PHI/clinical values in application logs, analytics, crash reports or third-party telemetry. Prototype on synthetic/de-identified data only.

---PAGEBREAK---

## 3. Predictive-model specification and validation

### 3.1 Endpoints and model family

Train four binary heads: `cad_present`, `lad_stenosis`, `lcx_stenosis`, `rca_stenosis`. The source defines CAD at ≥50% narrowing and describes CAD as present when at least one of the three target vessels is stenotic; verify row-level label consistency before training. Keep the four targets out of every feature matrix. Fit separate regularized logistic-regression baselines first (elastic-net if justified); benchmark a shallow random forest or gradient-boosted tree using identical outer folds. Do not prioritize a neural network on 303 records. A future multi-task model requires substantially larger, diverse data and a prespecified rationale.

Use scikit-learn `Pipeline`/`ColumnTransformer`: split first; fit imputation, scaling and categorical encoding **inside each training fold**; record missingness; tune only in inner folds; use class weights before considering resampling (any resampling must occur inside the training fold). Feature selection is fold-contained. Maintain a signed `feature_manifest.yaml`, target dictionary, preprocessing version, dataset hash and reproducible training command.

### 3.2 Leakage, calibration and explanation controls

- For every head, exclude all labels `CAD/LAD/LCX/RCA/Cath` plus angiography-derived or post-outcome proxies. Define the prediction timestamp and prove each retained feature was available by that time. Add schema and unit tests for this firewall.
- Use repeated, nested, patient-level stratified cross-validation for internal development; report the complete fold design and event counts. It is **internal validation only**. The same 303-row cohort cannot serve as independent external validation. Bootstrap confidence intervals at patient level; keep all transformations within folds.
- Calibrate only with a prespecified, cross-fitted method if event counts support it. With this small sample, isotonic calibration is likely unstable. If calibration has not been demonstrated, call the output a *model score*, not a calibrated probability. Never present a confidence interval or individual certainty estimate unless its method has been validated.
- Explain with coefficients for logistic models and/or SHAP for supported models. Show a few patient-level contributors alongside the actual value, unit, source and direction; flag imputed values. Explanations describe model associations, not causation. Report explanation stability across folds and do not translate feature attribution into anatomical location.

### 3.3 Evaluation and clinical benchmarks

For each of the four endpoints report prevalence and confusion matrix at a **predeclared, clinically reviewed** operating point; accuracy, precision, recall/sensitivity, specificity, F1, ROC-AUC, PR-AUC, PPV/NPV, Brier score, calibration plot and calibration slope/intercept, with confidence intervals. Include subgroup performance and missingness; use decision-curve analysis only when a relevant clinical decision and threshold are defined. Compare against the simple baseline, not only against other ML models. There is no universal AUC cutoff that makes this clinically safe: cardiology and statistics leads must set acceptable false-negative/false-positive trade-offs before evaluation. No prospective claim, alert threshold, or deployment gate is passed by cross-validation alone. Follow TRIPOD+AI reporting principles. ([R8])

**External gate:** Obtain an independent, representative, adequately powered cohort with the same label definition and pre-prediction features. Validate calibration and operating characteristics; then run prospective *silent mode* (no clinician-facing action), followed by usability/workflow evaluation. Size the validation cohort around confidence-interval precision and expected event counts, not a generic row-count rule. Monitor prevalence, calibration, feature missingness, subgroup performance and drift; freeze/version every model update.

### 3.4 Output contract and risk stratification

`POST /v1/predictions` returns `prediction_id`, `as_of`, `model_id/version`, `input_quality`, `in_scope`, and one object per target: `{estimate_type, probability_or_score, calibration_status, stratum, explanation[]}`. Each vessel object includes a stable `anatomy_id` (`coronary.lad`, `.lcx`, `.rca`) and a status of `estimated`, `not_estimable` or `out_of_scope`. Do not claim a joint probability distribution from four independent heads; surface discordance rather than forcing it away.

MVP shows numeric outputs with “research / not calibrated” as applicable; no red/amber/green clinical bands. Configure `low/intermediate/high` only after clinical thresholds are approved and validated for that exact endpoint/population. A future-event result must separately name calculator, outcome, horizon, eligible population and version; it has no vessel-level map.

---PAGEBREAK---

## 4. 3D visualization, API and clinician workflow

### 4.1 Renderer and anatomical asset

**Proposed production renderer:** React + TypeScript + React Three Fiber (Three.js/WebGL2), loading a compressed `.glb`/glTF heart and coronary tree. The current hackathon build uses React with direct Three.js/WebGL rather than React Three Fiber; it creates a procedural schematic without an external mesh. Either approach can run in a standard browser without a GPU-specific runtime, and React state can bind selected vessels to the model response. A translucent torso silhouette is optional context; the heart/coronaries are the MVP focus. Use a license-cleared, provenance-tracked model from an approved open resource (e.g., BodyParts3D/NIH 3D) or a commissioned mesh. Confirm the asset license and have a cardiologist/anatomist review vessel naming, laterality, branching and view orientation before release. Generic atlas anatomy must be labeled **illustrative, not patient-specific**.

Maintain an asset manifest mapping stable IDs to mesh nodes, display labels, source, license, coordinate orientation and asset version. Keep the mapper independent from the ML service: `coronary.lad → prediction.targets.lad`. Only color the whole LAD/LCX/RCA structure when that is the model’s output. No artery-segment hotspot, stenosis geometry or myocardial-wall heat map without validated segment-level labels and imaging-grounded coordinates.

### 4.2 Encoding and interaction

Use a neutral gray for unavailable/out-of-scope outputs and a perceptually ordered, color-vision-safe sequential ramp for scores; never rely on red/green alone. Provide a legend, numeric score, endpoint definition, calibration status and visible warning. Selecting an artery highlights it and opens a detail panel: model output, validation status, feature contributors, input values/units/source/time, and limitations. Include orbit/rotate, zoom, pan, reset, anterior/posterior presets, keyboard-accessible selection and textual alternatives. Optional cutaway/cross-section is a later illustrative view, not patient imaging. Show RWMA in the feature panel only; never use it to invent a 3D location.

### 4.3 Clinician workflow

1. Authenticate with SSO; launch in patient context or choose a permitted synthetic/de-identified case.
2. Review the imported measurements, units, provenance, dates, missing/out-of-range flags and prediction timestamp; confirm or correct before analysis.
3. Request prediction; API revalidates schema and scope, runs inference, and returns outputs with model version and data-quality status.
4. Inspect the 3D overview, select vessels, review the explanation and limitations. Clinician remains responsible for interpretation; there is no auto-triage, auto-order or auto-treatment.
5. In MVP, export a research report only. EHR write-back requires separate approval, content mapping and audit design.

### 4.4 Performance and service interface

Use lazy-loaded, decimated anatomy; preserve artery geometry while reducing heart-mesh detail; compress mesh/textures; avoid per-frame React rerenders and dispose GPU resources. Initial targets on a reference clinical workstation with integrated graphics: **≥30 fps at 1080p** during interaction, model asset **≤8 MB** compressed, API inference **p95 <500 ms** on CPU, and visible map update **<100 ms** after response. Measure on representative browsers/workstations and revise budgets from tests; no server-side GPU is required.

OpenAPI endpoints: `POST /v1/predictions` (validated snapshot; idempotency key), `GET /v1/model-info`, `GET /v1/health`. Return `request_id`, normalized-input summary, exact version, endpoint/horizon, scores, calibration/in-scope flags, explanation and non-actionable limitations. Never return raw training rows or expose model internals/identifiers. Use HTTPS, OAuth/OIDC access token, authorization on every patient reference, rate limits and audit events; API errors must fail closed. Paginate patient worklists and score on demand for multi-patient use.

---PAGEBREAK---

## 5. Technology, clinical integration, privacy and regulatory plan

### 5.1 Build stack and deployment

| Layer | Recommended starting choice | Rationale |
|---|---|---|
| Web / 3D | React, TypeScript, React Three Fiber, Three.js, glTF/GLB | Interactive browser renderer; no dedicated GPU or plug-in. |
| API | Python 3.12, FastAPI, Pydantic, OpenAPI | Shares validation/model ecosystem; typed contract. |
| ML / explainability | scikit-learn; SHAP where supported; NumPy/pandas | Auditable small-tabular-data baseline; CPU inference. |
| Persistence | PostgreSQL + encrypted object storage | Relational audit/metadata and versioned datasets/artifacts. |
| MLOps / delivery | MLflow or equivalent registry; Docker; CI/CD; IaC | Reproducibility, approvals, rollback and environment parity. |
| Identity / hosting | OIDC/SSO, RBAC; private hospital environment or approved managed cloud | Least privilege; use cloud only after security, residency and contractual review. |

Suggested repo boundaries: `/web`, `/api`, `/ml/{data,features,training,evaluation}`, `/contracts`, `/infra`, `/docs`. Pin dependencies; generate API types from OpenAPI; sign/checksum model bundles; load only reviewed artifacts. Do not load untrusted pickle files. CI runs schema/leakage tests, unit/integration tests, accessibility checks, dependency/container scans and reproducibility checks. Separate dev/test/prod; synthetic data in non-production.

### 5.2 EHR and operational integration

Use SMART App Launch with least-privilege patient-level read scopes and FHIR R4 mappings; retrieve only data needed for the selected patient and encounter. No write scopes in MVP. Verify code-system mappings and local FHIR profiles with each EHR; store source resource/version and effective time. Frontend never calls `localhost` or a database; use same-origin API routes or a server-side proxy. Pilot requires clinical-informatics sign-off, downtime behavior, audit review, training and a rollback plan.

### 5.3 Privacy and security controls

Determine jurisdiction, controller/processor/covered-entity roles, lawful basis, purpose, consent/notice and retention with counsel before real patient data. HIPAA applies when the deployment is within its scope; include risk analysis, access controls, audit, transmission/security safeguards and required business-associate terms. For GDPR-covered processing, health data is special-category data: establish both an Article 6 lawful basis and Article 9 condition, minimize data and assess DPIA/transfer obligations. ([R4], [R5])

For India deployment, assess the DPDP Act 2023 and DPDP Rules 2025; commencement is phased, so verify which provisions apply on the actual launch date and build toward the full control set. Add purpose limitation, clear notices, access/deletion workflows as legally applicable, breach handling and vendor controls. The current CDSCO Medical Device Software guidance under MDR-2017 should be included in the Indian classification review. ([R6], [R7])

Baseline safeguards: encryption in transit/at rest, managed keys, MFA, site/role isolation, minimum-scope tokens, session timeout, tamper-evident audit, secrets manager, backup/restore and incident response, vulnerability management, SBOM, penetration test, no PHI in logs, and tested deletion. Cloud provider must meet the jurisdiction’s contracting and security requirements (e.g., BAA where required); a “healthcare-ready” hosting claim alone is insufficient.

### 5.4 Medical-device and clinical safety pathway

Before any clinical pilot or marketing, approve intended use, target user/population, outputs and claims; complete a software-function and risk classification with regulatory counsel. FDA’s current CDS guidance was updated in January 2026; FDA/CDSCO classification turns on function and intended use, not a banner or disclaimer. A patient-specific CAD diagnosis/probability and anatomical overlay may be a regulated medical-device software function—do not assume a non-device CDS exemption. If regulated, plan the applicable quality system/design controls, software lifecycle, risk management, cybersecurity, usability/human-factors evidence, clinical evaluation and submission pathway (e.g., U.S. 510(k)/De Novo only as determined by FDA counsel). ([R2], [R7])

---PAGEBREAK---

## 6. Delivery plan, staffing, blockers and release gates

### 6.1 Milestones (16-week research prototype; production is separate)

| Weeks | Milestone / exit artifact |
|---|---|
| 0–2 | **Scope:** clinician-approved intended use, endpoints/data dictionary, dataset/license/ethics review, jurisdiction and regulatory/privacy owners. |
| 2–4 | **Data:** immutable UCI import, schema/unit/quality report, feature manifest, leakage tests and synthetic fixtures. |
| 4–7 | **Models:** four baseline heads, nested-CV metrics/CIs, calibration status, explanation checks and model card. No performance claim before review. |
| 5–10 (parallel) | **3D + integration:** licensed/reviewed mesh, dashboard, data-review flow, API, audit trail and model-to-vessel contract tests. |
| 11–16 | **Prototype review:** security/accessibility/performance tests, clinician usability on synthetic/de-identified cases, demo and external-validation go/no-go. |

**Not production:** independent validation, approved thresholds, prospective silent mode, human-factors evidence, monitoring, privacy/security sign-off and regulatory determination remain required. This plan establishes no clinical effectiveness or clearance.

### 6.2 Team and capacity

Plan **5–7 blended FTE for 16 weeks**: cardiology/product 0.3–0.5; clinical informatics/FHIR 0.5; ML 1; API 1; frontend/3D 1; QA 0.5; UX 0.3; DevSecOps 0.3–0.5; biostatistics 0.3–0.5; privacy/regulatory 0.2–0.3. Reserve clinical, statistics, security and regulatory effort from kickoff.

### 6.3 Blockers before real-data or clinical use

1. **Data:** verify actual file, feature dictionary, label derivation/timing, license and pre-angiography availability.
2. **Claim:** choose jurisdiction, user, population, setting and prediction time; specify whether “overall risk” means present CAD or a named future event/horizon.
3. **Evidence:** obtain an independent representative cohort and statistical plan; this cross-sectional dataset cannot train future-event risk.
4. **Governance:** resolve ethics, lawful basis, privacy/hosting terms and medical-device classification/pathway.
5. **Anatomy/thresholds:** secure mesh license and specialist review; approve risk-band thresholds or show continuous research scores only.

### 6.4 Risks and controls

| Risk | Control / stop condition |
|---|---|
| Small cohort or population shift | Research demo only; block clinical claims until independent validation. |
| Leakage / post-test features | Allowlist, timestamp review and forbidden-column tests; stop on any leakage. |
| False localization / automation bias | Vessel-level map only; show evidence/limits; no autonomous action; clinician review. |
| PHI breach / cross-site mix-up | Least privilege, tenant isolation, encryption, audit, no PHI logs; no PHI before sign-off. |
| License, performance or regulatory rework | Record mesh provenance; benchmark integrated-GPU fallback; classify intended use before pilot. |

### 6.5 Release acceptance

- [ ] `CAD/LAD/LCX/RCA/Cath` are excluded from all predictors; automated tests enforce it.
- [ ] Every result is traceable to source, units, timestamp, manifest, preprocessing, model version and request ID.
- [ ] Track A metrics plus calibration, PR-AUC and confidence intervals are reported and clinically/statistically reviewed.
- [ ] UI separates prevalent CAD from future risk and makes no unsupported lesion localization; invalid input returns `not_estimable`.
- [ ] Visible disclaimer, accessible non-color-only legend, security/performance tests, model approval and rollback pass.

### References

- **R1.** [UCI Z-Alizadeh extension](https://archive.ics.uci.edu/dataset/411/extention+of+z+alizadeh+sani+dataset)
- **R2.** [FDA CDS guidance, January 2026](https://www.fda.gov/media/109618/download)
- **R3.** [HL7 SMART App Launch / FHIR R4](https://hl7.org/fhir/smart-app-launch/)
- **R4.** [HHS HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- **R5.** [EU GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj)
- **R6.** [India DPDP Rules 2025](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf)
- **R7.** [CDSCO MDSW guidance 2026](https://cdsco.gov.in/opencms/export/sites/CDSCO_WEB/Pdf-documents/Guidance-document-on-Medical-Device-Software-under-MDR-2017.pdf)
- **R8.** [TRIPOD+AI (BMJ 2024)](https://doi.org/10.1136/bmj-2023-078378)
- **R9.** [AHA PREVENT FAQs](https://professional.heart.org/en/-/media/PHD-Files/Guidelines-and-Statements/PREVENT/PREVENT-FAQs-FINAL.pdf?sc_lang=en)
