import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  CV_TARGETS,
  STATIC_CV_SUMMARY,
  formatClassCounts,
  formatCvDesign,
  formatMeanSd,
  getTargetCvSummary,
  normalizeCvSummary,
  resolveCvSummary,
} from '../src/model-metrics.js';

const artifact = JSON.parse(readFileSync(new URL('../backend/artifacts/metrics.json', import.meta.url), 'utf8'));

test('bundled static CV summary matches the metrics artifact without fold-level payloads', () => {
  assert.equal(STATIC_CV_SUMMARY.cohort_n, 303);
  assert.equal(STATIC_CV_SUMMARY.design.folds, 5);
  assert.equal(STATIC_CV_SUMMARY.design.repeats, 5);
  assert.equal(STATIC_CV_SUMMARY.design.total_folds, 25);
  assert.equal('fold_metrics' in STATIC_CV_SUMMARY, false);

  for (const target of CV_TARGETS) {
    const bundled = STATIC_CV_SUMMARY.targets[target];
    const source = artifact[target];
    assert.equal(source.folds, STATIC_CV_SUMMARY.design.folds);
    assert.equal(source.repeats, STATIC_CV_SUMMARY.design.repeats);
    assert.deepEqual(bundled.class_counts, source.class_counts);
    assert.equal(bundled.cohort_n, source.class_counts.positive + source.class_counts.negative);
    assert.equal(bundled.threshold, source.threshold);
    for (const metric of ['roc_auc', 'pr_auc', 'brier']) {
      assert.deepEqual(bundled[metric], source.summary[metric]);
    }
  }
});

test('CV formatting shows mean ± SD across folds and never fabricates missing values', () => {
  assert.equal(formatMeanSd({ mean: 0.8478, sd_across_folds: 0.04377 }), '0.848 ± 0.044');
  assert.equal(formatMeanSd({ mean: 0.8478, sd_across_folds: 0.04377 }, 2), '0.85 ± 0.04');
  for (const invalid of [null, undefined, {}, { mean: 0.5 }, { mean: '0.5', sd_across_folds: 0.1 }, { mean: 0.5, sd_across_folds: Number.NaN }]) {
    assert.equal(formatMeanSd(invalid), 'Unavailable');
  }
  assert.equal(formatCvDesign(STATIC_CV_SUMMARY), '5×5 CV · 25 folds · n=303');
  assert.equal(formatClassCounts(STATIC_CV_SUMMARY.targets.lad), '177 positive / 126 negative');
  assert.equal(formatClassCounts(null), 'Source-cohort class counts unavailable');
});

test('CV summary normalization fails closed for malformed API data', () => {
  const malformedSummaries = [
    null,
    {},
    { status: 'unavailable', targets: {} },
    { ...STATIC_CV_SUMMARY, targets: { ...STATIC_CV_SUMMARY.targets, rca: undefined } },
    {
      ...STATIC_CV_SUMMARY,
      targets: {
        ...STATIC_CV_SUMMARY.targets,
        lcx: { ...STATIC_CV_SUMMARY.targets.lcx, roc_auc: { mean: 0.727 } },
      },
    },
    {
      ...STATIC_CV_SUMMARY,
      targets: {
        ...STATIC_CV_SUMMARY.targets,
        lad: { ...STATIC_CV_SUMMARY.targets.lad, brier: { mean: 0.16, sd_across_folds: -0.01 } },
      },
    },
  ];

  for (const summary of malformedSummaries) {
    const normalized = normalizeCvSummary(summary);
    assert.equal(normalized.status, 'unavailable');
    assert.deepEqual(normalized.targets, {});
    assert.equal(getTargetCvSummary(normalized, 'lad'), null);
  }
  assert.equal(getTargetCvSummary(STATIC_CV_SUMMARY, 'unknown'), null);
});

test('API CV summaries are preferred and bundled static values are the safe fallback', () => {
  const apiSummary = structuredClone(STATIC_CV_SUMMARY);
  apiSummary.source = 'metrics_json';
  apiSummary.targets.rca.roc_auc.mean = 0.71;

  assert.equal(resolveCvSummary({ cv_summary: apiSummary }).targets.rca.roc_auc.mean, 0.71);
  assert.equal(resolveCvSummary({ cv_summary: apiSummary }).source, 'metrics_json');
  assert.equal(resolveCvSummary({ cv_summary: { status: 'unavailable', targets: {} } }).source, 'bundled_static');
  assert.equal(resolveCvSummary(null).targets.lcx.brier.mean, artifact.lcx.summary.brier.mean);
  assert.equal(resolveCvSummary({}).cohort_n, 303);
});
