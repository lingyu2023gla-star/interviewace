"""Evaluate full_context prompt quality against a small manual eval case.

Default dry-run mode renders and saves the prompt only. Pass --run-llm to call
the existing analyzer and produce a model report plus machine-assisted checks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.analyzer import analyze_full_interview  # noqa: E402
from prompts.interview_analysis import build_full_context_analysis_prompt  # noqa: E402


CASE_ID = "agent_prompt_hallucination"
INTERVIEW_PATH = REPO_ROOT / "tests" / "fixtures" / "eval_cases" / "agent_prompt_hallucination_interview.txt"
EXPECTED_PATH = REPO_ROOT / "tests" / "fixtures" / "eval_cases" / "agent_prompt_hallucination_expected.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs" / "eval"

UNVERIFIED_MARKERS = ("未验证", "N/A", "证据不足")
GENERIC_ISSUE_WORDS = {
    "候选人",
    "项目中",
    "当前",
    "后续",
    "应该",
    "不能",
    "例如",
    "已经",
}


def _read_inputs() -> tuple[str, dict[str, Any]]:
    """Read the interview text and expected eval metadata."""
    interview_text = INTERVIEW_PATH.read_text(encoding="utf-8")
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    return interview_text, expected


def _context_contains_marker(report: str, needle: str, markers: tuple[str, ...]) -> bool:
    """Check whether a report line near the needle contains any marker."""
    lines = report.splitlines()
    for index, line in enumerate(lines):
        if needle not in line:
            continue
        start = max(0, index - 1)
        end = min(len(lines), index + 3)
        context = "\n".join(lines[start:end])
        if any(marker in context for marker in markers):
            return True
    return False


def _extract_issue_keywords(issue: str) -> list[str]:
    """Extract coarse keywords from an expected issue sentence."""
    ascii_terms = re.findall(r"[A-Za-z][A-Za-z0-9_+-]*(?:\s*/\s*[A-Za-z][A-Za-z0-9_+-]*)*", issue)
    chinese_chunks = re.split(r"[，。、；：\s/]+", issue)
    keywords = []
    for keyword in [*ascii_terms, *chinese_chunks]:
        keyword = keyword.strip()
        if len(keyword) < 2 or keyword in GENERIC_ISSUE_WORDS:
            continue
        if keyword not in keywords:
            keywords.append(keyword)
    return keywords


def _issue_keyword_hits(report: str, issue: str) -> list[str]:
    """Return expected issue keywords that appear in the report."""
    return [keyword for keyword in _extract_issue_keywords(issue) if keyword in report]


def _evaluate_report(report: str, expected: dict[str, Any]) -> dict[str, Any]:
    """Run machine-assisted checks against one model report."""
    must_cover = {
        item: item in report
        for item in expected["must_cover"]
    }
    should_mark_unverified = {
        item: _context_contains_marker(report, item, UNVERIFIED_MARKERS)
        for item in expected["should_mark_unverified"]
    }
    must_find_issues = {
        item: {
            "passed": bool(hits := _issue_keyword_hits(report, item)),
            "matched_keywords": hits,
        }
        for item in expected["must_find_issues"]
    }
    must_not_say = {
        item: item not in report
        for item in expected["must_not_say"]
    }

    return {
        "must_cover": must_cover,
        "should_mark_unverified": should_mark_unverified,
        "must_find_issues": must_find_issues,
        "must_not_say": must_not_say,
        "passed": (
            all(must_cover.values())
            and all(should_mark_unverified.values())
            and all(item["passed"] for item in must_find_issues.values())
            and all(must_not_say.values())
        ),
    }


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON with stable formatting."""
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _with_trailing_newline(text: str) -> str:
    """Ensure text artifacts display cleanly with cat in terminals."""
    return text if text.endswith("\n") else f"{text}\n"


def run_eval(run_llm: bool, repeat: int, output_dir: Path) -> dict[str, Any]:
    """Render prompt, optionally run LLM, save artifacts, and return eval data."""
    if repeat < 1:
        raise ValueError("--repeat must be >= 1")

    output_dir.mkdir(parents=True, exist_ok=True)
    interview_text, expected = _read_inputs()

    prompt = build_full_context_analysis_prompt(
        full_text=interview_text,
        job_direction=expected["job_direction"],
        dimension_profile="llm_app",
        max_suggestions=5,
    )
    prompt_path = output_dir / f"{CASE_ID}_prompt.md"
    prompt_path.write_text(_with_trailing_newline(prompt), encoding="utf-8")

    result: dict[str, Any] = {
        "case_id": expected["case_id"],
        "job_direction": expected["job_direction"],
        "dry_run": not run_llm,
        "repeat": repeat,
        "prompt_path": str(prompt_path),
        "report_path": None,
        "runs": [],
    }

    if not run_llm:
        result["note"] = "Dry-run mode rendered the prompt only. Pass --run-llm to call the model."
        _write_json(output_dir / f"{CASE_ID}_eval_result.json", result)
        return result

    canonical_report_path = output_dir / f"{CASE_ID}_report.md"
    for index in range(1, repeat + 1):
        report = analyze_full_interview(interview_text, expected["job_direction"])
        report_path = canonical_report_path
        if repeat > 1:
            report_path = output_dir / f"{CASE_ID}_report_{index}.md"
        report_path.write_text(_with_trailing_newline(report), encoding="utf-8")
        canonical_report_path.write_text(_with_trailing_newline(report), encoding="utf-8")

        result["runs"].append(
            {
                "index": index,
                "report_path": str(report_path),
                "checks": _evaluate_report(report, expected),
            }
        )

    result["report_path"] = str(canonical_report_path)
    result["passed"] = all(run["checks"]["passed"] for run in result["runs"])
    _write_json(output_dir / f"{CASE_ID}_eval_result.json", result)
    return result


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Evaluate the full_context prompt against a manual eval case.")
    parser.add_argument("--run-llm", action="store_true", help="Call the real LLM through analyze_full_interview.")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat LLM runs N times for stability observation.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for prompt, report, and eval result artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    try:
        result = run_eval(run_llm=args.run_llm, repeat=args.repeat, output_dir=args.output_dir)
    except Exception as exc:
        print(f"[eval failed] {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
