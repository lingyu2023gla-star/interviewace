"""Celery tasks for InterviewAce."""

from __future__ import annotations

from preparation.schemas import PreparationPlanRequest
from preparation.service import generate_preparation_plan
from worker.celery_app import celery_app


def run_generate_preparation_plan_task(payload: dict) -> dict:
    """Run preparation plan generation from a JSON-serializable payload."""
    db_path = payload.get("db_path")
    if not db_path:
        raise ValueError("db_path is required")

    request = PreparationPlanRequest(
        user_goal=payload["user_goal"],
        job_direction=payload.get("job_direction", ""),
        query=payload.get("query", ""),
        plan_days=payload.get("plan_days", 7),
        daily_minutes=payload.get("daily_minutes", 60),
        max_tasks_per_day=payload.get("max_tasks_per_day", 3),
        top_k=payload.get("top_k", 5),
    )
    result = generate_preparation_plan(
        db_path=db_path,
        request=request,
        include_prompt=bool(payload.get("include_prompt", False)),
    )
    return {
        "user_goal": result.user_goal,
        "job_direction": result.job_direction,
        "query": result.query,
        "plan": result.plan,
        "evidence_context": result.evidence_context,
        "used_evidence_count": result.used_evidence_count,
        "prompt": result.prompt,
    }


@celery_app.task(name="preparation.generate_plan")
def generate_preparation_plan_task(payload: dict) -> dict:
    """Celery wrapper for preparation plan generation."""
    return run_generate_preparation_plan_task(payload)
