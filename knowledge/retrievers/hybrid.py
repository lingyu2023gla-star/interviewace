"""Hybrid retriever using reciprocal rank fusion."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable

from knowledge.retrievers.base import BaseRetriever
from knowledge.retrievers.embedding import EmbeddingRetriever
from knowledge.retrievers.keyword import KeywordRetriever
from knowledge.schemas import KnowledgeSearchResult


def _validate_positive_integer(value: int, name: str) -> None:
    """Validate that a value is a positive integer."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _get_result_chunk_id(result: Any) -> Any:
    """Extract a chunk id from object-like or dict-like results."""
    if hasattr(result, "chunk_id"):
        return getattr(result, "chunk_id")
    if hasattr(result, "id"):
        return getattr(result, "id")
    if isinstance(result, dict):
        if "chunk_id" in result:
            return result["chunk_id"]
        if "id" in result:
            return result["id"]
    raise ValueError("retriever result must include chunk_id or id")


def reciprocal_rank_fusion(
    ranked_lists: list[list[Any]],
    id_getter: Callable[[Any], Any],
    k: int = 60,
) -> dict[Any, float]:
    """Fuse ranked result lists with reciprocal rank fusion."""
    _validate_positive_integer(k, "k")
    scores: dict[Any, float] = {}
    for ranked_list in ranked_lists:
        for rank, result in enumerate(ranked_list, start=1):
            result_id = id_getter(result)
            scores[result_id] = scores.get(result_id, 0.0) + 1.0 / (k + rank)
    return scores


class HybridRetriever(BaseRetriever):
    """Combine keyword and embedding retrieval results with RRF."""

    def __init__(
        self,
        keyword_retriever: BaseRetriever | None = None,
        embedding_retriever: BaseRetriever | None = None,
        rrf_k: int = 60,
    ) -> None:
        """Create a hybrid retriever."""
        _validate_positive_integer(rrf_k, "rrf_k")
        self.keyword_retriever = keyword_retriever or KeywordRetriever()
        self.embedding_retriever = embedding_retriever or EmbeddingRetriever()
        self.rrf_k = rrf_k

    def retrieve(
        self,
        db_path: str,
        query: str,
        session_id: int | None = None,
        source_type: str | None = None,
        topic: str | None = None,
        dimension_key: str | None = None,
        top_k: int = 5,
    ) -> list[KnowledgeSearchResult]:
        """Retrieve and fuse keyword and embedding results."""
        _validate_positive_integer(top_k, "top_k")
        candidate_k = max(top_k * 3, top_k)
        common_kwargs = {
            "db_path": db_path,
            "query": query,
            "session_id": session_id,
            "source_type": source_type,
            "topic": topic,
            "dimension_key": dimension_key,
            "top_k": candidate_k,
        }
        keyword_results = self.keyword_retriever.retrieve(**common_kwargs)
        embedding_results = self.embedding_retriever.retrieve(**common_kwargs)
        if not keyword_results and not embedding_results:
            return []

        rrf_scores = reciprocal_rank_fusion(
            [keyword_results, embedding_results],
            id_getter=_get_result_chunk_id,
            k=self.rrf_k,
        )
        merged: dict[Any, KnowledgeSearchResult] = {}
        for result in [*keyword_results, *embedding_results]:
            chunk_id = _get_result_chunk_id(result)
            if chunk_id not in merged:
                merged[chunk_id] = result

        fused_results = [
            replace(result, score=rrf_scores[chunk_id])
            for chunk_id, result in merged.items()
        ]
        fused_results.sort(key=lambda result: (result.score or 0.0, result.chunk_id), reverse=True)
        return fused_results[:top_k]
