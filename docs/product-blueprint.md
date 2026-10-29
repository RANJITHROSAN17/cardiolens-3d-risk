# CardioLens: research-to-product blueprint

Status: planning document, 30 October 2026. This repository remains a research demonstration, not a medical device ready for use on patients. Obtain clinical, regulatory, legal and security advice for the intended markets before deployment.

## 1. Choose one clinical problem first

Recommended first product hypothesis: support a clinician in reviewing *existing* coronary artery disease from an eligible coronary CT angiography (CCTA) scan, rather than claiming to predict heart attacks. Define exactly what is measured, intended users, patient population, setting, scan quality and contraindications, inputs, outputs, reference standard, and actions enabled. It must not independently diagnose, prioritize emergencies, or recommend treatment without a separately justified and validated claim. Have cardiologists and radiologists sign off on the intended-use statement.

This is **not** the same as early future-event prediction. The current 303-record model estimates source-cohort prevalent CAD/vessel labels, not a future heart attack, stroke, recovery or mortality risk. Its generic heart is not a scan; its vessel scores do not locate stenosis. Internal cross-validation is not proof of real-world performance. Optimizing one benchmark or adopting a larger neural network cannot guarantee the highest or safe results.

Alternative product: a prevention support tool for a precisely defined population with longitudinal outcomes and a specified prediction horizon. Validate an appropriate existing risk equation locally, subject to licensing and clinical review, before deciding whether a new model is justified. Do not reuse the current model as an event predictor.

## 2. MVP gates and deliverables

1. **Discovery:** interview patients, clinicians, IT and administrators; map decision, existing standard of care, workflow, failure costs, target population and desired measurable benefit. Assemble clinical and regulatory advisors.
2. **Technical research only:** use properly licensed, de-identified research CCTA data with permissions; prove secure ingestion, image quality checks and basic image display. No real patient uploads in this prototype.
3. **Retrospective research:** test locked algorithms on geographically and temporally independent institutions, with prespecified analyses and robust ground truth. Document model failures and subgroup performance.
4. **Prospective silent study:** run on eligible cases without showing predictions to care teams or affecting care, with ethics and institutional approval. Verify workflow, missing data, image quality, performance and monitoring.
5. **Supervised clinical study:** only after appropriate regulatory and ethics authorization, compare usual care against workflow with the tool; measure patient outcomes and unintended harms, not just AUC. Proceed based on predefined criteria.
6. **Market release:** only after required authorizations and quality, security, human-factors and deployment evidence are complete. Post-market monitoring and change control continue thereafter.

## 3. Imaging architecture

- DICOM ingestion: research-only drag-and-drop/series upload with explicit size and count limits, file-type and DICOM validation, malware scanning, quotas, and no silent uploads. DICOM often contains identifiers in tags, private tags and burned-in pixels; removing headers alone is not sufficient. Have a qualified de-identification pipeline and human review before use. Do not log image metadata or patient identifiers. Only use approved data under governance agreements.
- Backend: isolated ingestion service using pydicom, supported codecs, and optionally a DICOM server such as Orthanc; store original series and derived data separately, encrypted, with retention controls and audit logs. Consider DICOMweb for approved PACS connectivity; TLS, authentication and least privilege are mandatory.
- Image QA: select the correct series, verify modality, orientation, pixel spacing, contrast phase, slice consistency and completeness; detect unsupported scans, motion, metal artifacts, stents or poor quality; report "not analyzable" rather than fabricating a result. Explicitly constrain which scanners and protocols have validation.
- Segmentation research: investigate MONAI/PyTorch with clinically annotated CCTA datasets; version preprocessing, model, software and artifact hashes. Produce masks, confidence/quality signals and optional meshes; Three.js can render derived geometry, but a medical-image viewer must show source slices alongside overlays and enable clinician review. Render each case as patient-specific only when proven linked to that scan; never map tabular scores onto a schematic as a lesion.
- Validation: compare segmentation to expert labels (e.g., Dice, surface distances), and stenosis classification/localization to appropriate expert and reference standards. Prespecify how to handle inter-reader disagreement, multiple lesions, artifacts, missing segments and insufficient scans. Measure patient-level harms and incorrect/failed analyses, not only visual quality.
- Future direction: angiography and CCTA are different modalities and require separate intended use, datasets, preprocessing and validation. FFR-CT, plaque characterization, lesion quantification and treatment recommendations are separate high-risk claims; do not imply they exist.

## 4. Clinical workflow and integration

- Design a clinician worklist with authorized identities, source study, status, date, provenance and explicit review state. No automatic red/yellow/green clinical triage until thresholds, harms, operating context and actionability are validated and approved. Separate demo data from patient data.
- Use SMART on FHIR and HL7 FHIR for authorized launch and clinical context where supported; map Patient, Observation, DiagnosticReport and ImagingStudy with explicit units, codes, time stamps and data freshness. Enforce patient and encounter matching, provenance, conflict resolution and missing-data handling. Support hospital PACS through appropriate DICOMweb interfaces.
- Show model/version, intended population, data sources, limitations, confidence/quality limitations, and a clear no-result state; retain source image access and clinician override. Provide correction and escalation workflows. Do not introduce alert fatigue or conceal missing data behind a score.
- Perform clinical workflow simulations and usability studies, including erroneous patient selection, incomplete studies, failures and handoffs. Test accessibility, screen sizes and languages with intended users.

## 5. Data and model evidence plan

- Obtain governance approvals, data-use agreements, participant/ethics permissions as applicable, and documented dataset rights. UK Biobank and MIMIC require controlled access and are not automatically appropriate for coronary imaging or vessel stenosis labels. Assess population, modality, outcome, label quality and licensing first.
- Separate patients and sites between development and validation; prevent duplicates, temporal leakage and use of post-outcome variables. Define ground truth and adjudication before training. Independently validate with Indian and other relevant populations, multiple sites, equipment, ages, sexes and disease subgroups; define minimum subgroup sample sizes and confidence intervals.
- For binary outcomes report sensitivity, specificity, PPV/NPV at prespecified thresholds, ROC/PR AUC, uncertainty intervals, calibration plots/slope/intercept and decision-curve or clinical utility analysis where appropriate. For event prediction specify outcome, horizon, censoring, competing risks and validation design. Show unassessable-case rates and evaluate failures as well as successes.
- Predefine acceptance criteria with clinicians and regulators based on harms, benefit, baseline practice and sample-size calculations. Compare to standard care and validated alternatives. Record dataset/model lineage, locked test data, versions, model card and reproducible evaluation. Evaluate bias and performance drift; freeze models for regulated releases and apply controlled change management.

## 6. Privacy, security and operations

No real identifiers or health data in the current prototype. For a future production system: threat-model every workflow; encrypt in transit and at rest; manage keys, roles, access and consent/permissions; implement audit trails, secure backups, deletion/retention, breach response, vendor agreements and penetration testing. Isolate tenants; minimize data and telemetry; do not send patient data to external AI services without approved agreements and appropriate safeguards. Secure software supply chain, signed releases, SBOM, dependency scanning and disaster recovery. Evaluate applicable Indian DPDP requirements and rules, contractual obligations and any other relevant law; US HIPAA and EU GDPR apply only when their conditions are met. De-identification is not a guarantee of anonymity.

## 7. Regulatory and quality workstream

- Determine whether each specific claim/function is regulated, intended users and jurisdiction; get written advice from qualified specialists and engage regulators early. In the US, 510(k) is not universally mandatory: classification and pathway could be 510(k), De Novo, PMA, exempt, or not a device depending on intended use and circumstances. FDA's [2026 clinical decision support guidance](https://www.fda.gov/media/109618/download) explains device/non-device distinctions.
- EU: determine MDR/IVDR qualification and classification, applicable conformity assessment and notified-body involvement; MDR Rule 11 can apply to decision software. Consider AI Act interactions and current transitional dates with counsel. See the [European Commission guidance index](https://health.ec.europa.eu/medical-devices-sector/new-regulations/guidance-mdcg-endorsed-documents-and-other-guidance_en).
- India: assess intended use, class and applicable licensing under Medical Devices Rules 2017 with CDSCO and local experts; see [CDSCO medical-device software guidance](https://cdsco.gov.in/opencms/export/sites/CDSCO_WEB/Pdf-documents/Guidance-document-on-Medical-Device-Software-under-MDR-2017.pdf). Do not assume one classification applies to all features.
- Build a quality management system appropriate to target markets (e.g., ISO 13485); risk management (ISO 14971), software lifecycle (IEC 62304), usability (IEC 62366-1), cybersecurity, clinical evaluation, traceability, verification/validation, incident handling and post-market surveillance. Applicability and conformity must be assessed for the product; citing standards alone is not compliance.

## 8. Concrete next sprint

1. Obtain clinical partner and write one-page intended-use/non-use statement and hazard log; explicitly identify false-negative, wrong-patient, out-of-distribution, failed-upload and automation-bias hazards.
2. Keep the present app synthetic only. Add research-only image ingestion only after the dataset and de-identification workflow are approved. Add a local, clearly labeled sample study viewer with no scoring before considering segmentation.
3. Design a schema and test plan for image series, QA, derived masks, versioned model results and review status. Document architecture and retention before adding any production storage.
4. Draft retrospective study protocol and identify independent datasets/sites; calculate sample sizes and prespecify acceptance criteria with clinical/statistical partners.
5. Consult CDSCO/regulatory counsel, a privacy professional and target hospitals before integrating real patient data or publishing clinical claims.

## Current change in this workspace

Frontend now blocks incomplete, out-of-range or unsupported entries before both local and remote scoring, invalidates stale requests when the case changes, and fails closed on remote API errors rather than quietly producing a synthetic result. These are prototype safety improvements, not validation, security certification, imaging support or regulatory approval. Run `node --test tests/*.test.js` and `npm run build`.
