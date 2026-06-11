"""Celery task status endpoints."""

from __future__ import annotations

import uuid

from celery.result import AsyncResult
from fastapi import APIRouter

from api.deps import get_db_path
from api.schemas import TaskStatusResponse, TaskSubmitResponse
from worker.celery_app import celery_app
from worker.task_records import create_task_record, get_task_record
from worker.tasks import TASK_SYSTEM_PING, ping_task


router = APIRouter()


@router.post("/tasks/ping", response_model=TaskSubmitResponse, status_code=202)
def submit_ping_task() -> TaskSubmitResponse:
    """Submit a lightweight Celery ping task."""
    db_path = get_db_path()
    task_id = uuid.uuid4().hex
    payload = {"source": "api", "db_path": db_path}
    create_task_record(
        db_path=db_path,
        task_id=task_id,
        task_name=TASK_SYSTEM_PING,
        request=payload,
    )
    async_result = ping_task.apply_async(args=[payload], task_id=task_id)
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

    task_record = get_task_record(get_db_path(), task_id)
    return TaskStatusResponse(
        task_id=task_id,
        status=status,
        ready=ready,
        successful=successful,
        result=result,
        error=error,
        task_record=task_record,
    )
