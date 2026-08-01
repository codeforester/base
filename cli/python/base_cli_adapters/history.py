from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import base_cli
from base_cli.context import Context
from base_cli.history import HISTORY_SCOPE_INTERNAL
from base_cli.history import HISTORY_SCOPE_PRIMARY
from base_cli.history import SCHEMA_VERSION
from base_cli.history import compact_home_text
from base_cli.history import compact_optional_path
from base_cli.history import compact_path
from base_cli.history import display_command
from base_cli.history import duration_ms
from base_cli.history import format_timestamp
from base_cli.history import optional_int
from base_cli.history import optional_string
from base_cli.history import parse_finished_history_record_line
from base_cli.history import parse_positive_int
from base_cli.history import redact_history_argv
from base_cli.history import redact_history_text
from base_cli.history import update_run_metadata
from base_cli.history import utc_now
from base_cli.history import write_history_record as write_record

from .config import load_yaml_file
from .paths import base_cache_root


HISTORY_PATH = Path("base") / "history" / "runs.jsonl"


def build_finished_record(
    context: Context,
    argv: list[str],
    sensitive_options: set[str],
    started_at: Any,
    exit_code: int,
) -> dict[str, Any]:
    record = base_cli.history.build_finished_record(
        context,
        argv,
        sensitive_options,
        started_at,
        exit_code,
    )
    if "project" not in record:
        record["project"] = project_name(context)
    version = base_version(context.base_home)
    if version:
        record["base_version"] = version
    return {key: value for key, value in record.items() if value}


def project_name(context: Context) -> str | None:
    if context.project_name:
        return context.project_name
    if context.manifest_path is None:
        return None
    try:
        data = load_yaml_file(context.manifest_path)
    except (OSError, RuntimeError, ValueError):
        return None
    project_data = data.get("project")
    if not isinstance(project_data, dict):
        return None
    value = project_data.get("name")
    return value if isinstance(value, str) and value else None


def base_version(base_home: Path | None) -> str | None:
    if base_home is None:
        return None
    try:
        version = (base_home / "VERSION").read_text(encoding="utf-8").splitlines()[0].strip()
    except (IndexError, OSError):
        return None
    return version or None


def write_finished_record(
    context: Context,
    argv: list[str],
    sensitive_options: set[str],
    started_at: Any,
    exit_code: int,
) -> None:
    if context.dry_run or context.log_file is None or context.history_scope == HISTORY_SCOPE_INTERNAL:
        return
    try:
        record = build_finished_record(context, argv, sensitive_options, started_at, exit_code)
        write_history_record(record)
        if context.run_root is not None:
            update_run_metadata(context.run_root, record)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        context.log.debug("Unable to write command history record: %s", exc)


def write_history_record(record: dict[str, Any]) -> None:
    path = base_cache_root() / HISTORY_PATH
    write_record(path, record)


def runtime_bundle_path() -> Path | None:
    value = os.environ.get("BASE_CLI_RUN_ROOT")
    if not value:
        return None
    return Path(value).expanduser().resolve(strict=False)


# pylint: disable=too-many-arguments,too-many-positional-arguments
def write_primary_record(
    command: str,
    argv: list[str],
    started_at: Any,
    exit_code: int,
    run_id: str,
    scope: str = HISTORY_SCOPE_PRIMARY,
    project: str | None = None,
    project_root: str | None = None,
    manifest: str | None = None,
    log_path: str | None = None,
    owner: str = "base",
    bundle_path: str | None = None,
    *,
    raw_command: str = "basectl",
) -> None:
    path = base_cache_root() / HISTORY_PATH
    base_cli.history.write_primary_record(
        path=path,
        command=command,
        argv=argv,
        started_at=started_at,
        exit_code=exit_code,
        run_id=run_id,
        scope=scope,
        project=project,
        project_root=project_root,
        manifest=manifest,
        log_path=log_path,
        owner=owner,
        bundle_path=bundle_path or runtime_bundle_path(),
        raw_command=raw_command,
    )


__all__ = [
    "HISTORY_PATH",
    "HISTORY_SCOPE_INTERNAL",
    "HISTORY_SCOPE_PRIMARY",
    "SCHEMA_VERSION",
    "base_version",
    "build_finished_record",
    "compact_home_text",
    "compact_optional_path",
    "compact_path",
    "display_command",
    "duration_ms",
    "format_timestamp",
    "optional_int",
    "optional_string",
    "parse_finished_history_record_line",
    "parse_positive_int",
    "project_name",
    "redact_history_argv",
    "redact_history_text",
    "runtime_bundle_path",
    "utc_now",
    "write_finished_record",
    "write_history_record",
    "write_primary_record",
]
