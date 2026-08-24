from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from base_clean import engine


def create_old_run(root: Path) -> Path:
    run_root = root / "old-run"
    (run_root / "logs").mkdir(parents=True)
    (run_root / "logs" / "proof.log").write_text("outside\n", encoding="utf-8")
    metadata = run_root / "run.json"
    metadata.write_text('{"status":"ok"}\n', encoding="utf-8")
    old_time = time.time() - 40 * 24 * 60 * 60
    os.utime(metadata, (old_time, old_time))
    return run_root


def create_old_cache(root: Path) -> Path:
    cache_path = root / "old-cache"
    cache_path.mkdir(parents=True)
    (cache_path / "proof.txt").write_text("outside\n", encoding="utf-8")
    old_time = time.time() - 40 * 24 * 60 * 60
    os.utime(cache_path, (old_time, old_time))
    return cache_path


class BaseCleanTests(unittest.TestCase):  # pylint: disable=too-many-public-methods
    def test_parse_age_accepts_supported_units(self) -> None:
        self.assertEqual(engine.parse_age("30d"), 30 * 24 * 60 * 60)
        self.assertEqual(engine.parse_age("12h"), 12 * 60 * 60)
        self.assertEqual(engine.parse_age("45m"), 45 * 60)
        self.assertEqual(engine.parse_age("60s"), 60)

    def test_parse_age_rejects_invalid_values(self) -> None:
        for value in ("", "d", "0d", "-1d", "30", "1w"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    engine.parse_age(value)

    def test_parse_keep_last_accepts_positive_integer(self) -> None:
        self.assertEqual(engine.parse_keep_last("20"), 20)

    def test_parse_keep_last_rejects_invalid_values(self) -> None:
        for value in ("", "0", "-1", "ten", "1.5"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    engine.parse_keep_last(value)

    def test_find_clean_candidates_only_includes_old_runtime_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            old_run = cache_root / "base" / "runs" / "old-run"
            new_run = cache_root / "base" / "runs" / "new-run"
            old_log = old_run / "logs" / "old.log"
            new_log = new_run / "logs" / "new.log"
            old_cache = cache_root / "base" / "cache" / "components" / "old-cache"
            durable_state = cache_root / "durable-state" / ".base.d" / "cli" / "demo" / "logs" / "durable.log"

            old_run.mkdir(parents=True)
            (new_run / "logs").mkdir(parents=True)
            old_cache.mkdir(parents=True)
            old_log.parent.mkdir(parents=True, exist_ok=True)
            durable_state.parent.mkdir(parents=True)
            for path in (old_log, new_log, durable_state):
                path.write_text("x", encoding="utf-8")
            (old_run / "run.json").write_text('{"status":"ok"}\n', encoding="utf-8")
            (new_run / "run.json").write_text('{"status":"ok"}\n', encoding="utf-8")

            old_time = time.time() - 40 * 24 * 60 * 60
            new_time = time.time()
            for path in (old_run / "run.json", old_cache, durable_state):
                os.utime(path, (old_time, old_time))
            os.utime(new_run / "run.json", (new_time, new_time))

            candidates = engine.find_clean_candidates(cache_root, time.time() - 30 * 24 * 60 * 60)

        self.assertEqual(
            [(candidate.category, candidate.path.name) for candidate in candidates],
            [("cache", "old-cache"), ("run", "old-run")],
        )

    def test_find_clean_candidates_logs_examined_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            (cache_root / "base" / "runs").mkdir(parents=True)
            logger = mock.Mock()

            engine.find_clean_candidates(cache_root, time.time(), logger)

        logger.debug.assert_any_call("Scanning runtime owner root '%s'.", cache_root / "base")
        logger.debug.assert_any_call(
            "Scanning %s runtime artifacts in '%s'.",
            "cache",
            cache_root / "base" / "cache" / "components",
        )

    def test_find_log_retention_candidates_keeps_newest_logs_per_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            runs = cache_root / "base" / "runs"
            demo_old, demo_middle, demo_new = (runs / name for name in ("demo-1", "demo-2", "demo-3"))
            other_old, other_new = (runs / name for name in ("other-1", "other-2"))
            for path in (demo_old, demo_middle, demo_new, other_old, other_new):
                (path / "run.json").parent.mkdir(parents=True, exist_ok=True)
                (path / "run.json").write_text('{"status":"ok"}\n', encoding="utf-8")

            now = time.time()
            for offset, path in enumerate((demo_old, demo_middle, demo_new, other_old, other_new), start=1):
                timestamp = now - (10 - offset)
                os.utime(path / "run.json", (timestamp, timestamp))

            candidates = engine.find_log_retention_candidates(cache_root, keep_count=1)

        self.assertEqual(
            [(candidate.category, candidate.path.name) for candidate in candidates],
            [("run", "demo-1"), ("run", "demo-2"), ("run", "demo-3"), ("run", "other-1")],
        )

    def test_remove_path_removes_files_and_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            file_path = root / "file.log"
            dir_path = root / "run"
            file_path.write_text("x", encoding="utf-8")
            dir_path.mkdir()
            (dir_path / "temp.txt").write_text("x", encoding="utf-8")

            self.assertTrue(engine.remove_path(root, file_path))
            self.assertTrue(engine.remove_path(root, dir_path))

            self.assertFalse(file_path.exists())
            self.assertFalse(dir_path.exists())

    def test_remove_path_rejects_an_external_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cache_root = root / "cache"
            outside_path = root / "outside" / "run"
            outside_path.mkdir(parents=True)
            logger = mock.Mock()

            self.assertFalse(engine.remove_path(cache_root, outside_path, logger))

            self.assertTrue(outside_path.exists())
            warning = logger.warning.call_args.args[0] % logger.warning.call_args.args[1:]
            self.assertIn("Skipping unsafe Base cleanup candidate", warning)
            self.assertIn("outside the Base cache root", warning)

    def test_remove_path_fails_closed_if_a_parent_becomes_a_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cache_root = root / "cache"
            outside_root = root / "outside"
            external_run = create_old_run(outside_root)
            owner_link = cache_root / "base"
            owner_link.parent.mkdir(parents=True)
            owner_link.symlink_to(outside_root, target_is_directory=True)
            candidate = owner_link / external_run.name
            logger = mock.Mock()

            with mock.patch.object(engine, "clean_path_is_safe", return_value=True):
                self.assertFalse(engine.remove_path(cache_root, candidate, logger))

            self.assertTrue(external_run.is_dir())
            warning = logger.warning.call_args.args[0] % logger.warning.call_args.args[1:]
            self.assertIn("could not open cache path without following symlinks", warning)

    def test_remove_path_fails_closed_without_secure_descriptor_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            candidate = cache_root / "run"
            candidate.mkdir()
            logger = mock.Mock()

            with mock.patch.object(engine, "descriptor_safe_removal_supported", return_value=False):
                self.assertFalse(engine.remove_path(cache_root, candidate, logger))

            self.assertTrue(candidate.is_dir())
            warning = logger.warning.call_args.args[0] % logger.warning.call_args.args[1:]
            self.assertIn("secure descriptor-relative deletion is unavailable", warning)

    def test_clean_path_validation_fails_closed_on_metadata_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir)
            candidate = cache_root / "run"
            candidate.mkdir()
            logger = mock.Mock()
            original_lstat = Path.lstat

            def failing_lstat(path: Path):
                if path == candidate:
                    raise PermissionError("metadata denied")
                return original_lstat(path)

            with mock.patch.object(Path, "lstat", new=failing_lstat):
                self.assertFalse(
                    engine.clean_path_is_safe(cache_root, candidate, "candidate", logger)
                )

            self.assertTrue(candidate.is_dir())
            warning = logger.warning.call_args.args[0] % logger.warning.call_args.args[1:]
            self.assertIn("could not inspect", warning)
            self.assertIn("metadata denied", warning)

    def test_clean_rejects_symlinked_owner_roots(self) -> None:
        for owner_kind in ("base", "project"):
            with self.subTest(owner_kind=owner_kind), tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                cache_root = root / "cache"
                outside_owner = root / "outside-owner"
                external_run = create_old_run(outside_owner / "runs")
                if owner_kind == "base":
                    owner_link = cache_root / "base"
                else:
                    owner_link = cache_root / "projects" / "workspace" / "project"
                owner_link.parent.mkdir(parents=True)
                owner_link.symlink_to(outside_owner, target_is_directory=True)

                with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                    result = engine.main(["--older-than", "1s"])

                self.assertEqual(result, 0)
                self.assertTrue(owner_link.is_symlink())
                self.assertTrue(external_run.is_dir())
                self.assertTrue((external_run / "logs" / "proof.log").is_file())

    def test_clean_rejects_symlinked_project_parent_roots(self) -> None:
        cases = (
            (Path("projects"), Path("workspace/project/runs"), "projects-root"),
            (Path("projects/workspace"), Path("project/runs"), "project-namespace"),
        )
        for relative_link, outside_runs, path_kind in cases:
            with self.subTest(path_kind=path_kind), tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                cache_root = root / "cache-root"
                outside_root = root / "outside"
                external_run = create_old_run(outside_root / outside_runs)
                parent_link = cache_root / relative_link
                parent_link.parent.mkdir(parents=True)
                parent_link.symlink_to(outside_root, target_is_directory=True)

                with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                    result = engine.main(["--older-than", "1s"])

                self.assertEqual(result, 0)
                self.assertTrue(parent_link.is_symlink())
                self.assertTrue(external_run.is_dir())

    def test_clean_keep_last_rejects_a_symlinked_owner_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cache_root = root / "cache-root"
            outside_owner = root / "outside-owner"
            old_run = create_old_run(outside_owner / "runs")
            new_run = outside_owner / "runs" / "new-run"
            new_run.mkdir(parents=True)
            (new_run / "run.json").write_text('{"status":"ok"}\n', encoding="utf-8")
            owner_link = cache_root / "base"
            owner_link.parent.mkdir(parents=True)
            owner_link.symlink_to(outside_owner, target_is_directory=True)

            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                result = engine.main(["--keep-last", "1"])

            self.assertEqual(result, 0)
            self.assertTrue(owner_link.is_symlink())
            self.assertTrue(old_run.is_dir())
            self.assertTrue(new_run.is_dir())

    def test_clean_rejects_symlinked_category_roots(self) -> None:
        cases = (
            (Path("runs"), Path("outside-runs"), "run"),
            (Path("cache"), Path("outside-cache"), "cache-parent"),
            (Path("cache/components"), Path("outside-components"), "components"),
        )
        for relative_link, outside_relative, category_kind in cases:
            with self.subTest(category_kind=category_kind), tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                cache_root = root / "cache-root"
                owner_root = cache_root / "base"
                outside_root = root / outside_relative
                if category_kind == "run":
                    external_artifact = create_old_run(outside_root)
                elif category_kind == "cache-parent":
                    external_artifact = create_old_cache(outside_root / "components")
                else:
                    external_artifact = create_old_cache(outside_root)

                category_link = owner_root / relative_link
                category_link.parent.mkdir(parents=True)
                category_link.symlink_to(outside_root, target_is_directory=True)

                with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                    result = engine.main(["--older-than", "1s"])

                self.assertEqual(result, 0)
                self.assertTrue(category_link.is_symlink())
                self.assertTrue(external_artifact.is_dir())
                self.assertTrue(any(external_artifact.iterdir()))

    def test_clean_rejects_symlinked_candidates(self) -> None:
        for category_kind in ("run", "cache"):
            with self.subTest(category_kind=category_kind), tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                cache_root = root / "cache-root"
                if category_kind == "run":
                    category_root = cache_root / "base" / "runs"
                    external_artifact = create_old_run(root / "outside")
                else:
                    category_root = cache_root / "base" / "cache" / "components"
                    external_artifact = create_old_cache(root / "outside")
                category_root.mkdir(parents=True)
                candidate_link = category_root / external_artifact.name
                candidate_link.symlink_to(external_artifact, target_is_directory=True)

                with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                    result = engine.main(["--older-than", "1s"])

                self.assertEqual(result, 0)
                self.assertTrue(candidate_link.is_symlink())
                self.assertTrue(external_artifact.is_dir())
                self.assertTrue(any(external_artifact.iterdir()))

    def test_candidate_scan_warns_when_a_parent_is_a_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cache_root = root / "cache-root"
            outside_owner = root / "outside-owner"
            create_old_run(outside_owner / "runs")
            owner_link = cache_root / "projects" / "workspace" / "project"
            owner_link.parent.mkdir(parents=True)
            owner_link.symlink_to(outside_owner, target_is_directory=True)
            logger = mock.Mock()

            candidates = engine.find_clean_candidates(cache_root, time.time(), logger)

        self.assertEqual(candidates, [])
        warnings = [
            call.args[0] % call.args[1:]
            for call in logger.warning.call_args_list
        ]
        self.assertTrue(
            any(
                "Skipping unsafe Base cleanup owner root" in warning
                and "symlink" in warning
                for warning in warnings
            ),
            warnings,
        )

    def test_clean_dry_run_reports_without_removing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir) / "cache-root"
            old_run = cache_root / "base" / "runs" / "old-run"
            old_log = old_run / "logs" / "old.log"
            old_log.parent.mkdir(parents=True)
            old_log.write_text("x", encoding="utf-8")
            (old_run / "run.json").write_text('{"status":"ok"}\n', encoding="utf-8")
            old_time = time.time() - 40 * 24 * 60 * 60
            os.utime(old_run / "run.json", (old_time, old_time))

            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                result = engine.main(["--older-than", "30d", "--dry-run"])

            self.assertEqual(result, 0)
            self.assertTrue(old_log.exists())

    def test_clean_removes_old_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir) / "cache-root"
            old_run = cache_root / "base" / "runs" / "old-run"
            old_log = old_run / "logs" / "old.log"
            old_log.parent.mkdir(parents=True)
            old_log.write_text("x", encoding="utf-8")
            (old_run / "run.json").write_text('{"status":"ok"}\n', encoding="utf-8")
            old_time = time.time() - 40 * 24 * 60 * 60
            os.utime(old_run / "run.json", (old_time, old_time))

            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                result = engine.main(["--older-than", "30d"])

            self.assertEqual(result, 0)
            self.assertFalse(old_log.exists())

    def test_clean_keep_last_removes_old_logs_but_keeps_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir) / "cache-root"
            runs_dir = cache_root / "base" / "runs"
            old_run = runs_dir / "old-run"
            new_run = runs_dir / "new-run"
            old_log = old_run / "logs" / "old.log"
            new_log = new_run / "logs" / "new.log"
            for path, run in ((old_log, old_run), (new_log, new_run)):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x", encoding="utf-8")
                (run / "run.json").write_text('{"status":"ok"}\n', encoding="utf-8")
            now = time.time()
            os.utime(old_run / "run.json", (now - 10, now - 10))
            os.utime(new_run / "run.json", (now, now))

            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                result = engine.main(["--keep-last", "1"])

            self.assertEqual(result, 0)
            self.assertFalse(old_run.exists())
            self.assertTrue(new_log.exists())

    def test_clean_deduplicates_age_and_retention_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_root = Path(tmpdir) / "cache-root"
            old_run = cache_root / "base" / "runs" / "old-run"
            old_log = old_run / "logs" / "old.log"
            old_log.parent.mkdir(parents=True)
            old_log.write_text("x", encoding="utf-8")
            (old_run / "run.json").write_text('{"status":"ok"}\n', encoding="utf-8")
            old_time = time.time() - 40 * 24 * 60 * 60
            os.utime(old_run / "run.json", (old_time, old_time))

            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(cache_root)}):
                result = engine.main(["--older-than", "30d", "--keep-last", "1"])

            self.assertEqual(result, 0)
            self.assertFalse(old_run.exists())

    def test_clean_invalid_older_than_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(Path(tmpdir) / "cache-root")}):
                result = engine.main(["--older-than", "forever"])

        self.assertEqual(result, 2)

    def test_clean_missing_older_than_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(Path(tmpdir) / "cache-root")}):
                result = engine.main([])

        self.assertEqual(result, 2)

    def test_clean_invalid_keep_last_returns_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"BASE_CACHE_DIR": str(Path(tmpdir) / "cache-root")}):
                result = engine.main(["--keep-last", "many"])

        self.assertEqual(result, 2)

    def test_clean_click_usage_errors_do_not_traceback(self) -> None:
        result = engine.main(["--unknown"])

        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
