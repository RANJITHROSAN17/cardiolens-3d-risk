"""Exploratory research benchmark; not a clinical prediction implementation.

Outputs aggregate metrics only; no fitted model or row-level predictions are saved.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ['male', 'age', 'currentSmoker', 'BPMeds', 'diabetes', 'totChol', 'sysBP', 'BMI', 'glucose']
TARGET = 'TenYearCHD'
SEED = 42


def run(path):
    raw = Path(path).read_bytes()
    frame = pd.read_csv(path)
    required = FEATURES + [TARGET, 'prevalentStroke']
    if len(frame.columns) != len(set(frame.columns)) or not set(required).issubset(frame.columns):
        raise ValueError('Missing required columns or duplicate column names')
    if frame[required].apply(pd.to_numeric, errors='coerce').notna().sum().sum() != frame[required].notna().sum().sum():
        raise ValueError('Inputs must be numeric or missing')
    if not frame[TARGET].isin([0, 1]).all() or not frame['prevalentStroke'].isin([0, 1]).all():
        raise ValueError('Outcome and stroke history must be 0 or 1 and nonmissing')
    for name in ['male', 'currentSmoker', 'BPMeds', 'diabetes']:
        if not frame[name].dropna().isin([0, 1]).all():
            raise ValueError(f'{name} must be 0, 1 or missing')
    # The mirror does not contain sufficient information to exclude all prior CVD.
    eligible = frame[frame.prevalentStroke == 0].copy()
    X = eligible[FEATURES].astype(float)
    y = eligible[TARGET].astype(int)
    train_x, test_x, train_y, test_y = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    model = make_pipeline(SimpleImputer(strategy='median'), StandardScaler(), LogisticRegression(max_iter=1000, random_state=SEED))
    model.fit(train_x, train_y)
    prediction = model.predict_proba(test_x)[:, 1]
    # Rank-based, approximately equal-sized bins; not patient-level information.
    order = np.argsort(prediction, kind='stable')
    bins = []
    for indexes in np.array_split(order, 5):
        bins.append({'n': int(len(indexes)), 'mean_prediction': float(np.mean(prediction[indexes])),
                     'observed_event_fraction': float(np.mean(test_y.to_numpy()[indexes]))})
    return {
        'warning': 'Exploratory same-source holdout, not clinically validated; outcome is CHD only, not heart attack or stroke composite.',
        'dataset_sha256': hashlib.sha256(raw).hexdigest(), 'rows_total': len(frame),
        'excluded_prior_stroke': int((frame.prevalentStroke == 1).sum()), 'rows_analyzed': len(eligible),
        'training_rows': len(train_y), 'test_rows': len(test_y), 'training_events': int(train_y.sum()),
        'test_events': int(test_y.sum()), 'test_event_fraction': float(test_y.mean()),
        'roc_auc': float(roc_auc_score(test_y, prediction)), 'average_precision': float(average_precision_score(test_y, prediction)),
        'brier_score': float(brier_score_loss(test_y, prediction)),
        'baseline_brier_score': float(brier_score_loss(test_y, np.full(len(test_y), train_y.mean()))),
        'calibration_bins': bins, 'features': FEATURES, 'split_seed': SEED,
        'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__, 'scikit_learn': sklearn.__version__,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, help='Path to privately obtained CSV; do not commit it')
    parser.add_argument('--out', required=True, help='Path to write aggregate JSON')
    args = parser.parse_args()
    results = run(args.data)
    Path(args.out).write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
