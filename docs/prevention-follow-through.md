# CardioLens prevention follow-through: product and evidence proposal

**Status:** research concept, 30 October 2026. This is not a clinical system or a validated future-event prediction. No real patient data may be entered in this prototype. Do not use it for diagnosis, prioritization or treatment.

## Proposed idea

Build a clinician-supervised primary-prevention workflow that connects an evidence-based, locally assessed 10-year cardiovascular risk model to the steps that follow: screening, review, a jointly agreed plan and follow-up. Its differentiator would be a **closed-loop prevention pathway** for resource-constrained Indian settings: an explicit no-result state when data are incomplete, patient-consented follow-up, multilingual patient communication reviewed by clinicians, and auditable task completion. These are product hypotheses—not proof of uniqueness or impact. Existing services, including the Simple hypertension-management app and Indian public-sector NCD workflows, already address parts of this problem; discovery should identify gaps and avoid duplicating or disrupting them.

A 10-year risk model estimates population-based event probability; it does not detect an imminent heart attack or guarantee an outcome. Cardiovascular symptoms and emergencies need normal urgent-care pathways, not this application. Neither the existing CAD research score nor the 3D schematic estimates future risk.

## Evidence and rationale

- An observational assessment of public facilities in 18 Indian districts found 32.1% of eligible outpatient attendees were screened for hypertension, and estimated missed detection opportunities. Its numbers reflect the studied sites and methods, not all Indian clinics. [Study](https://bmcpublichealth.biomedcentral.com/articles/10.1186/s12889-025-22284-4).
- An Indian cross-sectional analysis applied the WHO South Asia non-laboratory chart, demonstrating feasibility of risk estimation with routine inputs, not validation against observed future events in that dataset. [Study](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2024.1407918/full).
- A Malaysian longitudinal validation found meaningful variation in calibration across risk equations; results from Malaysia must not be assumed to hold in India. [Study](https://www.thelancet.com/journals/lanwpc/article/PIIS2666-6065(23)00060-3/fulltext).
- A 2026 multinational evaluation found generally favorable performance of PREVENT and SCORE2, but noted limited Asia/Other evidence and the need for further investigation. This does not establish performance in the target clinics. [Study](https://www.nature.com/articles/s41591-026-04437-z).
- [TRIPOD+AI](https://www.bmj.com/content/385/bmj-2023-078378) supports transparent reporting; it is not validation or certification. A meaningful evaluation also needs calibration, subgroup results, clinical utility, workflow and safety evidence.

## What is implemented now

The in-memory demo presents five fictional identifiers in five administrative stages. Users can filter, move one case forward/back one step, inspect simple synthetic counts and reset. The figures are *simulation counts*, not clinic metrics. No names, measurements, free-text notes, persistence, messaging, prediction, urgency, triage, patient import, identity matching or scheduling are implemented. Refresh loses changes. A stage change is a user action, not evidence a clinical event occurred. The stages are deliberately simplified and do not cover non-linear care, missed appointments, refusals or eligibility.

## Next design stages (not implemented)

1. **Discovery and governance:** recruit clinicians, community health workers and patient representatives; observe real screening and follow-up workflows; obtain hospital, ethics, legal and security approvals; document existing NCD tools and integration constraints. Define target users, eligibility, consent and how urgent symptoms bypass this workflow.
2. **Model comparison:** assess WHO South Asia 2019 lab/non-lab charts and any relevant locally recommended equation. Confirm exact event definition, age range, population, data types, units, model specification, implementation rights and setting. Do not substitute variables or convert the current CAD score. Select and freeze one model only after clinical review; validate on geographically and temporally independent longitudinal cohorts and in key subgroups before considering use. Predefine abstention and failure modes.
3. **Workflow infrastructure:** identity reconciliation, access controls, consent/permissions, explicit eligibility and opt-out, source provenance and timestamps, idempotent events, audit logs, staff assignment, task closure and correction. Handle duplicate encounters, invalid data, pregnancy, pre-existing CVD, missing values, referrals outside the system, staff handoff, declined care and lost-to-follow-up explicitly. Model the stages as independently verifiable events, not a linear demo progression.
4. **Communications:** design opt-in, language-appropriate, privacy-preserving reminders co-designed with patients. Validate consent, number ownership, contact preferences and delivery state. Do not include health details in messages unless explicitly approved; never equate sent, delivered or read with care completed. Add escalation and manual review for non-delivery. Avoid worsening access inequities where phones or literacy are limited.
5. **Interoperability and security:** assess FHIR/SMART and DICOM only when relevant to existing systems. Map patient, encounter, observations and care plans to actual workflows; implement encryption, tenant isolation, identity matching, audit, retention/deletion, breach response, and threat-model/vendor review. Offline-first synchronization requires conflict resolution, device security and a separate safety design; it is not currently implemented.
6. **Safety and regulatory:** conduct ISO 14971-style hazard analysis; assess software-device status and applicable CDSCO requirements and privacy law with specialists. Follow appropriate quality and clinical evaluation processes; no clinical launch based on a disclaimer alone.

## Research protocol outline

**Population and outcome.** Adults without defined pre-existing CVD presenting for primary prevention, with prespecified age, location and exclusion criteria. Define incident fatal/nonfatal myocardial infarction and stroke precisely, index time, event source, adjudication and 10-year horizon. Confirm candidate model outcomes are compatible before comparisons.

**Retrospective external validation.** Freeze each candidate implementation; use independent, representative Indian longitudinal data, not the existing 303-record angiography data. Prespecify sample size by precision, site and temporal separation, label adjudication, missingness, censoring and competing risks. Report discrimination, calibration curves and calibration-in-the-large, slope, uncertainty, subgroup performance, missing-input/no-result frequency and decision-curve analysis where appropriate. Compare unmodified models before any recalibration; if updating, validate on another untouched dataset. Avoid claims of superiority based on AUC alone.

**Prospective evaluation.** First conduct a silent observational study with required institutional/ethics approval and no effect on clinical care. Then, only when permitted, a supervised implementation study comparing usual care to the workflow; pre-register endpoints and analysis, and include human-factors assessment. Depending on the question and feasibility, use a cluster randomized or carefully controlled design. Track screening completion (eligible encounters with screening / eligible encounters), review completion (eligible screened cases reviewed / eligible screened cases), documented follow-up completion (eligible cases with completed follow-up / eligible cases assigned follow-up), time to follow-up, false matches, exclusions, refusal, missingness, alert burden and differences by demographic/access subgroup. Specify observation windows, denominators, data sources, competing events and loss to follow-up in advance. Measure patient-centered outcomes and harms over sufficient time; improved task completion is not proof of fewer deaths.

**Release gates.** Document clinical benefit and risks, performance acceptance criteria based on intended use, safety and usability, security review, regulatory determinations/authorizations, deployment governance, incident response and ongoing monitoring. A research study, local calibration or high benchmark score alone is not a release approval.

## Links

- [Previous prevention-risk plan](prevention-risk-plan.md)
- [Full product blueprint](product-blueprint.md)
- [Current model card](model-card.md)
