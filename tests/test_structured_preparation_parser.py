"""Structured preparation plan parser tests."""

from __future__ import annotations

import json

import pytest

from preparation.structured_parser import (
    StructuredOutputParseError,
    extract_json_object,
    parse_structured_preparation_plan,
)
from preparation.structured_schemas import StructuredPreparationPlan


def _valid_plan_data() -> dict:
    """Return a valid structured plan payload."""
    return {
        "summary": "基于历史证据准备 Agent 架构。",
        "evidence_based_judgments": [
            {
                "type": "strength",
                "content": "候选人讲到了 Orchestrator。",
                "evidence_refs": ["E1"],
            }
        ],
        "daily_plan": [
            {
                "day": 1,
                "goal": "准备 Agent 架构",
                "tasks": [
                    {
                        "task": "整理 Orchestrator 回答",
                        "estimated_minutes": 30,
                        "output": "回答模板",
                        "evidence_refs": ["E1"],
                    }
                ],
            }
        ],
        "question_templates": [
            {
                "question": "请介绍 Agent 架构",
                "answer_goal": "说清编排和工具调用",
                "answer_structure": ["结论", "原因", "项目证据"],
                "sample_answer": "我会从 Orchestrator 讲起。",
                "evidence_refs": ["E1"],
            }
        ],
        "abilities_to_show": [
            {
                "ability": "RAG",
                "why_needed": "岗位需要",
                "current_evidence_status": "历史证据不足",
                "how_to_show_next_time": "说明边界和规划",
            }
        ],
        "risk_warnings": [
            {
                "risk": "不要夸大 RAG",
                "reason": "历史证据不足",
                "evidence_refs": [],
            }
        ],
        "metadata": {},
    }


def _valid_plan_json() -> str:
    """Return valid structured plan JSON text."""
    return json.dumps(_valid_plan_data(), ensure_ascii=False)


def test_extract_json_object_plain_json() -> None:
    text = _valid_plan_json()

    assert extract_json_object(text) == text


def test_extract_json_object_markdown_fence() -> None:
    text = f"```json\n{_valid_plan_json()}\n```"

    assert extract_json_object(text) == _valid_plan_json()


def test_extract_json_object_with_extra_text() -> None:
    text = f"前置说明\n{_valid_plan_json()}\n后置说明"

    assert extract_json_object(text) == _valid_plan_json()


def test_extract_json_object_invalid() -> None:
    with pytest.raises(StructuredOutputParseError):
        extract_json_object("没有 JSON")


def test_parse_structured_preparation_plan_success() -> None:
    plan = parse_structured_preparation_plan(_valid_plan_json())

    assert isinstance(plan, StructuredPreparationPlan)
    assert plan.summary == "基于历史证据准备 Agent 架构。"


def test_parse_structured_preparation_plan_invalid_json() -> None:
    with pytest.raises(StructuredOutputParseError, match="Invalid JSON"):
        parse_structured_preparation_plan('{"summary": "bad",}')


def test_parse_structured_preparation_plan_validation_error() -> None:
    data = _valid_plan_data()
    del data["summary"]

    with pytest.raises(StructuredOutputParseError, match="validation failed"):
        parse_structured_preparation_plan(json.dumps(data, ensure_ascii=False))
