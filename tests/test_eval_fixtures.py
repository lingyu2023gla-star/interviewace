"""人工评测样本结构测试。"""

from __future__ import annotations

import json
from pathlib import Path


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "eval_cases"
INTERVIEW_FILE = FIXTURE_DIR / "agent_prompt_hallucination_interview.txt"
EXPECTED_FILE = FIXTURE_DIR / "agent_prompt_hallucination_expected.json"


def test_agent_prompt_hallucination_interview_exists_and_not_empty() -> None:
    """评测面试文本必须存在且非空。"""
    assert INTERVIEW_FILE.exists()
    assert INTERVIEW_FILE.read_text(encoding="utf-8").strip()


def test_agent_prompt_hallucination_expected_exists_and_parses() -> None:
    """评测期望文件必须存在且可解析为 JSON。"""
    assert EXPECTED_FILE.exists()

    data = json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_agent_prompt_hallucination_expected_required_fields() -> None:
    """评测期望文件必须包含完整字段。"""
    data = json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))
    required_fields = {
        "case_id",
        "job_direction",
        "must_cover",
        "should_mark_partially_covered",
        "should_mark_unverified",
        "must_find_issues",
        "must_not_say",
        "ideal_suggestions",
    }

    assert required_fields.issubset(data.keys())


def test_agent_prompt_hallucination_expected_core_lists_not_empty() -> None:
    """核心评测约束字段必须是非空列表。"""
    data = json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))

    for key in ("must_cover", "should_mark_unverified", "must_find_issues", "must_not_say"):
        assert isinstance(data[key], list)
        assert data[key]


def test_agent_prompt_hallucination_job_direction_is_relevant() -> None:
    """岗位方向必须明确指向 Agent 或大模型应用。"""
    data = json.loads(EXPECTED_FILE.read_text(encoding="utf-8"))
    job_direction = data["job_direction"]

    assert isinstance(job_direction, str)
    assert any(keyword in job_direction for keyword in ("Agent", "大模型应用"))


def test_agent_prompt_hallucination_interview_contains_required_keywords() -> None:
    """面试文本必须覆盖本评测样本关注的核心关键词。"""
    text = INTERVIEW_FILE.read_text(encoding="utf-8")

    for keyword in ("Orchestrator", "Prompt", "幻觉", "RAG", "微调"):
        assert keyword in text
