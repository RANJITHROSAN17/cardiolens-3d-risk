// Synthetic workflow simulation. These states are administrative, not clinical advice.
export const STAGES = ['Screening pending', 'Screening recorded', 'Clinical review recorded', 'Follow-up planned', 'Follow-up completed'];
export const INITIAL_CASES = Object.freeze([
  { id: 'DEMO-101', stage: 0 },
  { id: 'DEMO-102', stage: 1 },
  { id: 'DEMO-103', stage: 2 },
  { id: 'DEMO-104', stage: 3 },
  { id: 'DEMO-105', stage: 4 },
]);
export function freshCases() { return INITIAL_CASES.map(item => ({ ...item })); }
export function transition(cases, id, direction) {
  if (!['next', 'back'].includes(direction)) return cases;
  return cases.map(item => {
    if (item.id !== id || !Number.isInteger(item.stage) || item.stage < 0 || item.stage >= STAGES.length) return item;
    const stage = item.stage + (direction === 'next' ? 1 : -1);
    return stage < 0 || stage >= STAGES.length ? item : { ...item, stage };
  });
}
export function summarize(cases) {
  return { total: cases.length, screening: cases.filter(item => item.stage >= 1 && item.stage < STAGES.length).length,
    reviewed: cases.filter(item => item.stage >= 2 && item.stage < STAGES.length).length,
    followup: cases.filter(item => item.stage === 4).length };
}
