#!/usr/bin/env python3
"""Auto-label newly opened human issues by CardioLens 3D research domain."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

AREA_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("area/visualization", re.compile(r"\b(3d|three\.js|webgl|heartscene|vessel|camera|orbit|color|mesh|tube)\b", re.I)),
    ("area/model", re.compile(r"\b(logistic|calibration|brier|roc|auc|scikit|joblib|log-odds|uncertainty|stenosis|model-card)\b", re.I)),
    ("area/api", re.compile(r"\b(fastapi|uvicorn|endpoint|json export|pydantic|schema_version|/api/)\b", re.I)),
    ("area/safety", re.compile(r"\b(phi|disclaimer|clinical|identifier|validation\.js|out-of-range|leakage|cath)\b", re.I)),
    ("area/docs", re.compile(r"\b(readme|docs/|documentation|attribution|blueprint)\b", re.I)),
)


def classify(title: str, body: str) -> list[str]:
    text = f"{title or ''}\n{body or ''}"
    labels: list[str] = []
    for name, pattern in AREA_PATTERNS:
        if pattern.search(text):
            labels.append(name)
    if re.search(r"\b(bug|crash|regression|error|broken|fails|exception)\b", text, re.I):
        labels.append("type/bug")
    elif re.search(r"\b(calibrat|explainab|uncertainty|log-odds|confidence)\b", text, re.I):
        labels.append("type/explainability")
    elif re.search(r"\b(feat|feature|enhancement|proposal|support|export)\b", text, re.I):
        labels.append("type/feature")
    return labels


class GitHubClient:
    def __init__(self, repo: str, token: str) -> None:
        self.base_url = f"https://api.github.com/repos/{repo}"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cardiolens-issue-labeler",
        }

    def request(self, method: str, path: str, payload: object = None) -> object:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=self.headers, method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None

    def apply_labels(self, number: int, labels: list[str]) -> list[str]:
        issue = self.request("GET", f"/issues/{number}") or {}
        existing = {
            entry["name"]
            for entry in (issue.get("labels", []) if isinstance(issue, dict) else [])
            if isinstance(entry, dict)
        }
        to_add = [lbl for lbl in labels if lbl not in existing]
        if to_add:
            self.request("POST", f"/issues/{number}/labels", {"labels": to_add})
        return to_add


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Label a new CardioLens issue from its text.")
    parser.add_argument("--event", type=Path, default=None)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    event_path = args.event or os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).is_file():
        print("error: no event JSON available", file=sys.stderr)
        return 2

    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    issue = event.get("issue") or {}
    if not issue.get("number") or "pull_request" in issue:
        return 0

    body = issue.get("body") or ""
    if "<!-- roadmap-id:" in body or "<!-- roadmap-status -->" in body:
        return 0

    labels = classify(issue.get("title") or "", body)
    if not labels:
        print("[labeler] no confident match; leaving unlabelled")
        return 0
    if args.dry_run:
        print(f"[dry-run] #{issue['number']} -> {', '.join(labels)}")
        return 0

    token = os.environ.get("GITHUB_TOKEN", "")
    if not args.repo or not token:
        print("error: GITHUB_REPOSITORY and GITHUB_TOKEN must be set", file=sys.stderr)
        return 2
    try:
        added = GitHubClient(args.repo, token).apply_labels(int(issue["number"]), labels)
    except urllib.error.HTTPError as exc:
        print(f"GitHub API error ({exc.code}): {exc.read().decode('utf-8', 'replace')}")
        return 1
    print(f"[labeler] #{issue['number']} added: {', '.join(added) or 'nothing new'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
