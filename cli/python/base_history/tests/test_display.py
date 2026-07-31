from __future__ import annotations

import unittest

from base_history.display import display_command


class BaseHistoryDisplayTests(unittest.TestCase):
    def test_base_commands_use_user_facing_aliases(self) -> None:
        self.assertEqual(display_command("base_history", []), "history")
        self.assertEqual(display_command("base_setup", ["--action", "check"]), "check")

    def test_non_base_names_keep_generic_formatting(self) -> None:
        self.assertEqual(display_command("base_something", []), "base-something")
        self.assertEqual(display_command("my_tool", []), "my-tool")
