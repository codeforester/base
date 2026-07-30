from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from typing import Any

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


@dataclass(frozen=True)
class WorkspaceSetupTarget:
    name: str
    root: Path
    manifest_path: Path | None
    project_name: str | None
    action: WorkspaceSetupAction
    reason: str | None = None
    required: bool = True


@dataclass(frozen=True)
class WorkspaceSetupCounts:
    setup: int = 0
    skipped: int = 0


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

    return workspace_setup_command(ctx, workspace_root, manifest, dry_run=options.dry_run)


def workspace_setup_command(
    ctx: base_cli.Context,
    workspace_root: Path,
    workspace_manifest: WorkspaceManifest,
    *,
    dry_run: bool,
) -> int:
    targets = workspace_setup_targets(workspace_root, workspace_manifest)
    print_workspace_setup_header(workspace_root, workspace_manifest, len(targets))

    counts = WorkspaceSetupCounts()
    for target in targets:
        counts = print_workspace_setup_target(target, counts)

    print(
        "Workspace setup plan complete: "
        f"setup={counts.setup} skipped={counts.skipped}."
    )
    if dry_run:
        print("[DRY-RUN] No repositories were modified.")
        return base_cli.ExitCode.SUCCESS

    ctx.log.error(
        "Workspace setup execution is not available yet. "
        "Use --dry-run to inspect the setup plan."
    )
    return base_cli.ExitCode.FAILURE


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


def print_workspace_setup_target(
    target: WorkspaceSetupTarget,
    counts: WorkspaceSetupCounts,
) -> WorkspaceSetupCounts:
    if target.action == "skip":
        print(f"SKIP repository '{target.name}' at '{target.root}': {target.reason}.")
        return WorkspaceSetupCounts(counts.setup, counts.skipped + 1)

    print(
        f"SETUP repository '{target.name}' at '{target.root}' "
        f"using '{target.manifest_path}' for project '{target.project_name}'."
    )
    return WorkspaceSetupCounts(counts.setup + 1, counts.skipped)
