"""Structured preparation plan schema tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from preparation.structured_parser import structured_plan_to_dict
from preparation.structured_schemas import StructuredPreparationPlan


def _valid_plan_data() -> dict:
    """Return a minimal valid structured plan payload."""
    return {
        "summary": "基于历史证据，优先准备 Agent 架构表达。",
        "evidence_based_judgments": [
            {
                "type": "strength",
                "content": "候选人讲到了 Orchestrator 和 ToolResult。",
                "evidence_refs": ["E1"],
            }
        ],
        "daily_plan": [
            {
                "day": 1,
                "goal": "整理 Agent 架构回答",
                "tasks": [
                    {
                        "task": "写出 Orchestrator 到 ToolResult 的流程话术",
                        "estimated_minutes": 30,
                        "output": "一段 2 分钟回答模板",
                        "evidence_refs": ["E1"],
                    }
                ],
            }
        ],
        "question_templates": [
            {
                "question": "请介绍你的 Agent 架构设计",
                "answer_goal": "说明编排、工具结果和降级策略",
                "answer_structure": ["先给结论", "解释技术原因", "结合项目证据"],
                "sample_answer": "我会先介绍 Orchestrator，再说明 ToolResult。",
                "evidence_refs": ["E1"],
            }
        ],
        "abilities_to_show": [
            {
                "ability": "RAG 边界说明",
                "why_needed": "目标岗位关注 RAG 落地能力",
                "current_evidence_status": "历史证据不足",
                "how_to_show_next_time": "说明当前尚未完整实现，并给出规划。",
            }
        ],
        "risk_warnings": [
            {
                "risk": "不要把 RAG 规划说成已落地",
                "reason": "历史证据不足",
                "evidence_refs": [],
            }
        ],
        "metadata": {
            "user_goal": "准备 Agent/RAG 面试",
            "job_direction": "大模型应用工程师",
            "plan_days": 1,
            "daily_minutes": 60,
            "max_tasks_per_day": 3,
        },
    }


def test_structured_preparation_plan_minimal_valid() -> None:
    plan = StructuredPreparationPlan(**_valid_plan_data())

    assert plan.summary
    assert plan.evidence_based_judgments[0].evidence_refs == ["E1"]
    assert plan.metadata["plan_days"] == 1


def test_structured_preparation_plan_nested_daily_tasks_validate() -> None:
    plan = StructuredPreparationPlan(**_valid_plan_data())

    task = plan.daily_plan[0].tasks[0]
    assert plan.daily_plan[0].day == 1
    assert task.estimated_minutes == 30
    assert task.output == "一段 2 分钟回答模板"


def test_structured_plan_to_dict_supports_pydantic_v1_v2() -> None:
    plan = StructuredPreparationPlan(**_valid_plan_data())

    data = structured_plan_to_dict(plan)

    assert isinstance(data, dict)
    assert data["summary"] == plan.summary
    assert data["daily_plan"][0]["tasks"][0]["estimated_minutes"] == 30


def test_structured_preparation_plan_missing_required_field_fails() -> None:
    data = _valid_plan_data()
    del data["summary"]

    with pytest.raises(ValidationError):
        StructuredPreparationPlan(**data)
