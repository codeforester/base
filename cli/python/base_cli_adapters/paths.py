from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

from base_cli.paths import runtime_run_directory_name
from base_cli.paths import runtime_slug


def base_state_root(home: Path | None = None) -> Path:
    return (home or Path.home()) / ".base.d"


def base_cache_root(home: Path | None = None) -> Path:
    value = os.environ.get("BASE_CACHE_DIR")
    if value:
        return Path(value).expanduser()
    generic_root = os.environ.get("BASE_CLI_CACHE_DIR")
    if generic_root:
        return Path(generic_root).expanduser() / "base"
    root = home or Path.home()
    if sys.platform == "darwin":
        return root / "Library" / "Caches" / "base"
    return root / ".cache" / "base"


def normalize_runtime_owner(value: str | None = None) -> str:
    owner = (value or os.environ.get("BASE_CLI_RUNTIME_OWNER") or "base").strip().lower()
    if owner not in {"base", "project"}:
        raise ValueError("BASE_CLI_RUNTIME_OWNER must be 'base' or 'project'.")
    return owner


def runtime_project_name(value: str | None = None) -> str | None:
    name = (value or os.environ.get("BASE_CLI_PROJECT_NAME") or "").strip()
    return name or None


def runtime_project_root(value: Path | str | None = None) -> Path | None:
    candidate = value or os.environ.get("BASE_CLI_PROJECT_ROOT")
    if not candidate:
        return None
    return Path(candidate).expanduser().resolve()


def runtime_owner_root(
    cache_root: Path,
    owner: str = "base",
    project_name: str | None = None,
    project_root: Path | None = None,
) -> Path:
    normalized_owner = normalize_runtime_owner(owner)
    if normalized_owner == "base":
        return cache_root / "base"

    name = runtime_slug(project_name or "unnamed")
    checkout = checkout_id(project_root) or "unknown"
    return cache_root / "projects" / name / checkout


def checkout_id(project_root: Path | None) -> str | None:
    if project_root is None:
        return None
    digest = hashlib.sha256(str(project_root.expanduser().resolve()).encode("utf-8")).hexdigest()
    return digest[:12]


def discover_manifest(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    while True:
        candidate = current / "base_manifest.yaml"
        if candidate.is_file():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def resolve_base_home() -> Path | None:
    value = os.environ.get("BASE_HOME")
    if not value:
        return None
    return Path(value).expanduser().resolve()


__all__ = [
    "base_cache_root",
    "base_state_root",
    "discover_manifest",
    "normalize_runtime_owner",
    "resolve_base_home",
    "runtime_owner_root",
    "runtime_project_name",
    "runtime_project_root",
    "runtime_run_directory_name",
    "runtime_slug",
]
