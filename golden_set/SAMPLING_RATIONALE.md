# Golden Set — Sampling & Diversity Rationale

The golden set (`golden_set.jsonl`) has **24 examples across 6 task
categories** (4 each). This is a deliberately small, evenly-stratified
sample — the goal for a portfolio-scale harness is to *demonstrate the
sampling methodology and grading logic are sound*, not to reach production
statistical power. A production version would grow each stratum to
50-200+ examples per category and add confidence intervals on pass rates.

## Why these 6 categories

Each category exists to exercise a **different failure mode** of an LLM
pipeline, mirroring the kinds of regressions that actually show up in
production evals work:

| Category | What it stresses | Why it's in the set |
|---|---|---|
| `factual_qa` | Closed-book correctness | Baseline sanity check — no context to hide behind, easy to grade, catches raw model regressions (e.g. a cheaper model swap getting facts wrong). |
| `context_grounded_qa` | Faithfulness when the answer *is* in context | Tests that the model actually reads and reports the provided context correctly, rather than pattern-matching from parametric memory. |
| `hallucination_trap` | Faithfulness when the answer is *not* in context | The highest-signal category for eval work. Correct behavior is refusal / "not stated" — any confident, specific-sounding answer here is a hallucination by construction. These are adversarially designed so a naive "does the output sound plausible" grader would pass them and only a real faithfulness check catches the failure. |
| `summarization` | Completeness + faithfulness together | Summaries can fail two independent ways — dropping required information (incomplete) or adding information not present (unfaithful) — so this category is graded on both axes. |
| `structured_extraction` | Schema/format correctness | LLM pipelines that feed downstream systems (search, agents, tool calls) live or die on valid structured output. Includes a deliberately malformed-JSON case to prove the schema grader actually fails bad output instead of rubber-stamping it. |
| `reasoning_math` | Multi-step correctness | Simple enough to hand-verify exactly (no grading ambiguity), which makes it a good control group for validating the LLM-judge's alignment with ground truth on unambiguous cases. |

## Difficulty spread

Each category mixes `easy` / `medium` / `hard` items rather than uniform
difficulty, so the pass-rate isn't trivially 100% or 0% — a flat score in
either direction is itself a signal that the golden set needs rebalancing.

## Deliberately injected failures

`model_outputs.jsonl` contains simulated outputs from the "system under
test" with **8 of 24 (33%) intentionally wrong or malformed**, spread
across every category (wrong facts, dropped context, hallucinated numbers,
incomplete summaries, malformed JSON, an arithmetic error). This is
intentional: an eval harness that only ever sees passing examples doesn't
prove anything about its detection power. The known failures let
`tests/test_eval_pipeline.py` assert the harness's *recall* — i.e. that it
actually flags the failures it's supposed to, not just that it runs.

## What a production version would add

- Stratified sampling from real production traffic/logs instead of
  hand-written examples, so the distribution matches actual usage.
- Per-category minimum sample sizes based on desired confidence interval
  width on the pass rate (e.g. ~200+ examples/category for a ±5% CI at the
  95% level).
- Periodic re-sampling to catch distribution drift as usage patterns change.
- De-duplication / near-duplicate detection so the set doesn't overweight
  one phrasing.
