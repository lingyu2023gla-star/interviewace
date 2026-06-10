"""Pydantic schemas for InterviewAce API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    session_id: int | None = None
    source_type: str | None = None
    topic: str | None = None
    dimension_key: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class KnowledgeSearchItem(BaseModel):
    chunk_id: int
    source_type: str
    source_id: str
    content: str
    title: str | None = None
    snippet: str | None = None

    session_id: int | None = None
    turn_id: int | None = None
    question_id: int | None = None

    job_direction: str | None = None
    topic: str | None = None
    dimension_key: str | None = None

    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None


class KnowledgeSearchResponse(BaseModel):
    query: str
    total: int
    results: list[KnowledgeSearchItem]


class EvidenceContextRequest(BaseModel):
    query: str = Field(..., min_length=1)
    session_id: int | None = None
    source_type: str | None = None
    topic: str | None = None
    dimension_key: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    max_content_chars: int = Field(default=600, ge=50, le=3000)


class EvidenceContextResponse(BaseModel):
    query: str
    used_evidence_count: int
    evidence_context: str


class PreparationPlanApiRequest(BaseModel):
    user_goal: str = Field(..., min_length=1)
    job_direction: str = ""
    query: str = ""
    plan_days: int = Field(default=7, ge=1, le=30)
    daily_minutes: int = Field(default=60, ge=10, le=240)
    max_tasks_per_day: int = Field(default=3, ge=1, le=8)
    top_k: int = Field(default=5, ge=1, le=20)
    include_prompt: bool = False


class PreparationPlanApiResponse(BaseModel):
    user_goal: str
    job_direction: str
    query: str
    plan: str
    evidence_context: str
    used_evidence_count: int
    prompt: str | None = None


class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    ready: bool
    successful: bool
    result: dict[str, Any] | None = None
    error: str | None = None
