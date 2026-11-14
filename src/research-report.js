import { FEATURE_FIELDS, validateCase } from './validation.js';

export const REPORT_SCHEMA_VERSION = '1.0';
export const REPORT_TYPE = 'cardiolens_research_report';
export const NON_CLINICAL_DISCLAIMER = 'Research-only report based on synthetic demo inputs. Scores are uncalibrated model outputs, not clinical probabilities, diagnoses, or treatment guidance. Do not use for patient care.';
export const REPORT_TOP_LEVEL_FIELDS = [
  'report_type', 'schema_version', 'mode', 'model', 'inputs', 'head_outputs',
  'log_odds_contributions', 'contribution_basis', 'future_risk', 'disclaimer', 'limitations',
];

const REPORT_MODES = new Set(['trained_research', 'synthetic_demo']);
const SHA256_PATTERN = /^[a-f0-9]{64}$/i;

function isRecord(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function safeString(value, fallback = '') {
  return typeof value === 'string' && value.trim() ? value : fallback;
}

function headOutput(prediction, source) {
  if (!isRecord(source) || typeof source.score !== 'number' || !Number.isFinite(source.score) || source.score < 0 || source.score > 1) {
    throw new Error('Cannot build research report: prediction is missing a finite 0–1 head score.');
  }
  return {
    score: source.score,
    estimate_type: safeString(source.estimate_type, 'uncalibrated_model_score'),
    status: safeString(source.status, 'estimated'),
    calibration_status: safeString(prediction.calibration_status, 'uncalibrated'),
    interpretation: 'Uncalibrated score; not a clinical probability.',
  };
}

function reportContributions(prediction) {
  if (prediction.explanation === undefined || prediction.explanation === null) return [];
  if (!Array.isArray(prediction.explanation)) {
    throw new Error('Cannot build research report: prediction explanation must be a list.');
  }
  return prediction.explanation
    .filter((item) => isRecord(item) && typeof item.contribution === 'number' && Number.isFinite(item.contribution))
    .map((item) => ({
      label: safeString(item.label, 'Model input'),
      value: item.value === undefined || item.value === null ? '' : String(item.value),
      unit: item.unit === undefined || item.unit === null ? '' : String(item.unit),
      contribution: item.contribution,
      direction: safeString(item.direction),
    }));
}

/**
 * Build a deterministic research report from validated synthetic inputs and
 * an already-computed prediction. The builder allow-lists fields and never
 * copies case IDs, timestamps, or arbitrary prediction/input keys.
 */
export function buildResearchReport({ features, prediction, modelInfo = null } = {}) {
  const validationErrors = validateCase(features);
  if (validationErrors.length) {
    throw new Error(`Cannot build research report: ${validationErrors.join('; ')}`);
  }
  if (!isRecord(prediction) || prediction.status !== 'ok') {
    throw new Error('Cannot build research report: a successful prediction is required.');
  }

  const mode = prediction.mode || modelInfo?.mode;
  if (!REPORT_MODES.has(mode)) {
    throw new Error('Cannot build research report: prediction mode must be trained_research or synthetic_demo.');
  }
  if (!isRecord(prediction.results) || !isRecord(prediction.results.vessels)) {
    throw new Error('Cannot build research report: prediction head outputs are missing.');
  }

  const isTrained = mode === 'trained_research';
  const modelBundleSha256 = isTrained
    && typeof modelInfo?.model_bundle_sha256 === 'string'
    && SHA256_PATTERN.test(modelInfo.model_bundle_sha256)
    ? modelInfo.model_bundle_sha256.toLowerCase()
    : null;
  const scikitLearnVersion = isTrained
    ? safeString(modelInfo?.scikit_learn_version, null)
    : null;

  const orderedFeatures = {};
  for (const field of FEATURE_FIELDS) orderedFeatures[field] = features[field];

  const limitations = Array.isArray(prediction.limitations)
    && prediction.limitations.every((item) => typeof item === 'string')
    ? [...prediction.limitations]
    : [
      'Research-only output; not clinically validated.',
      'Scores are uncalibrated and must not be interpreted as clinical probabilities.',
    ];
  const futureRisk = isRecord(prediction.future_risk) ? prediction.future_risk : {};

  return {
    report_type: REPORT_TYPE,
    schema_version: REPORT_SCHEMA_VERSION,
    mode,
    model: {
      model_id: safeString(prediction.model_id || modelInfo?.model_id, 'unknown'),
      model_version: safeString(prediction.model_version || modelInfo?.model_version, 'unknown'),
      calibration_status: safeString(prediction.calibration_status || modelInfo?.calibration_status, 'uncalibrated'),
      model_bundle_sha256: modelBundleSha256,
      model_bundle_status: isTrained
        ? (modelBundleSha256 ? 'available' : 'unavailable')
        : 'not_applicable_synthetic_demo',
      scikit_learn_version: scikitLearnVersion,
    },
    inputs: {
      provenance: 'validated_synthetic_inputs',
      contains_identifiers: false,
      features: orderedFeatures,
    },
    head_outputs: {
      cad_present: headOutput(prediction, prediction.results.cad_present),
      lad: headOutput(prediction, prediction.results.vessels.lad),
      lcx: headOutput(prediction, prediction.results.vessels.lcx),
      rca: headOutput(prediction, prediction.results.vessels.rca),
    },
    log_odds_contributions: reportContributions(prediction),
    contribution_basis: isTrained
      ? 'Local linear log-odds contributions for the overall CAD head; not causal effects or treatment guidance.'
      : 'Synthetic demo logit contributions; not trained-model log-odds, causal effects, or clinical explanations.',
    future_risk: {
      status: safeString(futureRisk.status, 'unavailable'),
      reason: safeString(futureRisk.reason, 'No longitudinal future-event model is included.'),
    },
    disclaimer: NON_CLINICAL_DISCLAIMER,
    limitations,
  };
}

export function serializeResearchReport(report) {
  if (!isRecord(report)) throw new Error('Cannot serialize research report: report must be an object.');
  return `${JSON.stringify(report, null, 2)}\n`;
}

export function researchReportFilename(report) {
  const mode = isRecord(report) && REPORT_MODES.has(report.mode) ? report.mode : 'synthetic_demo';
  return `cardiolens-research-report-v${REPORT_SCHEMA_VERSION}-${mode}.json`;
}
