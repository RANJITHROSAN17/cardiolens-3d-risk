// Form bounds are input-integrity checks, not clinical reference ranges.
export const NUMERIC_RANGES = {
  age: [18, 110], bmi: [10, 80], systolic_bp: [70, 250], pulse_rate: [30, 220],
  fbs: [30, 700], ldl: [10, 500], hdl: [5, 200], tg: [20, 2000],
  ef_tte: [5, 90], region_rwma: [0, 4],
};
export const BOOLEAN_FEATURES = ['smoking', 'ex_smoker', 'diabetes', 'hypertension', 'family_history',
  'typical_chest_pain', 'st_elevation', 'st_depression', 't_inversion', 'lvh'];

export const SEX_CATEGORIES = ['Female', 'Male'];
export const VHD_CATEGORIES = ['N', 'mild', 'Moderate', 'Severe'];
export const INTEGER_FEATURES = ['region_rwma'];
export const FORBIDDEN_FEATURES = ['cad', 'cath', 'lad', 'lcx', 'rca'];
export const FEATURE_FIELDS = [
  'age', 'sex', 'bmi', 'diabetes', 'hypertension', 'smoking', 'ex_smoker',
  'family_history', 'systolic_bp', 'pulse_rate', 'typical_chest_pain',
  'st_elevation', 'st_depression', 't_inversion', 'lvh', 'fbs', 'tg',
  'ldl', 'hdl', 'ef_tte', 'region_rwma', 'vhd',
];
export const IDENTIFIER_FIELDS = ['name', 'patient_id', 'mrn', 'dob', 'email', 'phone', 'address'];

// Machine-readable contract, exercised directly by the Python parity test.
export const VALIDATION_SCHEMA = {
  numeric_ranges: NUMERIC_RANGES, boolean_features: BOOLEAN_FEATURES,
  sex: SEX_CATEGORIES, vhd: VHD_CATEGORIES,
  integer_features: INTEGER_FEATURES, forbidden_features: FORBIDDEN_FEATURES,
  feature_fields: FEATURE_FIELDS, identifier_fields: IDENTIFIER_FIELDS,
};

const normalizeKey = (key) => String(key).trim().toLowerCase().replace(/[^a-z0-9]+/g, '');
const IDENTIFIER_NORMALIZED_KEYS = new Set([
  ...IDENTIFIER_FIELDS.map(normalizeKey),
  'fullname', 'patientname', 'dateofbirth', 'phonenumber', 'telephonenumber',
  'mobilenumber', 'emailaddress', 'homeaddress', 'postaladdress',
  'streetaddress', 'medicalrecordnumber',
]);

export function isIdentifierField(key) {
  const normalized = normalizeKey(key);
  return IDENTIFIER_NORMALIZED_KEYS.has(normalized)
    || normalized.endsWith('name')
    || normalized.startsWith('patient')
    || normalized.includes('email')
    || normalized.includes('phone')
    || normalized.includes('telephone')
    || normalized.includes('mobile')
    || normalized.includes('address')
    || normalized.includes('birth')
    || normalized.includes('medicalrecord');
}

export function validateCase(features) {
  if (!features || typeof features !== 'object' || Array.isArray(features)) {
    return ['Case inputs must be an object of validated synthetic fields'];
  }

  const errors = [];
  for (const key of Object.keys(features)) {
    if (isIdentifierField(key)) {
      errors.push(`${key} is an identifier/PHI field and must not be entered`);
    } else if (FORBIDDEN_FEATURES.includes(normalizeKey(key))) {
      errors.push(`${key} is an outcome/diagnostic field, not a predictor`);
    } else if (!FEATURE_FIELDS.includes(key)) {
      errors.push(`${key} is not a supported input field`);
    }
  }
  for (const [name, [min, max]] of Object.entries(NUMERIC_RANGES)) {
    const value = features[name];
    if (typeof value !== 'number' || !Number.isFinite(value) || value < min || value > max || (INTEGER_FEATURES.includes(name) && !Number.isInteger(value))) {
      errors.push(`${name.replaceAll('_', ' ')} must be ${name === 'region_rwma' ? 'an integer ' : ''}between ${min} and ${max}`);
    }
  }
  for (const name of BOOLEAN_FEATURES) if (typeof features[name] !== 'boolean') errors.push(`${name.replaceAll('_', ' ')} requires Yes or No`);
  if (!SEX_CATEGORIES.includes(features.sex)) errors.push('Sex must match a supported source-model category (Female or Male)');
  if (!VHD_CATEGORIES.includes(features.vhd)) errors.push('Select a supported VHD source label');
  if (features.smoking === true && features.ex_smoker === true) errors.push('Current and former smoker cannot both be Yes');
  return errors;
}
