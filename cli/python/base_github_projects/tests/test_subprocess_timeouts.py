from __future__ import annotations

import json
import subprocess

import pytest

from base_github_projects import engine
from base_github_projects import project_git
from base_github_projects import project_graphql


def test_infer_repo_from_git_passes_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    completed = subprocess.CompletedProcess(
        ["git", "config", "--get", "remote.origin.url"],
        0,
        stdout="git@github.com:basefoundry/base.git\n",
        stderr="",
    )

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command == ["git", "config", "--get", "remote.origin.url"]
        assert kwargs["timeout"] == project_git.GIT_COMMAND_TIMEOUT_SECONDS
        return completed

    monkeypatch.setattr(project_git.subprocess, "run", fake_run)

    assert engine.infer_repo_from_git() == "basefoundry/base"


def test_infer_repo_from_git_returns_none_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(project_git.subprocess, "run", fake_run)

    assert engine.infer_repo_from_git() is None


def test_run_graphql_passes_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    completed = subprocess.CompletedProcess(
        ["gh", "api", "graphql", "--input", "-"],
        0,
        stdout='{"data": {"viewer": {"login": "codeforester"}}}',
        stderr="",
    )

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command == ["gh", "api", "graphql", "--input", "-"]
        assert kwargs["timeout"] == project_graphql.GITHUB_GRAPHQL_TIMEOUT_SECONDS
        return completed

    monkeypatch.setattr(project_graphql.subprocess, "run", fake_run)

    assert engine.run_graphql("query Viewer { viewer { login } }", {}) == {
        "data": {"viewer": {"login": "codeforester"}}
    }


def test_run_graphql_reports_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(project_graphql.subprocess, "run", fake_run)

    with pytest.raises(engine.ProjectError) as excinfo:
        engine.run_graphql("query Viewer { viewer { login } }", {})

    assert "Timed out running GitHub GraphQL request after" in str(excinfo.value)


def test_run_graphql_reports_process_start_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise OSError("gh is unavailable")

    monkeypatch.setattr(project_graphql.subprocess, "run", fake_run)

    with pytest.raises(engine.ProjectError, match="Could not run GitHub GraphQL request: gh is unavailable"):
        engine.run_graphql("query Viewer { viewer { login } }", {})


@pytest.mark.parametrize(
    ("completed", "error_type", "message"),
    [
        (
            subprocess.CompletedProcess(["gh"], 1, stdout="", stderr="network failed\n"),
            engine.ProjectError,
            "network failed",
        ),
        (
            subprocess.CompletedProcess(
                ["gh"],
                1,
                stdout="",
                stderr="resource not accessible: project scope required\n",
            ),
            engine.ProjectAuthError,
            "project scope required",
        ),
        (
            subprocess.CompletedProcess(["gh"], 0, stdout="not-json", stderr=""),
            engine.ProjectError,
            "returned invalid JSON",
        ),
        (
            subprocess.CompletedProcess(
                ["gh"],
                0,
                stdout=json.dumps({"errors": [{"message": "GraphQL failed"}]}),
                stderr="",
            ),
            engine.ProjectError,
            "GraphQL failed",
        ),
        (
            subprocess.CompletedProcess(
                ["gh"],
                0,
                stdout=json.dumps({"errors": [{"message": "ProjectV2 is not accessible"}]}),
                stderr="",
            ),
            engine.ProjectAuthError,
            "ProjectV2 is not accessible",
        ),
    ],
)
def test_run_graphql_classifies_command_and_response_failures(
    monkeypatch: pytest.MonkeyPatch,
    completed: subprocess.CompletedProcess[str],
    error_type: type[Exception],
    message: str,
) -> None:
    monkeypatch.setattr(project_graphql.subprocess, "run", lambda *args, **kwargs: completed)

    with pytest.raises(error_type, match=message):
        engine.run_graphql("query Viewer { viewer { login } }", {})


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("project scope is required", True),
        ("PROJECT resource not accessible", True),
        ("ProjectV2 is not accessible", True),
        ("repository resource not accessible", False),
        ("project request timed out", False),
    ],
)
def test_is_project_scope_error(message: str, expected: bool) -> None:
    assert engine.is_project_scope_error(message) is expected
