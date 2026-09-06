from __future__ import annotations

import copy
import json
from pathlib import Path

from tests import stability_compatibility as compatibility


REPO_ROOT = Path(__file__).resolve().parents[1]
CURRENT_FIXTURE = REPO_ROOT / "docs" / "stability-baseline" / "current.json"
INITIAL_FIXTURE = REPO_ROOT / "docs" / "stability-baseline" / "v1.8.0.json"


def load_fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_current_fixture_matches_the_repository_contract() -> None:
    assert not compatibility.run_check(REPO_ROOT)


def test_runtime_diagnostic_output_matches_the_published_contract() -> None:
    reference = load_fixture(CURRENT_FIXTURE)["json_contracts"]["diagnostic-v1"]
    observed = compatibility.runtime_contracts(REPO_ROOT)["diagnostic-v1"]
    errors: list[str] = []

    compatibility.validate_runtime_shape(reference, observed, "runtime.diagnostic-v1", errors, reference)

    assert not errors


def test_fixtures_retain_v1_8_provenance() -> None:
    assert load_fixture(CURRENT_FIXTURE)["baseline_version"] == "1.8.0"
    assert load_fixture(INITIAL_FIXTURE)["baseline_version"] == "1.8.0"


def test_additive_contract_changes_are_compatible() -> None:
    reference = load_fixture(CURRENT_FIXTURE)
    actual = copy.deepcopy(reference)
    actual["commands"]["basectl synthetic"] = {"flags": {"--new": {"takes_value": False}}}
    actual["findings"]["BASE-X999"] = "New finding"
    actual["json_contracts"]["inspection-v1"]["properties"]["new_key"] = {"type": "string"}

    assert not compatibility.compare_snapshots(reference, actual)


def test_removed_flag_is_breaking() -> None:
    reference = load_fixture(CURRENT_FIXTURE)
    actual = copy.deepcopy(reference)
    del actual["commands"]["basectl check [project]"]["flags"]["--format"]

    errors = compatibility.compare_snapshots(reference, actual)

    assert any("removed stable option '--format'" in error for error in errors)


def test_enum_removal_and_type_change_are_breaking() -> None:
    reference = load_fixture(CURRENT_FIXTURE)
    actual = copy.deepcopy(reference)
    actual["commands"]["basectl check [project]"]["flags"]["--format"]["enum"].remove("json")
    actual["json_contracts"]["inspection-v1"]["properties"]["data"]["type"] = "array"

    errors = compatibility.compare_snapshots(reference, actual)

    assert any("removed enum values ['json']" in error for error in errors)
    assert any("json_contracts.inspection-v1.data.type" in error for error in errors)


def test_finding_id_reuse_is_breaking() -> None:
    reference = load_fixture(CURRENT_FIXTURE)
    actual = copy.deepcopy(reference)
    actual["findings"]["BASE-D001"] = "A different diagnostic"

    errors = compatibility.compare_snapshots(reference, actual)

    assert any("reused or changed meaning for BASE-D001" in error for error in errors)


def test_schema_field_removal_is_breaking() -> None:
    reference = load_fixture(CURRENT_FIXTURE)
    actual = copy.deepcopy(reference)
    del actual["schemas"]["workspace-update.json"]["properties"]["counts"]

    errors = compatibility.compare_snapshots(reference, actual)

    assert any("schemas.workspace-update.json.properties" in error for error in errors)


def test_fixture_update_requires_changelog_marker(monkeypatch, tmp_path: Path) -> None:
    diffs = {
        "docs/stability-baseline/current.json": "diff --git ...",
        "CHANGELOG.md": "+- Other change\n",
    }
    monkeypatch.setattr(compatibility, "_git_diff", lambda _root, _base, path: diffs[path])

    errors = compatibility.require_changelog_for_fixture_change(tmp_path, "base")

    assert errors and "Stability compatibility:" in errors[0]


def test_fixture_update_accepts_changelog_marker(monkeypatch, tmp_path: Path) -> None:
    diffs = {
        "docs/stability-baseline/current.json": "diff --git ...",
        "CHANGELOG.md": "+- Stability compatibility: document the migration.\n",
    }
    monkeypatch.setattr(compatibility, "_git_diff", lambda _root, _base, path: diffs[path])

    assert not compatibility.require_changelog_for_fixture_change(tmp_path, "base")
