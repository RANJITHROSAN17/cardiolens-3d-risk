import pandas as pd
import pytest

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


def test_demo_rejects_fractional_rwma_bad_sex_and_outcome():
    for overrides in ({"region_rwma": 1.5}, {"sex": "Other"}, {"Cath": "CAD"}):
        with pytest.raises(ValueError):
            _checked_demo_features({**DEMO, **overrides})


def test_research_rejects_fractional_rwma():
    if BUNDLE is None:
        pytest.skip("optional model bundle is not installed")
    with pytest.raises(ValueError):
        _bundle_predict({**DEMO, "region_rwma": 1.5}, BUNDLE)


def test_api_endpoints_and_schema_version():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    assert client.get('/api/health').status_code == 200
    assert client.get('/api/model-info').json()['future_risk_available'] is False
    assert client.get('/api/sample-case').json()['features'] == DEMO
    bad = client.post('/api/predict', json={'schema_version': '99', 'features': DEMO})
    assert bad.status_code == 422
    result = client.post('/api/predict', json={'schema_version': '0.2', 'features': DEMO})
    assert result.status_code == 200
    assert result.json()['future_risk']['status'] == 'unavailable'
    bad = client.post('/api/predict', json={'schema_version': '0.2', 'features': {**DEMO, 'region_rwma': 1.5}})
    assert bad.status_code == 422
