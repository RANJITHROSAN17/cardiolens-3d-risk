// Form bounds are input-integrity checks, not clinical reference ranges.
const ranges = {
  age: [18, 110], bmi: [10, 80], systolic_bp: [70, 250], pulse_rate: [30, 220],
  fbs: [30, 700], ldl: [10, 500], hdl: [5, 200], tg: [20, 2000],
  ef_tte: [5, 90], region_rwma: [0, 4],
};
const booleans = ['smoking', 'ex_smoker', 'diabetes', 'hypertension', 'family_history',
  'typical_chest_pain', 'st_elevation', 'st_depression', 't_inversion', 'lvh'];

export function validateCase(features) {
  const errors = [];
  for (const [name, [min, max]] of Object.entries(ranges)) {
    const value = features[name];
    if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max || (name === 'region_rwma' && !Number.isInteger(value))) {
      errors.push(`${name.replaceAll('_', ' ')} must be ${name === 'region_rwma' ? 'an integer ' : ''}between ${min} and ${max}`);
    }
  }
  for (const name of booleans) if (typeof features[name] !== 'boolean') errors.push(`${name.replaceAll('_', ' ')} requires Yes or No`);
  if (!['Female', 'Male'].includes(features.sex)) errors.push('Sex must match a supported source-model category (Female or Male)');
  if (!['N', 'mild', 'Moderate', 'Severe'].includes(features.vhd)) errors.push('Select a supported VHD source label');
  if (features.smoking === true && features.ex_smoker === true) errors.push('Current and former smoker cannot both be Yes');
  return errors;
}
