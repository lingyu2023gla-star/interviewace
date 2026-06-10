"""Data structures for preparation plan generation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PreparationPlanRequest:
    """Input parameters for generating an interview preparation plan."""

    user_goal: str
    job_direction: str = ""
    query: str = ""
    plan_days: int = 7
    daily_minutes: int = 60
    max_tasks_per_day: int = 3
    top_k: int = 5


@dataclass(frozen=True)
class PreparationPlanResult:
    """Generated preparation plan plus evidence and prompt metadata."""

    user_goal: str
    job_direction: str
    query: str
    plan: str
    evidence_context: str
    used_evidence_count: int
    prompt: str | None = None
