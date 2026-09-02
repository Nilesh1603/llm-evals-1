"""
Report generation + regression detection.

Takes the latest run (reports/latest_run.json, written by runner.py),
compares it against reports/history.json (the trend of past runs), and
produces:

  * reports/report.md    — human-readable summary for PR/CI comments
  * reports/report.html  — a small standalone dashboard (pass-rate trend,
    per-category breakdown, newly-failing examples) you can open directly
    in a browser — this is the "dashboard" deliverable, kept dependency-free
    (no plotting library) so it renders anywhere with zero setup.
  * reports/history.json — updated with the latest run appended (bounded
    to the most recent 20 runs)

Regression detection is done two ways, both included in the report:
  1. Aggregate pass-rate delta vs. the immediately preceding run.
  2. Per-example regression: any golden-set id that passed in the previous
     run but fails in this one. This is the more actionable signal — a
     flat pass-rate can hide a regression that's exactly offset by an
     unrelated fix elsewhere, but the per-example diff always catches it.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
LATEST_RUN_PATH = ROOT / "reports" / "latest_run.json"
HISTORY_PATH = ROOT / "reports" / "history.json"
REPORT_MD_PATH = ROOT / "reports" / "report.md"
REPORT_HTML_PATH = ROOT / "reports" / "report.html"

MAX_HISTORY = 20

# A regression fails the CI quality gate if the pass rate drops by more
# than this many percentage points vs. the previous run, OR if any
# previously-passing example newly fails (see detect_regressions below).
PASS_RATE_DROP_GATE = 0.05


def _load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def detect_regressions(latest: dict, previous: dict | None) -> dict:
    if previous is None:
        return {"has_previous_run": False, "newly_failing": [], "newly_passing": [],
                "pass_rate_delta": None, "regression_gate_failed": False}

    prev_failed = set(previous.get("failed_ids", []))
    curr_failed = set(latest.get("failed_ids", []))

    newly_failing = sorted(curr_failed - prev_failed)
    newly_passing = sorted(prev_failed - curr_failed)
    pass_rate_delta = round(latest["pass_rate"] - previous["pass_rate"], 3)

    gate_failed = (len(newly_failing) > 0) or (pass_rate_delta < -PASS_RATE_DROP_GATE)

    return {
        "has_previous_run": True,
        "newly_failing": newly_failing,
        "newly_passing": newly_passing,
        "pass_rate_delta": pass_rate_delta,
        "regression_gate_failed": gate_failed,
    }


def _render_markdown(latest: dict, history: list[dict], regressions: dict) -> str:
    lines = []
    lines.append(f"# Eval Run Report — `{latest['run_id']}`\n")
    lines.append(f"- **Commit:** `{latest['git_sha']}`")
    lines.append(f"- **Pass rate:** {latest['passed']}/{latest['total']} "
                 f"({latest['pass_rate']:.1%})")

    if regressions["has_previous_run"]:
        delta = regressions["pass_rate_delta"]
        sign = "+" if delta >= 0 else ""
        lines.append(f"- **Change vs. previous run:** {sign}{delta:.1%}")
    lines.append("")

    lines.append("## Regression detection\n")
    if not regressions["has_previous_run"]:
        lines.append("_No previous run to compare against — this is the baseline run._\n")
    elif regressions["regression_gate_failed"]:
        lines.append("**QUALITY GATE: FAILED** 🔴\n")
        if regressions["newly_failing"]:
            lines.append(f"Newly failing examples ({len(regressions['newly_failing'])}): "
                         + ", ".join(f"`{i}`" for i in regressions["newly_failing"]))
        if regressions["pass_rate_delta"] < -PASS_RATE_DROP_GATE:
            lines.append(f"Pass rate dropped {abs(regressions['pass_rate_delta']):.1%}, "
                         f"exceeding the {PASS_RATE_DROP_GATE:.0%} gate threshold.")
    else:
        lines.append("**Quality gate: passed** 🟢 — no new regressions vs. previous run.")
        if regressions["newly_passing"]:
            lines.append(f"\nNewly passing (fixed since last run): "
                         + ", ".join(f"`{i}`" for i in regressions["newly_passing"]))
    lines.append("")

    lines.append("## Category breakdown\n")
    lines.append("| Category | Passed | Total | Pass rate |")
    lines.append("|---|---|---|---|")
    for cat, stats in sorted(latest["category_breakdown"].items()):
        lines.append(f"| {cat} | {stats['passed']} | {stats['total']} "
                     f"| {stats['pass_rate']:.1%} |")
    lines.append("")

    if latest["failed_ids"]:
        lines.append("## Failing examples\n")
        for r in latest["results"]:
            if not r["overall_pass"]:
                lines.append(f"- **`{r['id']}`** ({r['category']}) — "
                             f"rubric_pass={r['rubric_pass']}, "
                             f"judge_score={r['judge']['score']}/5 — "
                             f"{r['judge']['rationale']}")
        lines.append("")

    if len(history) > 1:
        lines.append("## Pass-rate trend (last runs)\n")
        lines.append("| Run | Commit | Pass rate |")
        lines.append("|---|---|---|")
        for run in history[-10:]:
            lines.append(f"| {run['run_id']} | `{run['git_sha']}` | {run['pass_rate']:.1%} |")
        lines.append("")

    return "\n".join(lines)


def _render_html(latest: dict, history: list[dict], regressions: dict) -> str:
    gate_ok = not regressions.get("regression_gate_failed", False)
    gate_label = "PASSED" if gate_ok else "FAILED"
    gate_color = "#1a7f37" if gate_ok else "#cf222e"

    trend_points = "".join(
        f'<div class="bar" style="height:{run["pass_rate"] * 100}px" '
        f'title="{run["run_id"]}: {run["pass_rate"]:.1%}"></div>'
        for run in history[-15:]
    )

    cat_rows = "".join(
        f'<tr><td>{cat}</td><td>{s["passed"]}/{s["total"]}</td>'
        f'<td>{s["pass_rate"]:.1%}</td></tr>'
        for cat, s in sorted(latest["category_breakdown"].items())
    )

    fail_rows = "".join(
        f'<tr><td>{r["id"]}</td><td>{r["category"]}</td>'
        f'<td>{"✅" if r["rubric_pass"] else "❌"}</td>'
        f'<td>{r["judge"]["score"]}/5</td>'
        f'<td>{r["judge"]["rationale"]}</td></tr>'
        for r in latest["results"] if not r["overall_pass"]
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Eval Report — {latest['run_id']}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 860px;
         margin: 40px auto; color: #1f2328; background: #fff; }}
  h1 {{ font-size: 1.4rem; }}
  .gate {{ display:inline-block; padding: 4px 12px; border-radius: 6px; color: #fff;
          background: {gate_color}; font-weight: 600; font-size: 0.85rem; }}
  .stat {{ display:inline-block; margin-right: 28px; }}
  .stat .num {{ font-size: 1.6rem; font-weight: 700; }}
  .stat .label {{ font-size: 0.8rem; color: #57606a; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0 28px; }}
  th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #d0d7de;
           font-size: 0.9rem; }}
  th {{ background: #f6f8fa; }}
  .trend {{ display:flex; align-items:flex-end; gap:6px; height:100px; margin: 12px 0 28px; }}
  .bar {{ width: 18px; background: #2da44e; border-radius: 2px 2px 0 0; }}
</style>
</head>
<body>
  <h1>Eval Run Report — {latest['run_id']} <span class="gate">QUALITY GATE: {gate_label}</span></h1>
  <p style="color:#57606a">Commit <code>{latest['git_sha']}</code> · {latest['timestamp']}</p>

  <div>
    <div class="stat"><div class="num">{latest['passed']}/{latest['total']}</div><div class="label">Passed</div></div>
    <div class="stat"><div class="num">{latest['pass_rate']:.1%}</div><div class="label">Pass rate</div></div>
    <div class="stat"><div class="num">{len(regressions.get('newly_failing', []))}</div><div class="label">New regressions</div></div>
  </div>

  <h2>Pass-rate trend</h2>
  <div class="trend">{trend_points}</div>

  <h2>Category breakdown</h2>
  <table><tr><th>Category</th><th>Passed</th><th>Pass rate</th></tr>{cat_rows}</table>

  {'<h2>Failing examples</h2><table><tr><th>ID</th><th>Category</th><th>Rubric</th><th>Judge score</th><th>Judge rationale</th></tr>' + fail_rows + '</table>' if fail_rows else '<p>No failing examples 🎉</p>'}
</body>
</html>
"""


def generate_report() -> dict:
    latest = _load_json(LATEST_RUN_PATH, None)
    if latest is None:
        raise FileNotFoundError(
            "No reports/latest_run.json found — run `python -m harness.runner` first."
        )

    history = _load_json(HISTORY_PATH, [])
    previous = history[-1] if history else None
    regressions = detect_regressions(latest, previous)

    # append latest run to history (without the full per-example `results`
    # payload, to keep history.json small — that detail lives in latest_run.json)
    latest_summary_for_history = {k: v for k, v in latest.items() if k != "results"}
    history.append(latest_summary_for_history)
    history = history[-MAX_HISTORY:]
    HISTORY_PATH.write_text(json.dumps(history, indent=2))

    REPORT_MD_PATH.write_text(_render_markdown(latest, history, regressions))
    REPORT_HTML_PATH.write_text(_render_html(latest, history, regressions))

    return {"latest": latest, "regressions": regressions}


if __name__ == "__main__":
    result = generate_report()
    print(f"Report written to {REPORT_MD_PATH} and {REPORT_HTML_PATH}")
    if result["regressions"]["regression_gate_failed"]:
        print("QUALITY GATE FAILED — regressions detected.")
