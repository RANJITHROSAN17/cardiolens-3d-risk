## Summary

<!-- Describe what changed and add `Closes #<issue-number>` if this completes a roadmap issue. -->

## Research-only & safety checklist

- [ ] Preserves explicit non-clinical / uncalibrated warnings (`docs/model-card.md`)
- [ ] Contains zero real patient data, identifiers, or PHI
- [ ] `scikit-learn==1.6.1` compatibility preserved if `backend/` was touched

## Verification

```bash
npm ci
node --test tests/*.test.js
npm run build
python -m pip install -r backend/requirements-dev.txt
python -m pytest backend/tests -q
```
