from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from base_projects.command_helpers import ProjectUsageError
from base_projects.workspace_file_url import resolve_workspace_file_url


class WorkspaceFileUrlTests(unittest.TestCase):
    def test_file_url_decodes_spaces_unicode_and_literal_percent_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "Base Workspace-雪-%20" / "workspace.yaml"

            resolved = resolve_workspace_file_url(path.as_uri())

        self.assertEqual(resolved, path.resolve(strict=False))
        self.assertIn("%2520", path.as_uri())
        self.assertEqual(resolved.parent.name, "Base Workspace-雪-%20")

    def test_file_url_accepts_only_empty_and_localhost_authorities(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "workspace.yaml"
            local_url = path.as_uri()
            localhost_url = local_url.replace("file:///", "file://LOCALHOST/", 1)

            self.assertEqual(resolve_workspace_file_url(local_url), path.resolve(strict=False))
            self.assertEqual(resolve_workspace_file_url(localhost_url), path.resolve(strict=False))

        with self.assertRaisesRegex(ProjectUsageError, "only an empty or localhost authority"):
            resolve_workspace_file_url("file://files.example.test/private/workspace.yaml")

    def test_file_url_rejects_ambiguous_or_malformed_components(self) -> None:
        cases = (
            ("file://[broken/workspace.yaml", "Malformed workspace file URL"),
            ("file:///private/tmp/workspace%2.yaml", "malformed percent encoding"),
            ("file:///private/tmp/workspace%FF.yaml", "invalid UTF-8 percent encoding"),
            ("file:///private/tmp/workspace.yaml?ref=main", "cannot include parameters"),
            ("file:///private/tmp/workspace.yaml#fragment", "cannot include parameters"),
            ("file:relative/workspace.yaml", "must be an absolute local path"),
            ("file:////files.example.test/workspace.yaml", "must be an absolute local path"),
            ("file:///private/tmp/workspace%00.yaml", "cannot contain a NUL byte"),
        )
        for source, expected_message in cases:
            with self.subTest(source=source):
                with self.assertRaisesRegex(ProjectUsageError, expected_message):
                    resolve_workspace_file_url(source)
