"""
LLM-as-judge grader.

Design note on the replay/cache mode: hitting a paid LLM API on every CI
run (every push, plus a daily schedule) is both a real cost and a source of
flakiness (rate limits, transient API errors) for a portfolio CI pipeline
that should "just work" for anyone who clones the repo without API keys.

So the judge supports two modes, selected automatically:

  * LIVE mode — used when ANTHROPIC_API_KEY or OPENAI_API_KEY is set in the
    environment. Makes a real API call and asks the model to score the
    candidate output against the reference answer, returned as structured
    JSON (score 1-5 + rationale).

  * REPLAY mode — used otherwise (e.g. a fork's CI with no secrets, or a
    reviewer running `pytest` locally with no keys configured). Looks up a
    pre-recorded judge response from judge_alignment/cached_judge_responses.json
    keyed by example id. This is the *same* mechanism you'd use in
    production to make a judge grader's test suite deterministic and to
    avoid burning API budget on every CI run of the harness's own tests.

Both modes return the same JudgeResult shape, so callers (runner.py,
tests) don't need to know which mode ran.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path

CACHE_PATH = Path(__file__).parent.parent / "judge_alignment" / "cached_judge_responses.json"

JUDGE_PROMPT_TEMPLATE = """You are grading an AI model's answer against a reference answer.

Question: {prompt}
{context_block}
Reference answer: {reference_answer}
Model's answer: {model_output}

Score the model's answer from 1-5 on how well it matches the reference answer
in meaning and correctness (5 = fully correct and equivalent, 1 = wrong or
contradicts the reference). Penalize confident claims that aren't supported
by the question's context, if any was given.

Respond ONLY with JSON: {{"score": <1-5 integer>, "rationale": "<one sentence>"}}
"""


@dataclass
class JudgeResult:
    example_id: str
    score: int
    rationale: str
    mode: str  # "live" or "replay"


def _build_prompt(example: dict, model_output: str) -> str:
    context_block = f"Context: {example['context']}\n" if example.get("context") else ""
    return JUDGE_PROMPT_TEMPLATE.format(
        prompt=example["prompt"],
        context_block=context_block,
        reference_answer=example["reference_answer"],
        model_output=model_output,
    )


def _parse_judge_json(raw_text: str) -> tuple[int, str]:
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        raise ValueError(f"judge did not return parseable JSON: {raw_text!r}")
    data = json.loads(match.group(0))
    return int(data["score"]), str(data["rationale"])


def _call_anthropic(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if hasattr(block, "text"))


def _call_openai(prompt: str) -> str:
    import openai
    client = openai.OpenAI()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def judge_response(example: dict, model_output: str) -> JudgeResult:
    """
    Grades a single model output against its golden-set reference answer.
    Automatically picks live vs. replay mode based on available API keys.
    """
    has_anthropic_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_openai_key = bool(os.environ.get("OPENAI_API_KEY"))

    if has_anthropic_key or has_openai_key:
        prompt = _build_prompt(example, model_output)
        try:
            raw = _call_anthropic(prompt) if has_anthropic_key else _call_openai(prompt)
            score, rationale = _parse_judge_json(raw)
            return JudgeResult(example["id"], score, rationale, mode="live")
        except Exception as e:  # noqa: BLE001 — fall back rather than fail the run
            cache = _load_cache()
            if example["id"] in cache:
                cached = cache[example["id"]]
                return JudgeResult(example["id"], cached["score"],
                                    cached["rationale"] + f" [live call failed: {e}, used cache]",
                                    mode="replay")
            raise

    cache = _load_cache()
    if example["id"] not in cache:
        raise KeyError(
            f"No cached judge response for '{example['id']}' and no API key set. "
            f"Set ANTHROPIC_API_KEY/OPENAI_API_KEY, or add an entry to "
            f"{CACHE_PATH.relative_to(Path.cwd()) if CACHE_PATH.is_absolute() else CACHE_PATH}."
        )
    cached = cache[example["id"]]
    return JudgeResult(example["id"], cached["score"], cached["rationale"], mode="replay")


def judge_result_to_dict(result: JudgeResult) -> dict:
    return asdict(result)
