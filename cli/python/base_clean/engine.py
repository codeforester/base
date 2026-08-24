from __future__ import annotations

import json
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path

import base_cli
from base_cli_profile import base_cli_app
from base_cli_adapters.paths import base_cache_root


app = base_cli_app(name="base_clean")


@dataclass(frozen=True)
class CleanCandidate:
    path: Path
    category: str
    age_seconds: int


def main(argv: list[str] | None = None) -> int:
    return base_cli.run_app(app, argv)


@app.command(context_settings={"help_option_names": ["-h", "--help"]})
@base_cli.option(
    "--older-than",
    help="Remove runtime artifacts older than an age such as 30d, 12h, 45m, or 60s.",
)
@base_cli.option("--keep-last", help="Keep the newest N run bundles per owner namespace.")
@base_cli.option("--dry-run", is_flag=True, help="Print what would be removed without deleting anything.")
def run(ctx: base_cli.Context, older_than: str | None, keep_last: str | None, dry_run: bool) -> int:
    if not older_than and not keep_last:
        ctx.log.error("One of '--older-than' or '--keep-last' is required.")
        return base_cli.ExitCode.USAGE_ERROR

    cache_root = base_cache_root()
    ctx.log.debug("Scanning Base cache root '%s'.", cache_root)

    candidates: list[CleanCandidate] = []
    if older_than:
        try:
            threshold_seconds = parse_age(older_than)
        except ValueError as exc:
            ctx.log.error(str(exc))
            return base_cli.ExitCode.USAGE_ERROR
        cutoff = time.time() - threshold_seconds
        candidates.extend(find_clean_candidates(cache_root, cutoff, ctx.log))

    if keep_last:
        try:
            keep_count = parse_keep_last(keep_last)
        except ValueError as exc:
            ctx.log.error(str(exc))
            return base_cli.ExitCode.USAGE_ERROR
        candidates.extend(find_log_retention_candidates(cache_root, keep_count, ctx.log))

    unique_candidates = tuple(deduplicate_candidates(candidates))

    if not unique_candidates:
        ctx.log.info("No Base runtime artifacts matched the clean criteria.")
        return base_cli.ExitCode.SUCCESS

    acted_count = 0
    for candidate in unique_candidates:
        if dry_run:
            if not clean_path_is_safe(cache_root, candidate.path, "candidate", ctx.log):
                continue
            print(f"Would remove\t{candidate.category}\t{candidate.path}")
            acted_count += 1
        elif remove_path(cache_root, candidate.path, ctx.log):
            print(f"Removing\t{candidate.category}\t{candidate.path}")
            acted_count += 1

    if not acted_count:
        ctx.log.info("No safe Base runtime artifacts matched the clean criteria.")
        return base_cli.ExitCode.SUCCESS

    ctx.log.info(
        "%s %s Base runtime artifact(s).",
        "Would remove" if dry_run else "Removed",
        acted_count,
    )
    return base_cli.ExitCode.SUCCESS


def parse_age(value: str) -> int:
    units = {
        "d": 24 * 60 * 60,
        "h": 60 * 60,
        "m": 60,
        "s": 1,
    }
    if len(value) < 2:
        raise ValueError("Option '--older-than' must be an age such as 30d, 12h, 45m, or 60s.")

    number = value[:-1]
    unit = value[-1].lower()
    if unit not in units or not number.isdigit():
        raise ValueError("Option '--older-than' must be an age such as 30d, 12h, 45m, or 60s.")

    amount = int(number)
    if amount <= 0:
        raise ValueError("Option '--older-than' must be greater than zero.")
    return amount * units[unit]


def parse_keep_last(value: str) -> int:
    if not value.isdigit():
        raise ValueError("Option '--keep-last' must be a positive integer.")
    amount = int(value)
    if amount <= 0:
        raise ValueError("Option '--keep-last' must be greater than zero.")
    return amount


def find_clean_candidates(cache_root: Path, cutoff: float, logger: object | None = None) -> list[CleanCandidate]:
    candidates: list[CleanCandidate] = []
    for owner_root in runtime_owner_roots(cache_root, logger):
        if logger is not None:
            logger.debug("Scanning runtime owner root '%s'.", owner_root)
        candidates.extend(
            find_category_candidates(
                cache_root,
                owner_root / "runs",
                "run",
                cutoff,
                logger,
            )
        )
        candidates.extend(
            find_category_candidates(
                cache_root,
                owner_root / "cache" / "components",
                "cache",
                cutoff,
                logger,
            )
        )
    return sorted(candidates, key=lambda candidate: str(candidate.path))


def find_log_retention_candidates(
    cache_root: Path,
    keep_count: int,
    logger: object | None = None,
) -> list[CleanCandidate]:
    candidates: list[CleanCandidate] = []
    for owner_root in runtime_owner_roots(cache_root, logger):
        runs_root = owner_root / "runs"
        if logger is not None:
            logger.debug("Scanning run retention artifacts in '%s'.", runs_root)
        if not clean_path_is_safe(
            cache_root,
            runs_root,
            "category root",
            logger,
            require_directory=True,
        ):
            continue
        run_dirs = []
        for path in safe_directory_entries(runs_root, "category root", logger):
            if not clean_path_is_safe(
                cache_root,
                path,
                "candidate",
                logger,
                require_directory=True,
            ) or run_is_running(path):
                continue
            try:
                run_dirs.append((path, run_metadata_mtime(path)))
            except OSError as exc:
                warn_unsafe_path(logger, "candidate", path, f"could not read metadata: {exc}")
                continue
        retained = {
            path
            for path, _mtime in sorted(
                run_dirs,
                key=lambda item: (item[1], item[0].name),
                reverse=True,
            )[:keep_count]
        }
        candidates.extend(
            CleanCandidate(path=path, category="run", age_seconds=int(time.time() - mtime))
            for path, mtime in run_dirs
            if path not in retained
        )
    return sorted(candidates, key=lambda candidate: str(candidate.path))


def runtime_owner_roots(cache_root: Path, logger: object | None = None) -> list[Path]:
    roots: list[Path] = []
    base_root = cache_root / "base"
    if clean_path_is_safe(
        cache_root,
        base_root,
        "owner root",
        logger,
        require_directory=True,
    ):
        roots.append(base_root)

    projects_root = cache_root / "projects"
    if not clean_path_is_safe(
        cache_root,
        projects_root,
        "projects root",
        logger,
        require_directory=True,
    ):
        return roots

    for namespace_root in safe_directory_entries(projects_root, "projects root", logger):
        if not clean_path_is_safe(
            cache_root,
            namespace_root,
            "project namespace",
            logger,
            require_directory=True,
        ):
            continue
        for owner_root in safe_directory_entries(namespace_root, "project namespace", logger):
            if clean_path_is_safe(
                cache_root,
                owner_root,
                "owner root",
                logger,
                require_directory=True,
            ):
                roots.append(owner_root)
    return roots


def safe_directory_entries(
    directory: Path,
    path_kind: str,
    logger: object | None = None,
) -> list[Path]:
    try:
        return sorted(directory.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        warn_unsafe_path(logger, path_kind, directory, f"could not list directory: {exc}")
        return []


def clean_path_is_safe(  # pylint: disable=too-many-return-statements
    cache_root: Path,
    path: Path,
    path_kind: str,
    logger: object | None = None,
    *,
    require_directory: bool = False,
) -> bool:
    lexical_root = cache_root.absolute()
    lexical_path = path.absolute()
    try:
        relative_path = lexical_path.relative_to(lexical_root)
    except ValueError:
        warn_unsafe_path(logger, path_kind, path, "path is outside the Base cache root")
        return False

    try:
        resolved_root = lexical_root.resolve(strict=True)
    except FileNotFoundError:
        return False
    except OSError as exc:
        warn_unsafe_path(logger, path_kind, path, f"could not resolve the Base cache root: {exc}")
        return False

    current = lexical_root
    final_stat = None
    for index, part in enumerate(relative_path.parts):
        current /= part
        try:
            current_stat = current.lstat()
        except FileNotFoundError:
            return False
        except OSError as exc:
            warn_unsafe_path(logger, path_kind, path, f"could not inspect '{current}': {exc}")
            return False
        if stat.S_ISLNK(current_stat.st_mode):
            warn_unsafe_path(
                logger,
                path_kind,
                path,
                f"path component '{current}' is a symlink; replace it with a real directory before retrying",
            )
            return False
        if index < len(relative_path.parts) - 1 and not stat.S_ISDIR(current_stat.st_mode):
            warn_unsafe_path(
                logger,
                path_kind,
                path,
                f"parent component '{current}' is not a directory",
            )
            return False
        final_stat = current_stat

    if final_stat is None:
        return False
    if require_directory and not stat.S_ISDIR(final_stat.st_mode):
        return False

    try:
        resolved_path = lexical_path.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        warn_unsafe_path(logger, path_kind, path, f"could not resolve path: {exc}")
        return False
    if not resolved_path.is_relative_to(resolved_root):
        warn_unsafe_path(logger, path_kind, path, "resolved path is outside the Base cache root")
        return False
    return True


def warn_unsafe_path(
    logger: object | None,
    path_kind: str,
    path: Path,
    reason: str,
) -> None:
    if logger is not None:
        logger.warning(
            "Skipping unsafe Base cleanup %s '%s': %s.",
            path_kind,
            path,
            reason,
        )


def run_is_running(run_root: Path) -> bool:
    metadata = run_root / "run.json"
    if not metadata.is_file():
        return False
    try:
        payload = json.loads(metadata.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(payload, dict) and payload.get("status") == "running"


def find_log_retention_candidates_for_dir(
    logs_dir: Path,
    keep_count: int,
    logger: object | None = None,
) -> list[CleanCandidate]:
    if logger is not None:
        logger.debug("Scanning log retention artifacts in '%s'.", logs_dir)
    if not logs_dir.is_dir():
        return []

    log_files = []
    for path in sorted(logs_dir.glob("*.log"), key=lambda item: item.name):
        if not path.is_file():
            continue
        try:
            path_stat = path.stat()
        except OSError:
            continue
        log_files.append((path, path_stat.st_mtime))

    retained = sorted(log_files, key=lambda item: (item[1], item[0].name), reverse=True)[:keep_count]
    retained_paths = {path for path, _mtime in retained}
    return [
        CleanCandidate(path=path, category="log", age_seconds=int(time.time() - mtime))
        for path, mtime in log_files
        if path not in retained_paths
    ]


def deduplicate_candidates(candidates: list[CleanCandidate]) -> list[CleanCandidate]:
    unique = {candidate.path: candidate for candidate in candidates}
    return sorted(unique.values(), key=lambda candidate: str(candidate.path))


def find_category_candidates(
    cache_root: Path,
    category_root: Path,
    category: str,
    cutoff: float,
    logger: object | None = None,
) -> list[CleanCandidate]:
    if logger is not None:
        logger.debug("Scanning %s runtime artifacts in '%s'.", category, category_root)
    if not clean_path_is_safe(
        cache_root,
        category_root,
        "category root",
        logger,
        require_directory=True,
    ):
        return []

    candidates = []
    for path in safe_directory_entries(category_root, "category root", logger):
        if not clean_path_is_safe(cache_root, path, "candidate", logger):
            continue
        try:
            mtime = run_metadata_mtime(path) if category == "run" else path.stat().st_mtime
        except OSError as exc:
            warn_unsafe_path(logger, "candidate", path, f"could not read metadata: {exc}")
            continue
        if mtime < cutoff:
            candidates.append(CleanCandidate(path=path, category=category, age_seconds=int(time.time() - mtime)))
    return candidates


def run_metadata_mtime(path: Path) -> float:
    metadata = path / "run.json"
    try:
        if metadata.is_file():
            return metadata.stat().st_mtime
        return path.stat().st_mtime
    except OSError:
        return path.stat().st_mtime


def remove_path(
    cache_root: Path,
    path: Path,
    logger: object | None = None,
) -> bool:
    if not clean_path_is_safe(cache_root, path, "candidate", logger):
        return False
    if not descriptor_safe_removal_supported():
        warn_unsafe_path(
            logger,
            "candidate",
            path,
            "secure descriptor-relative deletion is unavailable on this platform",
        )
        return False

    lexical_root = cache_root.absolute()
    relative_path = path.absolute().relative_to(lexical_root)
    if not relative_path.parts:
        warn_unsafe_path(logger, "candidate", path, "refusing to remove the Base cache root")
        return False

    opened_fds: list[int] = []
    directory_flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        root_fd = os.open(lexical_root.resolve(strict=True), directory_flags)
        opened_fds.append(root_fd)
        parent_fd = root_fd
        for component in relative_path.parts[:-1]:
            parent_fd = os.open(component, directory_flags, dir_fd=parent_fd)
            opened_fds.append(parent_fd)
        secure_remove_entry(parent_fd, relative_path.parts[-1], directory_flags)
    except OSError as exc:
        warn_unsafe_path(
            logger,
            "candidate",
            path,
            f"could not open cache path without following symlinks: {exc}",
        )
        return False
    finally:
        for descriptor in reversed(opened_fds):
            os.close(descriptor)
    return True


def descriptor_safe_removal_supported() -> bool:
    return (
        hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and os.open in os.supports_dir_fd
        and os.stat in os.supports_dir_fd
        and os.stat in os.supports_follow_symlinks
        and os.unlink in os.supports_dir_fd
        and os.rmdir in os.supports_dir_fd
        and os.listdir in os.supports_fd
    )


def secure_remove_entry(parent_fd: int, name: str, directory_flags: int) -> None:
    entry_stat = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISDIR(entry_stat.st_mode):
        os.unlink(name, dir_fd=parent_fd)
        return

    child_fd = os.open(name, directory_flags, dir_fd=parent_fd)
    try:
        opened_stat = os.fstat(child_fd)
        if (opened_stat.st_dev, opened_stat.st_ino) != (entry_stat.st_dev, entry_stat.st_ino):
            raise OSError("cleanup candidate changed while it was being opened")
        for child_name in os.listdir(child_fd):
            secure_remove_entry(child_fd, child_name, directory_flags)
    finally:
        os.close(child_fd)
    os.rmdir(name, dir_fd=parent_fd)
