from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from base_cli.testing import invoke
from base_trust import engine


@pytest.mark.parametrize("output_format", ["yaml", "csv", "tsv"])
def test_project_status_supports_documented_output_formats(
    tmp_path: Path,
    manifest_factory,
    output_format: str,
) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "work"
    manifest_factory.write(workspace / "demo")

    result = invoke(
        engine.app,
        ["status", "demo", "--workspace", str(workspace), "--format", output_format],
        home=home,
        env={"BASE_HOME": str(workspace / "base")},
    )

    assert result.exit_code == 0, result.output
    if output_format == "yaml":
        payload = yaml.safe_load(result.stdout)
        assert payload["project"]["name"] == "demo"
        assert payload["status"] == "blocked"
    else:
        delimiter = "," if output_format == "csv" else "\t"
        assert result.stdout.splitlines() == [delimiter.join(("demo", "blocked", "not_allowed"))]


def test_workspace_status_supports_yaml_and_empty_terminal_output(
    tmp_path: Path,
    manifest_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "work"
    manifest_factory.write(workspace / "demo")
    yaml_result = invoke(
        engine.app,
        ["status", "--workspace", str(workspace), "--format", "yaml"],
        home=home,
        env={"BASE_HOME": str(workspace / "base")},
    )

    empty_workspace = tmp_path / "empty"
    empty_workspace.mkdir()
    monkeypatch.setattr(engine.base_cli, "is_terminal", lambda: True)
    text_result = invoke(
        engine.app,
        ["status", "--workspace", str(empty_workspace)],
        home=home,
        env={"BASE_HOME": str(tmp_path / "base")},
    )

    assert yaml.safe_load(yaml_result.stdout)["projects"][0]["project"]["name"] == "demo"
    assert text_result.exit_code == 0, text_result.output
    assert text_result.stdout == "No discovered projects require manifest command trust.\n"


def test_invalid_status_format_is_a_usage_error(tmp_path: Path) -> None:
    result = invoke(
        engine.app,
        ["status", "--format", "toml"],
        home=tmp_path / "home",
        env={"BASE_HOME": str(tmp_path / "base")},
    )

    assert result.exit_code == 2
    assert "Unsupported output format 'toml'" in result.stderr


@pytest.mark.parametrize("command", ["status", "require", "allow", "revoke"])
def test_project_commands_report_resolution_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    monkeypatch.setattr(
        engine,
        "resolve_trust_identity" if command != "require" else "resolve_trust_identity_for_require",
        lambda *args, **kwargs: (_ for _ in ()).throw(engine.TrustError("identity failed")),
    )

    result = invoke(
        engine.app,
        [command, "demo"],
        home=tmp_path / "home",
        env={"BASE_HOME": str(tmp_path / "base")},
    )

    assert result.exit_code == 1
    assert "identity failed" in result.stderr


def test_workspace_status_reports_discovery_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        engine,
        "workspace_status_projects",
        lambda *args: (_ for _ in ()).throw(engine.TrustError("workspace failed")),
    )

    result = invoke(
        engine.app,
        ["status"],
        home=tmp_path / "home",
        env={"BASE_HOME": str(tmp_path / "base")},
    )

    assert result.exit_code == 1
    assert "workspace failed" in result.stderr


def test_require_rejects_manifest_declaring_a_different_project(
    tmp_path: Path,
    manifest_factory,
) -> None:
    manifest_path = manifest_factory.write(tmp_path / "work" / "actual", name="actual")

    result = invoke(
        engine.app,
        ["require", "expected", "--manifest", str(manifest_path)],
        home=tmp_path / "home",
        env={"BASE_HOME": str(tmp_path / "base")},
    )

    assert result.exit_code == 1
    assert "declares project 'actual', not 'expected'" in result.stderr


def test_active_project_name_mismatch_is_reported(
    tmp_path: Path,
    manifest_factory,
) -> None:
    manifest_path = manifest_factory.write(tmp_path / "active", name="actual")

    result = invoke(
        engine.app,
        ["status"],
        home=tmp_path / "home",
        env={
            "BASE_HOME": str(tmp_path / "base"),
            "BASE_TRUST_ACTIVE_PROJECT": "expected",
            "BASE_TRUST_ACTIVE_PROJECT_MANIFEST": str(manifest_path),
        },
    )

    assert result.exit_code == 1
    assert "Active project is 'expected' but its manifest declares project 'actual'" in result.stderr


def test_revoke_without_record_reports_noop(
    tmp_path: Path,
    manifest_factory,
) -> None:
    workspace = tmp_path / "work"
    manifest_factory.write(workspace / "demo")

    result = invoke(
        engine.app,
        ["revoke", "demo", "--workspace", str(workspace)],
        home=tmp_path / "home",
        env={"BASE_HOME": str(tmp_path / "base")},
    )

    assert result.exit_code == 0, result.output
    assert result.stdout == "No manifest command trust record found for project 'demo'.\n"


def test_status_payload_ignores_malformed_changed_record(tmp_path: Path, manifest_factory) -> None:
    manifest_path = manifest_factory.write(tmp_path / "demo")
    identity = engine.compute_trust_identity_for_manifest(manifest_path)
    status = engine.TrustStatus(
        status="blocked",
        reason="manifest_changed",
        identity=identity,
        record=None,
        changed_record={"project": {"manifest_sha256": 42}},
    )

    payload = engine.status_payload(status)

    assert "recorded_manifest_sha256" not in payload
    assert json.loads(json.dumps(payload))["reason"] == "manifest_changed"
