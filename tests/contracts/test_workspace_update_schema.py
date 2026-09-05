from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "docs" / "schemas" / "workspace-update.json"


def test_workspace_update_command_matches_published_schema(tmp_path: Path) -> None:
    home = tmp_path / "home"
    base_home = tmp_path / "base"
    workspace = tmp_path / "workspace"
    manifest_path = tmp_path / "workspace.yaml"
    home.mkdir()
    base_home.mkdir()
    workspace.mkdir()
    for name in ("first", "later"):
        (workspace / name).mkdir()
    manifest_path.write_text(
        "schema_version: 1\n"
        "workspace:\n"
        "  name: update-suite\n"
        "repos:\n"
        "  - name: first\n"
        "  - name: later\n",
        encoding="utf-8",
    )

    environment = os.environ.copy()
    environment.update(
        {
            "BASE_HOME": str(base_home),
            "BASE_PROJECT": "",
            "BASE_PROJECT_MANIFEST": "",
            "HOME": str(home),
            "PYTHONPATH": os.pathsep.join(
                [str(REPO_ROOT / "lib/python"), str(REPO_ROOT / "cli/python"), environment.get("PYTHONPATH", "")]
            ),
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "base_projects",
            "update",
            "--workspace",
            str(workspace),
            "--manifest",
            str(manifest_path),
            "--repos",
            "later,first",
            "--dry-run",
            "--format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(payload, schema)
    assert payload["schema_version"] == 1
    assert payload["selected_repositories"] == ["first", "later"]
