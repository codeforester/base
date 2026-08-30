import ast
import inspect
from pathlib import Path

import yaml

from tests.github_workflow_test_support import (
    project_intake_run_command,
    run_project_intake_script,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"


def load_workflow(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{path} did not parse as a YAML mapping"
    return payload


def test_project_intake_script_runner_uses_subprocess_timeout() -> None:
    tree = ast.parse(inspect.getsource(run_project_intake_script))
    subprocess_run_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "run"
    ]

    assert len(subprocess_run_calls) == 1
    assert any(keyword.arg == "timeout" for keyword in subprocess_run_calls[0].keywords)


def test_project_intake_requires_base_project_token() -> None:
    workflow = load_workflow(WORKFLOW_DIR / "project-intake.yml")
    sync_job = workflow["jobs"]["sync"]
    run_command = project_intake_run_command()

    assert sync_job["env"]["GH_TOKEN"] == "${{ secrets.BASE_PROJECT_TOKEN }}"
    assert "github.token" not in run_command
    assert "BASE_PROJECT_TOKEN secret is required for Project Intake." in run_command
    assert "gh auth token | gh secret set BASE_PROJECT_TOKEN --repo $GITHUB_REPOSITORY" in (
        run_command
    )


def test_project_intake_template_matches_repository_workflow() -> None:
    assert (REPO_ROOT / "templates" / "project-intake.yml").read_text(encoding="utf-8") == (
        WORKFLOW_DIR / "project-intake.yml"
    ).read_text(encoding="utf-8")


def test_project_intake_classifies_rate_limits_and_auth_failures() -> None:
    run_command = project_intake_run_command()

    assert "project_intake_gh()" in run_command
    assert "project_intake_is_retryable_api_failure()" in run_command
    assert "project_intake_retry_delay_seconds()" in run_command
    assert "Retry-After" in run_command
    assert "x-ratelimit-reset" in run_command
    assert "retrying once" in run_command
    assert 'sleep "$retry_delay"' in run_command
    assert "Bad credentials" in run_command
    assert "Rotate BASE_PROJECT_TOKEN and rerun this workflow_dispatch" in run_command
    assert 'project_intake_gh "view issue" gh api' in run_command
    assert '"list Projects" gh project list' in run_command
    assert '"add Project item" gh project item-add' in run_command
    assert '"set Project field $field_name" gh project item-edit' in run_command
    assert "project_intake_is_project_transport_failure()" in run_command
    assert "unknown owner type" in run_command
    assert "Falling back to the REST Projects API." in run_command
    assert 'project_intake_gh "update REST Project fields" gh api --method PATCH' in run_command


def test_project_intake_retries_rate_limited_operations_once(tmp_path: Path) -> None:
    result = run_project_intake_script(tmp_path, PROJECT_INTAKE_RATE_LIMIT_ONCE="1")

    assert result.returncode == 0, result.stderr
    assert "GitHub API pressure during Project Intake: view issue" in result.stderr
    assert "retrying once" in result.stderr
    assert (tmp_path / "sleep.log").read_text(encoding="utf-8") == "7\n"
    assert (tmp_path / "issue-view-count").read_text(encoding="utf-8") == "2\n"
    assert "Synced issue #1311 into Project base via GraphQL." in result.stdout


def test_project_intake_keeps_success_stderr_out_of_json_stdout(tmp_path: Path) -> None:
    result = run_project_intake_script(tmp_path, PROJECT_INTAKE_WARN_ON_SUCCESS="1")

    assert result.returncode == 0, result.stderr
    assert "warning: gh emitted a non-fatal notice" in result.stderr
    assert "warning: gh emitted a non-fatal notice" not in result.stdout
    assert "Synced issue #1311 into Project base via GraphQL." in result.stdout


def test_project_intake_auth_failures_do_not_retry(tmp_path: Path) -> None:
    result = run_project_intake_script(tmp_path, PROJECT_INTAKE_AUTH_FAIL="1")

    assert result.returncode != 0
    assert "GitHub authentication failed during Project Intake: view issue" in result.stderr
    assert "Rotate BASE_PROJECT_TOKEN and rerun this workflow_dispatch" in result.stderr
    assert "Bad credentials" in result.stderr
    assert "retrying once" not in result.stderr
    assert not (tmp_path / "sleep.log").exists()
    assert (tmp_path / "issue-view-count").read_text(encoding="utf-8") == "1\n"


def test_project_intake_falls_back_to_rest_for_graphql_quota_exhaustion(
    tmp_path: Path,
) -> None:
    result = run_project_intake_script(tmp_path, PROJECT_INTAKE_GRAPHQL_FAILURE="quota")

    assert result.returncode == 0, result.stderr
    assert "GraphQL Project transport failed during Project Intake: list Project items" in (
        result.stderr
    )
    assert "Falling back to the REST Projects API." in result.stderr
    assert "Synced issue #1311 into Project base via REST fallback." in result.stdout
    assert not (tmp_path / "sleep.log").exists()
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    assert "api orgs/basefoundry/projectsV2?per_page=100" in gh_log
    assert "api --method PATCH orgs/basefoundry/projectsV2/1/items/101 --input -" in gh_log


def test_project_intake_falls_back_to_user_rest_for_unknown_owner(
    tmp_path: Path,
) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_GRAPHQL_FAILURE="unknown-owner",
        PROJECT_INTAKE_OWNER_TYPE="User",
    )

    assert result.returncode == 0, result.stderr
    assert "unknown owner type" in result.stderr
    assert "Synced issue #1311 into Project base via REST fallback." in result.stdout
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    assert "api users/basefoundry/projectsV2?per_page=100" in gh_log
    assert "api --method PATCH users/basefoundry/projectsV2/1/items/101 --input -" in gh_log


def test_project_intake_rest_fallback_preserves_existing_nonempty_fields(
    tmp_path: Path,
) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_GRAPHQL_FAILURE="quota",
        PROJECT_INTAKE_EXISTING_PRIORITY="P1",
        PROJECT_INTAKE_EXISTING_AREA="Security",
    )

    assert result.returncode == 0, result.stderr
    payload = (tmp_path / "rest-patches.log").read_text(encoding="utf-8")
    updates = {entry["id"]: entry["value"] for entry in yaml.safe_load(payload)["fields"]}
    assert updates == {
        10: "O_backlog",
        12: "O_s",
        14: "O_adoption",
    }
    assert (tmp_path / "priority").exists() is False
    assert (tmp_path / "area").exists() is False


def test_project_intake_primary_path_is_idempotent_for_complete_fields(tmp_path: Path) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_EXISTING_STATUS="Backlog",
        PROJECT_INTAKE_EXISTING_PRIORITY="P1",
        PROJECT_INTAKE_EXISTING_SIZE="M",
        PROJECT_INTAKE_EXISTING_AREA="Security",
        PROJECT_INTAKE_EXISTING_INITIATIVE="Contract Hardening",
    )

    assert result.returncode == 0, result.stderr
    assert "via GraphQL" in result.stdout
    assert not (tmp_path / "edits.log").exists()


def test_project_intake_rest_fallback_applies_closed_status(tmp_path: Path) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_GRAPHQL_FAILURE="quota",
        PROJECT_INTAKE_ISSUE_STATE="closed",
    )

    assert result.returncode == 0, result.stderr
    payload = yaml.safe_load((tmp_path / "rest-patches.log").read_text(encoding="utf-8"))
    updates = {entry["id"]: entry["value"] for entry in payload["fields"]}
    assert updates[10] == "O_done"
    assert (tmp_path / "status").read_text(encoding="utf-8") == "Done\n"


def test_project_intake_rest_fallback_adds_a_missing_exact_item(tmp_path: Path) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_GRAPHQL_FAILURE="quota",
        PROJECT_INTAKE_ITEM_EXISTS="0",
    )

    assert result.returncode == 0, result.stderr
    gh_log = (tmp_path / "gh.log").read_text(encoding="utf-8")
    assert "api --method POST orgs/basefoundry/projectsV2/1/items -f type=Issue -F id=1311" in (
        gh_log
    )


def test_project_intake_rest_failures_remain_fail_closed(tmp_path: Path) -> None:
    result = run_project_intake_script(
        tmp_path,
        PROJECT_INTAKE_GRAPHQL_FAILURE="quota",
        PROJECT_INTAKE_REST_FAIL_OPERATION="update",
    )

    assert result.returncode != 0
    assert "GitHub API command failed during Project Intake: update REST Project fields" in (
        result.stderr
    )
    assert "REST field update failed" in result.stderr
    assert "Synced issue" not in result.stdout
