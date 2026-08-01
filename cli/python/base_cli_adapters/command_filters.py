"""Base's compatibility policy for command-name filters."""

from __future__ import annotations

from base_cli.command_filters import CommandFilterNormalizer
from base_cli.command_filters import command_matches as _command_matches
from base_cli.command_filters import normalize_command_filter as _normalize_command_filter
from base_cli.command_filters import normalize_command_filters as _normalize_command_filters


def _normalize_base_command(value: str) -> str:
    """Treat stored Base command names as aliases of public command names."""

    return value.removeprefix("base_")


BASE_COMMAND_FILTER_NORMALIZER: CommandFilterNormalizer = _normalize_base_command


def normalize_command_filter(value: str) -> str:
    """Normalize a Base command filter, including legacy ``base_`` names."""

    return _normalize_command_filter(value, normalizer=BASE_COMMAND_FILTER_NORMALIZER)


def normalize_command_filters(value: str | None) -> tuple[str, ...]:
    """Normalize Base's comma-separated command filters."""

    return _normalize_command_filters(value, normalizer=BASE_COMMAND_FILTER_NORMALIZER)


def command_matches(value: str, command_filters: tuple[str, ...]) -> bool:
    """Match a stored or public Base command against normalized filters."""

    return _command_matches(value, command_filters, normalizer=BASE_COMMAND_FILTER_NORMALIZER)


__all__ = [
    "BASE_COMMAND_FILTER_NORMALIZER",
    "command_matches",
    "normalize_command_filter",
    "normalize_command_filters",
]
