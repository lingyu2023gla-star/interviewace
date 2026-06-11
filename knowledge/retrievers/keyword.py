"""Keyword retriever backed by the existing knowledge search service."""

from __future__ import annotations

from knowledge.retrievers.base import BaseRetriever
from knowledge.schemas import KnowledgeSearchResult
from knowledge.search import search_knowledge_chunks


class KeywordRetriever(BaseRetriever):
    """Retriever that delegates to search_knowledge_chunks."""

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
        """Retrieve chunks using existing keyword / FTS search."""
        return search_knowledge_chunks(
            db_path=db_path,
            query=query,
            session_id=session_id,
            source_type=source_type,
            topic=topic,
            dimension_key=dimension_key,
            top_k=top_k,
        )
