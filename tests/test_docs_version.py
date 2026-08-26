import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = REPO_ROOT / "VERSION"
DEVELOPMENT_VERSION_FILE = REPO_ROOT / "DEVELOPMENT_VERSION"

CURRENT_VERSION_REFERENCES = (
    (
        REPO_ROOT / "README.md",
        r"!\[Version\]\(https://img\.shields\.io/badge/version-([0-9]+\.[0-9]+\.[0-9]+)-blue\)",
    ),
    (
        REPO_ROOT / "README.md",
        r"Base `([0-9]+\.[0-9]+\.[0-9]+)` is the current release\.",
    ),
    (
        REPO_ROOT / "docs" / "technical-overview.md",
        r"Base \*\*([0-9]+\.[0-9]+\.[0-9]+)\*\* \([^)]+\) covers:",
    ),
)


def test_current_version_references_match_version_file() -> None:
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    mismatches: list[str] = []

    for path, pattern in CURRENT_VERSION_REFERENCES:
        text = path.read_text(encoding="utf-8")
        match = re.search(pattern, text)
        if match is None:
            mismatches.append(f"{path.relative_to(REPO_ROOT)}: missing guarded current-version reference")
            continue
        documented_version = match.group(1)
        if documented_version != version:
            mismatches.append(
                f"{path.relative_to(REPO_ROOT)}: expected current version {version}, found {documented_version}"
            )

    assert not mismatches, "\n".join(mismatches)


def test_development_version_contract_and_stable_installer_ref_are_documented() -> None:
    release_version = VERSION_FILE.read_text(encoding="utf-8").strip()
    development_version = DEVELOPMENT_VERSION_FILE.read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", development_version)
    assert development_version != release_version

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    release_docs = (REPO_ROOT / "docs" / "release-process.md").read_text(encoding="utf-8")
    stable_ref = f"v{release_version}"
    assert f"raw.githubusercontent.com/basefoundry/base/{stable_ref}/install.sh" in readme
    assert f"--branch {stable_ref}" in readme
    assert "DEVELOPMENT_VERSION-dev+g<short-sha>" in readme
    assert "DEVELOPMENT_VERSION-dev+g<short-sha>" in release_docs
