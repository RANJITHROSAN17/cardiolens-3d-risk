# 10-year cardiovascular prevention: research plan

**Status:** planning and synthetic demonstration only; no validated future-risk model is implemented. Do not enter real patient data or use the application for patient care. The checklist is not evidence or approval.

## Product hypothesis

For adults without known cardiovascular disease, a clinician-facing tool may support shared primary-prevention discussions using an independently validated 10-year prediction of heart attack or stroke. The precise cohort, event definitions, exclusions, care setting, intended user, model output, clinical action and jurisdiction must be confirmed with clinical and regulatory partners before development of claims. A 10-year estimate does not predict whether or when an individual will experience an event and cannot be used as an emergency assessment.

The current CAD model uses cross-sectional angiographic labels, not longitudinal incident events. Do not reuse its output or vessel scores for this purpose. A 3D schematic adds no evidence of future-risk accuracy and must not suggest patient-specific lesions.

## Candidate evaluation — no model selected

1. Compare official 2019 WHO regional CVD charts and underlying technical specifications for relevant geography and population, including lab and non-lab variants. A published study describes 10-year fatal/nonfatal myocardial infarction or stroke, and laboratory inputs including age, sex, systolic BP, total cholesterol, smoking and diabetes. Confirm the correct regional mapping, exact exclusions, data definitions, implementation rights and local applicability using WHO source documentation before adoption. [Published study](https://pmc.ncbi.nlm.nih.gov/articles/PMC11403776/).
2. Compare AHA PREVENT-ASCVD equations, whose intended use and outcome are not necessarily identical to WHO charts. AHA recommends PREVENT-ASCVD for specified primary-prevention populations in its 2026 US dyslipidemia guidance; confirm inclusion criteria, outcome, required predictors, permissions and whether US-derived performance transfers to the planned Indian population. [AHA guidance summary](https://professional.heart.org/en/science-news/2026-guideline-on-the-management-of-dyslipidemia/top-things-to-know). Different equations and cutoffs cannot be interchanged.
3. Ask Indian clinicians which current local guidelines and approved tools suit the target setting, and assess external validation and calibration in representative Indian cohorts. A regional chart or international guideline is not proof of validation at a particular hospital.

Choose one equation only after a documented comparison, and separately decide whether a new model is justified. Do not invent coefficients, substitute LDL for total cholesterol, or interpolate categories without source authorization and review.

## Data and evaluation protocol

- Specify index date; adults eligible and free of defined pre-existing CVD; outcome component definitions, fatality, event ascertainment and 10-year follow-up; exclusion and re-entry rules. Account for migration, censoring, competing death, missing follow-up and interventions during follow-up.
- Obtain lawful access, data-use permissions, ethics approvals and governance. Include multiple representative sites; separate development, calibration and external validation by patient, institution and time. Prevent outcome leakage. Compute sample sizes and decision-relevant performance targets before analysis.
- Record predictor source, units, collection time, measurement method, medication context, provenance and missingness; assess whether each is available at the intended decision point. Only implement predictor fields required by the chosen equation, and avoid silently imputing or converting missing values to zero.
- Prespecify discrimination (e.g. time-dependent discrimination where appropriate), calibration-in-the-large and slope, calibration by risk range, confidence intervals, subgroup and site performance, missingness and no-result rates. Evaluate clinical usefulness and harms against usual care at pre-agreed decision thresholds. Thresholds are context-dependent and require clinical approval.
- Lock the implementation, compare against official reference examples, add boundary and missing-data tests, perform external validation and only then consider a prospective silent study. A visible clinical pilot requires the appropriate authorizations and safeguards.

## Proposed implementation sequence

1. Clinical product specification and hazard analysis; candidate equation comparison and regulatory assessment.
2. Model-specific, versioned input schema: eligibility, units, allowed ranges, time horizon, explicit missing and unsupported states. Client and server reject invalid or unknown inputs. No fallback to a different model on failure.
3. Isolated deterministic implementation with traceable model metadata, source provenance and tests against official reference cases; unit conversion and rounding tested separately. No live patient data until infrastructure and governance permit it.
4. Versioned validation pipeline and reproducible report with site/time split, model card, calibration, subgroup analysis, uncertainty and performance by missingness. Set acceptance thresholds before examining the locked test set.
5. Clinician workflow design with patient identity verification, clear ineligibility/abstention, provenance, explicit target and horizon, clinician interpretation, audit trail and no unvalidated automated actions. Build privacy, security and quality controls before any production deployment.
6. Prospective silent evaluation and, subject to required oversight, clinical impact study and post-market monitoring. Treat recalibration or equation changes as controlled changes requiring appropriate review.

See `product-blueprint.md` for imaging, integration, security, and jurisdiction-specific regulatory workstreams.
