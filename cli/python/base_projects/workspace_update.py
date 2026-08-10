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
from base_projects.workspace_manifest import WorkspaceManifestRepo
from base_projects.workspace_manifest import WorkspaceManifestError
from base_projects.workspace_scanner import ProjectDiscoveryError


WorkspaceUpdateAction = Literal["pull", "skip"]
WORKSPACE_UPDATE_TIMEOUT_SECONDS = 1800


@dataclass(frozen=True)
class WorkspaceUpdateTarget:
    name: str
    root: Path
    action: WorkspaceUpdateAction
    reason: str | None = None
    required: bool = True
    fatal: bool = False


@dataclass(frozen=True)
class WorkspaceUpdateCounts:
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed: int = 0


def workspace_update_from_options(
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
            "Workspace update requires a configured or explicit workspace manifest. "
            "Pass --manifest <path> or configure workspace.manifest."
        )
        return base_cli.ExitCode.FAILURE

    return workspace_update_command(
        ctx,
        workspace_root,
        manifest,
        dry_run=options.dry_run,
    )


def workspace_update_command(
    ctx: base_cli.Context,
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    *,
    dry_run: bool,
) -> int:
    targets = workspace_update_targets(workspace_root, workspace_manifest)
    print_workspace_update_header(workspace_root, workspace_manifest, len(targets))

    counts = WorkspaceUpdateCounts()
    for target in targets:
        if target.action == "skip":
            counts = print_workspace_update_skip(target, counts)
            continue

        print_workspace_update_target(target)
        if dry_run:
            continue

        counts = execute_workspace_update_target(ctx, target, counts)

    if dry_run:
        planned = sum(target.action == "pull" for target in targets)
        print(
            "Workspace update plan complete: "
            f"planned={planned} skipped={counts.skipped} failed={counts.failed}."
        )
        print("[DRY-RUN] No repositories were modified.")
        return base_cli.ExitCode.FAILURE if counts.failed else base_cli.ExitCode.SUCCESS

    print(
        "Workspace update completed: "
        f"updated={counts.updated} unchanged={counts.unchanged} "
        f"skipped={counts.skipped} failed={counts.failed}."
    )
    return base_cli.ExitCode.FAILURE if counts.failed else base_cli.ExitCode.SUCCESS


def workspace_update_targets(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
) -> tuple[WorkspaceUpdateTarget, ...]:
    return tuple(
        workspace_update_manifest_target(
            workspace_root,
            repo,
        )
        for repo in workspace_manifest.repos
    )


def workspace_update_manifest_target(
    workspace_root: Path,
    repo: WorkspaceManifestRepo,
) -> WorkspaceUpdateTarget:
    root = (workspace_root / repo.name).resolve()

    if not root.is_dir():
        return WorkspaceUpdateTarget(
            name=repo.name,
            root=root,
            action="skip",
            reason=f"repository is missing at '{root}'",
            required=repo.required,
            fatal=repo.required,
        )

    return WorkspaceUpdateTarget(
        name=repo.name,
        root=root,
        action="pull",
        required=repo.required,
    )


def print_workspace_update_header(
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    target_count: int,
) -> None:
    print(f"Workspace update plan: {workspace_root} ({target_count} manifest repos)")
    print(f"Workspace manifest: {workspace_manifest.path} ({workspace_manifest.name})")


def print_workspace_update_target(target: WorkspaceUpdateTarget) -> None:
    print(f"PULL repository '{target.name}' at '{target.root}': git pull --ff-only")


def print_workspace_update_skip(
    target: WorkspaceUpdateTarget,
    counts: WorkspaceUpdateCounts,
) -> WorkspaceUpdateCounts:
    print(f"SKIP repository '{target.name}' at '{target.root}': {target.reason}.")
    failed = counts.failed + (1 if target.fatal else 0)
    return WorkspaceUpdateCounts(
        counts.updated,
        counts.unchanged,
        counts.skipped + 1,
        failed,
    )


def execute_workspace_update_target(
    ctx: base_cli.Context,
    target: WorkspaceUpdateTarget,
    counts: WorkspaceUpdateCounts,
) -> WorkspaceUpdateCounts:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["LC_ALL"] = "C"

    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            check=False,
            capture_output=True,
            text=True,
            cwd=target.root,
            env=env,
            timeout=WORKSPACE_UPDATE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        ctx.log.error(
            "Timed out running git pull for repository '%s' after %s seconds.",
            target.name,
            WORKSPACE_UPDATE_TIMEOUT_SECONDS,
        )
        return WorkspaceUpdateCounts(
            counts.updated,
            counts.unchanged,
            counts.skipped,
            counts.failed + 1,
        )
    except OSError as exc:
        ctx.log.error("Could not run git pull for repository '%s': %s", target.name, exc)
        return WorkspaceUpdateCounts(
            counts.updated,
            counts.unchanged,
            counts.skipped,
            counts.failed + 1,
        )

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        ctx.log.error("Git pull failed for repository '%s'.", target.name)
        return WorkspaceUpdateCounts(
            counts.updated,
            counts.unchanged,
            counts.skipped,
            counts.failed + 1,
        )

    if git_pull_was_unchanged(result.stdout, result.stderr):
        return WorkspaceUpdateCounts(
            counts.updated,
            counts.unchanged + 1,
            counts.skipped,
            counts.failed,
        )
    return WorkspaceUpdateCounts(
        counts.updated + 1,
        counts.unchanged,
        counts.skipped,
        counts.failed,
    )


def git_pull_was_unchanged(stdout: str, stderr: str) -> bool:
    output = f"{stdout}\n{stderr}".lower()
    return "already up to date" in output or "already up-to-date" in output
