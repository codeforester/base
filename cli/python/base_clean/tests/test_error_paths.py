from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

from base_clean import engine


def rendered_warning(logger: mock.Mock) -> str:
    call = logger.warning.call_args
    return call.args[0] % call.args[1:]


def test_safe_directory_entries_reports_unreadable_directory(tmp_path: Path) -> None:
    logger = mock.Mock()
    directory = tmp_path / "unreadable"

    with mock.patch.object(Path, "iterdir", side_effect=PermissionError("listing denied")):
        assert engine.safe_directory_entries(directory, "category root", logger) == []

    assert "could not list directory: listing denied" in rendered_warning(logger)


def test_clean_path_rejects_non_directory_parent_component(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    parent_file = cache_root / "base"
    parent_file.write_text("not a directory", encoding="utf-8")
    logger = mock.Mock()

    assert not engine.clean_path_is_safe(cache_root, parent_file / "runs", "candidate", logger)

    assert "parent component" in rendered_warning(logger)
    assert "is not a directory" in rendered_warning(logger)


def test_clean_path_reports_cache_root_resolution_failure(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    candidate = cache_root / "candidate"
    candidate.mkdir()
    logger = mock.Mock()
    original_resolve = Path.resolve

    def fail_root_resolution(path: Path, *, strict: bool = False) -> Path:
        if path == cache_root:
            raise PermissionError("root denied")
        return original_resolve(path, strict=strict)

    with mock.patch.object(Path, "resolve", new=fail_root_resolution):
        assert not engine.clean_path_is_safe(cache_root, candidate, "candidate", logger)

    assert "could not resolve the Base cache root: root denied" in rendered_warning(logger)


def test_retention_skips_candidate_with_unreadable_metadata(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    run_root = cache_root / "base" / "runs" / "run-1"
    run_root.mkdir(parents=True)
    logger = mock.Mock()

    with mock.patch.object(engine, "run_metadata_mtime", side_effect=PermissionError("metadata denied")):
        candidates = engine.find_log_retention_candidates(cache_root, 1, logger)

    assert not candidates
    assert "could not read metadata: metadata denied" in rendered_warning(logger)


def test_category_scan_skips_candidate_with_unreadable_metadata(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    category_root = cache_root / "base" / "cache" / "components"
    candidate = category_root / "entry"
    candidate.mkdir(parents=True)
    logger = mock.Mock()
    original_stat = Path.stat

    def fail_candidate_stat(path: Path, *args, **kwargs):
        if path == candidate:
            raise PermissionError("stat denied")
        return original_stat(path, *args, **kwargs)

    with mock.patch.object(Path, "stat", new=fail_candidate_stat), mock.patch.object(
        engine,
        "clean_path_is_safe",
        return_value=True,
    ):
        candidates = engine.find_category_candidates(
            cache_root,
            category_root,
            "cache",
            cutoff=float("inf"),
            logger=logger,
        )

    assert not candidates
    assert "could not read metadata: stat denied" in rendered_warning(logger)


def test_remove_path_fails_closed_when_descriptor_relative_removal_fails(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    candidate = cache_root / "base" / "runs" / "run-1"
    candidate.mkdir(parents=True)
    proof = candidate / "proof.log"
    proof.write_text("keep", encoding="utf-8")
    logger = mock.Mock()

    with mock.patch.object(engine, "descriptor_safe_removal_supported", return_value=True), mock.patch.object(
        engine,
        "secure_remove_entry",
        side_effect=PermissionError("removal denied"),
    ):
        assert not engine.remove_path(cache_root, candidate, logger)

    assert proof.read_text(encoding="utf-8") == "keep"
    assert "could not open cache path without following symlinks: removal denied" in rendered_warning(logger)


def test_secure_remove_entry_rejects_directory_replacement() -> None:
    initial = mock.Mock(st_mode=0o040755, st_dev=1, st_ino=2)
    opened = mock.Mock(st_dev=1, st_ino=3)

    with mock.patch.object(os, "stat", return_value=initial), mock.patch.object(
        os, "open", return_value=99
    ), mock.patch.object(os, "fstat", return_value=opened), mock.patch.object(os, "close") as close_mock:
        try:
            engine.secure_remove_entry(10, "candidate", 0)
        except OSError as exc:
            assert "changed while it was being opened" in str(exc)
        else:
            raise AssertionError("replacement must fail closed")

    close_mock.assert_called_once_with(99)


def test_run_that_becomes_active_is_retained_without_removal(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    cache_root = tmp_path / "cache"
    run_root = cache_root / "base" / "runs" / "run-1"
    run_root.mkdir(parents=True)
    candidate = engine.CleanCandidate(run_root, "run", 100)
    monkeypatch.setenv("BASE_CACHE_DIR", str(cache_root))
    monkeypatch.setattr(engine, "find_clean_candidates", lambda *args, **kwargs: [candidate])
    monkeypatch.setattr(engine, "run_is_running", lambda path: True)
    remove = mock.Mock()
    monkeypatch.setattr(engine, "remove_path", remove)

    assert engine.main(["--older-than", "1s", "--yes"]) == 0

    assert f"Retaining\tactive run\t{run_root}" in capsys.readouterr().out
    remove.assert_not_called()


def test_preview_with_only_unsafe_matches_reports_no_safe_result(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    cache_root = tmp_path / "cache"
    candidate_path = cache_root / "candidate"
    candidate = engine.CleanCandidate(candidate_path, "cache", 100)
    monkeypatch.setenv("BASE_CACHE_DIR", str(cache_root))
    monkeypatch.setattr(engine, "find_clean_candidates", lambda *args, **kwargs: [candidate])
    monkeypatch.setattr(engine, "clean_path_is_safe", lambda *args, **kwargs: False)

    assert engine.main(["--older-than", "1s", "--dry-run"]) == 0

    assert "No safe Base runtime artifacts matched" in capsys.readouterr().err
    assert not candidate_path.exists()
