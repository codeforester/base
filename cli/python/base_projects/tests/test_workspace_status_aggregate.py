"""Aggregate status field on workspace status JSON (#1993)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from base_projects.workspace_report_json import workspace_aggregate_status
from base_projects.workspace_report_json import workspace_status_to_json


def _status(name: str, status: str) -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        status=status,
        root=Path(f"/tmp/{name}"),
        manifest_path=None,
        venv="ok",
        manifest="ok",
        last_check=None,
        issues=(),
        python_runtime=None,
        repository=None,
        required=False,
        repo="ok",
    )


def test_workspace_aggregate_status_all_ok():
    assert workspace_aggregate_status((_status("a", "ok"), _status("b", "ok"))) == "ok"


def test_workspace_aggregate_status_attention():
    assert workspace_aggregate_status((_status("a", "ok"), _status("b", "warn"))) == "attention"


def test_workspace_aggregate_status_empty():
    assert workspace_aggregate_status(()) == "ok"


def test_workspace_status_to_json_includes_aggregate_ok(tmp_path: Path):
    payload = workspace_status_to_json(tmp_path, (_status("a", "ok"), _status("b", "ok")))
    assert payload["status"] == "ok"
    assert payload["project_count"] == 2
    assert [p["status"] for p in payload["projects"]] == ["ok", "ok"]


def test_workspace_status_to_json_includes_aggregate_attention(tmp_path: Path):
    payload = workspace_status_to_json(tmp_path, (_status("a", "ok"), _status("b", "error")))
    assert payload["status"] == "attention"
    assert payload["projects"][1]["status"] == "error"
