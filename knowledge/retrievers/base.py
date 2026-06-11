"""Base abstraction for knowledge retrievers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from knowledge.schemas import KnowledgeSearchResult


class BaseRetriever(ABC):
    """Abstract interface for retrieving knowledge chunks."""

    @abstractmethod
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
        """Retrieve knowledge chunks matching a query."""
