"""eval_prompt_quality.py deterministic logic tests."""

from __future__ import annotations

import json

from scripts import eval_prompt_quality


def test_load_eval_case() -> None:
    interview_text, expected = eval_prompt_quality._read_inputs()

    assert interview_text.strip()
    assert {
        "case_id",
        "job_direction",
        "must_cover",
        "should_mark_unverified",
        "must_find_issues",
        "must_not_say",
    }.issubset(expected.keys())


def test_check_must_cover() -> None:
    _, expected = eval_prompt_quality._read_inputs()
    report = """
    | 维度 | 覆盖状态 | 诊断 |
    | Agent 架构能力 | 已覆盖 | Orchestrator 和 ToolResult 说明清楚 |
    | Prompt 工程能力 | 已覆盖 | 约束设计和输出结构明确 |
    """

    checks = eval_prompt_quality._evaluate_report(report, expected)

    assert checks["must_cover"]["Agent 架构能力"] is True
    assert checks["must_cover"]["Prompt 工程能力"] is True


def test_check_should_mark_unverified() -> None:
    _, expected = eval_prompt_quality._read_inputs()
    report = "Redis 状态管理：未验证 / N/A，本场没有足够证据。"

    checks = eval_prompt_quality._evaluate_report(report, expected)

    assert checks["should_mark_unverified"]["Redis 状态管理"] is True


def test_check_must_not_say() -> None:
    _, expected = eval_prompt_quality._read_inputs()
    report = "候选人已经完整实现 RAG 系统。"

    checks = eval_prompt_quality._evaluate_report(report, expected)

    assert checks["must_not_say"]["候选人已经完整实现 RAG 系统"] is False


def test_dry_run_generates_prompt(tmp_path) -> None:
    interview_text, expected = eval_prompt_quality._read_inputs()

    result = eval_prompt_quality.run_eval(run_llm=False, repeat=1, output_dir=tmp_path)

    prompt_path = tmp_path / "agent_prompt_hallucination_prompt.md"
    eval_result_path = tmp_path / "agent_prompt_hallucination_eval_result.json"
    prompt = prompt_path.read_text(encoding="utf-8")
    eval_result = json.loads(eval_result_path.read_text(encoding="utf-8"))

    assert result["dry_run"] is True
    assert result["runs"] == []
    assert prompt_path.exists()
    assert eval_result_path.exists()
    assert prompt.endswith("\n")
    assert not prompt.rstrip("\n").endswith("%")
    assert interview_text in prompt
    assert expected["job_direction"] in prompt

    for dimension in ("Agent 架构能力", "Prompt 工程能力", "RAG 能力"):
        assert dimension in prompt

    for rule in ("未验证 / N/A", "能力不足", "证据不足", "覆盖缺口"):
        assert rule in prompt

    assert eval_result["dry_run"] is True
