from __future__ import annotations

from pathlib import Path

import base_cli
import pytest

from base_cli_profile import base_cli_profile


pytestmark = pytest.mark.skipif(
    not hasattr(base_cli, "CliProfile"),
    reason="explicit consumer profiles require base-cli with profile support",
)


def test_base_profile_discovers_base_manifests_and_projects(tmp_path: Path) -> None:
    manifest = tmp_path / "base_manifest.yaml"
    manifest.write_text("project:\n  name: demo\n", encoding="utf-8")

    project = base_cli_profile().discover_project(tmp_path)

    assert project is not None
    assert project.root == tmp_path
    assert project.manifest == manifest
    assert project.name == "demo"


def test_base_profile_owns_base_runtime_and_history_policies(tmp_path: Path, monkeypatch) -> None:
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("BASE_CACHE_DIR", str(cache_root))
    monkeypatch.delenv("BASE_CLI_DISPLAY_COMMAND", raising=False)

    profile = base_cli_profile()
    binding = profile.resolve_runtime("demo", None)

    assert binding.cache_root == cache_root.resolve()
    assert binding.layout.owner_root == cache_root.resolve() / "base"
    assert profile.history_writer is not None
    assert profile.display_command() is None
    assert profile.history_display_command("base_setup", ["--action", "check"]) == "check"
