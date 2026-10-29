import { useMemo, useState } from 'react';
import { freshCases, STAGES, summarize, transition } from './preventionWorkflow.js';

export default function FollowThrough() {
  const [cases, setCases] = useState(freshCases);
  const [filter, setFilter] = useState('all');
  const stats = useMemo(() => summarize(cases), [cases]);
  const shown = filter === 'all' ? cases : cases.filter(item => item.stage === Number(filter));
  return <section className="panel follow-panel" id="follow-through" aria-labelledby="follow-title">
    <div className="follow-title"><div><div className="section-eyebrow">PREVENTION FOLLOW-THROUGH · INTERACTIVE CONCEPT</div><h2 id="follow-title">From screening to follow-up</h2><p>A fictional worklist to explore how a care team might keep track of the prevention pathway.</p></div><span className="prevention-status">FICTIONAL CASES ONLY</span></div>
    <div className="follow-disclaimer"><strong>Simulation, not a clinical worklist.</strong> No real patient data, clinical decisions, scheduling or messages. Status changes are invented and reset when the page reloads.</div>
    <div className="follow-metrics" aria-label="Fictional workflow totals">
      <div><strong>{stats.total}</strong><span>demo cases</span></div><div><strong>{stats.screening}/{stats.total}</strong><span>screening recorded</span></div><div><strong>{stats.reviewed}/{stats.total}</strong><span>review recorded</span></div><div><strong>{stats.followup}/{stats.total}</strong><span>follow-up completed</span></div>
    </div>
    <div className="follow-toolbar"><div><h3>Demo worklist</h3><p>Administrative stage only — not risk or urgency.</p></div><div className="follow-controls"><label htmlFor="stage-filter">Stage</label><select id="stage-filter" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All stages</option>{STAGES.map((stage, i) => <option value={i} key={stage}>{stage}</option>)}</select><button type="button" onClick={() => { setCases(freshCases()); setFilter('all'); }}>Reset demo</button></div></div>
    <div className="follow-list">{shown.map(item => <div className="follow-row" key={item.id}><div><strong>{item.id}</strong><small>Fictional scenario</small></div><span className="follow-stage">{STAGES[item.stage]}</span><div className="follow-actions"><button type="button" aria-label={`Move ${item.id} back one stage`} disabled={item.stage === 0} onClick={() => setCases(prev => transition(prev, item.id, 'back'))}>Back</button><button type="button" aria-label={`Advance ${item.id} one stage`} disabled={item.stage === STAGES.length - 1} onClick={() => setCases(prev => transition(prev, item.id, 'next'))}>Advance</button></div></div>)}{shown.length === 0 && <p className="follow-empty">No fictional cases in this stage.</p>}</div>
    <p className="prevention-footer">A real implementation would require verified eligibility, consent, authorized users, reliable documentation, audit logs, clinical oversight and independent evaluation. This prototype provides none of those.</p>
  </section>;
}
