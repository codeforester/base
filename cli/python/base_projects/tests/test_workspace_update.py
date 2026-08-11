from __future__ import annotations

import io
import os
import re
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from base_projects import engine


def write_workspace_manifest(path: Path) -> None:
    path.write_text(
        """schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: base
  - name: first
  - name: failing
  - name: unchanged
  - name: optional-missing
    required: false
  - name: required-missing
  - name: later
""",
        encoding="utf-8",
    )


class WorkspaceUpdateTests(unittest.TestCase):
    def test_workspace_update_dry_run_preserves_order_and_includes_active_base(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            base_home.mkdir()
            for name in ("first", "failing", "unchanged", "later"):
                (root / name).mkdir()
            write_workspace_manifest(manifest_path)

            status, stdout, stderr = invoke_engine(
                [
                    "update",
                    "--workspace",
                    str(root),
                    "--manifest",
                    str(manifest_path),
                    "--dry-run",
                ],
                base_home,
                home,
            )

            self.assertEqual(status, 1)
            self.assertEqual(stderr, "")
            self.assertIn(f"Workspace update: {root.resolve()} (7 manifest repos)", stdout)
            self.assertIn("REPOSITORY", stdout)
            assert_workspace_result(self, stdout, "base", "PULL", "planned")
            assert_workspace_result(self, stdout, "first", "PULL", "planned")
            assert_workspace_result(self, stdout, "optional-missing", "SKIP", "skipped")
            assert_workspace_result(self, stdout, "later", "PULL", "planned")
            self.assertNotIn("active Base control plane is managed from BASE_HOME", stdout)
            self.assertIn("Workspace update plan complete: planned=5 skipped=2 failed=1.", stdout)
            self.assertIn("[DRY-RUN] No repositories were modified.", stdout)
            self.assertLess(stdout.index("\nbase "), stdout.index("\nfirst "))
            self.assertLess(stdout.index("\nfirst "), stdout.index("\nlater "))

    def test_workspace_update_pulls_serially_and_aggregates_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            workspace = root / "workspace"
            base_home = workspace / "base"
            manifest_path = root / "workspace.yaml"
            home.mkdir()
            workspace.mkdir()
            base_home.mkdir()
            for name in ("first", "failing", "unchanged", "later"):
                (workspace / name).mkdir()
            manifest_path.write_text(
                """schema_version: 1
workspace:
  name: demo-suite
repos:
  - name: base
  - name: first
  - name: failing
  - name: unchanged
  - name: optional-missing
    required: false
  - name: later
""",
                encoding="utf-8",
            )

            results = [
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    0,
                    stdout="Already up to date.\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    0,
                    stdout="Updating abc..def\nFast-forward\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    1,
                    stdout="",
                    stderr="fatal: Not possible to fast-forward, aborting.\n",
                ),
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    0,
                    stdout="Already up to date.\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    ["git", "pull", "--ff-only"],
                    0,
                    stdout="Updating ghi..jkl\nFast-forward\n",
                    stderr="",
                ),
            ]
            with mock.patch("base_projects.workspace_update.subprocess.run", side_effect=results) as run:
                status, stdout, stderr = invoke_engine(
                    [
                        "update",
                        "--workspace",
                        str(workspace),
                        "--manifest",
                        str(manifest_path),
                    ],
                    base_home,
                    home,
                )

            self.assertEqual(status, 1)
            self.assertEqual(stderr, "")
            assert_workspace_result(self, stdout, "base", "PULL", "unchanged")
            assert_workspace_result(self, stdout, "first", "PULL", "updated")
            assert_workspace_result(self, stdout, "failing", "PULL", "failed (exit 1)")
            self.assertIn("fatal: Not possible to fast-forward, aborting.", stdout)
            assert_workspace_result(self, stdout, "later", "PULL", "updated")
            self.assertNotIn("Already up to date.", stdout)
            self.assertIn("Workspace update completed: updated=2 unchanged=2 skipped=1 failed=1.", stdout)
            self.assertEqual(
                [call.kwargs["cwd"] for call in run.call_args_list],
                [
                    workspace.resolve() / "base",
                    workspace.resolve() / "first",
                    workspace.resolve() / "failing",
                    workspace.resolve() / "unchanged",
                    workspace.resolve() / "later",
                ],
            )
            for call in run.call_args_list:
                self.assertEqual(call.args[0], ["git", "pull", "--ff-only"])
                self.assertEqual(call.kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
                self.assertEqual(call.kwargs["env"]["LC_ALL"], "C")

    def test_workspace_update_requires_a_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            home = root / "home"
            base_home = root / "base"
            workspace = root / "workspace"
            home.mkdir()
            base_home.mkdir()
            workspace.mkdir()

            status, stdout, stderr = invoke_engine(
                ["update", "--workspace", str(workspace), "--dry-run"],
                base_home,
                home,
            )

            self.assertEqual(status, 1)
            self.assertEqual(stdout, "")
            self.assertIn("requires a configured or explicit workspace manifest", stderr)


def assert_workspace_result(
    test_case: unittest.TestCase,
    output: str,
    repository: str,
    action: str,
    result: str,
) -> None:
    pattern = rf"^{re.escape(repository)}\s+{re.escape(action)}\s+{re.escape(result)}$"
    test_case.assertRegex(output, re.compile(pattern, re.MULTILINE))


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
        "BASE_PROJECT_ROOT": "inherited-root",
        "BASE_PROJECT_MANIFEST": "",
        "BASE_PROJECT_VENV_DIR": "inherited-venv",
    }
    with mock.patch.dict(os.environ, env):
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = engine.main(args)
    return status, stdout.getvalue(), stderr.getvalue()
