"""Integration test from knowledge search to evidence context."""

from __future__ import annotations

from knowledge.context_builder import build_evidence_context
from knowledge.repository import upsert_knowledge_chunks
from knowledge.schemas import KnowledgeChunk
from knowledge.search import search_knowledge_chunks


def test_search_results_build_evidence_context(tmp_path) -> None:
    db_path = str(tmp_path / "evidence_context.db")
    upsert_knowledge_chunks(
        db_path,
        [
            KnowledgeChunk(
                source_type="turn_feedback",
                source_id="turn:1:feedback",
                session_id=1,
                content="候选人讲到了 Agent Orchestrator 和 ToolResult。",
                title="Agent 架构复盘",
                topic="Agent 架构",
            )
        ],
    )

    results = search_knowledge_chunks(db_path, query="Agent")
    context = build_evidence_context(results)

    assert "[E1]" in context
    assert "turn:1:feedback" in context
    assert "Agent Orchestrator" in context
