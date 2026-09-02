"""
Quality-gate tests for the eval harness.

These tests validate the *harness's grading power*, not the target model —
i.e. they prove the pipeline correctly distinguishes the 9 deliberately
injected bad outputs from the 15 good ones in golden_set/model_outputs.jsonl
(see golden_set/SAMPLING_RATIONALE.md for why the set is seeded this way).
That's what makes this a real regression-detection tool rather than a
harness that just always reports "pass" — a harness with zero recall on
known failures would be worse than no harness at all.

This file is what CI runs on every push. It should stay green: it is
checking the *grader's* correctness, which doesn't change unless someone
edits the harness or the golden set.
"""
from harness.runner import evaluate_example

# The 9 examples with deliberately injected errors (wrong facts, dropped
# context, hallucinated numbers, incomplete summary, malformed JSON, and
# one arithmetic error) — see golden_set/generate_golden_set.py.
KNOWN_BAD_IDS = {
    "fqa_03", "fqa_04", "cgq_04", "hal_02", "hal_04",
    "sum_02", "sum_03", "ext_03", "math_02",
}


def test_golden_set_and_outputs_are_aligned(golden_set, model_outputs):
    """Every golden-set example has a corresponding model output and vice versa."""
    golden_ids = {ex["id"] for ex in golden_set}
    output_ids = set(model_outputs.keys())
    assert golden_ids == output_ids


def test_harness_flags_all_known_bad_outputs(golden_by_id, model_outputs):
    """
    Recall check: the harness must flag every example with an injected
    error. A miss here means a real regression could slip through CI
    undetected — this is the test that matters most for trusting the gate.
    """
    misses = []
    for ex_id in KNOWN_BAD_IDS:
        result = evaluate_example(golden_by_id[ex_id], model_outputs[ex_id])
        if result["overall_pass"]:
            misses.append(ex_id)
    assert not misses, f"Harness failed to flag known-bad outputs: {misses}"


def test_harness_does_not_flag_known_good_outputs(golden_by_id, model_outputs):
    """
    Precision check: the harness must NOT flag the 15 correct outputs.
    A harness with lots of false positives is just as useless as one with
    no recall — nobody trusts (or keeps) a quality gate that cries wolf.
    """
    good_ids = set(golden_by_id) - KNOWN_BAD_IDS
    false_positives = []
    for ex_id in good_ids:
        result = evaluate_example(golden_by_id[ex_id], model_outputs[ex_id])
        if not result["overall_pass"]:
            false_positives.append(ex_id)
    assert not false_positives, f"Harness false-flagged good outputs: {false_positives}"


def test_schema_grader_rejects_malformed_json(golden_by_id, model_outputs):
    """Targeted check on the structured-output dimension specifically."""
    result = evaluate_example(golden_by_id["ext_03"], model_outputs["ext_03"])
    assert result["rubric"]["schema"]["applicable"] is True
    assert result["rubric"]["schema"]["valid"] is False


def test_faithfulness_grader_catches_hallucinated_numbers(golden_by_id, model_outputs):
    """Targeted check on the hallucination/faithfulness dimension specifically."""
    result = evaluate_example(golden_by_id["hal_02"], model_outputs["hal_02"])
    assert result["rubric"]["faithfulness"]["faithful"] is False


def test_faithfulness_grader_accepts_correct_refusal(golden_by_id, model_outputs):
    """The flip side: declining to answer when the context doesn't say should PASS."""
    result = evaluate_example(golden_by_id["hal_01"], model_outputs["hal_01"])
    assert result["rubric"]["faithfulness"]["faithful"] is True


def test_full_pipeline_run_matches_expected_pass_rate(golden_set, model_outputs):
    """
    End-to-end sanity check on the whole golden set at once (rather than
    per-example), pinned to the known pass rate given the fixed
    model_outputs.jsonl fixture. If this drifts, either the fixture data
    changed or the harness's grading logic changed — both worth a second
    look before merging.
    """
    from harness.rubric_grader import run_rubric
    from harness.llm_judge import judge_response

    passed = 0
    for ex in golden_set:
        output = model_outputs[ex["id"]]
        rubric = run_rubric(ex, output)
        judge = judge_response(ex, output)
        if rubric["rubric_pass"] and judge.score >= 3:
            passed += 1

    assert passed == len(golden_set) - len(KNOWN_BAD_IDS)
