import { useEffect, useMemo, useState } from 'react';
import HeartScene from './HeartScene.jsx';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');
const apiUrl = (path) => `${API_BASE_URL}${path}`;

const DEMO_CASE = {
  age: 58,
  sex: 'Female',
  bmi: 27.4,
  systolic_bp: 138,
  pulse_rate: 74,
  smoking: false,
  ex_smoker: false,
  diabetes: false,
  hypertension: true,
  family_history: true,
  typical_chest_pain: false,
  st_elevation: false,
  st_depression: false,
  t_inversion: true,
  lvh: false,
  fbs: 96,
  ldl: 122,
  hdl: 48,
  tg: 154,
  ef_tte: 55,
  region_rwma: 0,
  vhd: 'N',
};

const EMPTY_MANUAL_CASE = {
  age: '', sex: '', bmi: '', systolic_bp: '', pulse_rate: '',
  smoking: null, ex_smoker: null, diabetes: null, hypertension: null,
  family_history: null, typical_chest_pain: null, st_elevation: null,
  st_depression: null, t_inversion: null, lvh: null,
  fbs: '', ldl: '', hdl: '', tg: '', ef_tte: '', region_rwma: '', vhd: '',
};

const SAMPLE_CASES = {
  'Balanced demo': DEMO_CASE,
  'Lower-factor demo': {
    ...DEMO_CASE, age: 42, bmi: 22.8, systolic_bp: 116, pulse_rate: 68,
    smoking: false, ex_smoker: false, diabetes: false, hypertension: false,
    family_history: false, typical_chest_pain: false, st_elevation: false,
    st_depression: false, t_inversion: false, lvh: false, fbs: 90,
    ldl: 82, hdl: 62, tg: 88, ef_tte: 65, region_rwma: 0, vhd: 'N',
  },
  'Higher-factor demo': {
    ...DEMO_CASE, age: 68, bmi: 31.2, systolic_bp: 158, pulse_rate: 82,
    smoking: true, ex_smoker: false, diabetes: true, hypertension: true,
    family_history: true, typical_chest_pain: true, st_elevation: true,
    st_depression: true, t_inversion: true, lvh: true, fbs: 132,
    ldl: 164, hdl: 34, tg: 242, ef_tte: 40, region_rwma: 2, vhd: 'Moderate',
  },
};

const VESSEL_META = {
  lad: { title: 'LAD', full: 'Left Anterior Descending', territory: 'Anterior wall', color: 'var(--lad)' },
  lcx: { title: 'LCX', full: 'Left Circumflex', territory: 'Lateral wall', color: 'var(--lcx)' },
  rca: { title: 'RCA', full: 'Right Coronary Artery', territory: 'Right / inferior', color: 'var(--rca)' },
};

function HeartMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 42 42" aria-hidden="true">
      <path d="M21 35s-13-8.1-13-17.1C8 12 11.2 8.8 16 8.8c2.5 0 4.1 1.4 5 3.1 1-1.7 2.6-3.1 5-3.1 4.8 0 8 3.2 8 9.1C34 26.9 21 35 21 35Z" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinejoin="round" />
      <path d="M11.8 21h5l2.4-4.5 3.4 9.1 2.4-4.6h5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Icon({ name, size = 17 }) {
  const paths = {
    sliders: <><path d="M4 6h16M4 12h16M4 18h16" /><circle cx="8" cy="6" r="2" /><circle cx="16" cy="12" r="2" /><circle cx="10" cy="18" r="2" /></>,
    rotate: <><path d="M20 11a8 8 0 0 0-14.8-4L3 10" /><path d="M3 4v6h6" /><path d="M4 13a8 8 0 0 0 14.8 4L21 14" /><path d="M21 20v-6h-6" /></>,
    shield: <><path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" /><path d="m9 12 2 2 4-4" /></>,
    activity: <><path d="M3 12h4l3-8 4 16 3-8h4" /></>,
    info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><path d="M12 8h.01" /></>,
    spark: <><path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z" /><path d="m19 16 .8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16Z" /></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function Toggle({ label, checked, onChange }) {
  return (
    <div className={`toggle-row ${checked === null ? 'toggle-unanswered' : ''}`}>
      <span>{label}</span>
      <div className="toggle-options" role="group" aria-label={label}>
        <button type="button" className={`toggle-choice yes ${checked === true ? 'selected' : ''}`} aria-pressed={checked === true} onClick={() => onChange(true)}>Yes</button>
        <button type="button" className={`toggle-choice no ${checked === false ? 'selected' : ''}`} aria-pressed={checked === false} onClick={() => onChange(false)}>No</button>
        {checked === null && <small className="toggle-required">Required</small>}
      </div>
    </div>
  );
}

function NumberField({ label, name, value, unit, min, max, onChange }) {
  const empty = value === '' || value === null || value === undefined;
  return (
    <label className="number-field">
      <span className="field-label">{label}{empty && <em className="field-required">required</em>}</span>
      <span className="input-wrap">
        <input type="number" name={name} value={value} min={min} max={max} onChange={(event) => onChange(name, event.target.value === '' ? '' : Number(event.target.value))} />
        <span className="unit">{unit}</span>
      </span>
    </label>
  );
}

function scoreLabel(score) {
  if (typeof score !== 'number' || !Number.isFinite(score)) return '—';
  return score.toFixed(2);
}

function ScoreMeter({ score, selected }) {
  const width = typeof score === 'number' ? Math.max(0, Math.min(100, score * 100)) : 0;
  return <div className={`score-meter ${selected ? 'selected' : ''}`}><span style={{ width: `${width}%` }} /></div>;
}

function VesselCard({ id, score, selected, onClick }) {
  const meta = VESSEL_META[id];
  return (
    <button type="button" className={`vessel-card ${selected ? 'active' : ''}`} onClick={onClick} aria-pressed={selected}>
      <span className={`vessel-dot ${id}`} />
      <span className="vessel-copy"><strong>{meta.title}</strong><small>{meta.territory}</small></span>
      <span className="vessel-score">{scoreLabel(score)}</span>
      <ScoreMeter score={score} selected={selected} />
    </button>
  );
}

function App() {
  const [features, setFeatures] = useState(DEMO_CASE);
  const [caseName, setCaseName] = useState('Balanced demo');
  const [caseId, setCaseId] = useState('DEMO-01');
  const [inputKind, setInputKind] = useState('synthetic');
  const [manualCounter, setManualCounter] = useState(0);
  const [prediction, setPrediction] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [activeVessel, setActiveVessel] = useState('lad');
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [apiError, setApiError] = useState('');
  const [apiReady, setApiReady] = useState(false);

  async function requestPrediction(nextFeatures = features) {
    setBusy(true);
    setApiError('');
    try {
      const response = await fetch(apiUrl('/api/predict'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ schema_version: '0.2', features: nextFeatures }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Prediction service returned an error.');
      setPrediction(data);
      setDirty(false);
      setApiReady(true);
    } catch (error) {
      setApiError(error.message || 'Could not connect to the prediction API.');
      setApiReady(false);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch(apiUrl('/api/sample-case')).then((r) => r.json()),
      fetch(apiUrl('/api/model-info')).then((r) => r.json()),
    ]).then(([sample, info]) => {
      if (cancelled) return;
      setFeatures(sample.features);
      setCaseId(sample.case_id);
      setModelInfo(info);
      requestPrediction(sample.features);
    }).catch(() => {
      if (!cancelled) setApiError('The prediction API is unavailable. Check that it is running, then refresh.');
    });
    return () => { cancelled = true; };
  }, []);

  const currentMode = prediction?.mode || modelInfo?.mode || 'synthetic_demo';
  const isDemo = currentMode === 'synthetic_demo';
  const cadScore = prediction?.results?.cad_present?.score;
  const vesselResults = prediction?.results?.vessels || {};
  const currentVessel = useMemo(() => VESSEL_META[activeVessel], [activeVessel]);

  function updateFeature(name, value) {
    setFeatures((previous) => {
      const next = { ...previous, [name]: value };
      if (name === 'smoking' && value === true) next.ex_smoker = false;
      if (name === 'ex_smoker' && value === true) next.smoking = false;
      return next;
    });
    setPrediction(null);
    setApiError('');
    setDirty(true);
  }

  function loadCase(name) {
    if (name === 'New manual case') {
      const nextCount = manualCounter + 1;
      setManualCounter(nextCount);
      setCaseName(name);
      setCaseId(`MANUAL-${String(nextCount).padStart(2, '0')}`);
      setInputKind('manual');
      setFeatures({ ...EMPTY_MANUAL_CASE });
      setPrediction(null);
      setApiError('');
      setDirty(true);
      return;
    }
    const next = SAMPLE_CASES[name];
    if (!next) return;
    setCaseName(name);
    setCaseId(name === 'Balanced demo' ? 'DEMO-01' : name === 'Lower-factor demo' ? 'DEMO-LOW' : 'DEMO-HIGH');
    setInputKind('synthetic');
    setFeatures({ ...next });
    setPrediction(null);
    setApiError('');
    setDirty(true);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-icon"><HeartMark /></div>
          <div><div className="brand-name">Cardio<span>Lens</span></div><div className="brand-subtitle">CORONARY MODEL EXPLORER</div></div>
        </div>
        <nav className="top-nav" aria-label="Primary navigation">
          <button className="nav-item active"><Icon name="activity" size={15} /> Overview</button>
          <button className="nav-item" onClick={() => document.getElementById('model-notes')?.scrollIntoView({ behavior: 'smooth' })}><Icon name="info" size={15} /> Model notes</button>
        </nav>
        <div className="topbar-right">
          <span className={`api-status ${apiReady ? 'online' : ''}`}><i />{apiReady ? 'API connected' : 'Connecting'}</span>
          <span className="environment-pill"><span className="env-dot" /> SANDBOX</span>
          <div className="avatar">CL</div>
        </div>
      </header>

      <div className="safety-banner" role="note">
        <span className="safety-icon"><Icon name="shield" size={16} /></span>
        <span><strong>{isDemo ? 'Research prototype · synthetic demo data only.' : 'Research prototype · uncalibrated research model.'}</strong> Scores are unvalidated and not for patient care, diagnosis, triage or treatment.</span>
        <span className="safety-banner-end">NOT A DIAGNOSTIC TOOL</span>
      </div>

      <main className="page-content">
        <section className="page-heading">
          <div>
            <div className="eyebrow">CLINICAL VISUALIZATION · PROTOTYPE 0.2</div>
            <h1>One heart. Three coronary territories.</h1>
            <p>Explore how an input snapshot can connect to whole-vessel model outputs in an interactive 3D view.</p>
          </div>
          <div className="case-chip"><span className="case-chip-icon"><Icon name="activity" size={17} /></span><span><small>ACTIVE CASE</small><strong>{caseId} <em>· {inputKind === 'manual' ? 'manual demo' : 'synthetic'}</em></strong></span></div>
        </section>

        <div className="dashboard-grid">
          <section className="panel input-panel" aria-labelledby="inputs-title">
            <div className="panel-heading">
              <div className="heading-icon mint"><Icon name="sliders" /></div>
              <div><h2 id="inputs-title">Case snapshot</h2><p>{inputKind === 'manual' ? 'Enter a new single-case demo record' : 'Review or edit synthetic demo inputs'}</p></div>
              <span className="step-number">01</span>
            </div>

            <label className="select-field case-select">
              <span className="field-label">{inputKind === 'manual' ? 'Manual case · start another or choose a preset' : 'Synthetic scenario / manual entry'}</span>
              <select value={caseName} onChange={(e) => loadCase(e.target.value)}>
                {Object.keys(SAMPLE_CASES).map((name) => <option key={name}>{name}</option>)}
                <option>New manual case</option>
              </select>
            </label>
            {inputKind === 'manual' && <p className="micro-note manual-note">Enter every field; blank or unsupported values will not be scored. Demo/research only—do not enter names, identifiers, or PHI.</p>}

            <div className="input-group-label"><span>01</span> Demographics</div>
            <div className="two-column-fields">
              <NumberField label="Age" name="age" value={features.age} unit="years" min="18" max="110" onChange={updateFeature} />
              <label className="select-field">
                <span className="field-label">Sex variable{!features.sex && <em className="field-required">required</em>}</span>
                <select value={features.sex} onChange={(e) => updateFeature('sex', e.target.value)}><option value="">Select</option><option>Female</option><option>Male</option><option value="Other / not recorded">Other / not recorded · unsupported by this cohort</option></select>
              </label>
            </div>

            <div className="input-group-label"><span>02</span> Vitals &amp; anthropometry</div>
            <div className="two-column-fields">
              <NumberField label="Systolic BP" name="systolic_bp" value={features.systolic_bp} unit="mmHg" min="70" max="250" onChange={updateFeature} />
              <NumberField label="Pulse rate" name="pulse_rate" value={features.pulse_rate} unit="bpm" min="30" max="220" onChange={updateFeature} />
              <NumberField label="BMI" name="bmi" value={features.bmi} unit="kg/m²" min="10" max="80" onChange={updateFeature} />
            </div>

            <div className="input-group-label"><span>03</span> Lipids &amp; glucose</div>
            <div className="two-column-fields">
              <NumberField label="LDL" name="ldl" value={features.ldl} unit="mg/dL" min="10" max="500" onChange={updateFeature} />
              <NumberField label="HDL" name="hdl" value={features.hdl} unit="mg/dL" min="5" max="200" onChange={updateFeature} />
              <NumberField label="Triglycerides" name="tg" value={features.tg} unit="mg/dL" min="20" max="2000" onChange={updateFeature} />
              <NumberField label="Fasting glucose" name="fbs" value={features.fbs} unit="mg/dL" min="30" max="700" onChange={updateFeature} />
            </div>

            <div className="input-group-label"><span>04</span> History &amp; symptoms <span className="group-note">{inputKind === 'manual' ? 'select Yes / No' : 'demo flags'}</span></div>
            <div className="toggle-list">
              <Toggle label="Current smoker" checked={features.smoking} onChange={(v) => updateFeature('smoking', v)} />
              <Toggle label="Former smoker" checked={features.ex_smoker} onChange={(v) => updateFeature('ex_smoker', v)} />
              <Toggle label="Diabetes" checked={features.diabetes} onChange={(v) => updateFeature('diabetes', v)} />
              <Toggle label="Hypertension history" checked={features.hypertension} onChange={(v) => updateFeature('hypertension', v)} />
              <Toggle label="Family history" checked={features.family_history} onChange={(v) => updateFeature('family_history', v)} />
              <Toggle label="Typical chest pain" checked={features.typical_chest_pain} onChange={(v) => updateFeature('typical_chest_pain', v)} />
            </div>

            <details className="advanced-details" open>
              <summary><span className="input-group-label"><span>05</span> ECG &amp; echo findings</span><span className="details-caret">⌄</span></summary>
              <div className="toggle-list advanced-toggles">
                <Toggle label="ST elevation" checked={features.st_elevation} onChange={(v) => updateFeature('st_elevation', v)} />
                <Toggle label="ST depression" checked={features.st_depression} onChange={(v) => updateFeature('st_depression', v)} />
                <Toggle label="T-wave inversion" checked={features.t_inversion} onChange={(v) => updateFeature('t_inversion', v)} />
                <Toggle label="LVH" checked={features.lvh} onChange={(v) => updateFeature('lvh', v)} />
              </div>
              <div className="two-column-fields echo-fields">
                <NumberField label="EF-TTE" name="ef_tte" value={features.ef_tte} unit="%" min="5" max="90" onChange={updateFeature} />
                <label className="select-field">
                  <span className="field-label">RWMA source code{features.region_rwma === '' && <em className="field-required">required</em>}</span>
                  <select value={features.region_rwma} onChange={(e) => updateFeature('region_rwma', e.target.value === '' ? '' : Number(e.target.value))}>
                    <option value="">Select</option><option value={0}>0 · source code</option><option value={1}>1 · source code</option><option value={2}>2 · source code</option><option value={3}>3 · source code</option><option value={4}>4 · source code</option>
                  </select>
                </label>
                <label className="select-field vhd-field">
                  <span className="field-label">VHD source label{!features.vhd && <em className="field-required">required</em>}</span>
                  <select value={features.vhd} onChange={(e) => updateFeature('vhd', e.target.value)}>
                    <option value="">Select</option><option value="N">None (N)</option><option value="mild">Mild</option><option value="Moderate">Moderate</option><option value="Severe">Severe</option>
                  </select>
                </label>
              </div>
              <p className="micro-note">RWMA source codes are categorical inputs, not anatomical coordinates. Confirm the dataset codebook before clinical use.</p>
            </details>

            <div className="snapshot-footer">
              <span className="data-origin"><i /> {inputKind === 'manual' ? 'Manual demo entry · not saved' : 'Synthetic input · no identifiers'}</span>
              {dirty && <span className="unsaved-chip">Changes not scored</span>}
            </div>
            <button className="primary-button" onClick={() => requestPrediction()} disabled={busy}>
              {busy ? <span className="spinner" /> : <Icon name="spark" size={18} />}
              {busy ? 'Calculating estimate…' : isDemo ? 'Run demo estimate' : 'Run research estimate'}
            </button>
            <p className="button-footnote">{isDemo ? 'Demo formula only · not a trained clinical model' : 'Research baseline only · uncalibrated'}</p>
          </section>

          <section className="center-column">
            <div className="panel viewer-panel">
              <div className="panel-heading viewer-heading">
                <div className="heading-icon lilac"><Icon name="activity" /></div>
                <div><h2>3D coronary map</h2><p>Schematic anterior view · generic anatomy</p></div>
                <div className="view-controls"><span className="drag-hint"><Icon name="rotate" size={14} /> Drag to rotate</span><button type="button" className="icon-button" title="Reset selected vessel" onClick={() => setActiveVessel('lad')}><Icon name="rotate" size={16} /></button></div>
              </div>
              <div className="viewer-stage">
                <div className="viewer-sheen" />
                <div className="anatomy-badge"><span className="pulse-dot" />ILLUSTRATIVE ANATOMY</div>
                <div className="view-tag">ANTERIOR VIEW <span>·</span> NOT PATIENT-SPECIFIC</div>
                <HeartScene results={prediction?.results} activeVessel={activeVessel} onVesselSelect={setActiveVessel} />
                <div className="map-legend">
                  <div className="legend-title">WHOLE-VESSEL SCORE · NOT LESION MAP</div>
                  <div className="legend-row"><span>Lower</span><span className="legend-gradient" /><span>Higher</span></div>
                </div>
                <div className="scene-compass"><span className="compass-n">A</span><span className="compass-line" /><span className="compass-s">P</span></div>
              </div>
              <div className="vessel-list-heading"><span>Select a coronary territory</span><span>Tap a vessel or its score</span></div>
              <div className="vessel-card-row">
                {['lad', 'lcx', 'rca'].map((id) => <VesselCard key={id} id={id} score={vesselResults[id]?.score} selected={activeVessel === id} onClick={() => setActiveVessel(id)} />)}
              </div>
              <div className="anatomy-footnote"><span className="footnote-mark">i</span><span>{isDemo ? 'Colors encode synthetic whole-vessel scores only.' : 'Colors encode uncalibrated research model scores only.'} They do not indicate a lesion, stenosis location or patient-specific anatomy.</span></div>
            </div>

            <div className="bottom-stat-row">
              <div className="mini-stat"><span className="mini-stat-icon"><Icon name="shield" size={16} /></span><span><small>DATA MODE</small><strong>{isDemo ? 'Synthetic demo' : 'Research model'}</strong></span></div>
              <div className="mini-stat"><span className="mini-stat-icon violet"><Icon name="info" size={16} /></span><span><small>CALIBRATION</small><strong>{isDemo ? 'Not calibrated' : 'Not established'}</strong></span></div>
              <div className="mini-stat"><span className="mini-stat-icon amber"><Icon name="activity" size={16} /></span><span><small>FUTURE RISK</small><strong>Unavailable in prototype</strong></span></div>
            </div>
          </section>

          <aside className="right-column" aria-label="Prediction details">
            <section className="panel summary-panel">
              <div className="result-topline"><span className="result-kicker">CAD LABEL SCORE</span><span className={`calibration-pill ${isDemo ? 'demo' : ''}`}>{isDemo ? 'DEMO SCORE' : 'RESEARCH SCORE'}</span></div>
              {prediction?.status === 'not_estimable' ? (
                <div className="not-estimable"><strong>Not estimable</strong><p>{prediction.reason}</p>{prediction.missing_features?.length > 0 && <small>Missing required fields: {prediction.missing_features.join(', ')}</small>}</div>
              ) : (
                <>
                  <div className="cad-score-line"><strong>{scoreLabel(cadScore)}</strong><span className="score-ring"><i style={{ '--score': `${(cadScore || 0) * 100}%` }} /></span></div>
                  <p className="result-subtitle">{isDemo ? 'Synthetic demo score on a 0–1 scale; not a clinical probability' : 'Uncalibrated score for a source-cohort prevalent CAD label; not a clinical probability'}</p>
                  <div className="summary-progress"><span style={{ width: `${Math.max(0, Math.min(100, (cadScore || 0) * 100))}%` }} /></div>
                  <div className="score-scale"><span>0.00</span><span>1.00</span></div>
                </>
              )}
              <div className="model-version-row"><span>MODEL</span><strong>{prediction?.model_version || modelInfo?.model_version || 'Loading…'}</strong></div>
              <div className="result-divider" />
              <div className="future-risk-box">
                <div className="future-icon"><Icon name="activity" size={16} /></div>
                <div><small>FUTURE CARDIOVASCULAR RISK</small><strong>Not calculated</strong><p>No longitudinal model or validated time horizon is included.</p></div>
                <span className="lock-mark">—</span>
              </div>
            </section>

            <section className="panel vessel-detail-panel">
              <div className="section-eyebrow"><span className={`vessel-dot ${activeVessel}`} /> SELECTED VESSEL</div>
              <div className="selected-vessel-title"><div><h3>{currentVessel.title}</h3><p>{currentVessel.full}</p></div><span className="vessel-pill">{currentVessel.territory}</span></div>
              <div className="detail-score"><span>{isDemo ? 'Demo score' : 'Research score'}</span><strong>{scoreLabel(vesselResults[activeVessel]?.score)}</strong></div>
              <ScoreMeter score={vesselResults[activeVessel]?.score} selected />
              <p className="vessel-detail-note">A vessel-level output is highlighted on the schematic. No segment-level prediction is available.</p>
            </section>

            <section className="panel explanation-panel" id="model-notes">
              <div className="explanation-heading"><div><div className="section-eyebrow"><Icon name="spark" size={13} /> MODEL NOTES</div><h3>Score contributors</h3></div><span className="explanation-badge">NOT SHAP</span></div>
              <p className="explanation-intro">{isDemo ? 'A demo-only ranking of inputs used by the synthetic score. Not causal and not a clinical explanation.' : 'Linear model log-odds contributions for the fitted baseline. Not causal and not a clinical explanation.'}</p>
              <div className="factor-list">
                {(prediction?.explanation || []).slice(0, 5).map((factor) => {
                  const width = Math.max(4, Math.min(100, Math.abs(factor.contribution || 0) * 100));
                  return <div className="factor-item" key={factor.label}>
                    <div className="factor-head"><span>{factor.label}</span><strong>{factor.value}{factor.unit ? ` ${factor.unit}` : ''}</strong></div>
                    <div className={`factor-direction ${factor.contribution < 0 ? 'negative' : ''}`}>{factor.direction}</div>
                    <div className="factor-track"><span className={factor.contribution < 0 ? 'negative' : ''} style={{ width: `${width}%` }} /></div>
                  </div>;
                })}
                {!prediction?.explanation?.length && <div className="empty-explanation">Run an estimate to see model input contributors.</div>}
              </div>
              <div className="explanation-disclaimer"><Icon name="info" size={14} />{isDemo ? 'Factors show formula contribution only in this synthetic demo.' : 'Model contributions are unvalidated and do not establish causation.'}</div>
            </section>
          </aside>
        </div>

        {apiError && <div className="toast-error" role="alert"><Icon name="info" size={17} /><span>{apiError} Check the prediction API service.</span></div>}
        <footer className="app-footer"><span>CardioLens Prototype <b>·</b> build 0.2.0</span><span>For software demonstration only <b>·</b> No real patient data</span><span className="footer-links">API {apiReady ? 'online' : 'offline'} <i className={apiReady ? 'online' : ''} /></span></footer>
      </main>
    </div>
  );
}

export default App;
