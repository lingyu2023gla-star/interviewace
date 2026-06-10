"""knowledge.search tests."""

from __future__ import annotations

from knowledge.repository import upsert_knowledge_chunks
from knowledge.schemas import KnowledgeChunk
from knowledge.search import search_knowledge_chunks


def _seed_chunks(db_path: str, chunks: list[KnowledgeChunk]) -> None:
    """Insert test chunks into a temporary DB."""
    upsert_knowledge_chunks(db_path, chunks)


def test_search_returns_matching_chunks(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge_search.db")
    _seed_chunks(
        db_path,
        [
            KnowledgeChunk(
                source_type="turn_feedback",
                source_id="turn:1:feedback",
                session_id=1,
                title="Agent 架构复盘",
                content="候选人讲到了 Orchestrator、ToolResult 和降级策略。",
                topic="Agent 架构",
            ),
            KnowledgeChunk(
                source_type="turn_feedback",
                source_id="turn:2:feedback",
                session_id=1,
                title="Prompt 工程复盘",
                content="候选人讲到了语音识别噪音、输出结构化和证据不足。",
                topic="Prompt 工程",
            ),
            KnowledgeChunk(
                source_type="turn_feedback",
                source_id="turn:3:feedback",
                session_id=1,
                title="后端工程复盘",
                content="本场没有充分讨论 Redis 和 Celery。",
                topic="后端工程",
            ),
        ],
    )

    results = search_knowledge_chunks(db_path, query="Orchestrator", top_k=5)

    assert results
    assert "Agent" in (results[0].title or "")
    assert "Orchestrator" in results[0].content
    assert results[0].snippet
    assert results[0].source_type == "turn_feedback"


def test_search_filters_by_session_id(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge_search.db")
    _seed_chunks(
        db_path,
        [
            KnowledgeChunk("turn_feedback", "turn:1:feedback", "Orchestrator 设计", session_id=1),
            KnowledgeChunk("turn_feedback", "turn:2:feedback", "Orchestrator 复盘", session_id=2),
        ],
    )

    results = search_knowledge_chunks(db_path, query="Orchestrator", session_id=2)

    assert results
    assert {result.session_id for result in results} == {2}


def test_search_filters_by_source_type(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge_search.db")
    _seed_chunks(
        db_path,
        [
            KnowledgeChunk("turn_feedback", "turn:1:feedback", "Agent 架构反馈", session_id=1),
            KnowledgeChunk("question_bank", "question:1:reference_answer", "Agent 架构参考答案", session_id=1),
        ],
    )

    results = search_knowledge_chunks(db_path, query="Agent", source_type="question_bank")

    assert results
    assert {result.source_type for result in results} == {"question_bank"}


def test_search_filters_by_topic(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge_search.db")
    _seed_chunks(
        db_path,
        [
            KnowledgeChunk("turn_feedback", "turn:1:feedback", "Prompt 约束设计", session_id=1, topic="Prompt 工程"),
            KnowledgeChunk("turn_feedback", "turn:2:feedback", "Prompt 复盘", session_id=1, topic="Agent 架构"),
        ],
    )

    results = search_knowledge_chunks(db_path, query="Prompt", topic="Prompt 工程")

    assert results
    assert {result.topic for result in results} == {"Prompt 工程"}


def test_search_filters_by_dimension_key(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge_search.db")
    _seed_chunks(
        db_path,
        [
            KnowledgeChunk(
                "turn_feedback",
                "turn:1:feedback",
                "Agent Orchestrator 设计",
                session_id=1,
                dimension_key="agent_architecture",
            ),
            KnowledgeChunk(
                "turn_feedback",
                "turn:2:feedback",
                "Agent Prompt 设计",
                session_id=1,
                dimension_key="prompt_engineering",
            ),
        ],
    )

    results = search_knowledge_chunks(db_path, query="Agent", dimension_key="agent_architecture")

    assert results
    assert {result.dimension_key for result in results} == {"agent_architecture"}


def test_search_respects_top_k(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge_search.db")
    _seed_chunks(
        db_path,
        [
            KnowledgeChunk("turn_feedback", f"turn:{index}:feedback", f"Agent 反馈 {index}", session_id=1)
            for index in range(5)
        ],
    )

    results = search_knowledge_chunks(db_path, query="Agent", top_k=2)

    assert len(results) == 2


def test_search_empty_query_returns_empty(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge_search.db")
    _seed_chunks(
        db_path,
        [KnowledgeChunk("turn_feedback", "turn:1:feedback", "Agent 反馈", session_id=1)],
    )

    assert search_knowledge_chunks(db_path, query="") == []
    assert search_knowledge_chunks(db_path, query="   ") == []
    assert search_knowledge_chunks(db_path, query="Agent", top_k=0) == []


def test_search_like_fallback(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "knowledge_search.db")
    _seed_chunks(
        db_path,
        [
            KnowledgeChunk(
                "turn_feedback",
                "turn:1:feedback",
                "候选人讲到了 Orchestrator 和降级策略。",
                session_id=1,
                title="Agent 架构复盘",
            )
        ],
    )
    monkeypatch.setattr("knowledge.search.rebuild_fts_index", lambda db_path: False)

    results = search_knowledge_chunks(db_path, query="Orchestrator")

    assert results
    assert results[0].title == "Agent 架构复盘"
    assert "Orchestrator" in results[0].content


def test_search_result_parses_tags_and_metadata(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge_search.db")
    _seed_chunks(
        db_path,
        [
            KnowledgeChunk(
                source_type="turn_feedback",
                source_id="turn:1:feedback",
                session_id=1,
                content="Agent 架构需要说明 Orchestrator。",
                tags=["Agent", "Prompt"],
                metadata={"question": "请介绍 Agent 架构"},
            )
        ],
    )

    results = search_knowledge_chunks(db_path, query="Orchestrator")

    assert results
    assert results[0].tags == ["Agent", "Prompt"]
    assert results[0].metadata["question"] == "请介绍 Agent 架构"
