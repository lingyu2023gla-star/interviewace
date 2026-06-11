"""knowledge retriever tests."""

from __future__ import annotations

import pytest

from knowledge.retrievers import BaseRetriever, KeywordRetriever, get_retriever
from knowledge.schemas import KnowledgeSearchResult


def test_keyword_retriever_calls_search_knowledge_chunks(monkeypatch) -> None:
    captured = {}
    expected = [
        KnowledgeSearchResult(
            chunk_id=1,
            source_type="turn_feedback",
            source_id="turn:1:feedback",
            content="Agent Orchestrator evidence",
            title="Agent 架构",
        )
    ]

    def fake_search_knowledge_chunks(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        "knowledge.retrievers.keyword.search_knowledge_chunks",
        fake_search_knowledge_chunks,
    )

    retriever = KeywordRetriever()
    results = retriever.retrieve(
        db_path="/tmp/test.db",
        query="Agent",
        session_id=1,
        source_type="turn_feedback",
        topic="Agent 架构",
        dimension_key="agent_architecture",
        top_k=3,
    )

    assert results == expected
    assert captured == {
        "db_path": "/tmp/test.db",
        "query": "Agent",
        "session_id": 1,
        "source_type": "turn_feedback",
        "topic": "Agent 架构",
        "dimension_key": "agent_architecture",
        "top_k": 3,
    }


def test_keyword_retriever_is_base_retriever() -> None:
    assert isinstance(KeywordRetriever(), BaseRetriever)


def test_get_retriever_keyword_returns_keyword_retriever() -> None:
    retriever = get_retriever("keyword")

    assert isinstance(retriever, KeywordRetriever)


def test_get_retriever_fts_alias_returns_keyword_retriever() -> None:
    retriever = get_retriever("fts")

    assert isinstance(retriever, KeywordRetriever)


def test_get_retriever_defaults_to_keyword() -> None:
    retriever = get_retriever()

    assert isinstance(retriever, KeywordRetriever)


def test_get_retriever_unknown_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown retriever_type"):
        get_retriever("unknown")
