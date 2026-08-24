from __future__ import annotations

import json

from tests import coverage_gate


def write_report(tmp_path, *, statements: float, branches: float, combined: float):
    report_path = tmp_path / "coverage.json"
    report_path.write_text(
        json.dumps(
            {
                "totals": {
                    "percent_statements_covered": statements,
                    "percent_branches_covered": branches,
                    "percent_covered": combined,
                }
            }
        ),
        encoding="utf-8",
    )
    return report_path


def test_coverage_gate_reports_each_metric_separately(tmp_path, capsys) -> None:
    report_path = write_report(
        tmp_path,
        statements=87.51,
        branches=76.99,
        combined=84.94,
    )

    assert coverage_gate.main([str(report_path)]) == 0

    output = capsys.readouterr().out
    assert "Statements: 87.51% (minimum 85.00%) PASS" in output
    assert "Branches: 76.99% (minimum 76.00%) PASS" in output
    assert "Combined: 84.94% (minimum 84.00%) PASS" in output


def test_coverage_gate_fails_with_actionable_metric_output(tmp_path, capsys) -> None:
    report_path = write_report(
        tmp_path,
        statements=84.99,
        branches=75.99,
        combined=83.99,
    )

    assert coverage_gate.main([str(report_path)]) == 1

    captured = capsys.readouterr()
    assert "Statements: 84.99% (minimum 85.00%) FAIL" in captured.out
    assert "Branches: 75.99% (minimum 76.00%) FAIL" in captured.out
    assert "Combined: 83.99% (minimum 84.00%) FAIL" in captured.out
    assert "Coverage ratchet failed for: statements, branches, combined" in captured.err


def test_coverage_gate_rejects_incomplete_coverage_json(tmp_path, capsys) -> None:
    report_path = tmp_path / "coverage.json"
    report_path.write_text('{"totals": {}}', encoding="utf-8")

    assert coverage_gate.main([str(report_path)]) == 2

    assert "missing numeric totals" in capsys.readouterr().err
