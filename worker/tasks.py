"""Celery tasks for InterviewAce."""

from __future__ import annotations

import os
from typing import Callable

from preparation.schemas import PreparationPlanRequest
from preparation.service import generate_preparation_plan
from preparation.structured_parser import structured_plan_to_dict
from preparation.structured_service import generate_structured_preparation_plan
from skills import SkillRequest, SkillResult, create_default_skill_registry
from worker.celery_app import celery_app
from worker.task_records import mark_task_failure, mark_task_started, mark_task_success


TASK_SYSTEM_PING = "system.ping"
TASK_PREPARATION_GENERATE_PLAN = "preparation.generate_plan"
TASK_PREPARATION_GENERATE_STRUCTURED_PLAN = "preparation.generate_structured_plan"
TASK_SKILLS_RUN_SKILL = "skills.run_skill"


def _task_db_path(payload: dict | None = None) -> str:
    """Return DB path for task record updates."""
    if payload and payload.get("db_path"):
        return payload["db_path"]
    if payload and isinstance(payload.get("context"), dict) and payload["context"].get("db_path"):
        return payload["context"]["db_path"]
    return os.getenv("INTERVIEWACE_DB_PATH", "data/interviews.db")


def _task_id_from_request(task_self, fallback: str | None = None) -> str | None:
    """Return current Celery task id when available."""
    request = getattr(task_self, "request", None)
    return getattr(request, "id", None) or fallback


def _safe_mark_started(db_path: str, task_id: str | None) -> None:
    """Mark task started without affecting the task outcome."""
    if not task_id:
        return
    try:
        mark_task_started(db_path, task_id)
    except Exception:
        pass


def _safe_mark_success(db_path: str, task_id: str | None, result) -> None:
    """Mark task success without affecting the task outcome."""
    if not task_id:
        return
    try:
        mark_task_success(db_path, task_id, result)
    except Exception:
        pass


def _safe_mark_failure(db_path: str, task_id: str | None, exc: Exception) -> None:
    """Mark task failure without swallowing the original exception."""
    if not task_id:
        return
    try:
        mark_task_failure(db_path, task_id, str(exc))
    except Exception:
        pass


def _run_tracked_task(task_self, payload: dict | None, runner: Callable[[], dict]) -> dict:
    """Run a Celery task and persist STARTED/SUCCESS/FAILURE transitions."""
    db_path = _task_db_path(payload)
    task_id = _task_id_from_request(task_self)
    _safe_mark_started(db_path, task_id)
    try:
        result = runner()
    except Exception as exc:
        _safe_mark_failure(db_path, task_id, exc)
        raise
    _safe_mark_success(db_path, task_id, result)
    return result


def run_ping_task(payload: dict | None = None) -> dict:
    """Return a lightweight JSON-serializable ping response."""
    payload = payload or {}
    return {
        "status": "ok",
        "message": "pong",
        "payload": payload,
    }


def skill_result_to_dict(result: SkillResult) -> dict:
    """Convert SkillResult to a JSON-compatible dict."""
    return {
        "skill_name": result.skill_name,
        "success": result.success,
        "output": result.output,
        "metadata": result.metadata,
        "error_message": result.error_message,
    }


@celery_app.task(name=TASK_SYSTEM_PING, bind=True)
def ping_task(self, payload: dict | None = None) -> dict:
    """Celery ping task for local Redis/worker integration checks."""
    public_payload = dict(payload or {})
    public_payload.pop("db_path", None)
    return _run_tracked_task(
        self,
        payload,
        lambda: run_ping_task(public_payload),
    )


def run_generate_preparation_plan_task(payload: dict) -> dict:
    """Run preparation plan generation from a JSON-serializable payload."""
    db_path = payload.get("db_path")
    if not db_path:
        raise ValueError("db_path is required")

    request = PreparationPlanRequest(
        user_goal=payload["user_goal"],
        job_direction=payload.get("job_direction", ""),
        query=payload.get("query", ""),
        retriever_type=payload.get("retriever_type", "keyword"),
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


@celery_app.task(name=TASK_PREPARATION_GENERATE_PLAN, bind=True)
def generate_preparation_plan_task(self, payload: dict) -> dict:
    """Celery wrapper for preparation plan generation."""
    return _run_tracked_task(
        self,
        payload,
        lambda: run_generate_preparation_plan_task(payload),
    )


def run_generate_structured_preparation_plan_task(payload: dict) -> dict:
    """Run structured preparation plan generation from a JSON payload."""
    db_path = payload.get("db_path")
    if not db_path:
        raise ValueError("db_path is required")

    result = generate_structured_preparation_plan(
        db_path=db_path,
        user_goal=payload["user_goal"],
        job_direction=payload.get("job_direction", ""),
        query=payload.get("query", ""),
        retriever_type=payload.get("retriever_type", "keyword"),
        plan_days=payload.get("plan_days", 7),
        daily_minutes=payload.get("daily_minutes", 60),
        max_tasks_per_day=payload.get("max_tasks_per_day", 3),
        top_k=payload.get("top_k", 5),
        include_prompt=bool(payload.get("include_prompt", False)),
    )
    return {
        "user_goal": result.user_goal,
        "job_direction": result.job_direction,
        "query": result.query,
        "structured_plan": structured_plan_to_dict(result.structured_plan),
        "raw_output": result.raw_output,
        "evidence_context": result.evidence_context,
        "used_evidence_count": result.used_evidence_count,
        "prompt": result.prompt,
    }


@celery_app.task(name=TASK_PREPARATION_GENERATE_STRUCTURED_PLAN, bind=True)
def generate_structured_preparation_plan_task(self, payload: dict) -> dict:
    """Celery wrapper for structured preparation plan generation."""
    return _run_tracked_task(
        self,
        payload,
        lambda: run_generate_structured_preparation_plan_task(payload),
    )


def run_skill_task(payload: dict) -> dict:
    """Run a registered skill from a JSON-serializable payload."""
    skill_name = payload.get("skill_name")
    if not skill_name:
        raise ValueError("skill_name is required")

    inputs = payload.get("inputs") or {}
    context = payload.get("context") or {}
    metadata = payload.get("metadata") or {}
    registry = create_default_skill_registry()
    skill = registry.get(skill_name)
    request = SkillRequest(
        skill_name=skill_name,
        inputs=inputs,
        context=context,
        metadata=metadata,
    )
    return skill_result_to_dict(skill.run(request))


@celery_app.task(name=TASK_SKILLS_RUN_SKILL, bind=True)
def run_skill_task_celery(self, payload: dict) -> dict:
    """Celery wrapper for registered skill execution."""
    return _run_tracked_task(
        self,
        payload,
        lambda: run_skill_task(payload),
    )
