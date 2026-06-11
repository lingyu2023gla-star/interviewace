"""Preparation plan endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from api.deps import get_db_path
from api.schemas import (
    PreparationPlanApiRequest,
    PreparationPlanApiResponse,
    StructuredPreparationPlanApiRequest,
    StructuredPreparationPlanApiResponse,
    TaskSubmitResponse,
)
from preparation.schemas import PreparationPlanRequest
from preparation.service import generate_preparation_plan
from preparation.structured_service import generate_structured_preparation_plan
from worker.tasks import generate_preparation_plan_task


router = APIRouter()


def _model_to_dict(model) -> dict:
    """Convert Pydantic models to dict across v1/v2."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


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


@router.post("/structured-plan", response_model=StructuredPreparationPlanApiResponse)
def create_structured_preparation_plan(
    request: StructuredPreparationPlanApiRequest,
) -> StructuredPreparationPlanApiResponse:
    """Generate a structured JSON preparation plan."""
    result = generate_structured_preparation_plan(
        db_path=get_db_path(),
        user_goal=request.user_goal,
        job_direction=request.job_direction,
        query=request.query,
        plan_days=request.plan_days,
        daily_minutes=request.daily_minutes,
        max_tasks_per_day=request.max_tasks_per_day,
        top_k=request.top_k,
        include_prompt=request.include_prompt,
    )
    return StructuredPreparationPlanApiResponse(
        user_goal=result.user_goal,
        job_direction=result.job_direction,
        query=result.query,
        structured_plan=_model_to_dict(result.structured_plan),
        raw_output=result.raw_output,
        evidence_context=result.evidence_context,
        used_evidence_count=result.used_evidence_count,
        prompt=result.prompt,
    )


@router.post("/plan-tasks", response_model=TaskSubmitResponse, status_code=202)
def submit_preparation_plan_task(request: PreparationPlanApiRequest) -> TaskSubmitResponse:
    """Submit an asynchronous preparation plan task."""
    payload = {
        "db_path": get_db_path(),
        "user_goal": request.user_goal,
        "job_direction": request.job_direction,
        "query": request.query,
        "plan_days": request.plan_days,
        "daily_minutes": request.daily_minutes,
        "max_tasks_per_day": request.max_tasks_per_day,
        "top_k": request.top_k,
        "include_prompt": request.include_prompt,
    }
    async_result = generate_preparation_plan_task.delay(payload)
    return TaskSubmitResponse(
        task_id=async_result.id,
        status="PENDING",
        message="Preparation plan task submitted.",
    )
