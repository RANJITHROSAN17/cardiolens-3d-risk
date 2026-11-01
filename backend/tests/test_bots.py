"""Unit tests for CardioLens 3D roadmap, labeler, PR context, and workflow validators."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / ".github" / "scripts"


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def roadmap() -> dict:
    return json.loads((ROOT / ".github" / "roadmap.json").read_text(encoding="utf-8"))


def test_manifest_ids_labels_and_criteria_are_complete() -> None:
    bot = load("sync_roadmap_issues")
    data = roadmap()
    ids = [item["id"] for item in data["items"]]
    assert len(ids) == len(set(ids))
    known = {label["name"] for label in data["labels"]}
    for item in data["items"]:
        assert set(item["labels"]).issubset(known), f"{item['id']} uses undefined label"
        if item.get("status") != "shipped":
            assert item.get("acceptance_criteria"), f"{item['id']} missing acceptance criteria"
            assert item.get("files"), f"{item['id']} missing files"
        assert f"<!-- roadmap-id: {item['id']} -->" in bot.render_issue_body(item, data)


def test_plan_doc_and_referenced_files_have_no_drift() -> None:
    status = load("roadmap_status")
    data = roadmap()
    assert (ROOT / data["plan_doc"]).is_file()
    assert status.file_drift(data, ROOT) == []
    body = status.render_status(data, [], root=ROOT, version="0.2.0", tag=None)
    assert body.startswith(status.STATUS_MARKER)


def test_curator_never_reopens_closed_roadmap_items() -> None:
    bot = load("sync_roadmap_issues")
    data = roadmap()
    closed = [{"state": "closed", "body": "<!-- roadmap-id: CL-001 -->\nsolved"}]
    opened = bot.select_items_to_open(data, closed)
    opened_ids = [item["id"] for item in opened]
    assert "CL-001" not in opened_ids
    assert len(opened_ids) == data["max_open_roadmap_issues"]


def test_issue_classifier_routes_cardiolens_domains() -> None:
    labeler = load("auto_label_issue")
    labels = labeler.classify(
        "Three.js WebGL crash when selecting RCA vessel",
        "HeartScene throws exception when WebGL context is unavailable",
    )
    assert "area/visualization" in labels
    assert "type/bug" in labels


def test_pr_context_matches_heartscene_to_roadmap() -> None:
    ctx = load("pr_context")
    out = ctx.render_context(roadmap(), ["src/HeartScene.jsx"], "Closes #10")
    assert "CL-003" in out or "CL-007" in out
    assert "#10" in out


def test_every_workflow_is_valid_and_non_placeholder() -> None:
    validator = load("validate_workflows")
    problems: list[str] = []
    for path in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        problems.extend(validator.validate_workflow(path))
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        assert doc.get("jobs"), f"{path.name} defines no jobs"
    assert not problems, "\n".join(problems)
