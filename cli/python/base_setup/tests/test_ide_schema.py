from __future__ import annotations

import unittest

from base_setup.ide_schema import parse_ide_extensions
from base_setup.ide_schema import parse_ide_settings


class IdeSchemaTests(unittest.TestCase):
    def test_parse_ide_extensions_trims_and_rejects_empty_values(self) -> None:
        self.assertEqual(
            parse_ide_extensions("ide.vscode.extensions", [" ms-python.python "]),
            ("ms-python.python",),
        )

        with self.assertRaisesRegex(ValueError, r"ide.vscode.extensions\[1\]"):
            parse_ide_extensions("ide.vscode.extensions", [""])

    def test_parse_ide_settings_allows_auto_as_literal_by_default(self) -> None:
        self.assertEqual(
            parse_ide_settings("ide.vscode.settings", {"editor.defaultFormatter": "auto"}),
            {"editor.defaultFormatter": "auto"},
        )

    def test_parse_ide_settings_can_restrict_consumer_auto_values(self) -> None:
        project_auto_setting_keys = frozenset({"python.defaultInterpreterPath"})
        self.assertEqual(
            parse_ide_settings(
                "ide.vscode.settings",
                {"python.defaultInterpreterPath": "auto"},
                auto_setting_keys=project_auto_setting_keys,
            ),
            {"python.defaultInterpreterPath": "auto"},
        )

        with self.assertRaisesRegex(ValueError, "does not support the special value 'auto'"):
            parse_ide_settings(
                "ide.vscode.settings",
                {"editor.defaultFormatter": "auto"},
                auto_setting_keys=project_auto_setting_keys,
            )


if __name__ == "__main__":
    unittest.main()
