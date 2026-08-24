"""Enforce Base's separate Python coverage ratchets from coverage.py JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


METRICS = (
    ("statements", "Statements", "percent_statements_covered", 85.0),
    ("branches", "Branches", "percent_branches_covered", 76.0),
    ("combined", "Combined", "percent_covered", 84.0),
)


class CoverageReportError(ValueError):
    """Raised when a coverage report cannot provide the required metrics."""


def load_percentages(report_path: Path) -> dict[str, float]:
    """Load the separate statement, branch, and combined percentages."""
    try:
        payload: Any = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoverageReportError(f"cannot read coverage report {report_path}: {exc}") from exc

    totals = payload.get("totals") if isinstance(payload, dict) else None
    if not isinstance(totals, dict):
        raise CoverageReportError("coverage report is missing numeric totals")

    percentages: dict[str, float] = {}
    missing: list[str] = []
    for metric, _label, json_key, _floor in METRICS:
        value = totals.get(json_key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            missing.append(json_key)
            continue
        percentages[metric] = float(value)

    if missing:
        raise CoverageReportError(
            "coverage report is missing numeric totals: " + ", ".join(missing)
        )
    return percentages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="coverage.py JSON report")
    options = parser.parse_args(argv)

    try:
        percentages = load_percentages(options.report)
    except CoverageReportError as exc:
        print(f"Coverage report error: {exc}", file=sys.stderr)
        return 2

    failed: list[str] = []
    for metric, label, _json_key, floor in METRICS:
        percentage = percentages[metric]
        result = "PASS" if percentage >= floor else "FAIL"
        print(f"{label}: {percentage:.2f}% (minimum {floor:.2f}%) {result}")
        if percentage < floor:
            failed.append(metric)

    if failed:
        print(
            "Coverage ratchet failed for: " + ", ".join(failed),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
