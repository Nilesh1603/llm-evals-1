"""
Evaluation pipeline runner.

Loads the golden set + the model outputs to be graded, runs both grading
layers (rule-based rubric + LLM-as-judge) per example, and writes a
structured run result to reports/latest_run.json for the reporting layer
to pick up.

This is the piece that turns "a pytest file that checks some strings" into
"an evaluation pipeline" — it's runnable standalone (`python -m
harness.runner`) or from CI (see scripts/run_evals.py), independent of
whether pytest is what's driving it.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from harness.rubric_grader import run_rubric
from harness.llm_judge import judge_response, judge_result_to_dict

ROOT = Path(__file__).parent.parent
GOLDEN_SET_PATH = ROOT / "golden_set" / "golden_set.jsonl"
MODEL_OUTPUTS_PATH = ROOT / "golden_set" / "model_outputs.jsonl"
LATEST_RUN_PATH = ROOT / "reports" / "latest_run.json"

# An example passes overall only if BOTH grading layers agree it's good.
# This is deliberate: the rubric alone can be fooled by keyword overlap,
# and the judge alone can be inconsistent — requiring both to agree is a
# stricter, more defensible quality gate than either one in isolation.
JUDGE_PASS_THRESHOLD = 3  # out of 5


def _load_jsonl(path: Path) -> list[dict]:
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def _git_sha() -> str:
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return sha[:8]
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=ROOT, capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "local"


def evaluate_example(example: dict, model_output: str) -> dict:
    rubric = run_rubric(example, model_output)
    judge = judge_response(example, model_output)
    judge_pass = judge.score >= JUDGE_PASS_THRESHOLD
    return {
        "id": example["id"],
        "category": example["category"],
        "difficulty": example["difficulty"],
        "prompt": example["prompt"],
        "model_output": model_output,
        "rubric": rubric,
        "judge": judge_result_to_dict(judge),
        "rubric_pass": rubric["rubric_pass"],
        "judge_pass": judge_pass,
        "overall_pass": rubric["rubric_pass"] and judge_pass,
    }


def run_all() -> dict:
    golden_set = _load_jsonl(GOLDEN_SET_PATH)
    outputs_by_id = {row["id"]: row["model_output"]
                      for row in _load_jsonl(MODEL_OUTPUTS_PATH)}

    results = [evaluate_example(ex, outputs_by_id[ex["id"]]) for ex in golden_set]

    total = len(results)
    passed = sum(1 for r in results if r["overall_pass"])
    failed_ids = [r["id"] for r in results if not r["overall_pass"]]

    categories = sorted({r["category"] for r in results})
    category_breakdown = {}
    for cat in categories:
        cat_results = [r for r in results if r["category"] == cat]
        cat_passed = sum(1 for r in cat_results if r["overall_pass"])
        category_breakdown[cat] = {
            "total": len(cat_results),
            "passed": cat_passed,
            "pass_rate": round(cat_passed / len(cat_results), 3),
        }

    summary = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "failed_ids": failed_ids,
        "category_breakdown": category_breakdown,
        "results": results,
    }

    LATEST_RUN_PATH.parent.mkdir(parents=True, exist_ok=True)
    LATEST_RUN_PATH.write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    summary = run_all()
    print(f"Ran {summary['total']} examples — {summary['passed']} passed "
          f"({summary['pass_rate']:.1%})")
    if summary["failed_ids"]:
        print("Failed:", ", ".join(summary["failed_ids"]))
