"""Shared pytest setup helpers for Base's Python tests."""

from __future__ import annotations

from pathlib import Path

import pytest


class ManifestFactory:
    """Build the small manifest variants used by package-level tests."""

    @staticmethod
    def _write(root: Path, lines: list[str]) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        manifest_path = root / "base_manifest.yaml"
        manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return manifest_path

    def write(
        self,
        root: Path,
        name: str = "demo",
        *,
        test_command: str | None = "pytest tests/",
    ) -> Path:
        """Write the standard manifest used by command-trust tests."""

        lines = ["project:", f"  name: {name}"]
        if test_command is not None:
            lines.extend(["test:", f"  command: {test_command}"])
        lines.append("artifacts: []")
        return self._write(root, lines)

    def write_project(self, root: Path, name: str = "demo") -> Path:
        """Write a minimal Python-project manifest."""

        return self._write(
            root,
            ["project:", f"  name: {name}", "python: {}", "artifacts: []"],
        )

    def write_shell(self, root: Path, name: str = "demo") -> Path:
        """Write a minimal shell-project manifest."""

        return self._write(root, ["project:", f"  name: {name}", "artifacts: []"])

    def write_python(self, root: Path, name: str = "demo") -> Path:
        """Write a uv-managed Python-project manifest with a ready venv."""

        manifest_path = self._write(
            root,
            ["project:", f"  name: {name}", "python:", "  manager: uv"],
        )
        self.write_ready_python_bin(root / ".venv" / "bin" / "python")
        return manifest_path

    def write_inline_python(self, root: Path, name: str = "demo") -> Path:
        """Write an inline-uv Python-project manifest with a ready venv."""

        manifest_path = self._write(
            root,
            ["project:", f"  name: {name}", "python: {manager: uv}", "artifacts: []"],
        )
        self.write_ready_python_bin(root / ".venv" / "bin" / "python")
        return manifest_path

    def write_command_surfaces(self, root: Path, name: str = "demo") -> Path:
        """Write a manifest containing every executable command surface."""

        return self._write(
            root,
            [
                "project:",
                f"  name: {name}",
                "test:",
                "  command: pytest tests/",
                "commands:",
                "  lint: ruff check .",
                "build:",
                "  targets:",
                "    api:",
                "      command: go build ./...",
                "demo:",
                "  script: demo.sh",
                "activate:",
                "  source:",
                "    - .base/activate.sh",
                "artifacts: []",
            ],
        )

    @staticmethod
    def write_ready_python_bin(python_bin: Path) -> None:
        python_bin.parent.mkdir(parents=True, exist_ok=True)
        python_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        python_bin.chmod(0o755)


@pytest.fixture(name="manifest_factory")
def manifest_factory_fixture() -> ManifestFactory:
    """Return shared manifest writers for pytest-style tests."""

    return ManifestFactory()


@pytest.fixture(name="project_root")
def project_root_fixture(tmp_path: Path) -> Path:
    """Return an isolated project root for tests that need one project."""

    return tmp_path / "project"


@pytest.fixture(autouse=True)
def attach_shared_test_fixtures(request: pytest.FixtureRequest, manifest_factory: ManifestFactory) -> None:
    """Expose fixture values on legacy unittest test cases during migration."""

    instance = getattr(request.node, "instance", None)
    if instance is not None:
        instance.manifest_factory = manifest_factory
