from __future__ import annotations


_BASE_DISPLAY_COMMANDS = frozenset(
    {
        "base_activate",
        "base_build",
        "base_check",
        "base_ci",
        "base_clean",
        "base_config",
        "base_demo",
        "base_dev",
        "base_devcontainer",
        "base_devenv",
        "base_devenv_report",
        "base_docs",
        "base_export_context",
        "base_gh",
        "base_github_projects",
        "base_history",
        "base_logs",
        "base_onboard",
        "base_pr_policy",
        "base_projects",
        "base_prompt",
        "base_release",
        "base_repo",
        "base_run",
        "base_setup",
        "base_test",
        "base_trust",
        "base_update",
        "base_update_profile",
        "base_workspace",
    }
)


def display_command(cli_name: str, argv: list[str]) -> str:
    if cli_name == "base_setup":
        return base_setup_action(argv) or "setup"
    if cli_name in _BASE_DISPLAY_COMMANDS:
        return cli_name.removeprefix("base_").replace("_", "-")
    return cli_name.replace("_", "-")


def base_setup_action(argv: list[str]) -> str | None:
    for index, arg in enumerate(argv):
        if arg == "--action" and index + 1 < len(argv):
            return argv[index + 1]
        if arg.startswith("--action="):
            return arg.partition("=")[2]
    return None
