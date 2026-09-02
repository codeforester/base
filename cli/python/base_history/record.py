"""Append a history record for a Bash-dispatched command."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

import base_cli
from base_cli_adapters.history import utc_now
from base_cli_adapters.history import write_primary_record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--exit-code", required=True, type=int)
    parser.add_argument("--scope", choices=("primary", "internal"), default="primary")
    parser.add_argument("--started-at")
    parser.add_argument("--project")
    parser.add_argument("--project-root")
    parser.add_argument("--manifest")
    parser.add_argument("--owner", default=os.environ.get("BASE_CLI_RUNTIME_OWNER", "base"))
    parser.add_argument("--bundle-path")
    parser.add_argument("--raw-command", default="basectl")
    parser.add_argument("argv", nargs=argparse.REMAINDER)
    options = parser.parse_args(argv)

    command_argv = list(options.argv)
    if command_argv and command_argv[0] == "--":
        command_argv = command_argv[1:]
    started_at = parse_timestamp(options.started_at) if options.started_at else utc_now()
    write_primary_record(
        command=options.command,
        argv=command_argv,
        started_at=started_at,
        exit_code=options.exit_code,
        run_id=options.run_id,
        scope=options.scope,
        project=options.project,
        project_root=options.project_root,
        manifest=options.manifest,
        log_path=None,
        owner=options.owner,
        bundle_path=options.bundle_path,
        raw_command=options.raw_command,
    )
    return base_cli.ExitCode.SUCCESS


def parse_timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError as exc:
        raise SystemExit(f"Invalid --started-at timestamp: {value}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
