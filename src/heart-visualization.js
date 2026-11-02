// Display helpers only: these scores are not calibrated clinical probabilities.
export const VESSEL_IDS = ['lad', 'lcx', 'rca'];
export const PALETTES = {
  classic: ['#2aa99a', '#e2b04a', '#d84d70'],
  viridis: ['#440154', '#3b528b', '#21918c', '#5ec962', '#fde725'],
};
export const UNKNOWN_COLOR = '#9eabb4';
export const FALLBACK_PATHS = {
  lad: 'M160 62 C151 105 177 146 161 232',
  lcx: 'M160 62 C123 62 73 79 65 121 C61 148 87 156 110 158',
  rca: 'M160 62 C204 63 247 100 249 138 C250 173 222 192 201 205',
};
export function scoreColor(score, palette = 'viridis') {
  if (!Number.isFinite(score)) return UNKNOWN_COLOR;
  const stops = PALETTES[palette] || PALETTES.viridis;
  const position = Math.max(0, Math.min(1, score)) * (stops.length - 1);
  const index = Math.min(Math.floor(position), stops.length - 2);
  const fraction = position - index;
  const rgb = hex => hex.match(/[a-f0-9]{2}/gi).map(channel => parseInt(channel, 16));
  const start = rgb(stops[index]), end = rgb(stops[index + 1]);
  return '#' + start.map((channel, i) => Math.round(channel + (end[i] - channel) * fraction).toString(16).padStart(2, '0')).join('');
}
export function paletteGradient(palette = 'viridis') {
  return `linear-gradient(90deg, ${(PALETTES[palette] || PALETTES.viridis).join(', ')})`;
}
export function vesselCards(results) {
  return VESSEL_IDS.map(id => {
    const value = results?.vessels?.[id]?.score;
    const score = Number.isFinite(value) && value >= 0 && value <= 1 ? value : null;
    return { id, label: id.toUpperCase(), score, text: score === null ? 'Unavailable' : `${score.toFixed(2)} / 1` };
  });
}
export function tryCreateRenderer(factory) {
  try { return factory(); } catch { return null; }
}
