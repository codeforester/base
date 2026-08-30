import os
from pathlib import Path
import subprocess

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_SCRIPT = REPO_ROOT / "tests" / "scan-secrets.sh"
TESTS_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "tests.yml"
GITLEAKS_VERSION = "8.30.1"
GITLEAKS_LINUX_X64_SHA256 = (
    "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"
)


def _security_steps() -> list[dict]:
    workflow = yaml.safe_load(TESTS_WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["security"]["steps"]
    assert isinstance(steps, list)
    return [step for step in steps if isinstance(step, dict)]


def _write_gitleaks_mock(tmp_path: Path, *, version: str = GITLEAKS_VERSION) -> Path:
    mock = tmp_path / "gitleaks"
    mock.write_text(
        f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >> "${{GITLEAKS_MOCK_LOG:?}}"
if [[ "${{1:-}}" == "version" ]]; then
    printf '%s\\n' "{version}"
fi
""",
        encoding="utf-8",
    )
    mock.chmod(0o755)
    return mock


def _run_scan_script(tmp_path: Path, *args: str, version: str = GITLEAKS_VERSION):
    mock = _write_gitleaks_mock(tmp_path, version=version)
    log_path = tmp_path / "gitleaks.log"
    env = os.environ.copy()
    env.update({"GITLEAKS_BIN": str(mock), "GITLEAKS_MOCK_LOG": str(log_path)})
    result = subprocess.run(
        [str(SCAN_SCRIPT), *args],
        check=False,
        capture_output=True,
        env=env,
        text=True,
        timeout=10,
    )
    return result, log_path


def test_security_workflow_installs_checksum_pinned_gitleaks() -> None:
    steps = _security_steps()
    install_step = next(step for step in steps if step.get("name") == "Install pinned Gitleaks")
    scan_step = next(
        step for step in steps if step.get("name") == "Scan repository history for secrets"
    )

    assert install_step["env"] == {
        "GITLEAKS_VERSION": GITLEAKS_VERSION,
        "GITLEAKS_LINUX_X64_SHA256": GITLEAKS_LINUX_X64_SHA256,
    }
    assert "sha256sum --check -" in install_step["run"]
    assert "gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" in install_step["run"]
    assert scan_step["env"]["GITLEAKS_BIN"] == "${{ runner.temp }}/gitleaks"
    assert "./tests/scan-secrets.sh" in scan_step["run"]


def test_scan_script_redacts_the_default_history_scan(tmp_path: Path) -> None:
    result, log_path = _run_scan_script(tmp_path)

    assert result.returncode == 0, result.stderr
    assert log_path.read_text(encoding="utf-8").splitlines() == [
        "version",
        "git --redact=100 --no-banner --no-color --verbose .",
    ]


def test_scan_script_supports_controlled_directory_scans(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixture"
    fixture_dir.mkdir()
    result, log_path = _run_scan_script(tmp_path, "--dir", str(fixture_dir))

    assert result.returncode == 0, result.stderr
    assert log_path.read_text(encoding="utf-8").splitlines() == [
        "version",
        f"dir --redact=100 --no-banner --no-color --verbose {fixture_dir}",
    ]


def test_scan_script_rejects_an_unreviewed_gitleaks_version(tmp_path: Path) -> None:
    result, log_path = _run_scan_script(tmp_path, version="8.31.0")

    assert result.returncode == 1
    assert f"gitleaks {GITLEAKS_VERSION} is required" in result.stderr
    assert log_path.read_text(encoding="utf-8") == "version\n"


def test_security_policy_is_rotate_first_and_uses_narrow_exceptions() -> None:
    policy = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")

    assert policy.index("Revoke or rotate the credential first") < policy.index(
        "Rewrite published history"
    )
    assert "reviewed fingerprint" in policy
    assert "do not disable a rule or exclude a broad test directory" in policy
