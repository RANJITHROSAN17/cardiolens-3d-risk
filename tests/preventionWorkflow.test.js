import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { freshCases, transition, summarize, STAGES } from '../src/preventionWorkflow.js';

test('fixtures are independent and reset to original stages', () => {
  const a = freshCases(); a[0].stage = 3;
  assert.equal(freshCases()[0].stage, 0);
});
test('only the selected case moves exactly one step and input is unchanged', () => {
  const original = freshCases(); const moved = transition(original, 'DEMO-101', 'next');
  assert.equal(original[0].stage, 0); assert.equal(moved[0].stage, 1); assert.equal(moved[1].stage, original[1].stage);
  assert.equal(transition(moved, 'DEMO-101', 'back')[0].stage, 0);
});
test('invalid or boundary transitions cannot move', () => {
  const data = freshCases();
  assert.equal(transition(data, 'DEMO-101', 'back')[0].stage, 0);
  assert.equal(transition(data, 'DEMO-105', 'next')[4].stage, STAGES.length - 1);
  assert.deepEqual(transition(data, 'DEMO-101', 'jump'), data);
  assert.deepEqual(transition(data, 'unknown', 'next'), data);
});
test('summary tracks synthetic stages and changes with transitions', () => {
  const data = freshCases();
  assert.deepEqual(summarize(data), {total: 5, screening: 4, reviewed: 3, followup: 1});
  assert.equal(summarize(transition(data, 'DEMO-101', 'next')).screening, 5);
  assert.equal(summarize(transition(data, 'DEMO-104', 'next')).followup, 2);
});
