/**
 * Bundled internal cross-validation context for the trained research baseline.
 *
 * These values mirror the compact summary in backend/artifacts/metrics.json.
 * They describe variation of the fixed research baseline across internal CV
 * folds in the n=303 source cohort. They are not patient-level confidence
 * intervals, prediction intervals, calibration guarantees, or clinical
 * probabilities, and they do not validate the synthetic demo formula.
 */

export const CV_TARGETS = ['cad_present', 'lad', 'lcx', 'rca'];
export const CV_METRICS = ['roc_auc', 'pr_auc', 'brier'];

export const CV_COHORT_NOTE = 'n=303 source cohort';
export const CV_INTERPRETATION = 'Internal CV summary only: mean ± SD across repeated stratified cross-validation folds. Not a patient-level confidence interval, prediction interval, or clinical probability.';

const metric = (mean, sd_across_folds) => ({ mean, sd_across_folds });

export const STATIC_CV_SUMMARY = {
  status: 'available',
  source: 'bundled_static',
  evaluation: 'internal repeated stratified cross-validation',
  design: {
    folds: 5,
    repeats: 5,
    total_folds: 25,
    label: '5×5 CV',
  },
  cohort_n: 303,
  cohort_note: CV_COHORT_NOTE,
  interpretation: CV_INTERPRETATION,
  summary_only: true,
  targets: {
    cad_present: {
      roc_auc: metric(0.9359138581436803, 0.025095468369989504),
      pr_auc: metric(0.9729429387182826, 0.010817556486061117),
      brier: metric(0.10195011224199295, 0.023854774368690747),
      class_counts: { positive: 216, negative: 87 },
      cohort_n: 303,
      threshold: 0.5,
      note: 'Repeated internal CV of a fixed baseline; not external validation and not a clinical benchmark.',
    },
    lad: {
      roc_auc: metric(0.8478081562881563, 0.04377496364219761),
      pr_auc: metric(0.881353096675843, 0.042270869447019625),
      brier: metric(0.15952614644072907, 0.022946456382267236),
      class_counts: { positive: 177, negative: 126 },
      cohort_n: 303,
      threshold: 0.5,
      note: 'Repeated internal CV of a fixed baseline; not external validation and not a clinical benchmark.',
    },
    lcx: {
      roc_auc: metric(0.7270963354659006, 0.04553647201645504),
      pr_auc: metric(0.5919665118656657, 0.061703840034939623),
      brier: metric(0.2154849821344844, 0.02097624843232312),
      class_counts: { positive: 119, negative: 184 },
      cohort_n: 303,
      threshold: 0.5,
      note: 'Repeated internal CV of a fixed baseline; not external validation and not a clinical benchmark.',
    },
    rca: {
      roc_auc: metric(0.7087518202621179, 0.05848206957734096),
      pr_auc: metric(0.5854024794669054, 0.08543419697484979),
      brier: metric(0.22028001483050844, 0.026747057543597245),
      class_counts: { positive: 114, negative: 189 },
      cohort_n: 303,
      threshold: 0.5,
      note: 'Repeated internal CV of a fixed baseline; not external validation and not a clinical benchmark.',
    },
  },
};

export const UNAVAILABLE_CV_SUMMARY = {
  status: 'unavailable',
  source: 'unavailable',
  interpretation: CV_INTERPRETATION,
  targets: {},
};

function isRecord(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function finiteBoundedNumber(value) {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1
    ? value
    : null;
}

function positiveInteger(value) {
  return Number.isInteger(value) && value > 0 ? value : null;
}

function nonnegativeInteger(value) {
  return Number.isInteger(value) && value >= 0 ? value : null;
}

function normalizeMetric(value) {
  if (!isRecord(value)) return null;
  const mean = finiteBoundedNumber(value.mean);
  const sd = finiteBoundedNumber(value.sd_across_folds);
  return mean === null || sd === null ? null : { mean, sd_across_folds: sd };
}

function normalizeTarget(value) {
  if (!isRecord(value)) return null;

  const normalized = {};
  for (const metricName of CV_METRICS) {
    const metricSummary = normalizeMetric(value[metricName]);
    if (metricSummary === null) return null;
    normalized[metricName] = metricSummary;
  }

  if (!isRecord(value.class_counts)) return null;
  const positive = nonnegativeInteger(value.class_counts.positive);
  const negative = nonnegativeInteger(value.class_counts.negative);
  if (positive === null || negative === null || positive + negative <= 0) return null;

  const cohortN = positiveInteger(value.cohort_n) ?? (positive + negative);
  if (cohortN !== positive + negative) return null;

  const threshold = finiteBoundedNumber(value.threshold);
  if (threshold === null) return null;

  return {
    ...normalized,
    class_counts: { positive, negative },
    cohort_n: cohortN,
    threshold,
    ...(typeof value.note === 'string' && value.note.trim() ? { note: value.note.trim() } : {}),
  };
}

/**
 * Validate an API/static CV summary and return only the fields the UI needs.
 * Incomplete or malformed summaries fail closed instead of rendering zeroes.
 */
export function normalizeCvSummary(value) {
  if (!isRecord(value) || value.status === 'unavailable' || !isRecord(value.targets)) {
    return { ...UNAVAILABLE_CV_SUMMARY };
  }

  const targets = {};
  const cohortSizes = new Set();
  for (const target of CV_TARGETS) {
    const normalizedTarget = normalizeTarget(value.targets[target]);
    if (normalizedTarget === null) return { ...UNAVAILABLE_CV_SUMMARY };
    targets[target] = normalizedTarget;
    cohortSizes.add(normalizedTarget.cohort_n);
  }
  if (cohortSizes.size !== 1) return { ...UNAVAILABLE_CV_SUMMARY };

  const cohortN = positiveInteger(value.cohort_n) ?? [...cohortSizes][0];
  if (cohortN !== [...cohortSizes][0]) return { ...UNAVAILABLE_CV_SUMMARY };

  const design = isRecord(value.design) ? value.design : {};
  const folds = positiveInteger(design.folds);
  const repeats = positiveInteger(design.repeats);
  if (folds === null || repeats === null) return { ...UNAVAILABLE_CV_SUMMARY };

  return {
    status: 'available',
    source: typeof value.source === 'string' && value.source ? value.source : 'api',
    evaluation: typeof value.evaluation === 'string' && value.evaluation
      ? value.evaluation
      : 'internal repeated stratified cross-validation',
    design: {
      folds,
      repeats,
      total_folds: folds * repeats,
      label: `${folds}×${repeats} CV`,
    },
    cohort_n: cohortN,
    cohort_note: typeof value.cohort_note === 'string' && value.cohort_note
      ? value.cohort_note
      : `n=${cohortN} source cohort`,
    interpretation: CV_INTERPRETATION,
    summary_only: true,
    targets,
  };
}

/**
 * Prefer a valid API summary. When the static site has no API summary (or an
 * API response is malformed), use the bundled research-baseline summary.
 */
export function resolveCvSummary(modelInfo) {
  const apiSummary = normalizeCvSummary(modelInfo?.cv_summary);
  return apiSummary.status === 'available' ? apiSummary : normalizeCvSummary(STATIC_CV_SUMMARY);
}

export function getTargetCvSummary(cvSummary, targetId) {
  if (!CV_TARGETS.includes(targetId)) return null;
  const normalized = normalizeCvSummary(cvSummary);
  return normalized.status === 'available' ? normalized.targets[targetId] : null;
}

export function formatMeanSd(metricSummary, digits = 3) {
  const normalized = normalizeMetric(metricSummary);
  if (normalized === null) return 'Unavailable';
  const places = Number.isInteger(digits) && digits >= 0 && digits <= 6 ? digits : 3;
  return `${normalized.mean.toFixed(places)} ± ${normalized.sd_across_folds.toFixed(places)}`;
}

export function formatCvDesign(cvSummary) {
  const normalized = normalizeCvSummary(cvSummary);
  if (normalized.status !== 'available') return 'Internal CV unavailable';
  return `${normalized.design.label} · ${normalized.design.total_folds} folds · n=${normalized.cohort_n}`;
}

export function formatClassCounts(targetSummary) {
  const normalized = normalizeTarget(targetSummary);
  if (normalized === null) return 'Source-cohort class counts unavailable';
  return `${normalized.class_counts.positive} positive / ${normalized.class_counts.negative} negative`;
}
