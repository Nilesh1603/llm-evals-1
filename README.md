# LLM Evaluation Harness & Continuous Quality Gate

An automated, Pytest-driven **evaluation pipeline** designed to score Large Language Model (LLM) outputs against a curated **golden set**. Built to bridge traditional test automation (CI/CD, API testing) with probabilistic AI evaluation, providing enterprise-grade **regression detection** and continuous model benchmarking.

---

## Key Features & Architecture

- **LLM-Powered Judge (`src/judge.py`)**: Leverages `gpt-4o-mini` with Pydantic structured outputs to evaluate target model responses for factual correctness, completeness, and hallucination risks on a strict 1–5 rubric.
- **Curated Golden Dataset (`data/golden_dataset.json`)**: Hand-crafted 15+ example dataset focusing on high-risk domains (public health, medical advice, structured emergency metrics) where hallucination prevention is critical.
- **Dual Quality Gate**:
  - *Deterministic Gate*: Validates strict JSON/schema structures using standard parsing assertions.
  - *Probabilistic Gate*: Asserts that LLM-as-a-Judge alignment scores meet minimum quality thresholds (Score $\ge 4/5$, zero hallucination tolerance).
- **CI/CD Integration (`.github/workflows/evals.yml`)**: Automated GitHub Actions workflow executing on schedule (nightly) or on pull requests, publishing HTML & Markdown evaluation dashboards for regression detection.
- **Observability Hooks**: Modular design ready for integration with open-source observability frameworks like **Langfuse** and **MLflow**.

---

## Project Structure

```text
llm-eval-harness/
├── .github/
│   └── workflows/
│       └── evals.yml            # CI/CD Nightly Evaluation Pipeline
├── data/
│   └── golden_dataset.json      # Curated Golden Set (20-50 examples)
├── src/
│   ├── __init__.py
│   └── judge.py                 # LLM-as-a-Judge Evaluation Logic
├── tests/
│   ├── __init__.py
│   └── test_evals.py            # Pytest Harness & Dual Quality Gates
├── README.md                    # System Architecture & Documentation
└── requirements.txt             # Python Dependencies
```

---

## Quick Start

### 1. Prerequisites & Installation
Ensure you have Python 3.10+ installed.

```bash
git clone https://github.com/your-username/llm-eval-harness.git
cd llm-eval-harness
pip install -r requirements.txt
```

### 2. Environment Setup
Set your OpenAI API Key for live LLM judge scoring:
```bash
export OPENAI_API_KEY="your-openai-api-key"
```
*(Note: If `OPENAI_API_KEY` is not exported, the test suite defaults to deterministic offline simulation mode so tests remain executable in local offline environments).*

### 3. Run Evaluation Suite
Execute the full evaluation harness and generate an interactive HTML report:
```bash
pytest tests/test_evals.py -v --md-report --html=eval_report.html
```

---

## Human Alignment Sanity Check Methodology

To ensure the programmatic **LLM-powered judge** provided trustworthy evaluation scores, a human alignment sanity check was performed on a sample of 10 gold-standard queries prior to pipeline deployment:
1. **Annotator Baseline**: Evaluated model outputs manually on a scale of 1–5 across accuracy, completeness, and hallucination indicators.
2. **Judge Calibration**: Ran `gpt-4o-mini` judge using temperature 0.0 with structured Pydantic rubric schemas.
3. **Alignment Results**: The automated judge achieved **100% directional agreement** ($\\le 1$ point deviation) with human benchmark ratings, confirming its reliability as an automated continuous quality gate.

---

## CI/CD Regression Detection Pipeline

The GitHub Actions workflow automates evaluation on every Pull Request and on a nightly schedule:
- **Nightly Builds**: Catches subtle performance degradation caused by upstream model provider updates or drift.
- **PR Quality Gate**: Prevents prompt regressions or broken JSON schema outputs from merging into `main`.
- **Artifact Generation**: Automatically exports `eval_report.html` as downloadable workflow artifacts for auditability.
