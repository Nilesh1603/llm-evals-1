#!/usr/bin/env python3
"""
CI entrypoint: runs the full evaluation pipeline, generates the report, and
exits non-zero if the regression-detection quality gate fails.

Usage:
    python scripts/run_evals.py

This is deliberately separate from `pytest`: pytest (tests/) validates that
the *harness itself* grades correctly (recall/precision on known
good/bad outputs, judge-human alignment) and should always stay green.
This script runs the harness against the *current* model outputs and is
the piece that can legitimately fail when a real regression is introduced
— the bridge from "test automation" to "eval infrastructure."
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from harness.runner import run_all
from harness.report import generate_report


def main() -> int:
    print("Running evaluation pipeline against golden set...")
    summary = run_all()
    print(f"  {summary['passed']}/{summary['total']} passed "
          f"({summary['pass_rate']:.1%})")

    print("Generating report + checking for regressions...")
    result = generate_report()
    regressions = result["regressions"]

    if regressions["has_previous_run"]:
        print(f"  Pass-rate delta vs. previous run: "
              f"{regressions['pass_rate_delta']:+.1%}")
        if regressions["newly_failing"]:
            print(f"  Newly failing: {', '.join(regressions['newly_failing'])}")

    if regressions["regression_gate_failed"]:
        print("\n QUALITY GATE FAILED — regression(s) detected. See reports/report.md")
        return 1

    print("\n Quality gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
