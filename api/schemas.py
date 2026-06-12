"""Pydantic schemas for InterviewAce API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RetrieverType = Literal["keyword", "fts", "embedding", "hybrid"]


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
    retriever_type: RetrieverType = "keyword"
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


class StructuredPreparationPlanApiRequest(BaseModel):
    user_goal: str = Field(..., min_length=1)
    job_direction: str = ""
    query: str = ""
    retriever_type: RetrieverType = "keyword"
    plan_days: int = Field(default=7, ge=1, le=30)
    daily_minutes: int = Field(default=60, ge=10, le=240)
    max_tasks_per_day: int = Field(default=3, ge=1, le=8)
    top_k: int = Field(default=5, ge=1, le=20)
    include_prompt: bool = False


class StructuredPreparationPlanApiResponse(BaseModel):
    user_goal: str
    job_direction: str
    query: str
    structured_plan: dict[str, Any]
    raw_output: str
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
    task_record: dict[str, Any] | None = None


class SkillRunRequest(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillRunResponse(BaseModel):
    skill_name: str
    success: bool
    output: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


class SkillTaskCreateResponse(BaseModel):
    task_id: str
    skill_name: str
    status: str = "PENDING"


class SkillSpecResponse(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    supported_retriever_types: list[str]
    requires_evidence: bool
    supports_async: bool
    tags: list[str] = Field(default_factory=list)


class SkillListResponse(BaseModel):
    skills: list[SkillSpecResponse]
