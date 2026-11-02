import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { validateCase, VALIDATION_SCHEMA } from '../src/validation.js';
const valid = { age:58, sex:'Female', bmi:27, systolic_bp:138, pulse_rate:74, fbs:96, ldl:122, hdl:48, tg:154, ef_tte:55, region_rwma:0, vhd:'N', smoking:false, ex_smoker:false, diabetes:false, hypertension:true, family_history:true, typical_chest_pain:false, st_elevation:false, st_depression:false, t_inversion:true, lvh:false };
test('complete demo passes', () => assert.deepEqual(validateCase(valid), []));
test('blank and out of range do not score', () => { assert.ok(validateCase({...valid, age:''}).length); assert.ok(validateCase({...valid, ldl:501}).length); });
test('unsupported category and missing booleans do not score', () => { assert.ok(validateCase({...valid, sex:'Other'}).length); assert.ok(validateCase({...valid, diabetes:null}).length); });
test('invalid coding is rejected', () => { assert.ok(validateCase({...valid, region_rwma:1.5}).length); assert.ok(validateCase({...valid, smoking:true, ex_smoker:true}).length); });

// Exercise the exported contract through validation, not just constant equality.
for (const [name, [low, high]] of Object.entries(VALIDATION_SCHEMA.numeric_ranges)) {
  test(`${name} accepts inclusive bounds and rejects out-of-range/non-finite values`, () => {
    for (const value of [low, high]) assert.deepEqual(validateCase({...valid, [name]:value}), []);
    for (const value of [low - 1, high + 1, NaN, Infinity, -Infinity]) {
      assert.ok(validateCase({...valid, [name]:value}).length);
    }
  });
}
for (const name of VALIDATION_SCHEMA.boolean_features) {
  test(`${name} requires a real boolean`, () => {
    for (const value of [false, true]) assert.deepEqual(validateCase({...valid, [name]:value}), []);
    for (const value of [null, 0, 1, 'true']) assert.ok(validateCase({...valid, [name]:value}).length);
  });
}
test('all exported categories are accepted and unsupported categories rejected', () => {
  for (const name of ['sex', 'vhd']) {
    for (const value of VALIDATION_SCHEMA[name]) assert.deepEqual(validateCase({...valid, [name]:value}), []);
    for (const value of ['', null, 'unsupported']) assert.ok(validateCase({...valid, [name]:value}).length);
  }
});
for (const key of ['CAD', 'Cath', 'LAD', 'LCX', 'RCA', ' c-A_d ']) {
  test(`diagnostic leakage key ${key} is rejected`, () => {
    assert.ok(validateCase({...valid, [key]:false}).some(error => error.includes('not a predictor')));
  });
}
