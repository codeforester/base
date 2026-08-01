from __future__ import annotations

import unittest

from base_cli_adapters.command_filters import command_matches
from base_cli_adapters.command_filters import normalize_command_filter
from base_cli_adapters.command_filters import normalize_command_filters


class BaseCommandFilterTests(unittest.TestCase):
    def test_base_prefix_is_a_consumer_owned_compatibility_alias(self) -> None:
        self.assertEqual(normalize_command_filter("release"), "release")
        self.assertEqual(normalize_command_filter("base_release"), "release")
        self.assertEqual(normalize_command_filters("release, base_release"), ("release",))

    def test_stored_base_names_match_public_filters(self) -> None:
        filters = normalize_command_filters("setup")
        self.assertTrue(command_matches("base_setup", filters))
        self.assertFalse(command_matches("base_release", filters))


if __name__ == "__main__":
    unittest.main()
