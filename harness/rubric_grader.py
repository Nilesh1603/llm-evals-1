"""
Rule-based rubric grading.

These graders are deliberately simple, deterministic, and dependency-light
(no ML model calls) so they're fast, free, and reproducible — they run on
every CI push as the first line of the quality gate, before the (slower,
costlier) LLM-as-judge grader runs. This mirrors a common production
pattern: cheap deterministic checks catch the obvious regressions, an
LLM-powered judge catches the nuanced ones.

Each function returns a plain dict so results are trivially JSON-serializable
for the report/history layer.
"""
from __future__ import annotations

import json
import re
from typing import Any

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "in", "on", "at", "of",
    "to", "for", "and", "or", "but", "it", "its", "this", "that", "with",
    "as", "by", "be", "not", "stated", "passage", "according",
}


def _normalize_tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def correctness_score(reference_answer: str, model_output: str) -> dict:
    """
    Token-overlap correctness heuristic: how much of the reference answer's
    content words show up in the model output. 1.0 = full overlap.

    This is a coarse proxy (a real system would combine it with the LLM
    judge rather than rely on it alone) but it's cheap, deterministic, and
    catches the obvious case: the output doesn't contain the right answer
    at all.
    """
    ref_tokens = _normalize_tokens(reference_answer)
    out_tokens = _normalize_tokens(model_output)
    if not ref_tokens:
        score = 1.0 if not out_tokens else 0.5
    else:
        overlap = ref_tokens & out_tokens
        score = len(overlap) / len(ref_tokens)
    return {"score": round(score, 3), "ref_tokens": sorted(ref_tokens),
            "matched_tokens": sorted(ref_tokens & out_tokens)}


def completeness_score(reference_answer: str, model_output: str,
                        min_required_overlap: float = 0.6) -> dict:
    """
    Checks whether the output covers the *required* content of the
    reference answer (same token-overlap signal as correctness, but framed
    as a pass/fail against a coverage threshold — used to catch summaries
    that drop required information rather than getting facts wrong).
    """
    result = correctness_score(reference_answer, model_output)
    complete = result["score"] >= min_required_overlap
    return {**result, "complete": complete, "threshold": min_required_overlap}


def faithfulness_check(context: str | None, model_output: str,
                        expected_unstated: bool = False) -> dict:
    """
    Heuristic hallucination / faithfulness check for context-grounded
    prompts. Flags numbers and capitalized multi-word phrases that appear
    in the model output but NOT in the supplied context — these are the
    highest-signal indicators of a fabricated fact (invented statistic,
    invented name, invented phone number, etc).

    `expected_unstated=True` is used for the hallucination-trap category,
    where the correct behavior is an explicit refusal/"not stated" — in
    that case we additionally check the output actually declines to
    answer rather than confidently inventing something.
    """
    if context is None:
        return {"applicable": False, "faithful": True, "unsupported_claims": []}

    context_lower = context.lower()

    # numbers in the output not present anywhere in the context
    output_numbers = set(re.findall(r"\$?\d[\d,]*\.?\d*%?", model_output))
    unsupported_numbers = [n for n in output_numbers
                            if n.lower() not in context_lower]

    # capitalized 2+ word phrases (proxy for names/entities) not in context
    candidate_entities = re.findall(r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)\b",
                                     model_output)
    unsupported_entities = [e for e in candidate_entities
                             if e.lower() not in context_lower]

    unsupported = unsupported_numbers + unsupported_entities
    faithful = len(unsupported) == 0

    refusal_markers = ("not stated", "doesn't mention", "does not mention",
                        "not mentioned", "does not state", "doesn't state",
                        "no information", "isn't provided", "not provided",
                        "unable to determine", "not specified")
    declined = any(m in model_output.lower() for m in refusal_markers)

    result = {"applicable": True, "faithful": faithful,
              "unsupported_claims": unsupported, "declined_to_answer": declined}

    if expected_unstated:
        # correct behavior = decline; any unsupported specific claim = hallucination
        result["faithful"] = declined and not unsupported
    return result


def schema_validation(model_output: str, schema: dict[str, Any] | None) -> dict:
    """
    Validates that model_output is well-formed JSON conforming to `schema`.
    Used for the structured-output grading rubric dimension.
    """
    if schema is None:
        return {"applicable": False, "valid": True, "error": None}

    try:
        parsed = json.loads(model_output)
    except json.JSONDecodeError as e:
        return {"applicable": True, "valid": False,
                "error": f"invalid JSON: {e}"}

    if jsonschema is None:  # pragma: no cover
        return {"applicable": True, "valid": True,
                "error": "jsonschema not installed, skipped strict validation"}

    try:
        jsonschema.validate(instance=parsed, schema=schema)
    except jsonschema.ValidationError as e:
        return {"applicable": True, "valid": False, "error": str(e.message)}

    return {"applicable": True, "valid": True, "error": None}


def run_rubric(example: dict, model_output: str) -> dict:
    """Runs all applicable rubric dimensions for a single golden-set example."""
    is_trap = example["category"] == "hallucination_trap"

    correctness = correctness_score(example["reference_answer"], model_output)
    completeness = completeness_score(example["reference_answer"], model_output,
                                       min_required_overlap=0.5)
    faithfulness = faithfulness_check(example.get("context"), model_output,
                                       expected_unstated=is_trap)
    schema = schema_validation(model_output, example.get("schema")
                                if example.get("expects_schema") else None)

    if is_trap:
        # The "reference answer" for a hallucination trap is a meta-instruction
        # ("Not stated in the passage"), not real content to token-match against
        # — correctness/completeness are meaningless here. The only thing that
        # matters is whether the model fabricated an unsupported claim.
        checks = [faithfulness["faithful"]]
    else:
        checks = [completeness["complete"], faithfulness["faithful"]]
        if schema["applicable"]:
            checks.append(schema["valid"])
            # for schema tasks, correctness is judged by schema validity + judge,
            # not the coarse token-overlap heuristic (JSON key order etc. would
            # otherwise tank the score)
        else:
            checks.append(correctness["score"] >= 0.5)

    return {
        "correctness": correctness,
        "completeness": completeness,
        "faithfulness": faithfulness,
        "schema": schema,
        "rubric_pass": all(checks),
    }
