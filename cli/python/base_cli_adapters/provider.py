"""Compatibility checks for the extracted Base CLI provider."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType


REQUIRED_COMMAND_PROTOCOL_SYMBOLS = (
    "BOOLEAN",
    "CommandProtocolError",
    "FieldSpec",
    "NULLABLE_STRING",
    "STRING",
    "dumps_record",
    "dumps_records",
    "loads_records",
    "register_record_schema",
    "RECORD_SCHEMAS",
)


class BaseCliCompatibilityError(ImportError):
    """Raised when the installed base-cli provider cannot serve Base."""


def load_command_protocol() -> ModuleType:
    """Load the provider protocol or explain how to repair an incompatible one."""

    try:
        command_protocol = import_module("base_cli.command_protocol")
    except ImportError as exc:
        raise BaseCliCompatibilityError(
            "Base requires a compatible base-cli provider with "
            "base_cli.command_protocol. Install or upgrade base-cli, or set "
            "BASE_CLI_SOURCE_DIR to a compatible source checkout."
        ) from exc

    missing = [
        name
        for name in REQUIRED_COMMAND_PROTOCOL_SYMBOLS
        if not hasattr(command_protocol, name)
    ]
    if missing:
        names = ", ".join(missing)
        raise BaseCliCompatibilityError(
            "The installed base-cli provider is incompatible with Base: "
            f"base_cli.command_protocol is missing {names}. Install or upgrade "
            "base-cli, or set BASE_CLI_SOURCE_DIR to a compatible source checkout."
        )

    return command_protocol


__all__ = [
    "BaseCliCompatibilityError",
    "REQUIRED_COMMAND_PROTOCOL_SYMBOLS",
    "load_command_protocol",
]
