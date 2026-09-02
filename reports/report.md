# Eval Run Report — `20260902T195107Z`

- **Commit:** `local`
- **Pass rate:** 15/24 (62.5%)
- **Change vs. previous run:** +0.0%

## Regression detection

**Quality gate: passed** 🟢 — no new regressions vs. previous run.

## Category breakdown

| Category | Passed | Total | Pass rate |
|---|---|---|---|
| context_grounded_qa | 3 | 4 | 75.0% |
| factual_qa | 2 | 4 | 50.0% |
| hallucination_trap | 2 | 4 | 50.0% |
| reasoning_math | 3 | 4 | 75.0% |
| structured_extraction | 3 | 4 | 75.0% |
| summarization | 2 | 4 | 50.0% |

## Failing examples

- **`fqa_03`** (factual_qa) — rubric_pass=False, judge_score=1/5 — Wrong year (1991) — reference is 1989.
- **`fqa_04`** (factual_qa) — rubric_pass=False, judge_score=1/5 — Wrong symbol (Tu) — tungsten's symbol is W.
- **`cgq_04`** (context_grounded_qa) — rubric_pass=True, judge_score=1/5 — Attributes growth to the consumer segment; context says enterprise segment.
- **`hal_02`** (hallucination_trap) — rubric_pass=False, judge_score=1/5 — Invents a specific net income figure not present in the context.
- **`hal_04`** (hallucination_trap) — rubric_pass=False, judge_score=1/5 — Invents a phone number not present in the context.
- **`sum_02`** (summarization) — rubric_pass=False, judge_score=4/5 — Faithful and complete, slightly looser phrasing than the reference.
- **`sum_03`** (summarization) — rubric_pass=False, judge_score=2/5 — Drops the hardware-division loss and layoffs, a material omission.
- **`ext_03`** (structured_extraction) — rubric_pass=False, judge_score=1/5 — Output is not valid JSON (unquoted keys/values, string total).
- **`math_02`** (reasoning_math) — rubric_pass=False, judge_score=1/5 — Incorrect arithmetic — correct final price is $27, not $28.

## Pass-rate trend (last runs)

| Run | Commit | Pass rate |
|---|---|---|
| 20260828T091500Z | `a1b2c3d4` | 54.2% |
| 20260830T142200Z | `e5f6a7b8` | 62.5% |
| 20260902T195107Z | `local` | 62.5% |
