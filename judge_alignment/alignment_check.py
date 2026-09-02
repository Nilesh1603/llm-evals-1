"""
Human-alignment sanity check for the LLM-as-judge grader.

Before trusting an LLM judge to gate CI, you need evidence it actually
agrees with human judgment — otherwise you've just automated a random
number generator with a rubric-shaped prompt. This module loads a small
hand-labeled set (`human_labels.jsonl`, 16 of the 24 golden-set examples,
chosen to span every category) and compares each human label to the
judge's score for the same example (via `harness.llm_judge`, which uses
the recorded replay cache unless live API keys are set — see llm_judge.py
for why).

Two agreement metrics are reported:
  * exact_agreement   — judge score == human score
  * within_one_agreement — |judge score - human score| <= 1

`within_one` is the metric actually used as the quality gate threshold,
since a 1-point wobble on a 1-5 scale is normal inter-rater noise (see the
cgq_03 / sum_02 examples in human_labels.jsonl, which are genuine stylistic
disagreements, not judge errors).
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import correlation

from harness.llm_judge import judge_response

HERE = Path(__file__).parent
GOLDEN_SET_PATH = HERE.parent / "golden_set" / "golden_set.jsonl"
MODEL_OUTPUTS_PATH = HERE.parent / "golden_set" / "model_outputs.jsonl"
HUMAN_LABELS_PATH = HERE / "human_labels.jsonl"

# Minimum acceptable within-one-point agreement rate for the judge to be
# considered trustworthy enough to gate CI. Documented, not arbitrary:
# below this the judge is too noisy to distinguish real regressions from
# grading jitter.
ALIGNMENT_THRESHOLD = 0.85


def _load_jsonl(path: Path) -> list[dict]:
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def run_alignment_check() -> dict:
    golden_by_id = {row["id"]: row for row in _load_jsonl(GOLDEN_SET_PATH)}
    outputs_by_id = {row["id"]: row["model_output"]
                      for row in _load_jsonl(MODEL_OUTPUTS_PATH)}
    human_labels = _load_jsonl(HUMAN_LABELS_PATH)

    rows = []
    for label in human_labels:
        ex_id = label["id"]
        example = golden_by_id[ex_id]
        model_output = outputs_by_id[ex_id]
        judge = judge_response(example, model_output)
        rows.append({
            "id": ex_id,
            "human_score": label["human_score"],
            "judge_score": judge.score,
            "diff": abs(judge.score - label["human_score"]),
        })

    n = len(rows)
    exact_matches = sum(1 for r in rows if r["diff"] == 0)
    within_one = sum(1 for r in rows if r["diff"] <= 1)
    human_scores = [r["human_score"] for r in rows]
    judge_scores = [r["judge_score"] for r in rows]

    try:
        pearson_r = correlation(human_scores, judge_scores)
    except Exception:
        pearson_r = None

    return {
        "n_examples": n,
        "exact_agreement": round(exact_matches / n, 3),
        "within_one_agreement": round(within_one / n, 3),
        "pearson_r": round(pearson_r, 3) if pearson_r is not None else None,
        "threshold": ALIGNMENT_THRESHOLD,
        "passes_threshold": (within_one / n) >= ALIGNMENT_THRESHOLD,
        "rows": rows,
    }


if __name__ == "__main__":
    result = run_alignment_check()
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
    for row in result["rows"]:
        flag = "  " if row["diff"] <= 1 else "⚠️ "
        print(f"{flag}{row['id']:>8}  human={row['human_score']}  "
              f"judge={row['judge_score']}  diff={row['diff']}")
