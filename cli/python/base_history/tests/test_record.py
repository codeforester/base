from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest

from base_history import record


def test_main_writes_history_and_bundle_metadata(tmp_path: Path) -> None:
    bundle_path = tmp_path / "base" / "runs" / "run-123"
    bundle_path.mkdir(parents=True)
    argv = [
        "--command",
        "export-context",
        "--run-id",
        "run-123",
        "--exit-code",
        "7",
        "--scope",
        "primary",
        "--started-at",
        "2026-08-24T01:02:03Z",
        "--project",
        "base-demo",
        "--project-root",
        str(tmp_path / "base-demo"),
        "--manifest",
        str(tmp_path / "base-demo" / "base_manifest.yaml"),
        "--owner",
        "base",
        "--bundle-path",
        str(bundle_path),
        "--raw-command",
        "basectl",
        "--",
        "export-context",
        "base-demo",
    ]

    with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(tmp_path)}):
        assert record.main(argv) == 0

    history_path = tmp_path / "base" / "history" / "runs.jsonl"
    history_record = json.loads(history_path.read_text(encoding="utf-8"))
    assert history_record["run_id"] == "run-123"
    assert history_record["command"] == "export-context"
    assert history_record["raw_command"] == "basectl"
    assert history_record["argv"] == ["export-context", "base-demo"]
    assert history_record["project"] == "base-demo"
    assert history_record["owner"] == "base"
    assert history_record["scope"] == "primary"
    assert history_record["status"] == "error"
    assert history_record["exit_code"] == 7
    assert history_record["started_at"] == "2026-08-24T01:02:03Z"

    metadata = json.loads((bundle_path / "run.json").read_text(encoding="utf-8"))
    assert metadata["run_id"] == "run-123"
    assert metadata["command"] == "export-context"
    assert metadata["raw_command"] == "basectl"
    assert metadata["argv"] == ["export-context", "base-demo"]
    assert metadata["project"] == "base-demo"
    assert metadata["owner"] == "base"
    assert metadata["status"] == "error"
    assert metadata["exit_code"] == 7


def test_main_rejects_an_invalid_start_timestamp_without_writing_history(
    tmp_path: Path,
) -> None:
    with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(tmp_path)}):
        with pytest.raises(SystemExit, match="Invalid --started-at timestamp: yesterday"):
            record.main(
                [
                    "--command",
                    "check",
                    "--run-id",
                    "run-invalid",
                    "--exit-code",
                    "0",
                    "--started-at",
                    "yesterday",
                ]
            )

    assert not (tmp_path / "base" / "history" / "runs.jsonl").exists()


def test_main_propagates_history_write_failures() -> None:
    with mock.patch.object(
        record,
        "write_primary_record",
        side_effect=OSError("history is read-only"),
    ):
        with pytest.raises(OSError, match="history is read-only"):
            record.main(
                [
                    "--command",
                    "check",
                    "--run-id",
                    "run-write-failure",
                    "--exit-code",
                    "0",
                ]
            )
