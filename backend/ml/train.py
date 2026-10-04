"""Train Track A binary baselines from the public UCI Z-Alizadeh Sani extension.

Example (from backend/):
  python -m ml.train --data data/z_alizadeh_extension.xlsx --out artifacts

The default curated feature mapping matches the prototype form. It trains
research-only logistic baselines and writes repeated internal-CV results. It does
not establish clinical validity, calibration, or future-event risk.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

FORBIDDEN = {"cad", "lad", "lcx", "rca", "cath"}
TARGETS = {"cad_present": "cad", "lad": "lad", "lcx": "lcx", "rca": "rca"}
ID_NAMES = {"id", "patientid", "recordid", "subjectid", "serialnumber", "name"}
POSITIVE = {"1", "1.0", "true", "yes", "y", "positive", "pos", "present", "stenosis", "stenotic", "disease", "cad"}
NEGATIVE = {"0", "0.0", "false", "no", "n", "negative", "neg", "absent", "normal", "nocad", "nostenosis"}

# Source column (normalized) -> stable API/model feature key. All are available
# in the official 59-column UCI extension used for this prototype.
DEFAULT_FEATURE_MAP = {
    "age": "age",
    "sex": "sex",
    "bmi": "bmi",
    "dm": "diabetes",
    "htn": "hypertension",
    "currentsmoker": "smoking",
    "exsmoker": "ex_smoker",
    "fh": "family_history",
    "bp": "systolic_bp",
    "pr": "pulse_rate",
    "typicalchestpain": "typical_chest_pain",
    "stelevation": "st_elevation",
    "stdepression": "st_depression",
    "tinversion": "t_inversion",
    "lvh": "lvh",
    "fbs": "fbs",
    "tg": "tg",
    "ldl": "ldl",
    "hdl": "hdl",
    "eftte": "ef_tte",
    "regionrwma": "region_rwma",
    "vhd": "vhd",
}


def norm(name: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(name).strip().lower())


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_table(path: Path, sheet: str | None = None) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        frame = pd.read_excel(path, sheet_name=sheet or 0)
    elif suffix == ".csv":
        frame = pd.read_csv(path)
    else:
        raise ValueError("Input must be .xlsx, .xls, or .csv")
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError("The selected dataset sheet is empty or could not be read")
    frame.columns = [str(column).strip() for column in frame.columns]
    if len({norm(column) for column in frame.columns}) != len(frame.columns):
        raise ValueError("Column names collide after normalization; resolve them in the source file")
    return frame


def find_targets(frame: pd.DataFrame) -> dict[str, str]:
    indexed = {norm(column): column for column in frame.columns}
    # The official UCI xlsx calls the overall angiography label "Cath" (CAD/Normal).
    # Some Track A/Kaggle variants expose a separate "CAD" column; prefer that.
    overall = indexed.get("cad") or indexed.get("cath")
    if overall is None:
        raise ValueError(f"Missing overall CAD label column ('CAD' or 'Cath'). Found: {list(frame.columns)}")
    result = {"cad_present": overall}
    for target in ["lad", "lcx", "rca"]:
        if target not in indexed:
            raise ValueError(f"Missing vessel label column '{target.upper()}'. Found: {list(frame.columns)}")
        result[target] = indexed[target]
    if norm(overall) == "cath":
        print("INFO: using Cath as the overall CAD target because the source file has no separate CAD column; Cath remains forbidden as a predictor.")
    return result


def parse_binary_label(value: Any, column: str) -> int | None:
    if pd.isna(value):
        return None
    if isinstance(value, (bool, np.bool_)):
        return int(value)
    text = str(value).strip().lower()
    token = re.sub(r"[^a-z0-9.]+", "", text)
    if token in POSITIVE:
        return 1
    if token in NEGATIVE:
        return 0
    try:
        number = float(text)
        if number in (0.0, 1.0):
            return int(number)
    except ValueError:
        pass
    raise ValueError(f"Unrecognized label {value!r} in {column!r}. Map its positive/negative values explicitly.")


def select_features(frame: pd.DataFrame, target_columns: dict[str, str]) -> list[str]:
    """Select the curated subset that is represented by the UI; return source names."""
    indexed = {norm(column): column for column in frame.columns}
    selected = [indexed[source] for source in DEFAULT_FEATURE_MAP if source in indexed]
    if not selected:
        raise ValueError("No recognized clinical predictors remain after the target/diagnostic leakage firewall")
    forbidden = [column for column in selected if norm(column) in FORBIDDEN]
    if forbidden or set(selected).intersection(target_columns.values()):
        raise RuntimeError(f"Leakage firewall failed: {forbidden}")
    missing = [source for source in DEFAULT_FEATURE_MAP if source not in indexed]
    if missing:
        print("WARNING: source file is missing optional curated fields: " + ", ".join(missing))
    return selected


def normalize_feature_types(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    for column in output.columns:
        series = output[column]
        if pd.api.types.is_bool_dtype(series):
            output[column] = series.astype("object")
            continue
        if pd.api.types.is_numeric_dtype(series):
            continue
        stripped = series.astype("string").str.strip().replace({"": pd.NA, "?": pd.NA, "NA": pd.NA, "nan": pd.NA})
        if norm(column) == "sex":
            # The source xlsx contains the spelling "Fmale"; normalize without changing target labels.
            stripped = stripped.map(lambda value: "Female" if str(value).strip().lower() in {"fmale", "female", "f"} else ("Male" if str(value).strip().lower() in {"male", "m"} else value))
        numeric = pd.to_numeric(stripped, errors="coerce")
        nonmissing = stripped.notna().sum()
        if nonmissing and numeric.notna().sum() / nonmissing >= 0.95:
            output[column] = numeric
        else:
            output[column] = stripped.astype("object")
    return output


def make_pipeline(x: pd.DataFrame) -> Pipeline:
    categorical = []
    numeric = []
    for column in x.columns:
        series = x[column]
        is_cat = (not pd.api.types.is_numeric_dtype(series)) or pd.api.types.is_bool_dtype(series)
        if not is_cat and series.nunique(dropna=True) <= 10:
            is_cat = True
        (categorical if is_cat else numeric).append(column)

    transformers = []
    if numeric:
        numeric_pipe = Pipeline([
            ("impute", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)),
            ("scale", StandardScaler()),
        ])
        transformers.append(("num", numeric_pipe, numeric))
    if categorical:
        categorical_pipe = Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent", keep_empty_features=True)),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ])
        transformers.append(("cat", categorical_pipe, categorical))
    prep = ColumnTransformer(transformers, remainder="drop", verbose_feature_names_out=True)
    classifier = LogisticRegression(
        C=0.5,
        solver="liblinear",
        class_weight="balanced",
        max_iter=3000,
        random_state=2026,
    )
    return Pipeline([("prep", prep), ("clf", classifier)])


def _safe_metrics(y_true: np.ndarray, probability: np.ndarray, threshold: float = 0.5) -> dict[str, float]:
    predicted = (probability >= threshold).astype(int)
    metrics = {
        "accuracy": accuracy_score(y_true, predicted),
        "precision": precision_score(y_true, predicted, zero_division=0),
        "recall_sensitivity": recall_score(y_true, predicted, zero_division=0),
        "specificity": recall_score(y_true, predicted, pos_label=0, zero_division=0),
        "f1": f1_score(y_true, predicted, zero_division=0),
        "brier": brier_score_loss(y_true, probability),
    }
    metrics["roc_auc"] = roc_auc_score(y_true, probability) if len(np.unique(y_true)) == 2 else float("nan")
    metrics["pr_auc"] = average_precision_score(y_true, probability) if len(np.unique(y_true)) == 2 else float("nan")
    return {key: float(value) for key, value in metrics.items()}


def repeated_cv(x: pd.DataFrame, y: np.ndarray) -> dict[str, Any]:
    counts = np.bincount(y.astype(int), minlength=2)
    minority = int(counts.min())
    if minority < 2:
        raise ValueError("Each target needs at least two positive and two negative cases for stratified CV")
    folds = min(5, minority)
    splitter = RepeatedStratifiedKFold(n_splits=folds, n_repeats=5, random_state=2026)
    template = make_pipeline(x)
    rows = []
    for train_index, test_index in splitter.split(x, y):
        model = clone(template)
        model.fit(x.iloc[train_index], y[train_index])
        probability = model.predict_proba(x.iloc[test_index])[:, 1]
        rows.append(_safe_metrics(y[test_index], probability))
    summary = {}
    for key in rows[0]:
        values = np.array([row[key] for row in rows], dtype=float)
        summary[key] = {"mean": float(np.nanmean(values)), "sd_across_folds": float(np.nanstd(values, ddof=1))}
    return {
        "folds": folds,
        "repeats": 5,
        "fold_metrics": rows,
        "summary": summary,
        "class_counts": {"negative": int(counts[0]), "positive": int(counts[1])},
        "threshold": 0.5,
        "note": "Repeated internal CV of a fixed baseline; not external validation and not a clinical benchmark.",
    }


def label_consistency(frame: pd.DataFrame, target_columns: dict[str, str]) -> dict[str, Any] | None:
    """Compare overall CAD label with the OR of the three vessel labels where all exist."""
    parsed = {}
    for key, column in target_columns.items():
        parsed[key] = [parse_binary_label(value, column) for value in frame[column].tolist()]
    valid = []
    for idx in range(len(frame)):
        values = [parsed[key][idx] for key in ["cad_present", "lad", "lcx", "rca"]]
        if all(value is not None for value in values):
            overall, lad, lcx, rca = values
            valid.append(overall == int(bool(lad or lcx or rca)))
    if not valid:
        return None
    return {"rows_compared": len(valid), "agreement_rate": float(np.mean(valid)), "disagreements": int(len(valid) - sum(valid)), "note": "QA comparison only; source target is retained as supplied."}


def train(data_path: Path, output_dir: Path, sheet: str | None = None) -> None:
    frame = read_table(data_path, sheet)
    target_columns = find_targets(frame)
    feature_sources = select_features(frame, target_columns)
    source_to_canonical = {source: DEFAULT_FEATURE_MAP[norm(source)] for source in feature_sources}
    x_raw = frame[feature_sources].rename(columns=source_to_canonical)
    x_all = normalize_feature_types(x_raw)
    feature_columns = list(x_all.columns)
    if any(norm(name) in FORBIDDEN for name in feature_columns):
        raise RuntimeError("Forbidden target/diagnostic field found in canonical model features")

    models: dict[str, Any] = {}
    metrics: dict[str, Any] = {}
    row_counts: dict[str, int] = {}
    for target, column in target_columns.items():
        parsed = [parse_binary_label(value, column) for value in frame[column].tolist()]
        keep = np.array([value is not None for value in parsed])
        y = np.array([value for value in parsed if value is not None], dtype=int)
        x = x_all.loc[keep].reset_index(drop=True)
        if len(np.unique(y)) != 2:
            raise ValueError(f"Target {column!r} must contain both positive and negative cases")
        metrics[target] = repeated_cv(x, y)
        model = make_pipeline(x)
        model.fit(x, y)
        models[target] = model
        row_counts[target] = int(len(y))
        print(f"{target} (label={column}): n={len(y)}; positive={int(y.sum())}; CV ROC-AUC={metrics[target]['summary']['roc_auc']['mean']:.3f}")

    output_dir.mkdir(parents=True, exist_ok=True)
    consistency = label_consistency(frame, target_columns)
    metadata = {
        "model_id": "z-alizadeh-logistic-baseline",
        "version": "research-1.1.0",
        "dataset_name": "UCI extension of Z-Alizadeh Sani",
        "dataset_filename": data_path.name,
        "dataset_sha256": file_sha256(data_path),
        "source_rows": int(len(frame)),
        "feature_count": len(feature_columns),
        "feature_mapping": source_to_canonical,
        "target_columns": target_columns,
        "row_counts_by_target": row_counts,
        "label_consistency": consistency,
        "calibration_status": "uncalibrated_research",
        "training_library": f"scikit-learn {sklearn.__version__}",
        "leakage_exclusions": sorted(FORBIDDEN),
        "intended_use": "Research-only model for source-dataset prevalent CAD/vessel labels; no clinical use.",
    }
    bundle = {"models": models, "feature_columns": feature_columns, "metadata": metadata}
    joblib.dump(bundle, output_dir / "model_bundle.joblib", compress=3)
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, allow_nan=False), encoding="utf-8")
    (output_dir / "feature_manifest.json").write_text(json.dumps({
        "feature_columns": feature_columns,
        "source_to_canonical": source_to_canonical,
        "target_columns": target_columns,
        "forbidden_predictors": sorted(FORBIDDEN),
        "dataset_sha256": metadata["dataset_sha256"],
        "label_consistency": consistency,
    }, indent=2), encoding="utf-8")
    print(f"Label consistency (CAD vs any target vessel): {consistency}")
    print(f"\nWrote research bundle to {output_dir / 'model_bundle.joblib'}")
    print("Do not use clinical scores until independent validation, calibration, regulatory, privacy and workflow gates are passed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Track A CAD/vessel logistic-regression baselines")
    parser.add_argument("--data", required=True, type=Path, help="Path to the UCI extension .xlsx or .csv")
    parser.add_argument("--out", type=Path, default=Path("artifacts"), help="Output directory (default: artifacts)")
    parser.add_argument("--sheet", default=None, help="Optional Excel worksheet name")
    args = parser.parse_args()
    if not args.data.is_file():
        raise SystemExit(f"Dataset not found: {args.data}")
    train(args.data, args.out, args.sheet)


if __name__ == "__main__":
    main()
