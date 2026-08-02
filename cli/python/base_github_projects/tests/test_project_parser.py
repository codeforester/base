from __future__ import annotations

from base_github_projects import engine


def test_parse_project_issue_set_fields_accepts_cross_repo_opt_in() -> None:
    args = engine.parse_args(
        (
            "project",
            "issue",
            "set-fields",
            "1604",
            "--project",
            "Base Roadmap",
            "--owner",
            "basefoundry",
            "--repo",
            "basefoundry/base-cli",
            "--allow-cross-repo",
            "--priority",
            "P2",
        )
    )

    assert args.command == "issue-set-fields"
    assert args.repo == "basefoundry/base-cli"
    assert args.allow_cross_repo is True
    assert args.field_values == {"priority": "P2"}
