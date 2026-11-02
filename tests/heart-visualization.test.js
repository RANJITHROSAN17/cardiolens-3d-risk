import { test } from 'node:test';
import assert from 'node:assert/strict';
import { PALETTES, UNKNOWN_COLOR, VESSEL_IDS, FALLBACK_PATHS, scoreColor, paletteGradient, vesselCards, tryCreateRenderer } from '../src/heart-visualization.js';

test('both ramps interpolate through every stop and clamp finite scores', () => {
  for (const [palette, stops] of Object.entries(PALETTES)) {
    stops.forEach((color, index) => assert.equal(scoreColor(index / (stops.length - 1), palette), color));
    assert.equal(scoreColor(-1, palette), stops[0]);
    assert.equal(scoreColor(2, palette), stops.at(-1));
    assert.match(scoreColor(0.13, palette), /^#[0-9a-f]{6}$/);
    assert.equal(paletteGradient(palette), `linear-gradient(90deg, ${stops.join(', ')})`);
  }
  assert.equal(scoreColor(0.25, 'classic'), '#86ad72');
  assert.equal(scoreColor(0.7, 'unknown'), scoreColor(0.7, 'viridis'));
  assert.equal(paletteGradient('unknown'), paletteGradient('viridis'));
});
test('missing and non-finite scores stay neutral, never zero or a clinical percentage', () => {
  for (const value of [null, undefined, NaN, Infinity, -Infinity, '0.5']) assert.equal(scoreColor(value), UNKNOWN_COLOR);
  assert.ok(vesselCards().every(card => card.score === null && card.text === 'Unavailable'));
  for (const value of [-0.1, 1.1, null, undefined, NaN, Infinity, '0.5']) {
    assert.equal(vesselCards({vessels:{lad:{score:value}}})[0].text, 'Unavailable');
  }
  const cards = vesselCards({vessels:{lad:{score:0}, lcx:{score:0.456}, rca:{score:1}}});
  assert.deepEqual(cards.map(card => card.text), ['0.00 / 1', '0.46 / 1', '1.00 / 1']);
  assert.deepEqual(cards.map(card => card.label), ['LAD', 'LCX', 'RCA']);
});
test('fallback data has exactly three selectable vessels and renderer failure is contained', () => {
  assert.deepEqual(Object.keys(FALLBACK_PATHS), VESSEL_IDS);
  assert.deepEqual(vesselCards().map(card => card.id), VESSEL_IDS);
  for (const path of Object.values(FALLBACK_PATHS)) assert.match(path, /^M[\d\s]+ C/);
  const renderer = {dispose() {}};
  assert.equal(tryCreateRenderer(() => renderer), renderer);
  assert.equal(tryCreateRenderer(() => { throw Error('WebGL disabled'); }), null);
});
