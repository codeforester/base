from __future__ import annotations

from pathlib import Path

from base_cli._runtime import RuntimeLayout

from .paths import runtime_owner_root
from .paths import runtime_run_directory_name


# pylint: disable=too-many-arguments
def runtime_layout(
    cache_root: Path,
    cli_name: str,
    run_id: str,
    *,
    owner: str = "base",
    project_name: str | None = None,
    project_root: Path | None = None,
    inherited_run_root: Path | None = None,
) -> RuntimeLayout:
    owner_root = runtime_owner_root(cache_root, owner, project_name, project_root)
    run_root = inherited_run_root or owner_root / "runs" / runtime_run_directory_name(
        run_id,
        cli_name,
        project_name,
    )
    return RuntimeLayout(
        owner_root=owner_root,
        run_root=run_root,
        state_dir=owner_root,
        log_dir=run_root / "logs",
        cache_dir=owner_root / "cache" / "components" / cli_name,
        temp_dir=run_root / "tmp" / cli_name / run_id,
    )
