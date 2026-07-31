from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import base_cli
from base_projects import workspace_context
from base_projects.workspace_context import resolve_workspace_manifest
from base_projects.workspace_manifest import WorkspaceManifest
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_scanner import ProjectDiscoveryError
from base_setup.manifest import read_manifest
from base_setup.manifest_loader import ManifestError


WorkspaceSetupAction = Literal["setup", "skip"]
WORKSPACE_SETUP_TIMEOUT_SECONDS = 1800


@dataclass(frozen=True)
class WorkspaceSetupTarget:
    name: str
    root: Path
    manifest_path: Path | None
    project_name: str | None
    action: WorkspaceSetupAction
    reason: str | None = None
    required: bool = True
    fatal: bool = False


@dataclass(frozen=True)
class WorkspaceSetupCounts:
    setup: int = 0
    skipped: int = 0
    failed: int = 0


def workspace_setup_from_options(
    ctx: base_cli.Context,
    options: Any,
) -> int:
    if getattr(options, "output_format", "text") != "text":
        ctx.log.error("Unsupported output format '%s'. Expected: text.", options.output_format)
        return base_cli.ExitCode.USAGE_ERROR

    try:
        workspace_root = workspace_context.resolve_workspace_root(ctx, options.workspace)
        manifest = resolve_workspace_manifest(
            workspace_context.effective_workspace_manifest(ctx, options.workspace_manifest)
        )
    except (ProjectDiscoveryError, WorkspaceManifestError) as exc:
        ctx.log.error(str(exc))
        return base_cli.ExitCode.FAILURE

    if manifest is None:
        ctx.log.error(
            "Workspace setup requires a configured or explicit workspace manifest. "
            "Pass --manifest <path> or configure workspace.manifest."
        )
        return base_cli.ExitCode.FAILURE

    return workspace_setup_command(ctx, workspace_root, manifest, dry_run=options.dry_run, yes=options.yes)


def workspace_setup_command(
    ctx: base_cli.Context,
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    *,
    dry_run: bool,
    yes: bool = False,
) -> int:
    targets = workspace_setup_targets(workspace_root, workspace_manifest)
    print_workspace_setup_header(workspace_root, workspace_manifest, len(targets))

    counts = WorkspaceSetupCounts()
    if not dry_run and ctx.base_home is None:
        ctx.log.error("BASE_HOME is required to execute workspace setup.")
        return base_cli.ExitCode.FAILURE

    basectl = ctx.base_home / "bin" / "basectl" if ctx.base_home is not None else None
    if not dry_run and (basectl is None or not basectl.is_file() or not os.access(basectl, os.X_OK)):
        ctx.log.error("Base CLI '%s' is missing or is not executable.", basectl)
        return base_cli.ExitCode.FAILURE

    for target in targets:
        if target.action == "skip":
            counts = print_workspace_setup_skip(target, counts)
            continue

        print_workspace_setup_target(target)
        if dry_run:
            counts = WorkspaceSetupCounts(counts.setup + 1, counts.skipped, counts.failed)
            continue
        if basectl is None:
            ctx.log.error("Base CLI is unavailable for workspace setup execution.")
            return base_cli.ExitCode.FAILURE

        counts = execute_workspace_setup_target(
            ctx,
            basectl,
            target,
            counts,
            yes=yes,
        )

    if dry_run:
        print(f"Workspace setup plan complete: setup={counts.setup} skipped={counts.skipped}.")
        print("[DRY-RUN] No repositories were modified.")
        return base_cli.ExitCode.SUCCESS

    print(
        "Workspace setup completed: "
        f"setup={counts.setup} skipped={counts.skipped} failed={counts.failed}."
    )
    return base_cli.ExitCode.FAILURE if counts.failed else base_cli.ExitCode.SUCCESS


def workspace_setup_targets(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
) -> tuple[WorkspaceSetupTarget, ...]:
    return tuple(
        workspace_setup_manifest_target(workspace_root, repo)
        for repo in workspace_manifest.repos
    )


def workspace_setup_manifest_target(
    workspace_root: Path,
    repo: WorkspaceManifestRepo,
) -> WorkspaceSetupTarget:
    root = (workspace_root / repo.name).resolve()
    manifest_path = root / "base_manifest.yaml"

    if not root.is_dir():
        return WorkspaceSetupTarget(
            name=repo.name,
            root=root,
            manifest_path=None,
            project_name=None,
            action="skip",
            reason=f"repository is missing at '{root}'",
            required=repo.required,
            fatal=repo.required,
        )

    if repo.name == "base":
        return WorkspaceSetupTarget(
            name=repo.name,
            root=root,
            manifest_path=manifest_path if manifest_path.is_file() else None,
            project_name="base",
            action="skip",
            reason="active Base control plane is managed from BASE_HOME",
            required=repo.required,
        )

    if not manifest_path.is_file():
        return WorkspaceSetupTarget(
            name=repo.name,
            root=root,
            manifest_path=None,
            project_name=None,
            action="skip",
            reason="repository does not contain base_manifest.yaml",
            required=repo.required,
        )

    try:
        manifest = read_manifest(manifest_path)
    except ManifestError as exc:
        return WorkspaceSetupTarget(
            name=repo.name,
            root=root,
            manifest_path=manifest_path.resolve(),
            project_name=None,
            action="skip",
            reason=f"base_manifest.yaml is invalid: {exc}",
            required=repo.required,
            fatal=repo.required,
        )

    return WorkspaceSetupTarget(
        name=repo.name,
        root=root,
        manifest_path=manifest_path.resolve(),
        project_name=manifest.project_name,
        action="setup",
        required=repo.required,
    )


def print_workspace_setup_header(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    target_count: int,
) -> None:
    print(f"Workspace setup plan: {workspace_root} ({target_count} manifest repos)")
    print(f"Workspace manifest: {workspace_manifest.path} ({workspace_manifest.name})")


def print_workspace_setup_target(target: WorkspaceSetupTarget) -> None:
    print(
        f"SETUP repository '{target.name}' at '{target.root}' "
        f"using '{target.manifest_path}' for project '{target.project_name}'."
    )


def print_workspace_setup_skip(
    target: WorkspaceSetupTarget,
    counts: WorkspaceSetupCounts,
) -> WorkspaceSetupCounts:
    print(f"SKIP repository '{target.name}' at '{target.root}': {target.reason}.")
    failed = counts.failed + (1 if target.fatal else 0)
    return WorkspaceSetupCounts(counts.setup, counts.skipped + 1, failed)


def execute_workspace_setup_target(
    ctx: base_cli.Context,
    basectl: Path,
    target: WorkspaceSetupTarget,
    counts: WorkspaceSetupCounts,
    *,
    yes: bool,
) -> WorkspaceSetupCounts:
    if target.manifest_path is None or target.project_name is None:
        ctx.log.error("Setup target '%s' is missing manifest routing metadata.", target.name)
        return WorkspaceSetupCounts(counts.setup, counts.skipped, counts.failed + 1)

    command = [str(basectl), "setup", "--manifest", str(target.manifest_path)]
    if yes:
        command.append("--yes")
    command.append(target.project_name)

    env = os.environ.copy()
    env["BASE_HOME"] = str(ctx.base_home)
    for variable in ("BASE_PROJECT", "BASE_PROJECT_ROOT", "BASE_PROJECT_MANIFEST", "BASE_PROJECT_VENV_DIR"):
        env.pop(variable, None)

    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            cwd=target.root,
            env=env,
            timeout=WORKSPACE_SETUP_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        ctx.log.error(
            "Timed out running basectl setup for repository '%s' after %s seconds.",
            target.name,
            WORKSPACE_SETUP_TIMEOUT_SECONDS,
        )
        return WorkspaceSetupCounts(counts.setup, counts.skipped, counts.failed + 1)
    except OSError as exc:
        ctx.log.error("Could not run basectl setup for repository '%s': %s", target.name, exc)
        return WorkspaceSetupCounts(counts.setup, counts.skipped, counts.failed + 1)

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode == 0:
        return WorkspaceSetupCounts(counts.setup + 1, counts.skipped, counts.failed)

    ctx.log.error("Setup failed for repository '%s'.", target.name)
    return WorkspaceSetupCounts(counts.setup, counts.skipped, counts.failed + 1)
