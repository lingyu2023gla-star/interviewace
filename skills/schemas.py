"""Core schemas for InterviewAce skill execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SUPPORTED_RETRIEVER_TYPES = {"keyword", "fts", "embedding", "hybrid"}


@dataclass
class SkillRequest:
    """Input payload passed to a skill."""

    skill_name: str
    inputs: dict[str, Any]
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate basic request shape."""
        if not self.skill_name or not self.skill_name.strip():
            raise ValueError("skill_name must be non-empty")
        if not isinstance(self.inputs, dict):
            raise ValueError("inputs must be a dict")
        if not isinstance(self.context, dict):
            raise ValueError("context must be a dict")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dict")


@dataclass
class SkillResult:
    """Structured result returned by a skill."""

    skill_name: str
    output: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate basic result shape."""
        if not self.skill_name or not self.skill_name.strip():
            raise ValueError("skill_name must be non-empty")
        if not isinstance(self.output, dict):
            raise ValueError("output must be a dict")
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dict")


@dataclass(frozen=True)
class SkillSpec:
    """Metadata describing a skill and its supported execution modes."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    supported_retriever_types: tuple[str, ...] = ("keyword",)
    requires_evidence: bool = False
    supports_async: bool = False
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate immutable skill metadata."""
        if not self.name or not self.name.strip():
            raise ValueError("name must be non-empty")
        if not self.description or not self.description.strip():
            raise ValueError("description must be non-empty")
        if not isinstance(self.input_schema, dict):
            raise ValueError("input_schema must be a dict")
        if not isinstance(self.output_schema, dict):
            raise ValueError("output_schema must be a dict")

        retriever_types = tuple(self.supported_retriever_types)
        if not retriever_types:
            raise ValueError("supported_retriever_types must be non-empty")
        unsupported = set(retriever_types) - SUPPORTED_RETRIEVER_TYPES
        if unsupported:
            values = ", ".join(sorted(unsupported))
            raise ValueError(f"Unsupported retriever types: {values}")

        object.__setattr__(self, "supported_retriever_types", retriever_types)
        object.__setattr__(self, "tags", tuple(self.tags))
