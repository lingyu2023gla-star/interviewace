"""HybridRetriever tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from knowledge.retrievers import BaseRetriever, HybridRetriever, get_retriever
from knowledge.retrievers.hybrid import _get_result_chunk_id, reciprocal_rank_fusion
from knowledge.schemas import KnowledgeSearchResult


class FakeRetriever(BaseRetriever):
    """Test retriever returning fixed results."""

    def __init__(self, results):
        self.results = results
        self.calls = []

    def retrieve(self, **kwargs):
        self.calls.append(kwargs)
        return self.results


def _result(chunk_id: int, title: str | None = None, score: float | None = None) -> KnowledgeSearchResult:
    """Build a KnowledgeSearchResult for hybrid tests."""
    return KnowledgeSearchResult(
        chunk_id=chunk_id,
        source_type="turn_feedback",
        source_id=f"turn:{chunk_id}:feedback",
        content=f"content {chunk_id}",
        title=title or f"chunk {chunk_id}",
        score=score,
    )


def test_get_retriever_hybrid_returns_hybrid_retriever() -> None:
    retriever = get_retriever("hybrid")

    assert isinstance(retriever, HybridRetriever)


def test_hybrid_retriever_empty_results_returns_empty() -> None:
    retriever = HybridRetriever(FakeRetriever([]), FakeRetriever([]))

    assert retriever.retrieve("/tmp/test.db", query="Agent") == []


def test_hybrid_retriever_keyword_only_returns_keyword_results() -> None:
    keyword_result = _result(1)
    retriever = HybridRetriever(FakeRetriever([keyword_result]), FakeRetriever([]), rrf_k=60)

    results = retriever.retrieve("/tmp/test.db", query="Agent")

    assert len(results) == 1
    assert results[0].chunk_id == 1
    assert results[0].score == pytest.approx(1 / 61)


def test_hybrid_retriever_embedding_only_returns_embedding_results() -> None:
    embedding_result = _result(2)
    retriever = HybridRetriever(FakeRetriever([]), FakeRetriever([embedding_result]), rrf_k=60)

    results = retriever.retrieve("/tmp/test.db", query="Agent")

    assert len(results) == 1
    assert results[0].chunk_id == 2
    assert results[0].score == pytest.approx(1 / 61)


def test_hybrid_retriever_uses_rrf_fusion() -> None:
    keyword_results = [_result(1), _result(2)]
    embedding_results = [_result(2), _result(3)]
    retriever = HybridRetriever(FakeRetriever(keyword_results), FakeRetriever(embedding_results), rrf_k=60)

    results = retriever.retrieve("/tmp/test.db", query="Agent", top_k=3)

    assert [result.chunk_id for result in results] == [2, 1, 3]
    scores = {result.chunk_id: result.score for result in results}
    assert scores[2] == pytest.approx(1 / 62 + 1 / 61)
    assert scores[1] == pytest.approx(1 / 61)
    assert scores[3] == pytest.approx(1 / 62)


def test_reciprocal_rank_fusion_accumulates_duplicate_ids() -> None:
    scores = reciprocal_rank_fusion(
        [[_result(1), _result(2)], [_result(2), _result(3)]],
        id_getter=lambda result: result.chunk_id,
        k=60,
    )

    assert scores[2] == pytest.approx(1 / 62 + 1 / 61)
    assert scores[2] > scores[1]
    assert scores[2] > scores[3]


def test_hybrid_retriever_respects_top_k() -> None:
    retriever = HybridRetriever(FakeRetriever([_result(1), _result(2), _result(3)]), FakeRetriever([]))

    results = retriever.retrieve("/tmp/test.db", query="Agent", top_k=2)

    assert len(results) == 2


@pytest.mark.parametrize("top_k", [0, -1, True])
def test_hybrid_retriever_invalid_top_k_raises(top_k) -> None:
    retriever = HybridRetriever(FakeRetriever([]), FakeRetriever([]))

    with pytest.raises(ValueError, match="top_k must be a positive integer"):
        retriever.retrieve("/tmp/test.db", query="Agent", top_k=top_k)


@pytest.mark.parametrize("rrf_k", [0, -1, True])
def test_hybrid_retriever_invalid_rrf_k_raises(rrf_k) -> None:
    with pytest.raises(ValueError, match="rrf_k must be a positive integer"):
        HybridRetriever(FakeRetriever([]), FakeRetriever([]), rrf_k=rrf_k)


def test_hybrid_retriever_passes_filters_to_children() -> None:
    keyword = FakeRetriever([])
    embedding = FakeRetriever([])
    retriever = HybridRetriever(keyword, embedding)

    retriever.retrieve(
        db_path="/tmp/test.db",
        query="Agent",
        session_id=1,
        source_type="turn_feedback",
        topic="Agent 架构",
        dimension_key="agent_architecture",
        top_k=2,
    )

    expected = {
        "db_path": "/tmp/test.db",
        "query": "Agent",
        "session_id": 1,
        "source_type": "turn_feedback",
        "topic": "Agent 架构",
        "dimension_key": "agent_architecture",
        "top_k": 6,
    }
    assert keyword.calls == [expected]
    assert embedding.calls == [expected]


def test_hybrid_retriever_orders_by_hybrid_score_desc() -> None:
    retriever = HybridRetriever(
        FakeRetriever([_result(1), _result(2)]),
        FakeRetriever([_result(3), _result(2)]),
    )

    results = retriever.retrieve("/tmp/test.db", query="Agent", top_k=3)

    scores = [result.score for result in results]
    assert scores == sorted(scores, reverse=True)


def test_hybrid_retriever_preserves_result_fields() -> None:
    keyword_result = KnowledgeSearchResult(
        chunk_id=1,
        source_type="turn_feedback",
        source_id="turn:1:feedback",
        content="Agent content",
        title="Agent title",
        snippet="Agent snippet",
        session_id=10,
        turn_id=20,
        question_id=30,
        job_direction="大模型应用工程师",
        topic="Agent 架构",
        dimension_key="agent_architecture",
        tags=["Agent"],
        metadata={"question": "介绍 Agent"},
        score=123.0,
    )
    retriever = HybridRetriever(FakeRetriever([keyword_result]), FakeRetriever([]))

    result = retriever.retrieve("/tmp/test.db", query="Agent")[0]

    assert result.chunk_id == keyword_result.chunk_id
    assert result.source_type == keyword_result.source_type
    assert result.source_id == keyword_result.source_id
    assert result.content == keyword_result.content
    assert result.title == keyword_result.title
    assert result.snippet == keyword_result.snippet
    assert result.session_id == keyword_result.session_id
    assert result.turn_id == keyword_result.turn_id
    assert result.question_id == keyword_result.question_id
    assert result.job_direction == keyword_result.job_direction
    assert result.topic == keyword_result.topic
    assert result.dimension_key == keyword_result.dimension_key
    assert result.tags == keyword_result.tags
    assert result.metadata == keyword_result.metadata
    assert result.score != keyword_result.score


def test_get_retriever_unknown_still_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown retriever_type"):
        get_retriever("unknown")


def test_get_result_chunk_id_supports_object_and_dict() -> None:
    assert _get_result_chunk_id(SimpleNamespace(chunk_id=1)) == 1
    assert _get_result_chunk_id(SimpleNamespace(id=2)) == 2
    assert _get_result_chunk_id({"chunk_id": 3}) == 3
    assert _get_result_chunk_id({"id": 4}) == 4


def test_get_result_chunk_id_missing_raises_value_error() -> None:
    with pytest.raises(ValueError, match="chunk_id or id"):
        _get_result_chunk_id(SimpleNamespace(title="missing"))


def test_reciprocal_rank_fusion_invalid_k_raises() -> None:
    with pytest.raises(ValueError, match="k must be a positive integer"):
        reciprocal_rank_fusion([[_result(1)]], lambda result: result.chunk_id, k=0)
