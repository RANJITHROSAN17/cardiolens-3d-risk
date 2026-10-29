import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { validateCase } from '../src/validation.js';
const valid = { age:58, sex:'Female', bmi:27, systolic_bp:138, pulse_rate:74, fbs:96, ldl:122, hdl:48, tg:154, ef_tte:55, region_rwma:0, vhd:'N', smoking:false, ex_smoker:false, diabetes:false, hypertension:true, family_history:true, typical_chest_pain:false, st_elevation:false, st_depression:false, t_inversion:true, lvh:false };
test('complete demo passes', () => assert.deepEqual(validateCase(valid), []));
test('blank and out of range do not score', () => { assert.ok(validateCase({...valid, age:''}).length); assert.ok(validateCase({...valid, ldl:501}).length); });
test('unsupported category and missing booleans do not score', () => { assert.ok(validateCase({...valid, sex:'Other'}).length); assert.ok(validateCase({...valid, diabetes:null}).length); });
test('invalid coding is rejected', () => { assert.ok(validateCase({...valid, region_rwma:1.5}).length); assert.ok(validateCase({...valid, smoking:true, ex_smoker:true}).length); });
