import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  NON_CLINICAL_DISCLAIMER,
  REPORT_SCHEMA_VERSION,
  REPORT_TOP_LEVEL_FIELDS,
  buildResearchReport,
  researchReportFilename,
  serializeResearchReport,
} from '../src/research-report.js';

const features = {
  age: 58, sex: 'Female', bmi: 27.4, diabetes: false, hypertension: true,
  smoking: false, ex_smoker: false, family_history: true, systolic_bp: 138,
  pulse_rate: 74, typical_chest_pain: false, st_elevation: false,
  st_depression: false, t_inversion: true, lvh: false, fbs: 96, tg: 154,
  ldl: 122, hdl: 48, ef_tte: 55, region_rwma: 0, vhd: 'N',
};

const syntheticPrediction = {
  status: 'ok',
  mode: 'synthetic_demo',
  model_id: 'synthetic-score-v0.2',
  model_version: '0.2.0-demo',
  calibration_status: 'not_calibrated_synthetic',
  results: {
    cad_present: { score: 0.42, estimate_type: 'synthetic_demo_score', status: 'estimated' },
    vessels: {
      lad: { score: 0.39, estimate_type: 'synthetic_demo_score', status: 'estimated' },
      lcx: { score: 0.31, estimate_type: 'synthetic_demo_score', status: 'estimated' },
      rca: { score: 0.35, estimate_type: 'synthetic_demo_score', status: 'estimated' },
    },
  },
  explanation: [
    { label: 'Age', value: '58', unit: 'years', contribution: 0.12, direction: 'raises demo score', patient_id: 'must-not-copy' },
  ],
  future_risk: { status: 'unavailable', reason: 'No longitudinal future-event model is included.' },
  limitations: ['Synthetic demo only.', 'Not a clinical probability.'],
};

const trainedPrediction = {
  ...syntheticPrediction,
  mode: 'trained_research',
  model_id: 'z-alizadeh-logistic-baseline',
  model_version: 'research-1.1.0',
  calibration_status: 'uncalibrated_research',
  results: {
    cad_present: { score: 0.51, estimate_type: 'uncalibrated_research_model_score', status: 'estimated' },
    vessels: {
      lad: { score: 0.47, estimate_type: 'uncalibrated_research_model_score', status: 'estimated' },
      lcx: { score: 0.33, estimate_type: 'uncalibrated_research_model_score', status: 'estimated' },
      rca: { score: 0.38, estimate_type: 'uncalibrated_research_model_score', status: 'estimated' },
    },
  },
};

const bundleSha256 = 'a'.repeat(64);

test('research report has a deterministic self-describing structure', () => {
  const report = buildResearchReport({ features, prediction: syntheticPrediction });
  const secondReport = buildResearchReport({ features, prediction: syntheticPrediction });

  assert.deepEqual(Object.keys(report), REPORT_TOP_LEVEL_FIELDS);
  assert.equal(report.schema_version, REPORT_SCHEMA_VERSION);
  assert.equal(report.mode, 'synthetic_demo');
  assert.equal(report.model.model_bundle_sha256, null);
  assert.equal(report.model.model_bundle_status, 'not_applicable_synthetic_demo');
  assert.equal(report.model.scikit_learn_version, null);
  assert.equal(report.inputs.provenance, 'validated_synthetic_inputs');
  assert.equal(report.inputs.contains_identifiers, false);
  assert.deepEqual(report.inputs.features, features);
  assert.deepEqual(Object.keys(report.head_outputs), ['cad_present', 'lad', 'lcx', 'rca']);
  assert.equal(report.head_outputs.lad.score, 0.39);
  assert.equal(report.head_outputs.lad.calibration_status, 'not_calibrated_synthetic');
  assert.equal(report.disclaimer, NON_CLINICAL_DISCLAIMER);
  assert.match(report.disclaimer, /not clinical probabilities/);
  assert.equal('patient_id' in report.log_odds_contributions[0], false);
  assert.deepEqual(report, secondReport);
  assert.equal(serializeResearchReport(report), serializeResearchReport(secondReport));
  assert.equal(researchReportFilename(report), 'cardiolens-research-report-v1.0-synthetic_demo.json');
});

test('trained research reports preserve bundle hash and scikit-learn provenance', () => {
  const report = buildResearchReport({
    features,
    prediction: trainedPrediction,
    modelInfo: {
      mode: 'trained_research',
      model_bundle_sha256: bundleSha256.toUpperCase(),
      scikit_learn_version: '1.6.1',
    },
  });

  assert.equal(report.mode, 'trained_research');
  assert.equal(report.model.model_bundle_sha256, bundleSha256);
  assert.equal(report.model.model_bundle_status, 'available');
  assert.equal(report.model.scikit_learn_version, '1.6.1');
  assert.equal(report.head_outputs.cad_present.estimate_type, 'uncalibrated_research_model_score');
  assert.equal(researchReportFilename(report), 'cardiolens-research-report-v1.0-trained_research.json');
});

test('synthetic reports cannot be tied to a trained bundle hash', () => {
  const report = buildResearchReport({
    features,
    prediction: syntheticPrediction,
    modelInfo: { model_bundle_sha256: bundleSha256, scikit_learn_version: '1.6.1' },
  });

  assert.equal(report.model.model_bundle_sha256, null);
  assert.equal(report.model.scikit_learn_version, null);
});

test('research report builder refuses identifiers, unexpected keys, and invalid predictions', () => {
  for (const unsafeFeatures of [
    { ...features, patient_id: 'synthetic-id' },
    { ...features, email: 'person@example.invalid' },
    { ...features, unexpected_note: 'synthetic-value' },
  ]) {
    assert.throws(
      () => buildResearchReport({ features: unsafeFeatures, prediction: syntheticPrediction }),
      /identifier\/PHI field|not a supported input field/,
    );
  }
  assert.throws(
    () => buildResearchReport({ features, prediction: { ...syntheticPrediction, status: 'not_estimable' } }),
    /successful prediction/,
  );
  assert.throws(
    () => buildResearchReport({ features, prediction: { ...syntheticPrediction, mode: 'clinical' } }),
    /trained_research or synthetic_demo/,
  );
});
