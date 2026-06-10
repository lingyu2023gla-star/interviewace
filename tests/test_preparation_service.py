"""Preparation service tests."""

from __future__ import annotations

import pytest

from knowledge.repository import upsert_knowledge_chunks
from knowledge.schemas import KnowledgeChunk
from preparation.schemas import PreparationPlanRequest
from preparation.service import generate_preparation_plan


def _seed_evidence(db_path: str) -> None:
    """Insert preparation evidence chunks into a temporary DB."""
    upsert_knowledge_chunks(
        db_path,
        [
            KnowledgeChunk(
                source_type="turn_feedback",
                source_id="turn:1:feedback",
                session_id=1,
                title="Agent 架构复盘",
                content="候选人讲到了 Agent Orchestrator、ToolResult 和降级策略。",
                topic="Agent 架构",
            ),
            KnowledgeChunk(
                source_type="turn_feedback",
                source_id="turn:2:feedback",
                session_id=1,
                title="RAG 能力复盘",
                content="候选人说明 RAG 尚未完整实现，只是后续规划方向。",
                topic="RAG 能力",
            ),
        ],
    )


def test_generate_preparation_plan_with_evidence(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "preparation.db")
    _seed_evidence(db_path)
    monkeypatch.setattr("core.analyzer.generate_text", lambda prompt: "这是 mock 准备计划")
    request = PreparationPlanRequest(
        user_goal="准备 Agent/RAG 应用工程师面试",
        job_direction="大模型应用工程师",
        query="Agent RAG",
        plan_days=7,
        daily_minutes=60,
        max_tasks_per_day=3,
        top_k=5,
    )

    result = generate_preparation_plan(db_path, request, include_prompt=True)

    assert result.plan == "这是 mock 准备计划"
    assert result.used_evidence_count >= 1
    assert "[E1]" in result.evidence_context
    assert "Orchestrator" in result.evidence_context or "RAG" in result.evidence_context
    assert result.prompt is not None
    assert "只能基于【历史证据】" in result.prompt
    assert "7 天准备计划" in result.prompt
    assert result.query == "Agent RAG"


def test_generate_preparation_plan_uses_user_goal_when_query_empty(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "preparation.db")
    monkeypatch.setattr("core.analyzer.generate_text", lambda prompt: "计划")
    request = PreparationPlanRequest(
        user_goal="准备 Agent/RAG 应用工程师面试",
        query="",
    )

    result = generate_preparation_plan(db_path, request)

    assert result.query == request.user_goal


def test_generate_preparation_plan_without_evidence(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "preparation.db")
    monkeypatch.setattr("core.analyzer.generate_text", lambda prompt: "无证据计划")
    request = PreparationPlanRequest(user_goal="准备 Agent/RAG 应用工程师面试")

    result = generate_preparation_plan(db_path, request)

    assert result.used_evidence_count == 0
    assert "无可用历史证据" in result.evidence_context
    assert result.plan == "无证据计划"


def test_generate_preparation_plan_excludes_prompt_by_default(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "preparation.db")
    monkeypatch.setattr("core.analyzer.generate_text", lambda prompt: "计划")
    request = PreparationPlanRequest(user_goal="准备面试")

    result = generate_preparation_plan(db_path, request)

    assert result.prompt is None


def test_generate_preparation_plan_invalid_user_goal(tmp_path) -> None:
    db_path = str(tmp_path / "preparation.db")
    request = PreparationPlanRequest(user_goal="")

    with pytest.raises(ValueError):
        generate_preparation_plan(db_path, request)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"plan_days": 0},
        {"daily_minutes": 0},
        {"max_tasks_per_day": 0},
        {"top_k": 0},
    ],
)
def test_generate_preparation_plan_invalid_plan_params(tmp_path, kwargs) -> None:
    db_path = str(tmp_path / "preparation.db")
    request = PreparationPlanRequest(user_goal="准备面试", **kwargs)

    with pytest.raises(ValueError):
        generate_preparation_plan(db_path, request)


def test_generate_preparation_plan_propagates_llm_error(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "preparation.db")

    def fail_generate_text(prompt: str) -> str:
        raise RuntimeError("LLM failed")

    monkeypatch.setattr("core.analyzer.generate_text", fail_generate_text)
    request = PreparationPlanRequest(user_goal="准备面试")

    with pytest.raises(RuntimeError, match="LLM failed"):
        generate_preparation_plan(db_path, request)


def test_generate_preparation_plan_calls_llm_with_prompt(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "preparation.db")
    _seed_evidence(db_path)
    captured = {}

    def fake_generate_text(prompt: str) -> str:
        captured["prompt"] = prompt
        return "计划"

    monkeypatch.setattr("core.analyzer.generate_text", fake_generate_text)
    request = PreparationPlanRequest(
        user_goal="准备 Agent/RAG 应用工程师面试",
        job_direction="大模型应用工程师",
        query="Agent",
    )

    generate_preparation_plan(db_path, request)

    prompt = captured["prompt"]
    assert "准备 Agent/RAG 应用工程师面试" in prompt
    assert "大模型应用工程师" in prompt
    assert "Agent 架构复盘" in prompt
    assert "# 2. 7 天准备计划" in prompt
