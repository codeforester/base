from __future__ import annotations

from dataclasses import dataclass

from base_cli.ide_schema import parse_ide_extensions
from base_cli.ide_schema import parse_ide_settings


@dataclass(frozen=True)
class IdeDefinition:
    name: str
    label: str
    cli: str
    cask: str
    settings_app_dir: str


IDE_DEFINITIONS = {
    "vscode": IdeDefinition(
        name="vscode",
        label="VS Code",
        cli="code",
        cask="visual-studio-code",
        settings_app_dir="Code",
    ),
    "cursor": IdeDefinition(
        name="cursor",
        label="Cursor",
        cli="cursor",
        cask="cursor",
        settings_app_dir="Cursor",
    ),
}

SUPPORTED_IDES = frozenset(IDE_DEFINITIONS)
PROJECT_AUTO_SETTING_KEYS = frozenset({"python.defaultInterpreterPath"})

__all__ = [
    "IDE_DEFINITIONS",
    "IdeDefinition",
    "PROJECT_AUTO_SETTING_KEYS",
    "SUPPORTED_IDES",
    "parse_ide_extensions",
    "parse_ide_settings",
]
