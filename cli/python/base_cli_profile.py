from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import base_cli
import base_cli.app as base_cli_app_module
from base_cli._runtime import runtime_layout
from base_cli.config import load_config
from base_cli.config import load_yaml_file
from base_cli.config import read_user_config
from base_cli.history import HISTORY_SCOPE_INTERNAL
from base_cli.history import write_finished_record
from base_cli.paths import base_cache_root
from base_cli.paths import discover_manifest
from base_cli.paths import make_run_id
from base_cli.paths import normalize_runtime_owner
from base_cli.paths import resolve_base_home
from base_cli.paths import runtime_project_name
from base_cli.paths import runtime_project_root
from base_history.display import display_command as history_display_command
from base_setup.ide_schema import SUPPORTED_IDES


# Keep the legacy patch point available while Base supports released base-cli
# versions that still own this callback in base_cli.app.
base_cli_app_module.write_finished_record = write_finished_record


def base_cli_app(*args: Any, **kwargs: Any) -> Any:
    """Construct a Base CLI app with compatibility for older base-cli releases."""
    if hasattr(base_cli, "CliProfile"):
        kwargs["profile"] = base_cli_profile()
    return base_cli.App(*args, **kwargs)


def base_cli_profile() -> base_cli.CliProfile:
    """Return Base's explicit consumer policy for the shared CLI lifecycle."""

    def discover(cwd: Path) -> base_cli.ProjectInfo | None:
        manifest_override = os.environ.get("BASE_CLI_PROJECT_MANIFEST")
        manifest = (
            Path(manifest_override).expanduser().resolve()
            if manifest_override
            else discover_manifest(cwd)
        )
        if manifest is None:
            return None

        name: str | None = None
        try:
            project = load_yaml_file(manifest).get("project")
            if isinstance(project, dict) and isinstance(project.get("name"), str):
                name = project["name"]
        except (OSError, RuntimeError, ValueError):
            pass
        return base_cli.ProjectInfo(root=manifest.parent, manifest=manifest, name=name)

    def resolve_runtime(
        cli_name: str,
        project: base_cli.ProjectInfo | None,
    ) -> base_cli.RuntimeBinding:
        runtime_owner = normalize_runtime_owner()
        selected_project_root = runtime_project_root() or (project.root if project else None)
        selected_project_name = runtime_project_name() or (
            project.name if project else (selected_project_root.name if selected_project_root else None)
        )
        inherited_run_root = os.environ.get("BASE_CLI_RUN_ROOT") if runtime_owner == "base" else None
        inherited_path = Path(inherited_run_root).expanduser().resolve() if inherited_run_root else None
        inherited_run_id = os.environ.get("BASE_CLI_RUN_ID") if inherited_path is not None else None
        run_id = inherited_run_id or (
            inherited_path.name if inherited_path is not None else make_run_id()
        )
        cache_root = base_cache_root()
        return base_cli.RuntimeBinding(
            cache_root=cache_root,
            layout=runtime_layout(
                cache_root,
                cli_name,
                run_id,
                owner=runtime_owner,
                project_name=selected_project_name,
                project_root=selected_project_root,
                inherited_run_root=inherited_path,
            ),
            application_home=resolve_base_home(),
            runtime_owner=runtime_owner,
            project_root=selected_project_root,
            project_name=selected_project_name,
            inherited_path=inherited_path,
            history_parent_run_id=os.environ.get("BASE_CLI_HISTORY_PARENT_RUN_ID") or None,
            run_id=run_id,
            primary_log_file=(
                Path(os.environ["BASE_CLI_PRIMARY_LOG"]).expanduser()
                if inherited_path is not None and os.environ.get("BASE_CLI_PRIMARY_LOG")
                else None
            ),
            history_scope=os.environ.get(
                "BASE_CLI_HISTORY_SCOPE",
                HISTORY_SCOPE_INTERNAL if inherited_path is not None else "primary",
            ),
            write_identity=runtime_owner == "project",
        )

    return base_cli.CliProfile(
        discover_project=discover,
        load_user_config=_read_user_config,
        load_config=lambda project, explicit: load_config(
            project.root if project is not None else None,
            explicit,
        ),
        resolve_runtime=resolve_runtime,
        history_writer=_write_finished_record,
        display_command=_display_command,
        history_display_command=history_display_command,
    )


def _read_user_config() -> base_cli.UserConfig:
    return read_user_config(supported_ides=SUPPORTED_IDES)


def _write_finished_record(*args: Any) -> None:
    base_cli_app_module.write_finished_record(*args)


def _display_command() -> str | None:
    value = os.environ.get("BASE_CLI_DISPLAY_COMMAND", "").strip()
    return value or None
