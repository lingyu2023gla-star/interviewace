"""Evidence context builder tests."""

from __future__ import annotations

from knowledge.context_builder import build_evidence_blocks, build_evidence_context
from knowledge.schemas import KnowledgeSearchResult


def test_build_evidence_context_empty() -> None:
    context = build_evidence_context([])

    assert "无可用历史证据" in context


def test_build_evidence_context_formats_single_result() -> None:
    result = KnowledgeSearchResult(
        chunk_id=1,
        source_type="turn_feedback",
        source_id="turn:1:feedback",
        title="Agent 架构复盘",
        content="候选人讲到了 Orchestrator、ToolResult 和降级策略。",
        snippet="候选人讲到了 Orchestrator、ToolResult。",
        session_id=1,
        turn_id=1,
        topic="Agent 架构",
        dimension_key="agent_architecture",
        tags=["Agent"],
        metadata={"question": "请介绍 Agent 架构"},
    )

    context = build_evidence_context([result])

    assert "[E1]" in context
    assert "来源类型：turn_feedback" in context
    assert "来源ID：turn:1:feedback" in context
    assert "会话ID：1" in context
    assert "主题：Agent 架构" in context
    assert "维度：agent_architecture" in context
    assert "Agent 架构复盘" in context
    assert "Orchestrator" in context
    assert "ToolResult" in context


def test_build_evidence_context_respects_max_chunks() -> None:
    results = [
        KnowledgeSearchResult(i, "turn_feedback", f"turn:{i}:feedback", f"Agent 证据 {i}")
        for i in range(1, 4)
    ]

    context = build_evidence_context(results, max_chunks=2)

    assert "[E1]" in context
    assert "[E2]" in context
    assert "[E3]" not in context


def test_build_evidence_context_truncates_content() -> None:
    result = KnowledgeSearchResult(
        chunk_id=1,
        source_type="turn_feedback",
        source_id="turn:1:feedback",
        content="Agent" * 100,
    )

    context = build_evidence_context([result], max_content_chars=50)

    assert "..." in context
    assert "Agent" * 20 not in context


def test_build_evidence_blocks_use_snippet_first() -> None:
    result = KnowledgeSearchResult(
        chunk_id=1,
        source_type="turn_feedback",
        source_id="turn:1:feedback",
        content="完整内容",
        snippet="片段内容",
    )

    blocks = build_evidence_blocks([result])

    assert len(blocks) == 1
    assert blocks[0].content == "片段内容"
