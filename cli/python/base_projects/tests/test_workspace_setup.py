from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from base_projects import engine


def write_manifest(project_root: Path, name: str, *, python: bool = False) -> None:
    project_root.mkdir(parents=True)
    python_section = "python:\n  manager: uv\n" if python else ""
    (project_root / "base_manifest.yaml").write_text(
        f"schema_version: 1\nproject:\n  name: {name}\n{python_section}",
        encoding="utf-8",
    )


def write_workspace_manifest(path: Path) -> None:
    path.write_text(
        """schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: base
  - name: missing
    required: false
  - name: no-manifest
  - name: invalid
  - name: shell-only
  - name: python-project
""",
        encoding="utf-8",
    )


class WorkspaceSetupTests(unittest.TestCase):
    def test_workspace_setup_dry_run_preserves_manifest_order_and_classifies_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            write_manifest(workspace / "base", "base")
            (workspace / "no-manifest").mkdir()
            (workspace / "invalid").mkdir()
            (workspace / "invalid" / "base_manifest.yaml").write_text(
                "schema_version: 1\nproject: invalid\n",
                encoding="utf-8",
            )
            write_manifest(workspace / "shell-only", "shell-only")
            write_manifest(workspace / "python-project", "python-project", python=True)
            write_workspace_manifest(manifest_path)

            status, stdout, stderr = invoke_engine(
                [
                    "setup",
                    "--workspace",
                    str(workspace),
                    "--manifest",
                    str(manifest_path),
                    "--dry-run",
                ],
                base_home,
                home,
            )

            self.assertEqual(status, 0)
            self.assertEqual(stderr, "")
            self.assertIn(f"Workspace setup plan: {workspace.resolve()} (6 manifest repos)", stdout)
            self.assertIn(f"Workspace manifest: {manifest_path.resolve()} (demo-suite)", stdout)
            self.assertIn("SKIP repository 'base'", stdout)
            self.assertIn("active Base control plane is managed from BASE_HOME", stdout)
            self.assertIn("SKIP repository 'missing'", stdout)
            self.assertIn("repository is missing", stdout)
            self.assertIn("SKIP repository 'no-manifest'", stdout)
            self.assertIn("does not contain base_manifest.yaml", stdout)
            self.assertIn("SKIP repository 'invalid'", stdout)
            self.assertIn("base_manifest.yaml is invalid", stdout)
            self.assertIn("SETUP repository 'shell-only'", stdout)
            self.assertIn("SETUP repository 'python-project'", stdout)
            self.assertIn("Workspace setup plan complete: setup=2 skipped=4.", stdout)
            self.assertIn("[DRY-RUN] No repositories were modified.", stdout)
            self.assertLess(stdout.index("repository 'base'"), stdout.index("repository 'missing'"))
            self.assertLess(stdout.index("repository 'missing'"), stdout.index("repository 'no-manifest'"))
            self.assertLess(stdout.index("repository 'no-manifest'"), stdout.index("repository 'invalid'"))
            self.assertLess(stdout.index("repository 'invalid'"), stdout.index("repository 'shell-only'"))
            self.assertLess(stdout.index("repository 'shell-only'"), stdout.index("repository 'python-project'"))
            self.assertFalse((workspace / "shell-only" / ".venv").exists())
            self.assertFalse((workspace / "python-project" / ".venv").exists())

    def test_workspace_setup_requires_a_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()

            status, stdout, stderr = invoke_engine(
                ["setup", "--workspace", str(workspace), "--dry-run"],
                base_home,
                home,
            )

            self.assertEqual(status, 1)
            self.assertEqual(stdout, "")
            self.assertIn("requires a configured or explicit workspace manifest", stderr)

    def test_workspace_setup_does_not_mutate_without_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()
            write_manifest(workspace / "project", "project")
            manifest_path.write_text(
                """schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: project
""",
                encoding="utf-8",
            )

            status, stdout, stderr = invoke_engine(
                [
                    "setup",
                    "--workspace",
                    str(workspace),
                    "--manifest",
                    str(manifest_path),
                ],
                base_home,
                home,
            )

            self.assertEqual(status, 1)
            self.assertIn("SETUP repository 'project'", stdout)
            self.assertIn("execution is not available yet", stderr)
            self.assertFalse((workspace / "project" / ".venv").exists())


def invoke_engine(
    args: list[str],
    base_home: Path,
    home: Path,
) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    env = {
        "HOME": str(home),
        "BASE_HOME": str(base_home),
        "BASE_PROJECT": "",
        "BASE_PROJECT_MANIFEST": "",
    }
    with mock.patch.dict(os.environ, env):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()
