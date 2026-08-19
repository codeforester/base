from pathlib import Path


def test_project_root_fixture_is_isolated(project_root: Path) -> None:
    assert project_root.name == "project"
    assert not project_root.exists()


def test_manifest_factory_writes_standard_manifest(project_root: Path, manifest_factory) -> None:
    manifest_path = manifest_factory.write(project_root)

    assert manifest_path == project_root / "base_manifest.yaml"
    assert manifest_path.read_text(encoding="utf-8") == (
        "project:\n  name: demo\ntest:\n  command: pytest tests/\nartifacts: []\n"
    )


def test_manifest_factory_writes_command_surfaces(project_root: Path, manifest_factory) -> None:
    manifest_path = manifest_factory.write_command_surfaces(project_root)

    manifest = manifest_path.read_text(encoding="utf-8")
    assert "commands:" in manifest
    assert "build:" in manifest
    assert "demo:" in manifest
    assert "activate:" in manifest


def test_manifest_factory_writes_pull_request_policy(project_root: Path, manifest_factory) -> None:
    manifest_path = manifest_factory.write_pr_policy(project_root)

    assert manifest_path.read_text(encoding="utf-8") == (
        "project:\n  name: demo\ngithub:\n  pr:\n    required_sections:\n      default: [Summary]\n"
    )


def test_manifest_factory_writes_release_project(project_root: Path, manifest_factory) -> None:
    manifest_path = manifest_factory.write_release(project_root)

    assert manifest_path == project_root / "base_manifest.yaml"
    assert (project_root / "VERSION").read_text(encoding="utf-8") == "1.2.3\n"
    assert (project_root / "CHANGELOG.md").is_file()
    assert (project_root / ".git").is_dir()
