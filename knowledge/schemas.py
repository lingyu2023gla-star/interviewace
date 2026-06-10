"""Data structures for knowledge chunk indexing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class KnowledgeChunk:
    """A traceable piece of interview knowledge ready for indexing."""

    source_type: str
    source_id: str
    content: str

    title: str | None = None
    session_id: int | None = None
    turn_id: int | None = None
    question_id: int | None = None

    job_direction: str | None = None
    topic: str | None = None
    dimension_key: str | None = None

    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IndexResult:
    """Summary of a knowledge indexing operation."""

    session_id: int
    created: int
    skipped: int
    total: int
