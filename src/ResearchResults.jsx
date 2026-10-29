import results from './research-results.json';

const percent = x => `${(x * 100).toFixed(1)}%`;
export default function ResearchResults() {
  return <section className="panel research-panel" id="research-results" aria-labelledby="research-title">
    <div className="research-heading"><div><div className="section-eyebrow">EXPLORATORY DATASET TEST · OFFLINE EXPERIMENT</div><h2 id="research-title">Can a model rank future CHD events?</h2><p>One random held-out split of a public Framingham-labeled mirror. These are aggregate study results—not predictions for the cases on this page.</p></div><span className="prevention-status">NOT CLINICAL VALIDATION</span></div>
    <div className="follow-disclaimer"><strong>Different outcome and population:</strong> this dataset is labeled 10-year coronary heart disease (CHD), not the proposed heart-attack-or-stroke composite. It is not an Indian external validation. No future-risk calculator is enabled.</div>
    <div className="follow-metrics"><div><strong>{results.rows_analyzed.toLocaleString()}</strong><span>analyzed rows</span></div><div><strong>{results.test_rows}</strong><span>held-out rows · {results.test_events} events</span></div><div><strong>{results.roc_auc.toFixed(3)}</strong><span>test ROC-AUC · ranking</span></div><div><strong>{results.brier_score.toFixed(3)}</strong><span>test Brier score · lower is better</span></div></div>
    <p className="research-copy">Average precision: <strong>{results.average_precision.toFixed(3)}</strong> (test event fraction {percent(results.test_event_fraction)}). Constant-rate baseline Brier score: <strong>{results.baseline_brier_score.toFixed(3)}</strong>. One split has sampling uncertainty; these results cannot establish performance in a new hospital.</p>
    <h3 className="research-subtitle">Illustrative calibration by prediction fifth</h3>
    <div className="research-table-wrap"><table className="research-table"><thead><tr><th scope="col">Group</th><th scope="col">Rows</th><th scope="col">Mean prediction</th><th scope="col">Observed events</th></tr></thead><tbody>{results.calibration_bins.map((bin, index) => <tr key={index}><td>{index + 1} {index === 0 ? '(lowest)' : index === 4 ? '(highest)' : ''}</td><td>{bin.n}</td><td>{percent(bin.mean_prediction)}</td><td>{percent(bin.observed_event_fraction)}</td></tr>)}</tbody></table></div>
    <p className="prevention-footer">Exploratory logistic regression; median imputation and scaling fitted on training data only. No external or prospective validation; follow-up completeness, patient identity, prior CHD and source-data rights are not verified. No raw dataset or fitted model is published. See <code>docs/dataset-experiment.md</code>.</p>
  </section>;
}
