"""FastAPI service for the CardioLens research prototype.

A trusted local model bundle is used when available. Without one, the service
falls back to a clearly labelled fabricated synthetic demo scorer. Neither mode
is clinically validated or for patient care.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = APP_ROOT / "artifacts" / "model_bundle.joblib"
BUNDLE_PATH = Path(os.getenv("CARDIO_MODEL_BUNDLE", str(DEFAULT_BUNDLE)))
DEFAULT_METRICS = APP_ROOT / "artifacts" / "metrics.json"
METRICS_PATH = Path(os.getenv("CARDIO_MODEL_METRICS", str(DEFAULT_METRICS)))
CV_TARGETS = ("cad_present", "lad", "lcx", "rca")
CV_METRICS = ("roc_auc", "pr_auc", "brier")
CV_INTERPRETATION = (
    "Internal CV summary only: each value is the mean ± SD across repeated "
    "stratified cross-validation folds in the source cohort. It is not a "
    "patient-level confidence interval, prediction interval, or clinical probability."
)
FORBIDDEN_FEATURES = {"cad", "lad", "lcx", "rca", "cath"}
FEATURE_FIELDS = (
    "age", "sex", "bmi", "diabetes", "hypertension", "smoking", "ex_smoker",
    "family_history", "systolic_bp", "pulse_rate", "typical_chest_pain",
    "st_elevation", "st_depression", "t_inversion", "lvh", "fbs", "tg",
    "ldl", "hdl", "ef_tte", "region_rwma", "vhd",
)
IDENTIFIER_FIELDS = ("name", "patient_id", "mrn", "dob", "email", "phone", "address")
REPORT_SCHEMA_VERSION = "1.0"
REPORT_TYPE = "cardiolens_research_report"
NON_CLINICAL_DISCLAIMER = (
    "Research-only report based on synthetic demo inputs. Scores are uncalibrated "
    "model outputs, not clinical probabilities, diagnoses, or treatment guidance. "
    "Do not use for patient care."
)
DEMO_FEATURE_ALIASES = {
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
BOOLEAN_FEATURES = {
    "diabetes", "hypertension", "smoking", "ex_smoker", "family_history",
    "typical_chest_pain", "st_elevation", "st_depression", "t_inversion", "lvh",
}
NUMERIC_RANGES = {
    "age": (18, 110), "bmi": (10, 80), "systolic_bp": (70, 250),
    "pulse_rate": (30, 220), "fbs": (30, 700), "ldl": (10, 500),
    "hdl": (5, 200), "tg": (20, 2000), "ef_tte": (5, 90), "region_rwma": (0, 4),
}
SEX_CATEGORIES = {"Female", "Male"}
VHD_CATEGORIES = {"N", "mild", "Moderate", "Severe"}
INTEGER_FEATURES = {"region_rwma"}
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
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default="0.2")
    features: dict[str, Any]


def _norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


_IDENTIFIER_NORMALIZED_KEYS = {_norm_key(field) for field in IDENTIFIER_FIELDS} | {
    "fullname", "patientname", "dateofbirth", "phonenumber", "telephonenumber",
    "mobilenumber", "emailaddress", "homeaddress", "postaladdress",
    "streetaddress", "medicalrecordnumber",
}


def _is_identifier_key(value: Any) -> bool:
    normalized = _norm_key(value)
    return bool(
        normalized in _IDENTIFIER_NORMALIZED_KEYS
        or normalized.endswith("name")
        or normalized.startswith("patient")
        or "email" in normalized
        or "phone" in normalized
        or "telephone" in normalized
        or "mobile" in normalized
        or "address" in normalized
        or "birth" in normalized
        or "medicalrecord" in normalized
    )


def _feature_key_rejection(
    raw: dict[str, Any], allowed_normalized_keys: set[str]
) -> dict[str, Any] | None:
    """Return a fail-closed rejection for identifier, diagnostic, or unknown keys."""
    if not isinstance(raw, dict):
        return {
            "status": "not_estimable",
            "reason": "Input features must be an object of validated synthetic fields.",
            "rejection_type": "invalid_features",
            "rejected_fields": [],
        }

    identifier_fields = [str(key) for key in raw if _is_identifier_key(key)]
    if identifier_fields:
        return {
            "status": "not_estimable",
            "reason": (
                "Identifier/PHI fields are not accepted: "
                + ", ".join(identifier_fields)
                + ". Do not submit names or identifiers."
            ),
            "rejection_type": "identifier_fields",
            "rejected_fields": identifier_fields,
        }

    forbidden_fields = [str(key) for key in raw if _norm_key(key) in FORBIDDEN_FEATURES]
    if forbidden_fields:
        return {
            "status": "not_estimable",
            "reason": "Outcome/diagnostic fields are not accepted as predictors.",
            "rejection_type": "forbidden_features",
            "forbidden_fields": forbidden_fields,
            "rejected_fields": forbidden_fields,
        }

    unexpected_fields = [
        str(key) for key in raw if _norm_key(key) not in allowed_normalized_keys
    ]
    if unexpected_fields:
        return {
            "status": "not_estimable",
            "reason": (
                "Unexpected input fields are not accepted: "
                + ", ".join(unexpected_fields)
                + ". Only validated synthetic model fields may be submitted."
            ),
            "rejection_type": "unexpected_fields",
            "rejected_fields": unexpected_fields,
        }
    return None


def _validate_feature_keys(raw: dict[str, Any], allowed_normalized_keys: set[str]) -> None:
    rejection = _feature_key_rejection(raw, allowed_normalized_keys)
    if rejection is not None:
        raise ValueError(str(rejection["reason"]))


_INVALID_INPUT_MESSAGES = {
    "identifier_fields": "Identifier/PHI fields are not accepted. Do not submit names or identifiers.",
    "unexpected_fields": "Unexpected input fields are not accepted. Submit only validated synthetic predictor fields.",
    "forbidden_features": "Outcome/diagnostic fields are not accepted as predictors.",
    "missing_fields": "Missing required predictor fields. Submit the complete validated synthetic field set.",
    "invalid_input": "Invalid input. Submit only validated synthetic predictor fields.",
}
_FEATURE_FIELDS_BY_NORMALIZED = {_norm_key(field): field for field in FEATURE_FIELDS}
_SAFE_VALIDATION_LOCATIONS = {"body", "features", "schema_version"}
_SAFE_VALIDATION_MESSAGES = {
    "extra_forbidden": "Unexpected fields are not accepted.",
    "missing": "Field required.",
}


def _invalid_input_response(error_code: str = "invalid_input") -> JSONResponse:
    """Return a 422 response that never echoes unvalidated keys or values."""
    code = error_code if error_code in _INVALID_INPUT_MESSAGES else "invalid_input"
    return JSONResponse(
        status_code=422,
        content={
            "status": "invalid_input",
            "error_code": code,
            "message": _INVALID_INPUT_MESSAGES[code],
        },
    )


def _invalid_input_response_for_error(exc: Exception) -> JSONResponse:
    message = str(exc)
    if message.startswith("Identifier/PHI fields"):
        return _invalid_input_response("identifier_fields")
    if message.startswith("Unexpected input fields"):
        return _invalid_input_response("unexpected_fields")
    if message.startswith("Outcome/diagnostic fields"):
        return _invalid_input_response("forbidden_features")
    if message.startswith("Missing demo fields") or "missing fields" in message.lower():
        return _invalid_input_response("missing_fields")
    return _invalid_input_response()


def _safe_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Strip raw input/context from validation errors before returning them.

    Pydantic's default error objects include an ``input`` entry (and sometimes
    context) containing the exact unvalidated value. Those values can be
    accidental identifiers or free text, so only allow-listed field locations,
    the error type, and a fixed message are retained.
    """
    safe_errors: list[dict[str, Any]] = []
    for error in errors or []:
        if not isinstance(error, dict):
            safe_errors.append({
                "loc": ["body"],
                "type": "value_error",
                "message": "Invalid input.",
            })
            continue

        safe_loc: list[str | int] = []
        for part in error.get("loc") or ("body",):
            if isinstance(part, int) and not isinstance(part, bool):
                safe_loc.append(part)
            elif isinstance(part, str) and part in _SAFE_VALIDATION_LOCATIONS:
                safe_loc.append(part)
            elif isinstance(part, str) and _norm_key(part) in _FEATURE_FIELDS_BY_NORMALIZED:
                safe_loc.append(_FEATURE_FIELDS_BY_NORMALIZED[_norm_key(part)])
            elif isinstance(part, str) and _is_identifier_key(part):
                safe_loc.append("identifier_field")
            else:
                safe_loc.append("redacted_field")

        error_type = str(error.get("type") or "value_error")
        safe_errors.append({
            "loc": safe_loc,
            "type": error_type,
            "message": _SAFE_VALIDATION_MESSAGES.get(error_type, "Invalid input."),
        })
    return safe_errors


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Deliberately do not read or log the request body or stringify ``exc``:
    # both can contain raw, unvalidated free-text values.
    del request
    return JSONResponse(
        status_code=422,
        content={
            "status": "invalid_input",
            "error_code": "request_validation_failed",
            "message": (
                "Request validation failed. Submit only validated synthetic "
                "predictor fields; identifiers and free-text fields are not accepted."
            ),
            "errors": _safe_validation_errors(exc.errors()),
        },
    )


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
    allowed_keys = {
        _norm_key(alias)
        for aliases in DEMO_FEATURE_ALIASES.values()
        for alias in aliases
    }
    _validate_feature_keys(raw, allowed_keys)
    aliases = DEMO_FEATURE_ALIASES
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
        if name in INTEGER_FEATURES and not value.is_integer():
            raise ValueError(f"{name} must be an integer")
        result[name] = int(value) if name in INTEGER_FEATURES else value

    result["sex"] = str(result["sex"])
    if result["sex"] not in SEX_CATEGORIES:
        raise ValueError("sex category is not represented in the source cohort; this model cannot estimate it")
    for name in BOOLEAN_FEATURES:
        result[name] = _as_bool(result[name], name)
    if result["smoking"] and result["ex_smoker"]:
        raise ValueError("smoking and ex_smoker cannot both be true for this source-cohort encoding")
    vhd = str(result["vhd"]).strip()
    match = next((option for option in VHD_CATEGORIES if option.lower() == vhd.lower()), None)
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
                if isinstance(value, (bool, np.bool_)) or key in BOOLEAN_FEATURES - {"lvh"}:
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
    rejection = _feature_key_rejection(
        raw_features, {_norm_key(name) for name in expected}
    )
    if rejection is not None:
        return rejection
    indexed = {_norm_key(key): value for key, value in raw_features.items()}
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
        if key in INTEGER_FEATURES and not value.is_integer():
            raise ValueError(f"{key} must be an integer")
        row[key] = int(value) if key in INTEGER_FEATURES else value
    if "sex" in row:
        token = str(row["sex"]).strip().lower()
        row["sex"] = "Female" if token in {"female", "fmale", "f"} else ("Male" if token in {"male", "m"} else str(row["sex"]))
        if row["sex"] not in SEX_CATEGORIES:
            raise ValueError("sex category is not represented in the source cohort; this model cannot estimate it")
    if "vhd" in row:
        vhd = str(row["vhd"]).strip()
        match = next((option for option in VHD_CATEGORIES if option.lower() == vhd.lower()), None)
        if match is None:
            raise ValueError("vhd must be one of N, mild, Moderate, Severe")
        row["vhd"] = match

    # Snapshot the human-readable validated inputs before model encoding.
    validated_inputs = {
        name: (_as_bool(row[name], name) if name in BOOLEAN_FEATURES else row[name])
        for name in expected
    }
    if validated_inputs.get("smoking") is True and validated_inputs.get("ex_smoker") is True:
        raise ValueError("smoking and ex_smoker cannot both be true for this source-cohort encoding")

    # Training data contain numeric 0/1 flags, while the form uses real booleans.
    for key in BOOLEAN_FEATURES - {"lvh"}:
        if key in row:
            row[key] = int(_as_bool(row[key], key))
    if "lvh" in row:
        row["lvh"] = "Y" if _as_bool(row["lvh"], "lvh") else "N"
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
        "validated_inputs": validated_inputs,
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


def _model_bundle_sha256(bundle_path: Path | None = None) -> str | None:
    """Return the SHA-256 of the trusted local model bundle, when present."""
    path = Path(bundle_path) if bundle_path is not None else BUNDLE_PATH
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _scikit_learn_version() -> str:
    return str(sklearn.__version__)


def _ordered_validated_features(features: dict[str, Any]) -> dict[str, Any]:
    # Re-run the canonical validator so a report can never be built from
    # unvalidated values merely because the caller used the right key names.
    checked = _checked_demo_features(features)
    return {name: checked[name] for name in FEATURE_FIELDS}


def _report_head_output(prediction: dict[str, Any], target: str) -> dict[str, Any]:
    results = prediction.get("results")
    if not isinstance(results, dict):
        raise ValueError("Prediction results are missing from the report source.")
    if target == "cad_present":
        source = results.get("cad_present")
    else:
        vessels = results.get("vessels")
        source = vessels.get(target) if isinstance(vessels, dict) else None
    if not isinstance(source, dict) or not _is_finite_number(source.get("score")):
        raise ValueError(f"Prediction result is missing a finite score for '{target}'.")
    score = float(source["score"])
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"Prediction score for '{target}' is outside the 0–1 scale.")
    return {
        "score": score,
        "estimate_type": str(source.get("estimate_type") or "uncalibrated_model_score"),
        "status": str(source.get("status") or "estimated"),
        "calibration_status": str(prediction.get("calibration_status") or "uncalibrated"),
        "interpretation": "Uncalibrated score; not a clinical probability.",
    }


def _report_contributions(prediction: dict[str, Any]) -> list[dict[str, Any]]:
    explanation = prediction.get("explanation") or []
    if not isinstance(explanation, list):
        raise ValueError("Prediction explanation must be a list for a research report.")
    contributions: list[dict[str, Any]] = []
    for item in explanation:
        if not isinstance(item, dict) or not _is_finite_number(item.get("contribution")):
            continue
        contributions.append({
            "label": str(item.get("label") or "Model input"),
            "value": str(item.get("value") or ""),
            "unit": str(item.get("unit") or ""),
            "contribution": float(item["contribution"]),
            "direction": str(item.get("direction") or ""),
        })
    return contributions


def build_research_report(
    validated_features: dict[str, Any],
    prediction: dict[str, Any],
    *,
    model_bundle_sha256: str | None = None,
    scikit_learn_version: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic, self-describing research report.

    The report deliberately contains no timestamp, case identifier, free-text
    identifier, or raw prediction-object spread. Only allow-listed validated
    inputs, head outputs, and contribution fields are copied, in fixed order.
    """
    if not isinstance(prediction, dict) or prediction.get("status") != "ok":
        raise ValueError("A research report requires a successful prediction.")
    mode = prediction.get("mode")
    if mode not in {"trained_research", "synthetic_demo"}:
        raise ValueError("A research report requires a trained_research or synthetic_demo prediction.")

    ordered_features = _ordered_validated_features(validated_features)
    head_outputs = {
        target: _report_head_output(prediction, target)
        for target in CV_TARGETS
    }
    is_trained = mode == "trained_research"
    bundle_sha256 = (model_bundle_sha256 or _model_bundle_sha256()) if is_trained else None
    sklearn_version = (scikit_learn_version or _scikit_learn_version()) if is_trained else None
    limitations = prediction.get("limitations")
    if not isinstance(limitations, list) or not all(isinstance(item, str) for item in limitations):
        limitations = [
            "Research-only output; not clinically validated.",
            "Scores are uncalibrated and must not be interpreted as clinical probabilities.",
        ]

    future_risk = prediction.get("future_risk")
    if not isinstance(future_risk, dict):
        future_risk = {"status": "unavailable", "reason": "No longitudinal future-event model is included."}

    return {
        "report_type": REPORT_TYPE,
        "schema_version": REPORT_SCHEMA_VERSION,
        "mode": mode,
        "model": {
            "model_id": str(prediction.get("model_id") or "unknown"),
            "model_version": str(prediction.get("model_version") or "unknown"),
            "calibration_status": str(prediction.get("calibration_status") or "uncalibrated"),
            "model_bundle_sha256": bundle_sha256,
            "model_bundle_status": (
                "available" if bundle_sha256 else "unavailable"
            ) if is_trained else "not_applicable_synthetic_demo",
            "scikit_learn_version": sklearn_version,
        },
        "inputs": {
            "provenance": "validated_synthetic_inputs",
            "contains_identifiers": False,
            "features": ordered_features,
        },
        "head_outputs": head_outputs,
        "log_odds_contributions": _report_contributions(prediction),
        "contribution_basis": (
            "Local linear log-odds contributions for the overall CAD head; not causal effects or treatment guidance."
            if is_trained
            else "Synthetic demo logit contributions; not trained-model log-odds, causal effects, or clinical explanations."
        ),
        "future_risk": {
            "status": str(future_risk.get("status") or "unavailable"),
            "reason": str(future_risk.get("reason") or "No longitudinal future-event model is included."),
        },
        "disclaimer": NON_CLINICAL_DISCLAIMER,
        "limitations": list(limitations),
    }


def research_report_filename(report: dict[str, Any]) -> str:
    mode = report.get("mode") if isinstance(report, dict) else None
    if mode not in {"trained_research", "synthetic_demo"}:
        mode = "synthetic_demo"
    return f"cardiolens-research-report-v{REPORT_SCHEMA_VERSION}-{mode}.json"


def _report_for_features(raw_features: dict[str, Any]) -> dict[str, Any]:
    if BUNDLE:
        prediction = _bundle_predict(raw_features, BUNDLE)
        if prediction.get("status") != "ok":
            raise ValueError(str(prediction.get("reason") or "The research model could not estimate this case."))
        validated_features = prediction["validated_inputs"]
    else:
        validated_features = _checked_demo_features(raw_features)
        prediction = _demo_predict(validated_features)
    return build_research_report(validated_features, prediction)


def _cv_unavailable(reason: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "reason": reason,
        "interpretation": CV_INTERPRETATION,
        "targets": {},
    }


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _bounded_cv_number(value: Any) -> float | None:
    if not _is_finite_number(value):
        return None
    number = float(value)
    return number if 0.0 <= number <= 1.0 else None


def _positive_cv_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _nonnegative_cv_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _cv_metric_summary(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    mean = _bounded_cv_number(value.get("mean"))
    sd = _bounded_cv_number(value.get("sd_across_folds"))
    if mean is None or sd is None:
        return None
    return {"mean": mean, "sd_across_folds": sd}


def _load_cv_summary(metrics_path: Path | None = None) -> dict[str, Any]:
    """Load a compact, validated CV summary without exposing per-fold rows.

    The training artifact intentionally contains every fold's metrics. The API
    returns only the per-target mean/SD pairs needed by the UI so callers do
    not receive (or accidentally visualize) the raw fold-level payload. Any
    missing or malformed value fails closed as ``unavailable`` rather than
    being replaced with a fabricated zero.
    """
    path = Path(metrics_path) if metrics_path is not None else METRICS_PATH
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return _cv_unavailable("Internal cross-validation metrics artifact is not installed.")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _cv_unavailable("Internal cross-validation metrics artifact could not be read.")

    if not isinstance(raw, dict):
        return _cv_unavailable("Internal cross-validation metrics artifact has an invalid structure.")

    targets: dict[str, Any] = {}
    designs: set[tuple[int, int]] = set()
    cohort_sizes: set[int] = set()
    for target in CV_TARGETS:
        entry = raw.get(target)
        if not isinstance(entry, dict) or not isinstance(entry.get("summary"), dict):
            return _cv_unavailable(f"Internal cross-validation summary is missing target '{target}'.")

        folds = _positive_cv_int(entry.get("folds"))
        repeats = _positive_cv_int(entry.get("repeats"))
        if folds is None or repeats is None:
            return _cv_unavailable(f"Internal cross-validation design is invalid for target '{target}'.")
        designs.add((folds, repeats))

        summary: dict[str, Any] = {}
        for metric in CV_METRICS:
            metric_summary = _cv_metric_summary(entry["summary"].get(metric))
            if metric_summary is None:
                return _cv_unavailable(
                    f"Internal cross-validation metric '{metric}' is invalid for target '{target}'."
                )
            summary[metric] = metric_summary

        counts = entry.get("class_counts")
        if not isinstance(counts, dict):
            return _cv_unavailable(f"Internal cross-validation class counts are missing for target '{target}'.")
        positive = _nonnegative_cv_int(counts.get("positive"))
        negative = _nonnegative_cv_int(counts.get("negative"))
        if positive is None or negative is None or positive + negative <= 0:
            return _cv_unavailable(f"Internal cross-validation class counts are invalid for target '{target}'.")
        cohort_n = positive + negative
        cohort_sizes.add(cohort_n)

        threshold = _bounded_cv_number(entry.get("threshold"))
        if threshold is None:
            return _cv_unavailable(f"Internal cross-validation threshold is invalid for target '{target}'.")

        target_summary: dict[str, Any] = {
            **summary,
            "class_counts": {"positive": positive, "negative": negative},
            "cohort_n": cohort_n,
            "threshold": threshold,
        }
        if isinstance(entry.get("note"), str) and entry["note"].strip():
            target_summary["note"] = entry["note"].strip()
        targets[target] = target_summary

    if len(designs) != 1 or len(cohort_sizes) != 1:
        return _cv_unavailable("Internal cross-validation artifacts do not share one design and cohort.")

    folds, repeats = next(iter(designs))
    cohort_n = next(iter(cohort_sizes))
    return {
        "status": "available",
        "source": "metrics_json",
        "evaluation": "internal repeated stratified cross-validation",
        "design": {
            "folds": folds,
            "repeats": repeats,
            "total_folds": folds * repeats,
            "label": f"{folds}×{repeats} CV",
        },
        "cohort_n": cohort_n,
        "cohort_note": f"n={cohort_n} source cohort",
        "interpretation": CV_INTERPRETATION,
        "summary_only": True,
        "targets": targets,
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
        bundle_sha256 = _model_bundle_sha256()
        return {
            "mode": "trained_research",
            "model_id": meta.get("model_id", "local-logistic-baseline"),
            "model_version": meta.get("version", "research-1"),
            "feature_count": len(BUNDLE["feature_columns"]),
            "training_rows": meta.get("source_rows"),
            "label_consistency": meta.get("label_consistency"),
            "calibration_status": "uncalibrated_research",
            "model_bundle_sha256": bundle_sha256,
            "model_bundle_status": "available" if bundle_sha256 else "unavailable",
            "scikit_learn_version": _scikit_learn_version(),
            "targets": list(CV_TARGETS),
            "cv_summary": _load_cv_summary(),
            "future_risk_available": False,
        }
    return {
        "mode": "synthetic_demo",
        "model_id": "synthetic-score-v0.2",
        "model_version": "0.2.0-demo",
        "feature_count": len(FEATURE_LABELS),
        "calibration_status": "not_calibrated_synthetic",
        "model_bundle_sha256": None,
        "model_bundle_status": "not_applicable_synthetic_demo",
        "scikit_learn_version": None,
        "targets": list(CV_TARGETS),
        "cv_summary": _cv_unavailable(
            "The synthetic demo formula has no trained-model cross-validation summary."
        ),
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
            if result.get("status") == "not_estimable" and result.get("rejection_type"):
                return _invalid_input_response(str(result["rejection_type"]))
        else:
            result = _demo_predict(_checked_demo_features(request.features))
    except (ValueError, TypeError) as exc:
        return _invalid_input_response_for_error(exc)
    return JSONResponse(content=result)


@app.post("/api/report")
def report(request: PredictionRequest) -> JSONResponse:
    """Return a deterministic JSON research report as a download."""
    try:
        report_payload = _report_for_features(request.features)
    except (ValueError, TypeError) as exc:
        return _invalid_input_response_for_error(exc)
    return JSONResponse(
        content=report_payload,
        headers={
            "Content-Disposition": f'attachment; filename="{research_report_filename(report_payload)}"'
        },
    )
