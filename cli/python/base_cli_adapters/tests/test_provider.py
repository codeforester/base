from __future__ import annotations

from types import ModuleType
from unittest import TestCase
from unittest.mock import patch

from base_cli_adapters.provider import BaseCliCompatibilityError
from base_cli_adapters.provider import load_command_protocol


class BaseCliProviderTests(TestCase):
    def test_compatible_provider_loads(self) -> None:
        command_protocol = load_command_protocol()

        self.assertTrue(hasattr(command_protocol, "register_record_schema"))

    def test_missing_provider_has_actionable_error(self) -> None:
        with patch(
            "base_cli_adapters.provider.import_module",
            side_effect=ModuleNotFoundError("No module named 'base_cli'"),
        ):
            with self.assertRaisesRegex(
                BaseCliCompatibilityError,
                "Install or upgrade base-cli.*BASE_CLI_SOURCE_DIR",
            ):
                load_command_protocol()

    def test_missing_protocol_capability_has_actionable_error(self) -> None:
        command_protocol = ModuleType("base_cli.command_protocol")

        with patch(
            "base_cli_adapters.provider.import_module",
            return_value=command_protocol,
        ):
            with self.assertRaisesRegex(
                BaseCliCompatibilityError,
                "missing .*register_record_schema",
            ):
                load_command_protocol()
