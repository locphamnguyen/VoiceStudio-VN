"""Workflows that hold a write token on untrusted events must never run pull-request code.

Kept from the upstream CLA workflow tests when VoiceStudio-VN dropped the CLA gate:
the rule guards every workflow, not just the CLA one.
"""
from __future__ import annotations

from pathlib import Path

import yaml

_WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
# Triggers that run with a write token and repository secrets, even on fork PRs.
_PRIVILEGED_TRIGGERS = {"pull_request_target", "issue_comment", "workflow_run"}


def _load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    # PyYAML reads the bare `on:` key as boolean True.
    data["on"] = data.pop(True, data.get("on")) or {}
    return data


def _triggers(workflow: dict) -> set[str]:
    on = workflow["on"]
    return set(on) if isinstance(on, (dict, list)) else {on}


def test_privileged_workflows_never_run_pull_request_code():
    for path in sorted(_WORKFLOWS.glob("*.y*ml")):
        workflow = _load(path)
        if not _triggers(workflow) & _PRIVILEGED_TRIGGERS:
            continue
        text = path.read_text(encoding="utf-8")
        assert "pull_request.head" not in text and "head_sha" not in text, f"{path.name} references PR head code"
        for name, job in (workflow.get("jobs") or {}).items():
            where = f"{path.name}:{name}"
            assert "uses" not in job, f"{where} calls a reusable workflow"
            for step in job.get("steps", []):
                uses = step.get("uses", "")
                assert not uses.startswith("actions/download-artifact@"), f"{where} downloads artifacts"
                if uses.startswith("actions/checkout@"):
                    options = step.get("with") or {}
                    assert not {"ref", "repository"} & set(options), f"{where} checks out a non-base ref"
                    assert options.get("persist-credentials") is False, f"{where} keeps credentials"
                assert "${{ github.event" not in str(step.get("run", "")), f"{where} interpolates event data"


def test_no_cla_gate():
    # VoiceStudio-VN không dùng CLA của repo gốc (chủ repo chốt 2026-10-08).
    assert not (_WORKFLOWS / "cla.yml").exists()
