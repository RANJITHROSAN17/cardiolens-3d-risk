import json
from pathlib import Path

import pandas as pd
import pytest

import app.main as main
from app.main import BUNDLE, _bundle_predict, _checked_demo_features, _demo_predict
from ml.train import find_targets, parse_binary_label, select_features


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


def test_frontend_backend_schema_parity():
    """Read the actual ESM export; fail, rather than skip, if either schema drifts."""
    import json
    from pathlib import Path
    import subprocess
    from app.main import (
        BOOLEAN_FEATURES, FORBIDDEN_FEATURES, INTEGER_FEATURES,
        NUMERIC_RANGES, SEX_CATEGORIES, VHD_CATEGORIES,
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
    }
    assert {key: sorted(value) if isinstance(value, list) else value
            for key, value in frontend.items()} == expected


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
