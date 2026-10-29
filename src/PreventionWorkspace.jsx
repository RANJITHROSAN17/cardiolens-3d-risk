import { useState } from 'react';

const GATES = [
  ['purpose', 'Define the exact outcome and eligible population', 'Specify fatal and nonfatal events, exclusions, setting and data collection time.'],
  ['model', 'Select a candidate equation with clinical partners', 'Confirm its outcome, age range, predictor definitions, licensing and suitability for the target population.'],
  ['data', 'Secure longitudinal data and independent validation sites', 'Document permissions, follow-up, event adjudication and representative populations.'],
  ['validation', 'Predefine performance and clinical safety criteria', 'Evaluate calibration, discrimination, subgroup performance, missingness and clinical utility.'],
  ['governance', 'Obtain ethics, privacy and regulatory review', 'Review each intended claim and the proposed deployment before any clinical use.'],
];

export default function PreventionWorkspace() {
  const [checked, setChecked] = useState({});
  const count = GATES.filter(([id]) => checked[id]).length;
  return <section className="panel prevention-panel" id="prevention-roadmap" aria-labelledby="prevention-title">
    <div className="prevention-heading"><div><div className="section-eyebrow">NEXT PRODUCT DIRECTION · RESEARCH ONLY</div>
      <h2 id="prevention-title">10-year prevention research</h2>
      <p>For adults without known cardiovascular disease. The exact eligibility rules and event definition remain to be established.</p></div>
      <span className="prevention-status">NO RISK CALCULATOR</span></div>
    <div className="prevention-warning"><strong>No future risk is calculated.</strong> The CAD and vessel demo scores below describe a different target. Do not use them to estimate 10-year risk or make care decisions.</div>
    <div className="prevention-grid"><div><h3>Proposed study question</h3><p>Can a suitable, independently validated model support a clinician–patient prevention discussion about heart attack or stroke over 10 years?</p><p>Define fatal and nonfatal outcomes, patient eligibility, and intended clinical action before selecting a model.</p></div>
      <div><h3>Research readiness checklist <span>{count} / {GATES.length}</span></h3><p>Planning aid only; checking a box is not evidence of completion. Resets on reload.</p>
        <div className="prevention-checks">{GATES.map(([id, title, detail]) => <label key={id}><input type="checkbox" checked={!!checked[id]} onChange={(event) => setChecked({...checked, [id]: event.target.checked})} /><span><strong>{title}</strong><small>{detail}</small></span></label>)}</div>
      </div></div>
    <p className="prevention-footer">No patient information is collected or saved here. See <code>docs/prevention-risk-plan.md</code> in the source for the implementation and study plan.</p>
  </section>;
}
