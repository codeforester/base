from __future__ import annotations

import pytest

from base_github_projects import engine


def test_parse_project_issue_fields_defaults_to_repository_named_project() -> None:
    args = engine.parse_args(
        (
            "project",
            "issue",
            "set-fields",
            "1862",
            "--repo",
            "basefoundry/base-cli",
            "--status",
            "In Progress",
        )
    )

    assert args.project_title == "base-cli"
    assert args.repo == "basefoundry/base-cli"
    assert args.allow_cross_project is False


def test_parse_project_issue_fields_rejects_mismatched_project() -> None:
    with pytest.raises(engine.ProjectUsageError) as excinfo:
        engine.parse_args(
            (
                "project",
                "issue",
                "set-fields",
                "1862",
                "--project",
                "base",
                "--repo",
                "basefoundry/base-cli",
                "--status",
                "In Progress",
            )
        )

    assert str(excinfo.value) == (
        "Project 'base' does not match repository 'basefoundry/base-cli' "
        "(expected 'base-cli'). Use '--project base-cli' or pass "
        "'--allow-cross-project' for an intentional cross-project update."
    )


def test_parse_project_issue_fields_allows_explicit_cross_project_update() -> None:
    args = engine.parse_args(
        (
            "project",
            "issue",
            "set-fields",
            "1862",
            "--project",
            "base",
            "--repo",
            "basefoundry/base-cli",
            "--allow-cross-project",
            "--status",
            "In Progress",
        )
    )

    assert args.project_title == "base"
    assert args.allow_cross_project is True
