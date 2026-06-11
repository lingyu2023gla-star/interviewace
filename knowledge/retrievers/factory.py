"""Factory for knowledge retriever implementations."""

from __future__ import annotations

from knowledge.retrievers.base import BaseRetriever
from knowledge.retrievers.keyword import KeywordRetriever


def get_retriever(retriever_type: str = "keyword") -> BaseRetriever:
    """Return a retriever implementation by type."""
    normalized = (retriever_type or "keyword").strip().lower()
    if normalized in {"keyword", "fts"}:
        return KeywordRetriever()
    raise ValueError("Unknown retriever_type. Available retrievers: keyword, fts")
