"""
Human-alignment quality gate for the LLM-as-judge grader itself.

This is the test that answers "how do you know the judge is any good?" —
a question every eval-engineer role will ask in interview. It runs the
judge against the 16-example hand-labeled subset in
judge_alignment/human_labels.jsonl and asserts within-one-point agreement
meets the documented threshold (see judge_alignment/alignment_check.py for
the full rationale).

If this test starts failing after a prompt change to the judge, that's a
real signal: don't ship a judge prompt change without re-validating
alignment, the same way you wouldn't ship a rubric change without
re-running it against known-good/known-bad fixtures.
"""
from judge_alignment.alignment_check import run_alignment_check, ALIGNMENT_THRESHOLD


def test_judge_meets_human_alignment_threshold():
    result = run_alignment_check()
    assert result["n_examples"] >= 15, "Alignment set should cover a meaningful sample"
    assert result["within_one_agreement"] >= ALIGNMENT_THRESHOLD, (
        f"Judge only agreed with humans (within 1 point) on "
        f"{result['within_one_agreement']:.0%} of examples, below the "
        f"{ALIGNMENT_THRESHOLD:.0%} threshold — do not trust this judge to "
        f"gate CI until re-aligned."
    )


def test_judge_alignment_covers_every_category(golden_by_id):
    """The hand-labeled subset should span every task category, not just the easy ones."""
    import json
    from pathlib import Path

    labels_path = Path(__file__).parent.parent / "judge_alignment" / "human_labels.jsonl"
    labeled_ids = [json.loads(l)["id"] for l in labels_path.read_text().splitlines() if l.strip()]
    labeled_categories = {golden_by_id[i]["category"] for i in labeled_ids}
    all_categories = {ex["category"] for ex in golden_by_id.values()}
    assert labeled_categories == all_categories, (
        f"Human-labeled alignment set is missing categories: "
        f"{all_categories - labeled_categories}"
    )
