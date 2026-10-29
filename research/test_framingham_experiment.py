import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from framingham_experiment import FEATURES, run


class ExperimentTests(unittest.TestCase):
    def make_data(self):
        rng = np.random.default_rng(17)
        df = pd.DataFrame({name: rng.normal(100, 10, 80) for name in FEATURES})
        for name in ['male', 'currentSmoker', 'BPMeds', 'diabetes']:
            df[name] = rng.integers(0, 2, 80)
        df['prevalentStroke'] = 0
        df.loc[0, 'prevalentStroke'] = 1
        df['TenYearCHD'] = [0, 1] * 40
        df.loc[1, 'glucose'] = np.nan
        return df

    def test_aggregate_run_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'synthetic.csv'
            self.make_data().to_csv(path, index=False)
            a, b = run(path), run(path)
            self.assertEqual(a, b)
            self.assertEqual(a['rows_analyzed'], 79)
            self.assertEqual(a['excluded_prior_stroke'], 1)
            self.assertEqual(sum(group['n'] for group in a['calibration_bins']), a['test_rows'])
            self.assertTrue(0 <= a['roc_auc'] <= 1)
            self.assertNotIn('predictions', a)

    def test_missing_or_invalid_target_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'synthetic.csv'
            df = self.make_data()
            df.loc[0, 'TenYearCHD'] = 2
            df.to_csv(path, index=False)
            with self.assertRaises(ValueError): run(path)
            df.drop(columns=['TenYearCHD']).to_csv(path, index=False)
            with self.assertRaises(ValueError): run(path)


if __name__ == '__main__': unittest.main()
