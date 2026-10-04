"""FastAPI service for the CardioLens research prototype.

A trusted local model bundle is used when available. Without one, the service
falls back to a clearly labelled fabricated synthetic demo scorer. Neither mode
is clinically validated or for patient care.
"""
from __future__ import annotations

import math
import os
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = APP_ROOT / "artifacts" / "model_bundle.joblib"
BUNDLE_PATH = Path(os.getenv("CARDIO_MODEL_BUNDLE", str(DEFAULT_BUNDLE)))
FORBIDDEN_FEATURES = {"cad", "lad", "lcx", "rca", "cath"}
BOOLEAN_FEATURES = {
    "diabetes", "hypertension", "smoking", "ex_smoker", "family_history",
    "typical_chest_pain", "st_elevation", "st_depression", "t_inversion",
}
NUMERIC_RANGES = {
    "age": (18, 110), "bmi": (10, 80), "systolic_bp": (70, 250),
    "pulse_rate": (30, 220), "fbs": (30, 700), "ldl": (10, 500),
    "hdl": (5, 200), "tg": (20, 2000), "ef_tte": (5, 90), "region_rwma": (0, 4),
}
FEATURE_LABELS = {
    "age": ("Age", "years"), "sex": ("Sex", ""), "bmi": ("BMI", "kg/m²"),
    "diabetes": ("Diabetes", ""), "hypertension": ("Hypertension", ""),
    "smoking": ("Current smoker", ""), "ex_smoker": ("Former smoker", ""),
    "family_history": ("Family history", ""), "systolic_bp": ("Blood pressure", "mmHg"),
    "pulse_rate": ("Pulse rate", "bpm"), "typical_chest_pain": ("Typical chest pain", ""),
    "st_elevation": ("ST elevation", ""), "st_depression": ("ST depression", ""),
    "t_inversion": ("T-wave inversion", ""), "lvh": ("LVH", ""),
    "fbs": ("Fasting blood sugar", "mg/dL"), "tg": ("Triglycerides", "mg/dL"),
    "ldl": ("LDL", "mg/dL"), "hdl": ("HDL", "mg/dL"), "ef_tte": ("EF-TTE", "%"),
    "region_rwma": ("RWMA source code", "category"), "vhd": ("VHD", ""),
}

app = FastAPI(
    title="CardioLens Prototype API",
    version="0.2.0",
    description="Research-only CAD/vessel classifier and synthetic fallback. Not for clinical use.",
)


class PredictionRequest(BaseModel):
    schema_version: str = Field(default="0.2")
    features: dict[str, Any]


def _norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value))))


def _as_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"yes", "true", "1", "positive", "present", "y"}:
            return True
        if normalized in {"no", "false", "0", "negative", "absent", "n"}:
            return False
    raise ValueError(f"{name} must be a boolean / yes-no value")


def _checked_demo_features(raw: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "age": ["age"],
        "sex": ["sex", "gender"],
        "bmi": ["bmi"],
        "systolic_bp": ["systolic_bp", "sbp", "bp", "blood pressure"],
        "pulse_rate": ["pulse_rate", "pulse", "pr", "heart_rate"],
        "smoking": ["smoking", "current_smoker", "current smoker", "smoker"],
        "ex_smoker": ["ex_smoker", "ex-smoker", "former smoker"],
        "diabetes": ["diabetes", "dm"],
        "hypertension": ["hypertension", "htn"],
        "family_history": ["family_history", "fh", "family history"],
        "typical_chest_pain": ["typical_chest_pain", "typical chest pain"],
        "st_elevation": ["st_elevation", "st elevation"],
        "st_depression": ["st_depression", "st depression"],
        "t_inversion": ["t_inversion", "t inversion", "tinversion"],
        "lvh": ["lvh"],
        "fbs": ["fbs", "fasting blood sugar"],
        "ldl": ["ldl"],
        "hdl": ["hdl"],
        "tg": ["tg", "triglycerides"],
        "ef_tte": ["ef_tte", "ef-tte", "ejection fraction"],
        "region_rwma": ["region_rwma", "region rwma", "rwma source code"],
        "vhd": ["vhd"],
    }
    indexed = {_norm_key(key): value for key, value in raw.items()}
    result: dict[str, Any] = {}
    missing: list[str] = []
    for canonical, options in aliases.items():
        found = next((indexed[_norm_key(option)] for option in options if _norm_key(option) in indexed), None)
        if found is None:
            missing.append(canonical)
        else:
            result[canonical] = found
    if missing:
        raise ValueError("Missing demo fields: " + ", ".join(missing))

    for name, (low, high) in NUMERIC_RANGES.items():
        try:
            value = float(result[name])
        except (TypeError, ValueError):
            raise ValueError(f"{name} must be numeric") from None
        if not low <= value <= high:
            raise ValueError(f"{name} must be between {low} and {high} for this demo form")
        result[name] = int(value) if name == "region_rwma" else value

    result["sex"] = str(result["sex"])
    for name in BOOLEAN_FEATURES | {"lvh"}:
        result[name] = _as_bool(result[name], name)
    if result["smoking"] and result["ex_smoker"]:
        raise ValueError("smoking and ex_smoker cannot both be true for this source-cohort encoding")
    vhd = str(result["vhd"]).strip()
    allowed_vhd = {"N", "mild", "Moderate", "Severe"}
    match = next((option for option in allowed_vhd if option.lower() == vhd.lower()), None)
    if match is None:
        raise ValueError("vhd must be one of N, mild, Moderate, Severe")
    result["vhd"] = match
    return result


def _demo_predict(features: dict[str, Any]) -> dict[str, Any]:
    """Fabricated deterministic scores for exercising the UI only."""
    age = features["age"]
    sbp = features["systolic_bp"]
    pulse = features["pulse_rate"]
    rwma = features["region_rwma"] != 0
    vhd = {"N": 0.0, "mild": 0.08, "Moderate": 0.15, "Severe": 0.22}[features["vhd"]]
    factor_values = [
        ("Age", 0.34 * ((age - 50) / 25), f"{age:.0f}", "years"),
        ("Systolic blood pressure", 0.28 * ((sbp - 120) / 40), f"{sbp:.0f}", "mmHg"),
        ("BMI", 0.14 * ((features["bmi"] - 25) / 10), f"{features['bmi']:.1f}", "kg/m²"),
        ("LDL", 0.20 * ((features["ldl"] - 100) / 80), f"{features['ldl']:.0f}", "mg/dL"),
        ("HDL", 0.13 * ((50 - features["hdl"]) / 35), f"{features['hdl']:.0f}", "mg/dL"),
        ("Triglycerides", 0.10 * ((features["tg"] - 150) / 200), f"{features['tg']:.0f}", "mg/dL"),
        ("Current smoking", 0.40 if features["smoking"] else 0.0, "Yes" if features["smoking"] else "No", ""),
        ("Former smoking", 0.14 if features["ex_smoker"] else 0.0, "Yes" if features["ex_smoker"] else "No", ""),
        ("Diabetes", 0.32 if features["diabetes"] else 0.0, "Yes" if features["diabetes"] else "No", ""),
        ("Hypertension history", 0.20 if features["hypertension"] else 0.0, "Yes" if features["hypertension"] else "No", ""),
        ("Family history", 0.24 if features["family_history"] else 0.0, "Yes" if features["family_history"] else "No", ""),
        ("Typical chest pain", 0.25 if features["typical_chest_pain"] else 0.0, "Yes" if features["typical_chest_pain"] else "No", ""),
        ("ST elevation", 0.32 if features["st_elevation"] else 0.0, "Present" if features["st_elevation"] else "Absent", ""),
        ("ST depression", 0.24 if features["st_depression"] else 0.0, "Present" if features["st_depression"] else "Absent", ""),
        ("T inversion", 0.20 if features["t_inversion"] else 0.0, "Present" if features["t_inversion"] else "Absent", ""),
        ("LVH", 0.18 if features["lvh"] else 0.0, "Present" if features["lvh"] else "Absent", ""),
        ("RWMA code", 0.28 if rwma else 0.0, str(features["region_rwma"]), "source category"),
        ("EF-TTE", 0.12 * ((50 - features["ef_tte"]) / 20), f"{features['ef_tte']:.0f}", "%"),
        ("VHD", vhd, features["vhd"], ""),
        ("Fasting blood sugar", 0.10 * ((features["fbs"] - 100) / 50), f"{features['fbs']:.0f}", "mg/dL"),
    ]
    logit = -0.82 + sum(item[1] for item in factor_values) + 0.035 * ((pulse - 72) / 30)
    cad = _sigmoid(logit)
    lad = _sigmoid(logit - 0.18 + (0.10 if features["st_elevation"] else 0.0))
    lcx = _sigmoid(logit - 0.34 + (0.08 if features["t_inversion"] else 0.0))
    rca = _sigmoid(logit - 0.28 + (0.08 if features["hypertension"] else 0.0))

    explanations = []
    for label, contribution, value, unit in sorted(factor_values, key=lambda item: abs(item[1]), reverse=True)[:6]:
        explanations.append({
            "label": label,
            "value": value,
            "unit": unit,
            "contribution": float(contribution),
            "direction": "raises demo score" if contribution > 0.015 else ("lowers demo score" if contribution < -0.015 else "neutral in demo"),
        })
    return {
        "status": "ok",
        "mode": "synthetic_demo",
        "model_id": "synthetic-score-v0.2",
        "model_version": "0.2.0-demo",
        "calibration_status": "not_calibrated_synthetic",
        "target_definition": "Illustrative synthetic score only; no clinical interpretation.",
        "results": {
            "cad_present": {"score": cad, "estimate_type": "synthetic_demo_score", "status": "estimated"},
            "vessels": {
                "lad": {"score": lad, "estimate_type": "synthetic_demo_score", "status": "estimated"},
                "lcx": {"score": lcx, "estimate_type": "synthetic_demo_score", "status": "estimated"},
                "rca": {"score": rca, "estimate_type": "synthetic_demo_score", "status": "estimated"},
            },
        },
        "explanation": explanations,
        "future_risk": {"status": "unavailable", "reason": "No longitudinal future-event model is included."},
        "limitations": [
            "All displayed values are generated by a fabricated synthetic demo formula.",
            "Not trained on patient data, not calibrated, and not a clinical probability.",
            "Whole-vessel scores do not locate or measure a lesion.",
        ],
    }


def _linear_explanations(pipeline, frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Return local linear log-odds contributions for this baseline model."""
    try:
        transformed = pipeline.named_steps["prep"].transform(frame)
        if hasattr(transformed, "toarray"):
            transformed = transformed.toarray()
        clf = pipeline.named_steps["clf"]
        names = pipeline.named_steps["prep"].get_feature_names_out()
        contributions = np.asarray(transformed[0]).ravel() * np.asarray(clf.coef_[0]).ravel()
        order = np.argsort(np.abs(contributions))[::-1][:6]
        output = []
        for idx in order:
            feature_name = str(names[idx])
            key = next((candidate for candidate in FEATURE_LABELS if feature_name.startswith(f"num__{candidate}") or feature_name.startswith(f"cat__{candidate}_")), None)
            if key is None:
                label = feature_name.replace("num__", "").replace("cat__", "")
                value = "encoded"
                unit = ""
            else:
                label, unit = FEATURE_LABELS[key]
                value = frame.iloc[0][key]
                if isinstance(value, (bool, np.bool_)) or key in BOOLEAN_FEATURES:
                    value = "Yes" if bool(value) else "No"
                elif key == "lvh":
                    value = "Present" if str(value).upper() == "Y" else "Absent"
            output.append({
                "label": label,
                "value": str(value),
                "unit": unit,
                "contribution": float(contributions[idx]),
                "direction": "raises model log-odds" if contributions[idx] > 0 else "lowers model log-odds",
            })
        return output
    except Exception:
        return []


def _bundle_predict(raw_features: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    expected: list[str] = bundle["feature_columns"]
    indexed = {_norm_key(key): value for key, value in raw_features.items()}
    forbidden = [key for key in raw_features if _norm_key(key) in FORBIDDEN_FEATURES]
    if forbidden:
        return {"status": "not_estimable", "reason": "Outcome/diagnostic fields are not accepted as predictors.", "forbidden_fields": forbidden}
    missing = [
        name for name in expected
        if _norm_key(name) not in indexed
        or indexed[_norm_key(name)] is None
        or (isinstance(indexed[_norm_key(name)], str) and not indexed[_norm_key(name)].strip())
    ]
    if missing:
        return {
            "status": "not_estimable",
            "reason": "The research model requires the complete trained feature schema. No values were imputed at request time.",
            "missing_features": missing,
            "mode": "trained_research",
            "model_id": bundle.get("metadata", {}).get("model_id", "trained-research"),
            "model_version": bundle.get("metadata", {}).get("version", "unknown"),
        }

    row = {name: indexed[_norm_key(name)] for name in expected}
    for key, (low, high) in NUMERIC_RANGES.items():
        if key not in row:
            continue
        try:
            value = float(row[key])
        except (TypeError, ValueError):
            raise ValueError(f"{key} must be numeric") from None
        if not low <= value <= high:
            raise ValueError(f"{key} must be between {low} and {high}")
        row[key] = int(value) if key == "region_rwma" else value
    # Training data contain numeric 0/1 flags, while the form uses real booleans.
    for key in BOOLEAN_FEATURES:
        if key in row:
            row[key] = int(_as_bool(row[key], key))
    if row.get("smoking") == 1 and row.get("ex_smoker") == 1:
        raise ValueError("smoking and ex_smoker cannot both be true for this source-cohort encoding")
    if "lvh" in row:
        row["lvh"] = "Y" if _as_bool(row["lvh"], "lvh") else "N"
    if "sex" in row:
        token = str(row["sex"]).strip().lower()
        row["sex"] = "Female" if token in {"female", "fmale", "f"} else ("Male" if token in {"male", "m"} else str(row["sex"]))
        if row["sex"] not in {"Female", "Male"}:
            raise ValueError("sex category is not represented in the source cohort; this model cannot estimate it")
    if "vhd" in row:
        vhd = str(row["vhd"]).strip()
        allowed_vhd = {"N", "mild", "Moderate", "Severe"}
        match = next((option for option in allowed_vhd if option.lower() == vhd.lower()), None)
        if match is None:
            raise ValueError("vhd must be one of N, mild, Moderate, Severe")
        row["vhd"] = match
    frame = pd.DataFrame([row], columns=expected)

    results: dict[str, Any] = {}
    explanation: list[dict[str, Any]] = []
    for target in ["cad_present", "lad", "lcx", "rca"]:
        pipeline = bundle["models"][target]
        score = float(pipeline.predict_proba(frame)[0, 1])
        results[target] = {"score": score, "estimate_type": "uncalibrated_research_model_score", "status": "estimated"}
        if target == "cad_present":
            explanation = _linear_explanations(pipeline, frame)
    metadata = bundle.get("metadata", {})
    return {
        "status": "ok",
        "mode": "trained_research",
        "model_id": metadata.get("model_id", "local-logistic-baseline"),
        "model_version": metadata.get("version", "research-1"),
        "calibration_status": "uncalibrated_research",
        "target_definition": "Source-cohort prevalent CAD/vessel label; uncalibrated score, external validation required.",
        "results": {
            "cad_present": results["cad_present"],
            "vessels": {"lad": results["lad"], "lcx": results["lcx"], "rca": results["rca"]},
        },
        "explanation": explanation,
        "future_risk": {"status": "unavailable", "reason": "No future-event model is included in this prototype."},
        "limitations": [
            "Research baseline trained on a small source cohort; internal cross-validation is not external or prospective validation.",
            "Scores are uncalibrated and must not be interpreted as clinical risk probabilities.",
            "Whole-vessel labels do not provide lesion location or patient-specific anatomy.",
        ],
    }


def _load_bundle() -> dict[str, Any] | None:
    if not BUNDLE_PATH.exists():
        return None
    # Load only a locally produced, trusted artifact. Never load user-supplied joblib/pickle data.
    bundle = joblib.load(BUNDLE_PATH)
    needed = {"models", "feature_columns", "metadata"}
    if not isinstance(bundle, dict) or not needed.issubset(bundle):
        raise RuntimeError(f"Invalid model bundle structure at {BUNDLE_PATH}")
    for key in ["cad_present", "lad", "lcx", "rca"]:
        if key not in bundle["models"]:
            raise RuntimeError(f"Model bundle missing target {key}")
    if any(_norm_key(name) in FORBIDDEN_FEATURES for name in bundle["feature_columns"]):
        raise RuntimeError("Refusing to load model bundle with a forbidden target/diagnostic feature")
    return bundle


BUNDLE = _load_bundle()


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "cardiolens-api", "mode": "trained_research" if BUNDLE else "synthetic_demo"}


@app.get("/api/model-info")
def model_info() -> dict[str, Any]:
    if BUNDLE:
        meta = BUNDLE.get("metadata", {})
        return {
            "mode": "trained_research",
            "model_id": meta.get("model_id", "local-logistic-baseline"),
            "model_version": meta.get("version", "research-1"),
            "feature_count": len(BUNDLE["feature_columns"]),
            "training_rows": meta.get("source_rows"),
            "label_consistency": meta.get("label_consistency"),
            "calibration_status": "uncalibrated_research",
            "targets": ["cad_present", "lad", "lcx", "rca"],
            "future_risk_available": False,
        }
    return {
        "mode": "synthetic_demo",
        "model_id": "synthetic-score-v0.2",
        "model_version": "0.2.0-demo",
        "feature_count": len(FEATURE_LABELS),
        "calibration_status": "not_calibrated_synthetic",
        "targets": ["cad_present", "lad", "lcx", "rca"],
        "future_risk_available": False,
    }


@app.get("/api/sample-case")
def sample_case() -> dict[str, Any]:
    return {
        "case_id": "DEMO-01",
        "case_label": "Synthetic demo inputs",
        "as_of": "2026-10-04T09:00:00+05:30",
        "features": {
            "age": 58,
            "sex": "Female",
            "bmi": 27.4,
            "systolic_bp": 138,
            "pulse_rate": 74,
            "smoking": False,
            "ex_smoker": False,
            "diabetes": False,
            "hypertension": True,
            "family_history": True,
            "typical_chest_pain": False,
            "st_elevation": False,
            "st_depression": False,
            "t_inversion": True,
            "lvh": False,
            "fbs": 96,
            "ldl": 122,
            "hdl": 48,
            "tg": 154,
            "ef_tte": 55,
            "region_rwma": 0,
            "vhd": "N",
        },
    }


@app.post("/api/predict")
def predict(request: PredictionRequest) -> JSONResponse:
    try:
        if BUNDLE:
            result = _bundle_predict(request.features, BUNDLE)
        else:
            result = _demo_predict(_checked_demo_features(request.features))
    except (ValueError, TypeError) as exc:
        return JSONResponse(status_code=422, content={"status": "invalid_input", "message": str(exc)})
    return JSONResponse(content=result)
