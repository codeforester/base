from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OBSERVABILITY_DOC = REPO_ROOT / "docs" / "observability.md"


def implementation_split_section() -> str:
    text = OBSERVABILITY_DOC.read_text(encoding="utf-8")
    start = text.index("## Implementation Split")
    end = text.index("## First Slice Decisions")
    return text[start:end]


def test_unscheduled_observability_work_is_not_numbered_as_active_steps() -> None:
    section = implementation_split_section()

    assert "Unscheduled Future Work" in section
    assert "2. Add `basectl explain last-error`" not in section
    assert "3. Add `basectl report`" not in section
    assert "4. Extend `basectl clean`" not in section


def test_cleanup_docs_define_the_symlink_containment_boundary() -> None:
    observability = OBSERVABILITY_DOC.read_text(encoding="utf-8")
    cache_layout = (REPO_ROOT / "docs" / "cache-ownership-and-layout.md").read_text(
        encoding="utf-8"
    )
    commands = (REPO_ROOT / ".ai-context" / "COMMANDS.md").read_text(encoding="utf-8")

    assert "rejects symlinked" in observability
    assert "relative to trusted directory descriptors" in observability
    assert "Cleanup rejects symlinks below the resolved" in cache_layout
    assert "never follows them during deletion" in " ".join(commands.split())


def test_run_bundle_docs_define_inherited_context_validation() -> None:
    observability = OBSERVABILITY_DOC.read_text(encoding="utf-8")
    cache_layout = (REPO_ROOT / "docs" / "cache-ownership-and-layout.md").read_text(
        encoding="utf-8"
    )
    runtime_environment = (REPO_ROOT / "docs" / "runtime-environment.md").read_text(
        encoding="utf-8"
    )
    architecture = (REPO_ROOT / ".ai-context" / "ARCHITECTURE.md").read_text(
        encoding="utf-8"
    )

    assert "The same boundary is checked again before finalization" in observability
    assert "Arbitrary, symlinked," in cache_layout
    assert "Invalid inherited state is scrubbed" in runtime_environment
    assert "Run-bundle propagation is an internal capability" in architecture
