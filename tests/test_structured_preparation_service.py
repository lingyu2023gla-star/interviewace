"""Structured preparation service tests."""

from __future__ import annotations

import json

import pytest

from knowledge.repository import upsert_knowledge_chunks
from knowledge.schemas import KnowledgeChunk, KnowledgeSearchResult
from preparation.structured_parser import StructuredOutputParseError
from preparation.structured_service import generate_structured_preparation_plan


def _seed_evidence(db_path: str) -> None:
    """Insert searchable evidence chunks into a temporary DB."""
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
            )
        ],
    )


def _valid_llm_json(plan_days: int = 2, insufficient: bool = False) -> str:
    """Return legal structured JSON for mocked LLM output."""
    summary = "历史证据不足，需要先导入复盘记录。" if insufficient else "基于历史证据准备 Agent 架构。"
    data = {
        "summary": summary,
        "evidence_based_judgments": [
            {
                "type": "insufficient_evidence" if insufficient else "strength",
                "content": "历史证据不足" if insufficient else "候选人讲到了 Orchestrator 和 ToolResult。",
                "evidence_refs": [] if insufficient else ["E1"],
            }
        ],
        "daily_plan": [
            {
                "day": day,
                "goal": f"第 {day} 天准备目标",
                "tasks": [
                    {
                        "task": "整理 Agent 架构回答" if not insufficient else "准备通用项目介绍",
                        "estimated_minutes": 30,
                        "output": "回答模板",
                        "evidence_refs": [] if insufficient else ["E1"],
                    }
                ],
            }
            for day in range(1, plan_days + 1)
        ],
        "question_templates": [
            {
                "question": "请介绍 Agent 架构",
                "answer_goal": "说清编排和工具调用",
                "answer_structure": ["先给结论", "解释技术原因", "结合项目证据"],
                "sample_answer": "我会先介绍 Orchestrator，再说明 ToolResult。",
                "evidence_refs": [] if insufficient else ["E1"],
            },
            {
                "question": "如何减少模型幻觉",
                "answer_goal": "说清 evidence-based 约束",
                "answer_structure": ["结论", "规则", "校验"],
                "sample_answer": "我会要求模型引用证据编号。",
                "evidence_refs": [] if insufficient else ["E1"],
            },
        ],
        "abilities_to_show": [
            {
                "ability": "RAG",
                "why_needed": "目标岗位可能需要",
                "current_evidence_status": "历史证据不足",
                "how_to_show_next_time": "说明当前边界和后续规划",
            }
        ],
        "risk_warnings": [
            {
                "risk": "不要把 RAG 规划说成已完整实现",
                "reason": "历史证据不足" if insufficient else "证据中没有完整 RAG 落地说明",
                "evidence_refs": [] if insufficient else ["E1"],
            }
        ],
        "metadata": {
            "user_goal": "准备 Agent/RAG 应用工程师面试",
            "job_direction": "大模型应用工程师",
            "plan_days": plan_days,
            "daily_minutes": 60,
            "max_tasks_per_day": 3,
        },
    }
    return json.dumps(data, ensure_ascii=False)


def test_generate_structured_preparation_plan_with_evidence(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "structured.db")
    _seed_evidence(db_path)
    monkeypatch.setattr(
        "preparation.structured_service.generate_text",
        lambda prompt: _valid_llm_json(plan_days=2),
    )

    result = generate_structured_preparation_plan(
        db_path=db_path,
        user_goal="准备 Agent/RAG 应用工程师面试",
        job_direction="大模型应用工程师",
        query="Agent",
        plan_days=2,
        daily_minutes=60,
        max_tasks_per_day=3,
        top_k=5,
        include_prompt=True,
    )

    assert result.structured_plan.summary
    assert result.used_evidence_count >= 1
    assert "[E1]" in result.evidence_context
    assert result.prompt is not None
    assert "只输出 JSON" in result.prompt
    assert '"summary"' in result.raw_output
    assert len(result.structured_plan.daily_plan) == 2


def test_generate_structured_preparation_plan_query_fallback(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "structured.db")
    monkeypatch.setattr(
        "preparation.structured_service.generate_text",
        lambda prompt: _valid_llm_json(),
    )

    result = generate_structured_preparation_plan(
        db_path=db_path,
        user_goal="准备 Agent/RAG 应用工程师面试",
        query="",
    )

    assert result.query == "准备 Agent/RAG 应用工程师面试"


def test_generate_structured_preparation_plan_empty_evidence(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "structured.db")
    monkeypatch.setattr(
        "preparation.structured_service.generate_text",
        lambda prompt: _valid_llm_json(insufficient=True),
    )

    result = generate_structured_preparation_plan(
        db_path=db_path,
        user_goal="准备 Agent/RAG 应用工程师面试",
    )

    assert result.used_evidence_count == 0
    assert "无可用历史证据" in result.evidence_context
    assert "历史证据不足" in result.structured_plan.summary


def test_generate_structured_preparation_plan_parse_error(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "structured.db")
    monkeypatch.setattr("preparation.structured_service.generate_text", lambda prompt: "not json")

    with pytest.raises(StructuredOutputParseError):
        generate_structured_preparation_plan(
            db_path=db_path,
            user_goal="准备 Agent/RAG 应用工程师面试",
        )


def test_generate_structured_preparation_plan_llm_error(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "structured.db")

    def fail_generate_text(prompt: str) -> str:
        raise RuntimeError("LLM failed")

    monkeypatch.setattr("preparation.structured_service.generate_text", fail_generate_text)

    with pytest.raises(RuntimeError, match="LLM failed"):
        generate_structured_preparation_plan(
            db_path=db_path,
            user_goal="准备 Agent/RAG 应用工程师面试",
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"user_goal": ""},
        {"plan_days": 0},
        {"daily_minutes": 0},
        {"max_tasks_per_day": 0},
        {"top_k": 0},
    ],
)
def test_generate_structured_preparation_plan_invalid_params(tmp_path, kwargs) -> None:
    db_path = str(tmp_path / "structured.db")
    params = {"db_path": db_path, "user_goal": "准备面试"}
    params.update(kwargs)

    with pytest.raises(ValueError):
        generate_structured_preparation_plan(**params)


def test_generate_structured_preparation_plan_default_retriever_type_is_keyword(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = str(tmp_path / "structured.db")
    captured = {}

    class FakeRetriever:
        def retrieve(self, **kwargs):
            captured["retrieve_kwargs"] = kwargs
            return [
                KnowledgeSearchResult(
                    chunk_id=1,
                    source_type="turn_feedback",
                    source_id="turn:1:feedback",
                    title="Agent 架构复盘",
                    content="候选人讲到了 Orchestrator。",
                    snippet="候选人讲到了 Orchestrator。",
                )
            ]

    def fake_get_retriever(retriever_type: str = "keyword"):
        captured["retriever_type"] = retriever_type
        return FakeRetriever()

    monkeypatch.setattr("preparation.structured_service.get_retriever", fake_get_retriever)
    monkeypatch.setattr(
        "preparation.structured_service.generate_text",
        lambda prompt: _valid_llm_json(),
    )

    result = generate_structured_preparation_plan(
        db_path=db_path,
        user_goal="准备 Agent/RAG 应用工程师面试",
    )

    assert captured["retriever_type"] == "keyword"
    assert captured["retrieve_kwargs"]["query"] == "准备 Agent/RAG 应用工程师面试"
    assert result.used_evidence_count == 1


def test_generate_structured_preparation_plan_uses_opt_in_embedding_retriever(
    tmp_path,
    monkeypatch,
) -> None:
    db_path = str(tmp_path / "structured.db")
    captured = {}

    class FakeRetriever:
        def retrieve(self, **kwargs):
            captured["retrieve_kwargs"] = kwargs
            return []

    def fake_get_retriever(retriever_type: str = "keyword"):
        captured["retriever_type"] = retriever_type
        return FakeRetriever()

    monkeypatch.setattr("preparation.structured_service.get_retriever", fake_get_retriever)
    monkeypatch.setattr(
        "preparation.structured_service.generate_text",
        lambda prompt: _valid_llm_json(insufficient=True),
    )

    result = generate_structured_preparation_plan(
        db_path=db_path,
        user_goal="准备 Agent/RAG 应用工程师面试",
        query="Agent",
        retriever_type="embedding",
        top_k=4,
    )

    assert captured["retriever_type"] == "embedding"
    assert captured["retrieve_kwargs"]["query"] == "Agent"
    assert captured["retrieve_kwargs"]["top_k"] == 4
    assert result.used_evidence_count == 0
