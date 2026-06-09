"""Prompt builder 与人工评测样本的集成测试。"""

from __future__ import annotations

import json
from pathlib import Path

from prompts.interview_analysis import build_full_context_analysis_prompt


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "eval_cases"
INTERVIEW_FILE = FIXTURE_DIR / "agent_prompt_hallucination_interview.txt"
EXPECTED_FILE = FIXTURE_DIR / "agent_prompt_hallucination_expected.json"


def test_full_context_prompt_builder_renders_eval_case() -> None:
    """人工评测样本应能稳定渲染为 full_context Prompt。"""
    interview_text = INTERVIEW_FILE.read_text(encoding="utf-8")
    expected = json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))

    prompt = build_full_context_analysis_prompt(
        full_text=interview_text,
        job_direction=expected["job_direction"],
        dimension_profile="llm_app",
        max_suggestions=5,
    )

    assert expected["job_direction"] in prompt

    for keyword in ("Orchestrator", "ToolResult", "Prompt", "RAG", "微调", "幻觉"):
        assert keyword in prompt

    for dimension in (
        "Agent 架构能力",
        "Prompt 工程能力",
        "大模型应用理解",
        "RAG 能力",
        "微调与评估能力",
        "问题定位与稳定性意识",
    ):
        assert dimension in prompt

    for rule in (
        "未验证 / N/A",
        "能力不足",
        "证据不足",
        "覆盖缺口",
        "不要把语音识别错误归咎于候选人",
    ):
        assert rule in prompt

    for template_marker in ("{{", "}}", "{%", "%}"):
        assert template_marker not in prompt
