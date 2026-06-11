"""Pydantic schemas for structured preparation plan output."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvidenceBasedJudgment(BaseModel):
    """A judgment grounded in historical interview evidence."""

    type: str = Field(
        ...,
        description="strength | weakness | insufficient_evidence | coverage_gap",
    )
    content: str
    evidence_refs: list[str] = Field(default_factory=list)


class DailyTask(BaseModel):
    """One concrete preparation task for a day."""

    task: str
    estimated_minutes: int
    output: str
    evidence_refs: list[str] = Field(default_factory=list)


class DailyPlanItem(BaseModel):
    """A daily preparation plan item."""

    day: int
    goal: str
    tasks: list[DailyTask]


class QuestionTemplate(BaseModel):
    """A structured answer template for one interview question."""

    question: str
    answer_goal: str
    answer_structure: list[str]
    sample_answer: str
    evidence_refs: list[str] = Field(default_factory=list)


class AbilityToShow(BaseModel):
    """An ability that should be actively shown in the next interview."""

    ability: str
    why_needed: str
    current_evidence_status: str
    how_to_show_next_time: str


class RiskWarning(BaseModel):
    """A warning about over-packaging or unsupported claims."""

    risk: str
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)


class StructuredPreparationPlan(BaseModel):
    """Structured JSON preparation plan generated from historical evidence."""

    summary: str
    evidence_based_judgments: list[EvidenceBasedJudgment]
    daily_plan: list[DailyPlanItem]
    question_templates: list[QuestionTemplate]
    abilities_to_show: list[AbilityToShow]
    risk_warnings: list[RiskWarning]
    metadata: dict[str, Any] = Field(default_factory=dict)
