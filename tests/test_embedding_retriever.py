"""EmbeddingRetriever tests."""

from __future__ import annotations

import sqlite3

import pytest

from knowledge.embedding_store import init_chunk_embeddings_table, upsert_chunk_embedding
from knowledge.embeddings.providers import BaseEmbeddingProvider
from knowledge.repository import upsert_knowledge_chunks
from knowledge.retrievers import EmbeddingRetriever, get_retriever
from knowledge.schemas import KnowledgeChunk


class StaticEmbeddingProvider(BaseEmbeddingProvider):
    """Test provider returning a fixed query embedding."""

    def __init__(self, query_embedding: list[float], model_name: str = "test-embedding-v1") -> None:
        self.query_embedding = query_embedding
        self.model_name = model_name
        self.calls: list[str] = []

    def embed_text(self, text: str) -> list[float]:
        self.calls.append(text)
        return self.query_embedding


def _chunk_ids_by_source(db_path: str) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT id, source_id FROM knowledge_chunks").fetchall()
    conn.close()
    return {source_id: chunk_id for chunk_id, source_id in rows}


def _seed_chunks(db_path: str) -> dict[str, int]:
    upsert_knowledge_chunks(
        db_path,
        [
            KnowledgeChunk(
                source_type="turn_feedback",
                source_id="turn:1:feedback",
                session_id=1,
                title="Agent 架构",
                content="Agent Orchestrator and ToolResult",
                topic="Agent 架构",
                dimension_key="agent_architecture",
                tags=["Agent"],
                metadata={"question": "介绍 Agent 架构"},
            ),
            KnowledgeChunk(
                source_type="question_bank",
                source_id="question:1:reference_answer",
                session_id=2,
                title="RAG 题目",
                content="RAG recall and rerank",
                topic="RAG",
                dimension_key="rag_capability",
            ),
        ],
    )
    return _chunk_ids_by_source(db_path)


def test_get_retriever_embedding_returns_embedding_retriever() -> None:
    retriever = get_retriever("embedding")

    assert isinstance(retriever, EmbeddingRetriever)


def test_embedding_retriever_empty_db_returns_empty(tmp_path) -> None:
    db_path = str(tmp_path / "embedding_retriever.db")
    retriever = EmbeddingRetriever(StaticEmbeddingProvider([1.0, 0.0]))

    assert retriever.retrieve(db_path, query="Agent") == []


def test_embedding_retriever_returns_results(tmp_path) -> None:
    db_path = str(tmp_path / "embedding_retriever.db")
    chunk_ids = _seed_chunks(db_path)
    provider = StaticEmbeddingProvider([1.0, 0.0])
    upsert_chunk_embedding(db_path, chunk_ids["turn:1:feedback"], [1.0, 0.0], provider.model_name)

    results = EmbeddingRetriever(provider).retrieve(db_path, query="Agent", top_k=5)

    assert len(results) == 1
    assert results[0].chunk_id == chunk_ids["turn:1:feedback"]
    assert results[0].source_type == "turn_feedback"
    assert results[0].source_id == "turn:1:feedback"
    assert results[0].snippet
    assert results[0].score == pytest.approx(1.0)
    assert results[0].tags == ["Agent"]
    assert results[0].metadata["question"] == "介绍 Agent 架构"
    assert provider.calls == ["Agent"]


def test_embedding_retriever_sorts_by_cosine_similarity(tmp_path) -> None:
    db_path = str(tmp_path / "embedding_retriever.db")
    chunk_ids = _seed_chunks(db_path)
    provider = StaticEmbeddingProvider([1.0, 0.0])
    upsert_chunk_embedding(db_path, chunk_ids["turn:1:feedback"], [1.0, 0.0], provider.model_name)
    upsert_chunk_embedding(db_path, chunk_ids["question:1:reference_answer"], [0.0, 1.0], provider.model_name)

    results = EmbeddingRetriever(provider).retrieve(db_path, query="Agent", top_k=5)

    assert [result.chunk_id for result in results] == [
        chunk_ids["turn:1:feedback"],
        chunk_ids["question:1:reference_answer"],
    ]
    assert results[0].score > results[1].score


def test_embedding_retriever_respects_top_k(tmp_path) -> None:
    db_path = str(tmp_path / "embedding_retriever.db")
    chunk_ids = _seed_chunks(db_path)
    provider = StaticEmbeddingProvider([1.0, 0.0])
    upsert_chunk_embedding(db_path, chunk_ids["turn:1:feedback"], [1.0, 0.0], provider.model_name)
    upsert_chunk_embedding(db_path, chunk_ids["question:1:reference_answer"], [0.0, 1.0], provider.model_name)

    results = EmbeddingRetriever(provider).retrieve(db_path, query="Agent", top_k=1)

    assert len(results) == 1


@pytest.mark.parametrize("top_k", [0, -1])
def test_embedding_retriever_invalid_top_k_raises(tmp_path, top_k) -> None:
    db_path = str(tmp_path / "embedding_retriever.db")
    retriever = EmbeddingRetriever(StaticEmbeddingProvider([1.0, 0.0]))

    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        retriever.retrieve(db_path, query="Agent", top_k=top_k)


def test_embedding_retriever_filters_by_session_id(tmp_path) -> None:
    db_path = str(tmp_path / "embedding_retriever.db")
    chunk_ids = _seed_chunks(db_path)
    provider = StaticEmbeddingProvider([1.0, 0.0])
    upsert_chunk_embedding(db_path, chunk_ids["turn:1:feedback"], [1.0, 0.0], provider.model_name)
    upsert_chunk_embedding(db_path, chunk_ids["question:1:reference_answer"], [1.0, 0.0], provider.model_name)

    results = EmbeddingRetriever(provider).retrieve(db_path, query="Agent", session_id=2)

    assert {result.session_id for result in results} == {2}


def test_embedding_retriever_filters_by_source_type(tmp_path) -> None:
    db_path = str(tmp_path / "embedding_retriever.db")
    chunk_ids = _seed_chunks(db_path)
    provider = StaticEmbeddingProvider([1.0, 0.0])
    upsert_chunk_embedding(db_path, chunk_ids["turn:1:feedback"], [1.0, 0.0], provider.model_name)
    upsert_chunk_embedding(db_path, chunk_ids["question:1:reference_answer"], [1.0, 0.0], provider.model_name)

    results = EmbeddingRetriever(provider).retrieve(db_path, query="Agent", source_type="question_bank")

    assert {result.source_type for result in results} == {"question_bank"}


def test_embedding_retriever_filters_by_topic(tmp_path) -> None:
    db_path = str(tmp_path / "embedding_retriever.db")
    chunk_ids = _seed_chunks(db_path)
    provider = StaticEmbeddingProvider([1.0, 0.0])
    upsert_chunk_embedding(db_path, chunk_ids["turn:1:feedback"], [1.0, 0.0], provider.model_name)
    upsert_chunk_embedding(db_path, chunk_ids["question:1:reference_answer"], [1.0, 0.0], provider.model_name)

    results = EmbeddingRetriever(provider).retrieve(db_path, query="Agent", topic="RAG")

    assert {result.topic for result in results} == {"RAG"}


def test_embedding_retriever_filters_by_dimension_key(tmp_path) -> None:
    db_path = str(tmp_path / "embedding_retriever.db")
    chunk_ids = _seed_chunks(db_path)
    provider = StaticEmbeddingProvider([1.0, 0.0])
    upsert_chunk_embedding(db_path, chunk_ids["turn:1:feedback"], [1.0, 0.0], provider.model_name)
    upsert_chunk_embedding(db_path, chunk_ids["question:1:reference_answer"], [1.0, 0.0], provider.model_name)

    results = EmbeddingRetriever(provider).retrieve(
        db_path,
        query="Agent",
        dimension_key="agent_architecture",
    )

    assert {result.dimension_key for result in results} == {"agent_architecture"}


def test_embedding_retriever_ignores_mismatched_embedding_model(tmp_path) -> None:
    db_path = str(tmp_path / "embedding_retriever.db")
    chunk_ids = _seed_chunks(db_path)
    provider = StaticEmbeddingProvider([1.0, 0.0], model_name="test-embedding-v1")
    upsert_chunk_embedding(db_path, chunk_ids["turn:1:feedback"], [1.0, 0.0], "other-model")

    results = EmbeddingRetriever(provider).retrieve(db_path, query="Agent")

    assert results == []


def test_embedding_retriever_ignores_orphan_embeddings(tmp_path) -> None:
    db_path = str(tmp_path / "embedding_retriever.db")
    provider = StaticEmbeddingProvider([1.0, 0.0])
    upsert_chunk_embedding(db_path, 999, [1.0, 0.0], provider.model_name)

    results = EmbeddingRetriever(provider).retrieve(db_path, query="Agent")

    assert results == []


def test_embedding_retriever_invalid_embedding_json_raises(tmp_path) -> None:
    db_path = str(tmp_path / "embedding_retriever.db")
    chunk_ids = _seed_chunks(db_path)
    provider = StaticEmbeddingProvider([1.0, 0.0])
    init_chunk_embeddings_table(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO chunk_embeddings
           (chunk_id, embedding_json, embedding_model, embedding_dimension,
            content_hash, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            chunk_ids["turn:1:feedback"],
            "not-json",
            provider.model_name,
            2,
            None,
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
        ),
    )
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="invalid embedding_json"):
        EmbeddingRetriever(provider).retrieve(db_path, query="Agent")


def test_embedding_retriever_dimension_mismatch_raises(tmp_path) -> None:
    db_path = str(tmp_path / "embedding_retriever.db")
    chunk_ids = _seed_chunks(db_path)
    provider = StaticEmbeddingProvider([1.0, 0.0])
    init_chunk_embeddings_table(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO chunk_embeddings
           (chunk_id, embedding_json, embedding_model, embedding_dimension,
            content_hash, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            chunk_ids["turn:1:feedback"],
            "[1.0, 0.0]",
            provider.model_name,
            3,
            None,
            "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00",
        ),
    )
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="embedding_dimension mismatch"):
        EmbeddingRetriever(provider).retrieve(db_path, query="Agent")
