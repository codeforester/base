from __future__ import annotations

import os
import subprocess
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
WorkspaceUpdateStatus = Literal["planned", "updated", "unchanged", "skipped", "failed"]
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


@dataclass(frozen=True)
class WorkspaceUpdateResult:
    status: WorkspaceUpdateStatus
    detail: str | None = None
    exit_code: int | None = None


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
    name_width = max(len("REPOSITORY"), *(len(target.name) for target in targets))
    print_workspace_update_header(workspace_root, workspace_manifest, len(targets), name_width)

    counts = WorkspaceUpdateCounts()
    for target in targets:
        if target.action == "skip":
            result = WorkspaceUpdateResult("skipped", target.reason)
            counts = update_workspace_update_counts(counts, result, fatal=target.fatal)
            print_workspace_update_result(target, result, name_width)
            continue

        if dry_run:
            print_workspace_update_result(target, WorkspaceUpdateResult("planned"), name_width)
            continue

        result = execute_workspace_update_target(ctx, target)
        counts = update_workspace_update_counts(counts, result)
        print_workspace_update_result(target, result, name_width)

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
    name_width: int,
) -> None:
    print(f"Workspace update: {workspace_root} ({target_count} manifest repos)")
    print(f"Workspace manifest: {workspace_manifest.path} ({workspace_manifest.name})")
    print()
    print(f"{'REPOSITORY':<{name_width}}  {'ACTION':<6}  RESULT")


def print_workspace_update_result(
    target: WorkspaceUpdateTarget,
    result: WorkspaceUpdateResult,
    name_width: int,
) -> None:
    action = target.action.upper()
    outcome = result.status
    if result.exit_code is not None:
        outcome = f"{outcome} (exit {result.exit_code})"
    print(f"{target.name:<{name_width}}  {action:<6}  {outcome}")
    if result.detail:
        for line in result.detail.splitlines():
            print(f"{'':<{name_width}}  {'':<6}  {line}")


def update_workspace_update_counts(
    counts: WorkspaceUpdateCounts,
    result: WorkspaceUpdateResult,
    *,
    fatal: bool = False,
) -> WorkspaceUpdateCounts:
    return WorkspaceUpdateCounts(
        updated=counts.updated + (result.status == "updated"),
        unchanged=counts.unchanged + (result.status == "unchanged"),
        skipped=counts.skipped + (result.status == "skipped"),
        failed=counts.failed + (result.status == "failed" or fatal),
    )


def execute_workspace_update_target(
    ctx: base_cli.Context,
    target: WorkspaceUpdateTarget,
) -> WorkspaceUpdateResult:
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
        return WorkspaceUpdateResult(
            "failed",
            detail=f"timed out after {WORKSPACE_UPDATE_TIMEOUT_SECONDS} seconds",
        )
    except OSError as exc:
        return WorkspaceUpdateResult(
            "failed",
            detail=f"could not run git pull: {exc}",
        )

    ctx.log.debug(
        "Git pull for repository '%s' exited with %s; stdout=%r stderr=%r",
        target.name,
        result.returncode,
        result.stdout,
        result.stderr,
    )
    if result.returncode != 0:
        return WorkspaceUpdateResult(
            "failed",
            detail=git_pull_detail(result.stdout, result.stderr),
            exit_code=result.returncode,
        )

    if git_pull_was_unchanged(result.stdout, result.stderr):
        return WorkspaceUpdateResult("unchanged")
    return WorkspaceUpdateResult("updated")


def git_pull_detail(stdout: str, stderr: str) -> str:
    details = [part.strip() for part in (stderr, stdout) if part.strip()]
    return "\n".join(details) or "git pull failed without diagnostic output"


def git_pull_was_unchanged(stdout: str, stderr: str) -> bool:
    output = f"{stdout}\n{stderr}".lower()
    return "already up to date" in output or "already up-to-date" in output
