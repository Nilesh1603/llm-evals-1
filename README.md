# llm-evals-1

A small **LLM evaluation pipeline**: a Pytest-based harness that grades
LLM outputs against a **golden set** using both deterministic rubric
checks and an **LLM-powered judge**, wired into a CI **quality gate** with
automated **regression detection** and a generated report.

The goal is a harness that's actually trustworthy, not just present: every
grading dimension is validated against known-good/known-bad fixtures, and
the judge itself is checked against human labels before it's allowed to
gate anything.

## What's actually in here

```
golden_set/          24-example golden set (6 categories x 4), + sampling rationale
harness/
  rubric_grader.py    deterministic checks: correctness, completeness,
                       hallucination/faithfulness, schema validation
  llm_judge.py         LLM-as-judge grader (live API or offline replay cache)
  runner.py             evaluation pipeline: runs both graders over the golden set
  report.py              markdown + HTML report, regression detection vs. run history
judge_alignment/     human-labeled subset + judge-vs-human agreement check
tests/                pytest suite — the CI quality gate
scripts/run_evals.py CI entrypoint (pipeline + regression gate, exit code)
.github/workflows/    GitHub Actions: runs on push, PR, and a daily schedule
reports/               generated report.md / report.html / run history
```

## Why two grading layers

Rule-based rubric checks are cheap, fast, deterministic, and dependency-light
— they run first and catch the obvious stuff (malformed JSON, missing
required content, a fabricated number that isn't in the source context).
But rubric checks are a coarse proxy for meaning: a token-overlap heuristic
can't tell you that an answer *attributes revenue growth to the wrong
business segment* if the wrong segment name still overlaps with the rest of
the sentence.

That's what the LLM-as-judge grader is for — it scores semantic
correctness against the reference answer on a 1-5 scale with a rationale.
An example **flags as failed only if both layers disagree with "pass"**
(logical AND). One real example from this golden set shows exactly why
that matters:

> `cgq_04` — the rubric's token-overlap heuristic scored this a coarse
> "pass" (most keywords matched), but the LLM judge caught that the answer
> attributed revenue growth to the *wrong business segment* — a
> factual/faithfulness error the rubric alone would have missed. The
> AND-gate is what makes this example correctly fail.

## The LLM-as-judge grader, and why it has a replay mode

`harness/llm_judge.py` calls the Anthropic or OpenAI API to grade a
candidate output against the reference answer, returned as structured JSON
(`{"score": 1-5, "rationale": "..."}`). If no API key is set, it falls back
to a **pre-recorded replay cache** (`judge_alignment/cached_judge_responses.json`)
keyed by example id.

This isn't a shortcut — it's a deliberate production pattern: a CI
pipeline that hits a paid LLM API on every push *and* a daily cron job is
both a real cost and a source of flakiness (rate limits, transient errors)
for a suite that's supposed to be a reliable quality gate. Live mode is
fully wired and works with real keys (see `.github/workflows/evals.yml`);
replay mode is what makes the harness's own test suite fast, free, and
deterministic to run in CI or on a laptop with zero setup.

## Judge-human alignment (the sanity check)

Before trusting an LLM judge to gate CI, you need evidence it agrees with
human judgment. `judge_alignment/human_labels.jsonl` hand-labels 16 of the
24 golden-set examples (spanning every category); `alignment_check.py`
compares those to the judge's scores and reports:

- **Exact agreement:** 87.5%
- **Within-one-point agreement:** 100% (this is the metric used as the
  quality-gate threshold — a 1-point wobble on a 1-5 scale is normal
  inter-rater noise, see the `cgq_03`/`sum_02` disagreements in
  `human_labels.jsonl`, which are genuine stylistic differences, not judge
  errors)
- **Pearson correlation:** 0.98

`tests/test_judge_alignment.py` runs this as an actual CI-enforced quality
gate (`ALIGNMENT_THRESHOLD = 0.85`) — if a future prompt change to the
judge tanks its human alignment, CI fails before that judge ever gates a
real run.

## Golden set

24 examples across 6 categories (factual QA, context-grounded QA,
**hallucination traps** — adversarial cases where the correct answer is
"not stated in the passage" — summarization, structured JSON extraction,
and multi-step reasoning). See `golden_set/SAMPLING_RATIONALE.md` for the
full category-by-category rationale, including what a production-scale
version of this sampling strategy would look like (stratified sampling
from real traffic, per-category confidence-interval sizing, drift
re-sampling).

`golden_set/model_outputs.jsonl` has 9 of 24 outputs with **deliberately
injected errors** (wrong facts, dropped context, hallucinated numbers, an
incomplete summary, malformed JSON, one arithmetic error) — the pytest
suite asserts the harness catches every one of them (recall) without
false-flagging the other 15 (precision). A harness that only ever sees
passing examples doesn't prove it can detect anything.

## Regression detection

`harness/report.py` compares each run against `reports/history.json` two
ways:

1. **Aggregate pass-rate delta** vs. the previous run.
2. **Per-example diff** — any golden-set id that passed last run and fails
   this run. This is the higher-signal check: an unchanged aggregate pass
   rate can hide a real regression that happens to be offset by an
   unrelated fix elsewhere; the per-example diff always catches it.

The CI workflow persists `reports/history.json` back to the repo after
each run on `main`, so the trend and regression baseline are real and
accumulate over time — not reset on every run.

## Report / dashboard

Every run generates `reports/report.md` (posted to the GitHub Actions job
summary) and `reports/report.html` — a small, dependency-free standalone
dashboard (pass-rate trend bars, category breakdown, failing-example
table) you can open directly in a browser, no server or build step needed.

## Running it

```bash
pip install -r requirements.txt

# Run the harness's own quality-gate tests (validates the grader is correct)
pytest tests/ -v

# Run the full evaluation pipeline + generate the report (what CI runs)
python scripts/run_evals.py
open reports/report.html   # or just open the file in a browser
```

No API keys required — the judge runs in replay mode by default. To run
the judge live: `export ANTHROPIC_API_KEY=...` (or `OPENAI_API_KEY`) before
running.

## CI

`.github/workflows/evals.yml` runs on every push to `main`, every pull
request, and on a daily schedule (`workflow_dispatch` too, for manual
runs). It runs the pytest quality gate, runs the eval pipeline, writes the
report to the job summary, uploads the full report as a build artifact,
and — on pushes to `main` — commits the updated `reports/history.json`
back to the repo so the regression baseline persists across runs.

## What a production version would add

This is intentionally scoped small. A production version would add: stratified sampling from production logs
instead of hand-written examples; a larger golden set sized to a target
confidence interval per category; an ensemble or multiple judge models
with disagreement-based escalation to human review; embeddings-based (not
regex-based) faithfulness checking; statistical significance testing on
pass-rate deltas rather than a flat threshold; and cost/latency tracking
alongside quality metrics.

## Known limitations

- `golden_set/model_outputs.jsonl` is a static, hand-written set of
  simulated model outputs (some deliberately wrong, for testing the
  harness's detection). The runner doesn't yet call a live target model —
  swapping in a real API call in `harness/runner.py` is the natural next
  step for evaluating an actual model rather than the harness itself.
- The rubric's faithfulness/correctness checks are regex- and
  token-overlap-based, not embedding- or NLI-based, so they're coarse
  proxies (see `cgq_04` in the failing-examples table for a case where the
  rubric alone would have passed a wrong answer — the judge caught it).
- The golden set is small (24 examples) by design for this scope; see
  `SAMPLING_RATIONALE.md` for what a larger version would look like.