import json
from pathlib import Path

import pandas as pd
import pytest

import app.main as main
from app.main import BUNDLE, _bundle_predict, _checked_demo_features, _demo_predict
from ml.train import calibration_summary, find_targets, parse_binary_label, repeated_cv, select_features


DEMO = {
    "age": 58, "sex": "Female", "bmi": 27.4, "systolic_bp": 138,
    "pulse_rate": 74, "smoking": False, "ex_smoker": False,
    "diabetes": False, "hypertension": True, "family_history": True,
    "typical_chest_pain": False, "st_elevation": False, "st_depression": False,
    "t_inversion": True, "lvh": False, "fbs": 96, "ldl": 122, "hdl": 48,
    "tg": 154, "ef_tte": 55, "region_rwma": 0, "vhd": "N",
}


def test_synthetic_demo_returns_bounded_scores_and_safety_metadata():
    checked = _checked_demo_features(DEMO)
    result = _demo_predict(checked)
    assert result["mode"] == "synthetic_demo"
    assert result["calibration_status"] == "not_calibrated_synthetic"
    assert result["future_risk"]["status"] == "unavailable"
    assert 0 <= result["results"]["cad_present"]["score"] <= 1
    assert set(result["results"]["vessels"]) == {"lad", "lcx", "rca"}


def test_demo_rejects_out_of_range_input():
    with pytest.raises(ValueError):
        _checked_demo_features({**DEMO, "age": 9})


def test_bundled_research_schema_matches_form_and_rejects_outcomes():
    if BUNDLE is None:
        pytest.skip("optional model bundle is not installed")
    result = _bundle_predict(DEMO, BUNDLE)
    assert result["status"] == "ok"
    assert result["mode"] == "trained_research"
    assert set(result["results"]["vessels"]) == {"lad", "lcx", "rca"}
    rejected = _bundle_predict({**DEMO, "Cath": "CAD"}, BUNDLE)
    assert rejected["status"] == "not_estimable"
    incomplete = _bundle_predict({**DEMO, "bmi": ""}, BUNDLE)
    assert incomplete["status"] == "not_estimable"
    assert "bmi" in incomplete["missing_features"]
    with pytest.raises(ValueError):
        _bundle_predict({**DEMO, "age": 9}, BUNDLE)
    with pytest.raises(ValueError):
        _bundle_predict({**DEMO, "sex": "Other / not recorded"}, BUNDLE)
    with pytest.raises(ValueError):
        _bundle_predict({**DEMO, "smoking": True, "ex_smoker": True}, BUNDLE)


def test_target_and_cath_columns_never_become_features():
    frame = pd.DataFrame(columns=["Age", "BP", "CAD", "LAD", "LCX", "RCA", "Cath", "PatientID"])
    targets = {"cad_present": "CAD", "lad": "LAD", "lcx": "LCX", "rca": "RCA"}
    assert select_features(frame, targets) == ["Age", "BP"]


def test_official_extension_cath_can_be_overall_cad_label_not_predictor():
    frame = pd.DataFrame(columns=["Age", "BP", "LAD", "LCX", "RCA", "Cath"])
    targets = find_targets(frame)
    assert targets["cad_present"] == "Cath"
    assert "Cath" not in select_features(frame, targets)


def test_binary_label_decoder_fails_closed_on_unknown_labels():
    assert parse_binary_label("CAD", "Cath") == 1
    assert parse_binary_label("Normal", "Cath") == 0
    assert parse_binary_label("Stenotic", "LAD") == 1
    with pytest.raises(ValueError):
        parse_binary_label("maybe", "CAD")


def test_calibration_summary_reports_bounded_monotone_quantile_bins():
    import numpy as np

    probabilities = np.repeat([0.1, 0.3, 0.5, 0.7, 0.9], 20)
    labels = np.concatenate([
        np.concatenate([np.ones(int(fraction * 20), dtype=int), np.zeros(20 - int(fraction * 20), dtype=int)])
        for fraction in [0.1, 0.3, 0.5, 0.7, 0.9]
    ])

    calibration = calibration_summary(labels, probabilities, n_bins=5)
    bins = calibration["bins"]

    assert calibration["status"] == "uncalibrated_research"
    assert calibration["sample_count"] == calibration["prediction_count"] == 100
    assert [row["count"] for row in bins] == [20, 20, 20, 20, 20]
    assert sum(row["count"] for row in bins) == len(labels)
    assert [row["mean_predicted_score"] for row in bins] == pytest.approx([0.1, 0.3, 0.5, 0.7, 0.9])
    assert [row["observed_fraction"] for row in bins] == pytest.approx([0.1, 0.3, 0.5, 0.7, 0.9])
    assert all(
        left["mean_predicted_score"] <= right["mean_predicted_score"]
        for left, right in zip(bins, bins[1:])
    )
    assert all(0.0 <= row["mean_predicted_score"] <= 1.0 for row in bins)
    assert all(0.0 <= row["observed_fraction"] <= 1.0 for row in bins)
    assert calibration["slope"] == pytest.approx(1.0, abs=1e-6)
    assert calibration["intercept"] == pytest.approx(0.0, abs=1e-6)


def test_calibration_summary_rejects_non_probability_scores():
    import numpy as np

    with pytest.raises(ValueError, match="finite probabilities"):
        calibration_summary(np.array([0, 1]), np.array([0.2, 1.2]))


def test_repeated_cv_calibration_uses_synthetic_stratified_frame_without_target_leakage():
    import numpy as np

    rng = np.random.default_rng(2026)
    labels = np.tile([0, 1], 60)
    signal = labels + rng.normal(0.0, 0.65, size=len(labels))
    frame = pd.DataFrame({
        "Age": 35.0 + 20.0 * labels + rng.normal(0.0, 3.0, size=len(labels)),
        "Sex": np.where(np.arange(len(labels)) % 3, "Female", "Male"),
        "BP": 105.0 + 25.0 * signal + rng.normal(0.0, 4.0, size=len(labels)),
        "Cath": np.where(labels, "CAD", "Normal"),
        "LAD": np.where(labels, "Stenotic", "Normal"),
        "LCX": np.where(labels, "Stenotic", "Normal"),
        "RCA": np.where(labels, "Stenotic", "Normal"),
    })
    targets = find_targets(frame)
    feature_sources = select_features(frame, targets)

    assert feature_sources == ["Age", "Sex", "BP"]
    assert not {column.lower() for column in feature_sources} & {"cad", "cath", "lad", "lcx", "rca"}
    assert not set(feature_sources) & set(targets.values())

    result = repeated_cv(frame[feature_sources], labels)
    calibration = result["calibration"]
    bins = calibration["bins"]

    assert result["class_counts"] == {"negative": 60, "positive": 60}
    assert calibration["sample_count"] == 120
    assert calibration["prediction_count"] == 600
    assert sum(row["count"] for row in bins) == calibration["prediction_count"]
    assert max(row["count"] for row in bins) - min(row["count"] for row in bins) <= 1
    assert all(
        left["mean_predicted_score"] <= right["mean_predicted_score"]
        for left, right in zip(bins, bins[1:])
    )
    assert all(0.0 <= row["mean_predicted_score"] <= 1.0 for row in bins)
    assert all(0.0 <= row["observed_fraction"] <= 1.0 for row in bins)
    assert np.isfinite([calibration["slope"], calibration["intercept"]]).all()


def test_metrics_artifact_records_calibration_for_all_targets():
    root = Path(__file__).resolve().parents[2]
    artifact = json.loads((root / "backend" / "artifacts" / "metrics.json").read_text(encoding="utf-8"))

    assert set(artifact) == {"cad_present", "lad", "lcx", "rca"}
    for target in artifact.values():
        calibration = target["calibration"]
        bins = calibration["bins"]
        assert calibration["status"] == "uncalibrated_research"
        assert calibration["binning"] == "quantile"
        assert calibration["sample_count"] == 303
        assert calibration["prediction_count"] == 303 * target["repeats"]
        assert sum(row["count"] for row in bins) == calibration["prediction_count"]
        assert all(
            left["mean_predicted_score"] <= right["mean_predicted_score"]
            for left, right in zip(bins, bins[1:])
        )
        assert all(0.0 <= row["observed_fraction"] <= 1.0 for row in bins)


def test_frontend_backend_schema_parity():
    """Read the actual ESM export; fail, rather than skip, if either schema drifts."""
    import json
    from pathlib import Path
    import subprocess
    from app.main import (
        BOOLEAN_FEATURES, FEATURE_FIELDS, FORBIDDEN_FEATURES, IDENTIFIER_FIELDS,
        INTEGER_FEATURES, NUMERIC_RANGES, SEX_CATEGORIES, VHD_CATEGORIES,
    )

    root = Path(__file__).resolve().parents[2]
    output = subprocess.run(
        ["node", "--input-type=module", "-e",
         "import {VALIDATION_SCHEMA} from './src/validation.js';"
         "console.log(JSON.stringify(VALIDATION_SCHEMA));"],
        cwd=root, check=True, capture_output=True, text=True, timeout=15,
    )
    frontend = json.loads(output.stdout)
    expected = {
        "numeric_ranges": {name: list(bounds) for name, bounds in NUMERIC_RANGES.items()},
        "boolean_features": sorted(BOOLEAN_FEATURES),
        "sex": sorted(SEX_CATEGORIES), "vhd": sorted(VHD_CATEGORIES),
        "integer_features": sorted(INTEGER_FEATURES),
        "forbidden_features": sorted(FORBIDDEN_FEATURES),
        "feature_fields": list(FEATURE_FIELDS),
        "identifier_fields": list(IDENTIFIER_FIELDS),
    }
    normalized_frontend = {
        key: sorted(value)
        if isinstance(value, list) and key not in {"feature_fields", "identifier_fields"}
        else value
        for key, value in frontend.items()
    }
    assert normalized_frontend == expected


@pytest.mark.parametrize("updates", [
    {"smoking": True, "ex_smoker": True},
    {"region_rwma": 0.5}, {"region_rwma": 1.5}, {"region_rwma": 3.9},
    {"sex": "Other / not recorded"}, {"vhd": "unsupported"},
])
def test_both_backend_modes_reject_invalid_coding(updates):
    # Minimal bundle schema ensures validation runs without an optional model artifact.
    with pytest.raises(ValueError):
        _checked_demo_features({**DEMO, **updates})
    with pytest.raises(ValueError):
        _bundle_predict({**DEMO, **updates}, {"feature_columns": list(DEMO)})


@pytest.mark.parametrize("key", ["CAD", "Cath", "LAD", "LCX", "RCA", " c-A_d "])
def test_both_backend_modes_reject_diagnostic_leakage(key):
    raw = {**DEMO, key: False}
    with pytest.raises(ValueError, match="Outcome/diagnostic"):
        _checked_demo_features(raw)
    assert _bundle_predict(raw, {"feature_columns": list(DEMO)})["status"] == "not_estimable"


def test_demo_accepts_all_canonical_categories_and_numeric_boundaries():
    from app.main import BOOLEAN_FEATURES, NUMERIC_RANGES, SEX_CATEGORIES, VHD_CATEGORIES

    for name, bounds in NUMERIC_RANGES.items():
        for value in bounds:
            assert _checked_demo_features({**DEMO, name: value})[name] == value
        for value in [bounds[0] - 1, bounds[1] + 1, float("nan"), float("inf")]:
            with pytest.raises(ValueError):
                _checked_demo_features({**DEMO, name: value})
            with pytest.raises(ValueError):
                _bundle_predict({**DEMO, name: value}, {"feature_columns": list(DEMO)})
    for name, values in [("sex", SEX_CATEGORIES), ("vhd", VHD_CATEGORIES)]:
        for value in values:
            assert _checked_demo_features({**DEMO, name: value})[name] == value
    for name in BOOLEAN_FEATURES:
        for value in [True, False]:
            assert _checked_demo_features({**DEMO, name: value})[name] is value


@pytest.mark.parametrize("lvh,label", [(False, "Absent"), (True, "Present")])
def test_lvh_model_encoding_and_explanation_are_preserved(lvh, label):
    from types import SimpleNamespace
    import numpy as np

    class Pipeline:
        named_steps = {
            "prep": SimpleNamespace(
                transform=lambda frame: np.array([[1.0]]),
                get_feature_names_out=lambda: ["cat__lvh_N"],
            ),
            "clf": SimpleNamespace(coef_=np.array([[0.1]])),
        }

        def predict_proba(self, frame):
            assert frame.iloc[0]["lvh"] == ("Y" if lvh else "N")
            return np.array([[0.6, 0.4]])

    pipeline = Pipeline()
    bundle = {
        "feature_columns": list(DEMO),
        "models": {name: pipeline for name in ["cad_present", "lad", "lcx", "rca"]},
    }
    result = _bundle_predict({**DEMO, "lvh": lvh}, bundle)
    assert result["status"] == "ok"
    assert result["explanation"][0]["value"] == label


def _trained_model_info_bundle() -> dict:
    return {
        "feature_columns": list(DEMO),
        "metadata": {
            "model_id": "z-alizadeh-logistic-baseline",
            "version": "research-1.1.0",
            "source_rows": 303,
            "label_consistency": {"checked": True},
        },
    }


def test_model_info_exposes_compact_cv_summary_from_metrics_artifact(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    artifact = json.loads((root / "backend" / "artifacts" / "metrics.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(main, "BUNDLE", _trained_model_info_bundle())

    info = main.model_info()
    summary = info["cv_summary"]

    assert info["training_rows"] == 303
    assert summary["status"] == "available"
    assert summary["source"] == "metrics_json"
    assert summary["design"] == {"folds": 5, "repeats": 5, "total_folds": 25, "label": "5×5 CV"}
    assert summary["cohort_n"] == 303
    assert summary["cohort_note"] == "n=303 source cohort"
    assert summary["summary_only"] is True
    assert "not a patient-level confidence interval" in summary["interpretation"]
    assert "fold_metrics" not in json.dumps(info)

    for target, source in artifact.items():
        exposed = summary["targets"][target]
        assert exposed["class_counts"] == source["class_counts"]
        assert exposed["cohort_n"] == source["class_counts"]["positive"] + source["class_counts"]["negative"] == 303
        assert exposed["threshold"] == source["threshold"]
        for metric in ("roc_auc", "pr_auc", "brier"):
            assert exposed[metric] == source["summary"][metric]


def test_cv_summary_fails_closed_when_metrics_are_missing_or_malformed(tmp_path, monkeypatch):
    missing = main._load_cv_summary(tmp_path / "missing-metrics.json")
    assert missing["status"] == "unavailable"
    assert missing["targets"] == {}

    malformed_path = tmp_path / "metrics.json"
    malformed_path.write_text('{"lad": {"summary": {}}}', encoding="utf-8")
    malformed = main._load_cv_summary(malformed_path)
    assert malformed["status"] == "unavailable"
    assert malformed["targets"] == {}

    monkeypatch.setattr(main, "BUNDLE", _trained_model_info_bundle())
    monkeypatch.setattr(main, "METRICS_PATH", tmp_path / "missing-metrics.json")
    assert main.model_info()["cv_summary"]["status"] == "unavailable"


def test_synthetic_demo_model_info_does_not_claim_trained_cv_metrics(monkeypatch):
    monkeypatch.setattr(main, "BUNDLE", None)

    info = main.model_info()

    assert info["mode"] == "synthetic_demo"
    assert info["cv_summary"]["status"] == "unavailable"
    assert info["cv_summary"]["targets"] == {}
    assert "synthetic demo" in info["cv_summary"]["reason"]


def test_frontend_static_cv_fallback_matches_metrics_artifact():
    import subprocess

    root = Path(__file__).resolve().parents[2]
    artifact = json.loads((root / "backend" / "artifacts" / "metrics.json").read_text(encoding="utf-8"))
    output = subprocess.run(
        ["node", "--input-type=module", "-e",
         "import {STATIC_CV_SUMMARY} from './src/model-metrics.js';"
         "console.log(JSON.stringify(STATIC_CV_SUMMARY));"],
        cwd=root, check=True, capture_output=True, text=True, timeout=15,
    )
    bundled = json.loads(output.stdout)

    assert bundled["cohort_n"] == 303
    assert bundled["design"] == {"folds": 5, "repeats": 5, "total_folds": 25, "label": "5×5 CV"}
    assert "fold_metrics" not in json.dumps(bundled)
    for target, source in artifact.items():
        exposed = bundled["targets"][target]
        assert exposed["class_counts"] == source["class_counts"]
        assert exposed["threshold"] == source["threshold"]
        for metric in ("roc_auc", "pr_auc", "brier"):
            assert exposed[metric] == source["summary"][metric]


@pytest.mark.parametrize("key", [
    "name", "patient_id", "mrn", "dob", "email", "phone", "address",
    "patientId", "patient-id", "date_of_birth", "e-mail", "phone_number",
    "home_address", "medical_record_number",
])
def test_identifier_fields_are_rejected_by_both_backend_modes(key):
    with pytest.raises(ValueError, match="Identifier/PHI"):
        _checked_demo_features({**DEMO, key: "synthetic-value"})

    rejected = _bundle_predict(
        {**DEMO, key: "synthetic-value"}, {"feature_columns": list(DEMO)}
    )
    assert rejected["status"] == "not_estimable"
    assert rejected["rejection_type"] == "identifier_fields"
    assert rejected["rejected_fields"] == [key]


def test_unexpected_fields_are_rejected_by_both_backend_modes():
    with pytest.raises(ValueError, match="Unexpected input fields"):
        _checked_demo_features({**DEMO, "unexpected_note": "synthetic-value"})

    rejected = _bundle_predict(
        {**DEMO, "unexpected_note": "synthetic-value"}, {"feature_columns": list(DEMO)}
    )
    assert rejected["status"] == "not_estimable"
    assert rejected["rejection_type"] == "unexpected_fields"
    assert rejected["rejected_fields"] == ["unexpected_note"]


def test_prediction_request_rejects_unexpected_top_level_keys():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        main.PredictionRequest(
            schema_version="0.2", features=DEMO, patient_id="synthetic-id"
        )


def test_documented_demo_aliases_map_only_to_the_22_canonical_fields():
    assert set(main.DEMO_FEATURE_ALIASES) == set(main.FEATURE_FIELDS)
    assert set(main.DEMO_FEATURE_ALIASES) == set(DEMO) and len(DEMO) == 22

    alias_payload = {
        "age": DEMO["age"], "gender": DEMO["sex"], "bmi": DEMO["bmi"],
        "sbp": DEMO["systolic_bp"], "pr": DEMO["pulse_rate"],
        "current smoker": DEMO["smoking"], "ex-smoker": DEMO["ex_smoker"],
        "dm": DEMO["diabetes"], "htn": DEMO["hypertension"], "fh": DEMO["family_history"],
        "typical chest pain": DEMO["typical_chest_pain"],
        "st elevation": DEMO["st_elevation"], "st depression": DEMO["st_depression"],
        "t inversion": DEMO["t_inversion"], "lvh": DEMO["lvh"],
        "fasting blood sugar": DEMO["fbs"], "triglycerides": DEMO["tg"],
        "ldl": DEMO["ldl"], "hdl": DEMO["hdl"], "ef-tte": DEMO["ef_tte"],
        "region rwma": DEMO["region_rwma"], "vhd": DEMO["vhd"],
    }

    assert _checked_demo_features(alias_payload) == _checked_demo_features(DEMO)


def test_fastapi_validation_error_response_strips_raw_input_and_context():
    import asyncio
    from fastapi.exceptions import RequestValidationError

    marker = "SYNTHETIC_FREE_TEXT_MARKER"
    errors = [{
        "loc": ("body", "patient_id"),
        "msg": marker,
        "type": "extra_forbidden",
        "input": marker,
        "ctx": {"value": marker},
    }]

    safe = main._safe_validation_errors(errors)
    assert marker not in json.dumps(safe)
    assert safe == [{
        "loc": ["body", "identifier_field"],
        "type": "extra_forbidden",
        "message": "Unexpected fields are not accepted.",
    }]
    assert main._safe_validation_errors([
        {"loc": ("body", marker), "msg": marker, "type": "extra_forbidden", "input": marker}
    ])[0]["loc"] == ["body", "redacted_field"]

    response = asyncio.run(
        main.validation_exception_handler(None, RequestValidationError(errors))
    )
    body = response.body.decode()
    assert response.status_code == 422
    assert marker not in body
    assert json.loads(body)["error_code"] == "request_validation_failed"


@pytest.mark.parametrize("bundle", [None, {"feature_columns": list(DEMO)}])
def test_predict_endpoint_returns_sanitized_422_for_key_rejections(bundle, monkeypatch, caplog):
    marker = "SYNTHETIC_FREE_TEXT_MARKER"
    monkeypatch.setattr(main, "BUNDLE", bundle)

    for features in [
        {**DEMO, "patient_id": marker},
        {**DEMO, marker: "synthetic-value"},
        {**DEMO, "unexpected_note": marker},
    ]:
        with caplog.at_level("WARNING"):
            response = main.predict(
                main.PredictionRequest(schema_version="0.2", features=features)
            )
        body = response.body.decode()
        assert response.status_code == 422
        assert json.loads(body)["status"] == "invalid_input"
        assert marker not in body
        assert "unexpected_note" not in body
        assert marker not in caplog.text


def test_predict_endpoint_sanitizes_free_text_field_values(monkeypatch, caplog):
    marker = "SYNTHETIC_FREE_TEXT_MARKER"
    monkeypatch.setattr(main, "BUNDLE", None)

    with caplog.at_level("WARNING"):
        response = main.predict(
            main.PredictionRequest(schema_version="0.2", features={**DEMO, "sex": marker})
        )

    assert response.status_code == 422
    assert marker not in response.body.decode()
    assert marker not in caplog.text


def test_report_endpoint_returns_sanitized_422_for_unknown_keys(monkeypatch):
    marker = "SYNTHETIC_FREE_TEXT_MARKER"
    monkeypatch.setattr(main, "BUNDLE", None)

    response = main.report(
        main.PredictionRequest(
            schema_version="0.2", features={**DEMO, "unexpected_note": marker}
        )
    )

    assert response.status_code == 422
    assert json.loads(response.body)["error_code"] == "unexpected_fields"
    assert marker not in response.body.decode()
    assert "unexpected_note" not in response.body.decode()


def test_bundle_prediction_returns_human_readable_validated_inputs():
    from types import SimpleNamespace
    import numpy as np

    class Pipeline:
        named_steps = {
            "prep": SimpleNamespace(
                transform=lambda frame: np.array([[1.0]]),
                get_feature_names_out=lambda: ["cat__lvh_N"],
            ),
            "clf": SimpleNamespace(coef_=np.array([[0.1]])),
        }

        def predict_proba(self, frame):
            return np.array([[0.6, 0.4]])

    pipeline = Pipeline()
    bundle = {
        "feature_columns": list(DEMO),
        "models": {name: pipeline for name in ["cad_present", "lad", "lcx", "rca"]},
        "metadata": {"model_id": "fake-bundle", "version": "test"},
    }
    result = _bundle_predict({**DEMO, "age": "58", "lvh": True}, bundle)

    assert result["status"] == "ok"
    assert result["validated_inputs"] == {**DEMO, "age": 58.0, "lvh": True}


def test_research_report_is_deterministic_and_self_describing_for_trained_model():
    if BUNDLE is None:
        pytest.skip("optional model bundle is not installed")
    import hashlib
    import sklearn

    prediction = _bundle_predict(DEMO, BUNDLE)
    report = main.build_research_report(prediction["validated_inputs"], prediction)
    second_report = main.build_research_report(prediction["validated_inputs"], prediction)

    assert report == second_report
    assert json.dumps(report, sort_keys=True) == json.dumps(second_report, sort_keys=True)
    assert list(report) == [
        "report_type", "schema_version", "mode", "model", "inputs", "head_outputs",
        "log_odds_contributions", "contribution_basis", "future_risk", "disclaimer", "limitations",
    ]
    assert report["schema_version"] == main.REPORT_SCHEMA_VERSION == "1.0"
    assert report["mode"] == "trained_research"
    assert report["model"]["model_bundle_sha256"] == hashlib.sha256(
        main.BUNDLE_PATH.read_bytes()
    ).hexdigest()
    assert report["model"]["scikit_learn_version"] == sklearn.__version__ == "1.6.1"
    assert report["inputs"] == {
        "provenance": "validated_synthetic_inputs",
        "contains_identifiers": False,
        "features": prediction["validated_inputs"],
    }
    assert list(report["head_outputs"]) == ["cad_present", "lad", "lcx", "rca"]
    assert report["head_outputs"]["cad_present"]["score"] == prediction["results"]["cad_present"]["score"]
    assert report["head_outputs"]["rca"]["score"] == prediction["results"]["vessels"]["rca"]["score"]
    assert report["log_odds_contributions"] == prediction["explanation"]
    assert report["disclaimer"] == main.NON_CLINICAL_DISCLAIMER
    assert "not clinical probabilities" in report["disclaimer"]
    assert "patient_id" not in json.dumps(report)
    assert main.research_report_filename(report) == "cardiolens-research-report-v1.0-trained_research.json"


def test_research_report_is_deterministic_and_unbundled_for_synthetic_demo():
    checked = _checked_demo_features(DEMO)
    prediction = _demo_predict(checked)

    report = main.build_research_report(checked, prediction)
    second_report = main.build_research_report(checked, prediction)

    assert report == second_report
    assert report["mode"] == "synthetic_demo"
    assert report["model"]["model_bundle_sha256"] is None
    assert report["model"]["model_bundle_status"] == "not_applicable_synthetic_demo"
    assert report["model"]["scikit_learn_version"] is None
    assert report["inputs"]["features"] == checked
    assert report["head_outputs"]["lad"]["estimate_type"] == "synthetic_demo_score"
    assert report["disclaimer"] == main.NON_CLINICAL_DISCLAIMER


def test_report_endpoint_downloads_json_and_refuses_identifier_fields():
    if BUNDLE is None:
        pytest.skip("optional model bundle is not installed")

    response = main.report(main.PredictionRequest(schema_version="0.2", features=DEMO))
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith("attachment; filename=")
    assert payload["mode"] == "trained_research"
    assert payload["model"]["model_bundle_sha256"]

    refused = main.report(
        main.PredictionRequest(schema_version="0.2", features={**DEMO, "email": "person@example.invalid"})
    )
    assert refused.status_code == 422
    assert json.loads(refused.body)["status"] == "invalid_input"
    assert "head_outputs" not in refused.body.decode()


def test_model_info_records_bundle_hash_and_scikit_learn_version(monkeypatch):
    import hashlib
    import sklearn

    monkeypatch.setattr(main, "BUNDLE", _trained_model_info_bundle())
    info = main.model_info()

    assert info["model_bundle_sha256"] == hashlib.sha256(main.BUNDLE_PATH.read_bytes()).hexdigest()
    assert info["model_bundle_status"] == "available"
    assert info["scikit_learn_version"] == sklearn.__version__ == "1.6.1"


def test_frontend_report_constants_match_backend():
    import subprocess

    root = Path(__file__).resolve().parents[2]
    output = subprocess.run(
        ["node", "--input-type=module", "-e",
         "import {NON_CLINICAL_DISCLAIMER, REPORT_SCHEMA_VERSION, REPORT_TYPE} from './src/research-report.js';"
         "console.log(JSON.stringify({NON_CLINICAL_DISCLAIMER, REPORT_SCHEMA_VERSION, REPORT_TYPE}));"],
        cwd=root, check=True, capture_output=True, text=True, timeout=15,
    )
    frontend = json.loads(output.stdout)

    assert frontend == {
        "NON_CLINICAL_DISCLAIMER": main.NON_CLINICAL_DISCLAIMER,
        "REPORT_SCHEMA_VERSION": main.REPORT_SCHEMA_VERSION,
        "REPORT_TYPE": main.REPORT_TYPE,
    }
