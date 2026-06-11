"""Service orchestration for evidence-based preparation plan generation."""

from __future__ import annotations

from core import analyzer
from knowledge.context_builder import build_evidence_context
from knowledge.retrievers import get_retriever
from preparation.schemas import PreparationPlanRequest, PreparationPlanResult
from prompts.preparation_plan import build_preparation_plan_prompt


def _validate_request(request: PreparationPlanRequest) -> None:
    """Validate preparation plan request parameters."""
    if not request.user_goal.strip():
        raise ValueError("user_goal 不能为空")
    if request.plan_days <= 0:
        raise ValueError("plan_days 必须大于 0")
    if request.daily_minutes <= 0:
        raise ValueError("daily_minutes 必须大于 0")
    if request.max_tasks_per_day <= 0:
        raise ValueError("max_tasks_per_day 必须大于 0")
    if request.top_k <= 0:
        raise ValueError("top_k 必须大于 0")


def generate_preparation_plan(
    db_path: str,
    request: PreparationPlanRequest,
    include_prompt: bool = False,
) -> PreparationPlanResult:
    """Generate a preparation plan from retrieved historical evidence."""
    _validate_request(request)
    query = request.query.strip() or request.user_goal
    retriever = get_retriever(request.retriever_type)
    results = retriever.retrieve(
        db_path=db_path,
        query=query,
        top_k=request.top_k,
    )
    evidence_context = build_evidence_context(results, max_chunks=request.top_k)
    prompt = build_preparation_plan_prompt(
        user_goal=request.user_goal,
        evidence_context=evidence_context,
        job_direction=request.job_direction,
        plan_days=request.plan_days,
        daily_minutes=request.daily_minutes,
        max_tasks_per_day=request.max_tasks_per_day,
    )
    plan = analyzer.generate_text(prompt)

    return PreparationPlanResult(
        user_goal=request.user_goal,
        job_direction=request.job_direction,
        query=query,
        plan=plan,
        evidence_context=evidence_context,
        used_evidence_count=len(results),
        prompt=prompt if include_prompt else None,
    )
