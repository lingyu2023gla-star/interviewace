"""Celery task status endpoints."""

from __future__ import annotations

from celery.result import AsyncResult
from fastapi import APIRouter

from api.schemas import TaskStatusResponse, TaskSubmitResponse
from worker.celery_app import celery_app
from worker.tasks import ping_task


router = APIRouter()


@router.post("/tasks/ping", response_model=TaskSubmitResponse, status_code=202)
def submit_ping_task() -> TaskSubmitResponse:
    """Submit a lightweight Celery ping task."""
    async_result = ping_task.delay({"source": "api"})
    return TaskSubmitResponse(
        task_id=async_result.id,
        status="PENDING",
        message="Ping task submitted.",
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str) -> TaskStatusResponse:
    """Return Celery task status from the result backend."""
    async_result = AsyncResult(task_id, app=celery_app)
    status = async_result.status
    ready = async_result.ready()
    successful = async_result.successful() if ready else False

    result = None
    error = None
    if ready and successful:
        result = async_result.result
    elif ready:
        error = str(async_result.result)

    return TaskStatusResponse(
        task_id=task_id,
        status=status,
        ready=ready,
        successful=successful,
        result=result,
        error=error,
    )
