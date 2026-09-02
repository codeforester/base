from __future__ import annotations

import io
import importlib.util
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from base_dev.engine import main
from base_dev import linux_lab
from base_setup.errors import ArtifactError


def run_engine(args: list[str], extra_env: dict[str, str] | None = None) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with tempfile.TemporaryDirectory() as home_dir:
        env = {
            "HOME": home_dir,
            "BASE_HOME": str(Path(__file__).resolve().parents[4]),
            "BASE_PLATFORM": "",
        }
        if extra_env:
            env.update(extra_env)
        with mock.patch.dict(os.environ, env):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                status = main(args)
    return status, stdout.getvalue(), stderr.getvalue()


@unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
class LinuxLabProfileTests(unittest.TestCase):
    def test_check_multipass_reports_timeout_with_stable_warning(self) -> None:
        with mock.patch.object(linux_lab.shutil, "which", return_value="/opt/bin/multipass"), mock.patch.object(
            linux_lab.subprocess,
            "run",
            side_effect=linux_lab.subprocess.TimeoutExpired(
                ["/opt/bin/multipass", "version"],
                linux_lab.DIAGNOSTIC_TIMEOUT_SECONDS,
            ),
        ) as run:
            check = linux_lab.check_multipass()

        self.assertFalse(check.ok)
        self.assertEqual(check.status, "warn")
        self.assertEqual(check.finding_id, "BASE-D108")
        self.assertIn(f"timed out after {linux_lab.DIAGNOSTIC_TIMEOUT_SECONDS} seconds", check.message)
        self.assertIn("Retry 'multipass version'", check.fix)
        self.assertEqual(run.call_args.args[0], ["/opt/bin/multipass", "version"])
        self.assertEqual(run.call_args.kwargs["timeout"], linux_lab.DIAGNOSTIC_TIMEOUT_SECONDS)

    def test_check_multipass_reports_nonzero_stderr_or_stdout_detail(self) -> None:
        cases = (
            ("daemon unavailable\n", "ignored stdout\n", "daemon unavailable"),
            ("", "client failed\n", "client failed"),
            ("", "", "Multipass version check failed with exit 5."),
        )
        for stderr, stdout, expected in cases:
            with self.subTest(expected=expected), mock.patch.object(
                linux_lab.shutil,
                "which",
                return_value="/opt/bin/multipass",
            ), mock.patch.object(
                linux_lab.subprocess,
                "run",
                return_value=linux_lab.subprocess.CompletedProcess(
                    ["/opt/bin/multipass", "version"],
                    5,
                    stdout=stdout,
                    stderr=stderr,
                ),
            ):
                check = linux_lab.check_multipass()

            self.assertFalse(check.ok)
            self.assertEqual(check.finding_id, "BASE-D108")
            self.assertIn(expected, check.message)
            self.assertEqual(check.fix, "basectl setup --profile linux-lab")

    def test_check_multipass_accepts_version_on_stdout_stderr_or_unknown(self) -> None:
        cases = (
            ("multipass 1.15.1\n", "", "multipass 1.15.1"),
            ("", "multipass 1.15.2\n", "multipass 1.15.2"),
            ("", "", "version unknown"),
        )
        for stdout, stderr, expected in cases:
            with self.subTest(expected=expected), mock.patch.object(
                linux_lab.shutil,
                "which",
                return_value="/opt/bin/multipass",
            ), mock.patch.object(
                linux_lab.subprocess,
                "run",
                return_value=linux_lab.subprocess.CompletedProcess(
                    ["/opt/bin/multipass", "version"],
                    0,
                    stdout=stdout,
                    stderr=stderr,
                ),
            ):
                check = linux_lab.check_multipass()

            self.assertTrue(check.ok)
            self.assertEqual(check.finding_id, "BASE-D108")
            self.assertEqual(check.fix, "")
            self.assertEqual(
                check.message,
                f"Multipass is already installed at '/opt/bin/multipass' ({expected}).",
            )

    def test_summarize_command_output_collapses_whitespace_and_none(self) -> None:
        self.assertEqual(linux_lab.summarize_command_output("  multipass\n  1.15  "), "multipass 1.15")
        self.assertEqual(linux_lab.summarize_command_output(None), "")

    def test_check_profile_linux_lab_reports_missing_multipass(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            status, stdout, stderr = run_engine(
                ["check", "--profile", "linux-lab", "--format", "json"],
                extra_env={"PATH": bin_dir},
            )

        payload = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["profiles"], ["linux-lab"])
        self.assertEqual(
            payload["checks"],
            [
                {
                    "id": "BASE-D108",
                    "status": "error",
                    "name": "multipass",
                    "message": "Multipass 'multipass' was not found.",
                    "fix": "basectl setup --profile linux-lab",
                }
            ],
        )

    def test_setup_profile_linux_lab_dry_run_prints_multipass_install_plan(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            status, _stdout, stderr = run_engine(
                ["setup", "--profile", "linux-lab", "--dry-run"],
                extra_env={"BASE_PLATFORM": "macos", "PATH": bin_dir},
            )

        self.assertEqual(status, 0)
        self.assertIn("Setting up Base 'linux-lab' prerequisites.", stderr)
        self.assertIn("[DRY-RUN] Would run: brew install --cask multipass", stderr)
        self.assertIn("Base 'linux-lab' prerequisite setup dry-run is complete.", stderr)
        self.assertIn(
            "Multipass creates host-managed Ubuntu VMs; Base does not create VM instances during setup.",
            stderr,
        )

    def test_setup_profile_linux_lab_missing_multipass_is_macos_homebrew_only(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            status, _stdout, stderr = run_engine(
                ["setup", "--profile", "linux-lab"],
                extra_env={"BASE_PLATFORM": "linux-debian", "PATH": bin_dir},
            )

        self.assertEqual(status, 1)
        self.assertIn(
            "The 'linux-lab' setup profile installs Multipass via Homebrew cask "
            "and is supported only on macOS hosts.",
            stderr,
        )

    def test_setup_profile_linux_lab_returns_success_when_already_installed(self) -> None:
        installed = linux_lab.DevCheck(
            "multipass",
            True,
            "Multipass is already installed at '/opt/bin/multipass' (1.15.1).",
            "",
            finding_id="BASE-D108",
        )
        with mock.patch.object(linux_lab, "check_multipass", return_value=installed), mock.patch.object(
            linux_lab.process,
            "run_command",
        ) as run_command:
            status, stdout, stderr = run_engine(
                ["setup", "--profile", "linux-lab"],
                extra_env={"BASE_PLATFORM": "macos"},
            )

        self.assertEqual(status, 0)
        self.assertEqual(stdout, "")
        self.assertIn(installed.message, stderr)
        self.assertIn("prerequisite setup is complete", stderr)
        run_command.assert_not_called()

    def test_setup_profile_linux_lab_reports_missing_homebrew(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir, mock.patch.object(
            linux_lab.process,
            "command_exists",
            return_value=False,
        ):
            status, stdout, stderr = run_engine(
                ["setup", "--profile", "linux-lab"],
                extra_env={"BASE_PLATFORM": "macos", "PATH": bin_dir},
            )

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Homebrew is required to install Multipass", stderr)
        self.assertIn("brew install --cask multipass", stderr)

    def test_setup_profile_linux_lab_runs_homebrew_install(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir, mock.patch.object(
            linux_lab.process,
            "command_exists",
            return_value=True,
        ), mock.patch.object(linux_lab.process, "run_command") as run_command:
            status, stdout, stderr = run_engine(
                ["setup", "--profile", "linux-lab"],
                extra_env={"BASE_PLATFORM": "macos", "PATH": bin_dir},
            )

        self.assertEqual(status, 0)
        self.assertEqual(stdout, "")
        self.assertIn("Installing Multipass via Homebrew cask.", stderr)
        self.assertIn("prerequisite setup is complete", stderr)
        self.assertEqual(run_command.call_args.args[1], ["brew", "install", "--cask", "multipass"])

    def test_setup_profile_linux_lab_reports_homebrew_install_failure(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir, mock.patch.object(
            linux_lab.process,
            "command_exists",
            return_value=True,
        ), mock.patch.object(
            linux_lab.process,
            "run_command",
            side_effect=ArtifactError("brew install failed"),
        ):
            status, stdout, stderr = run_engine(
                ["setup", "--profile", "linux-lab"],
                extra_env={"BASE_PLATFORM": "macos", "PATH": bin_dir},
            )

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("brew install failed", stderr)

    def test_doctor_profile_linux_lab_json_uses_stable_finding_id(self) -> None:
        with tempfile.TemporaryDirectory() as bin_dir:
            status, stdout, stderr = run_engine(
                ["doctor", "--profile", "linux-lab", "--format", "json"],
                extra_env={"PATH": bin_dir},
            )

        findings = json.loads(stdout)
        self.assertEqual(status, 1)
        self.assertEqual(stderr, "")
        self.assertEqual(findings[0]["id"], "BASE-D108")
        self.assertEqual(findings[0]["fix"], "basectl setup --profile linux-lab")


if __name__ == "__main__":
    unittest.main()
