"""Preparation plan endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from api.deps import get_db_path
from api.schemas import PreparationPlanApiRequest, PreparationPlanApiResponse
from preparation.schemas import PreparationPlanRequest
from preparation.service import generate_preparation_plan


router = APIRouter()


@router.post("/plan", response_model=PreparationPlanApiResponse)
def create_preparation_plan(request: PreparationPlanApiRequest) -> PreparationPlanApiResponse:
    """Generate an evidence-based interview preparation plan."""
    service_request = PreparationPlanRequest(
        user_goal=request.user_goal,
        job_direction=request.job_direction,
        query=request.query,
        plan_days=request.plan_days,
        daily_minutes=request.daily_minutes,
        max_tasks_per_day=request.max_tasks_per_day,
        top_k=request.top_k,
    )
    result = generate_preparation_plan(
        db_path=get_db_path(),
        request=service_request,
        include_prompt=request.include_prompt,
    )
    return PreparationPlanApiResponse(
        user_goal=result.user_goal,
        job_direction=result.job_direction,
        query=result.query,
        plan=result.plan,
        evidence_context=result.evidence_context,
        used_evidence_count=result.used_evidence_count,
        prompt=result.prompt,
    )
