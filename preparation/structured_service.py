"""Service orchestration for structured preparation plan generation."""

from __future__ import annotations

from dataclasses import dataclass

from core.analyzer import generate_text
from knowledge.context_builder import build_evidence_context
from knowledge.search import search_knowledge_chunks
from preparation.structured_parser import parse_structured_preparation_plan
from preparation.structured_schemas import StructuredPreparationPlan
from prompts.structured_preparation_plan import build_structured_preparation_plan_prompt


@dataclass(frozen=True)
class StructuredPreparationPlanResult:
    """Result returned by the structured preparation plan service."""

    user_goal: str
    job_direction: str
    query: str
    structured_plan: StructuredPreparationPlan
    raw_output: str
    evidence_context: str
    used_evidence_count: int
    prompt: str | None = None


def _validate_params(
    user_goal: str,
    plan_days: int,
    daily_minutes: int,
    max_tasks_per_day: int,
    top_k: int,
) -> None:
    """Validate structured preparation plan input parameters."""
    if not user_goal.strip():
        raise ValueError("user_goal 不能为空")
    if plan_days <= 0:
        raise ValueError("plan_days 必须大于 0")
    if daily_minutes <= 0:
        raise ValueError("daily_minutes 必须大于 0")
    if max_tasks_per_day <= 0:
        raise ValueError("max_tasks_per_day 必须大于 0")
    if top_k <= 0:
        raise ValueError("top_k 必须大于 0")


def generate_structured_preparation_plan(
    db_path: str,
    user_goal: str,
    job_direction: str = "",
    query: str = "",
    plan_days: int = 7,
    daily_minutes: int = 60,
    max_tasks_per_day: int = 3,
    top_k: int = 5,
    include_prompt: bool = False,
) -> StructuredPreparationPlanResult:
    """Generate and validate a structured JSON preparation plan."""
    _validate_params(user_goal, plan_days, daily_minutes, max_tasks_per_day, top_k)
    clean_goal = user_goal.strip()
    search_query = query.strip() or clean_goal

    results = search_knowledge_chunks(
        db_path=db_path,
        query=search_query,
        top_k=top_k,
    )
    evidence_context = build_evidence_context(results, max_chunks=top_k)
    prompt = build_structured_preparation_plan_prompt(
        user_goal=clean_goal,
        evidence_context=evidence_context,
        job_direction=job_direction,
        plan_days=plan_days,
        daily_minutes=daily_minutes,
        max_tasks_per_day=max_tasks_per_day,
    )
    raw_output = generate_text(prompt)
    structured_plan = parse_structured_preparation_plan(raw_output)

    return StructuredPreparationPlanResult(
        user_goal=clean_goal,
        job_direction=job_direction,
        query=search_query,
        structured_plan=structured_plan,
        raw_output=raw_output,
        evidence_context=evidence_context,
        used_evidence_count=len(results),
        prompt=prompt if include_prompt else None,
    )
