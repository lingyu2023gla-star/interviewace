"""Skill discovery and execution endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from api.deps import get_db_path
from api.schemas import (
    SkillListResponse,
    SkillRunRequest,
    SkillRunResponse,
    SkillSpecResponse,
    SkillTaskCreateResponse,
)
from skills import SkillNotFoundError, SkillRequest, create_default_skill_registry
from skills.registry import SkillRegistry
from worker.task_records import create_task_record
from worker.tasks import TASK_SKILLS_RUN_SKILL, run_skill_task_celery


router = APIRouter()


def _spec_to_response(spec) -> SkillSpecResponse:
    """Convert SkillSpec to API response schema."""
    return SkillSpecResponse(
        name=spec.name,
        description=spec.description,
        input_schema=spec.input_schema,
        output_schema=spec.output_schema,
        supported_retriever_types=list(spec.supported_retriever_types),
        requires_evidence=spec.requires_evidence,
        supports_async=spec.supports_async,
        tags=list(spec.tags),
    )


def _result_to_response(result) -> SkillRunResponse:
    """Convert SkillResult to API response schema."""
    return SkillRunResponse(
        skill_name=result.skill_name,
        success=result.success,
        output=result.output,
        metadata=result.metadata,
        error_message=result.error_message,
    )


def _registry() -> SkillRegistry:
    """Return the default skill registry."""
    return create_default_skill_registry()


def _get_skill_or_404(skill_name: str):
    """Return a skill or raise a 404 HTTP error."""
    try:
        return _registry().get(skill_name)
    except SkillNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _request_context_with_db_path(request: SkillRunRequest) -> dict:
    """Return request context with a default db_path for services and workers."""
    context = dict(request.context)
    context.setdefault("db_path", get_db_path())
    return context


@router.get("/skills", response_model=SkillListResponse)
def list_skills() -> SkillListResponse:
    """List registered skill specs."""
    registry = _registry()
    return SkillListResponse(skills=[_spec_to_response(spec) for spec in registry.list_specs()])


@router.get("/skills/{skill_name}", response_model=SkillSpecResponse)
def get_skill_spec(skill_name: str) -> SkillSpecResponse:
    """Return one registered skill spec."""
    skill = _get_skill_or_404(skill_name)
    return _spec_to_response(skill.spec)


@router.post("/skills/{skill_name}/run", response_model=SkillRunResponse)
def run_skill(skill_name: str, request: SkillRunRequest) -> SkillRunResponse:
    """Run one registered skill synchronously."""
    skill = _get_skill_or_404(skill_name)
    try:
        skill_request = SkillRequest(
            skill_name=skill_name,
            inputs=request.inputs,
            context=_request_context_with_db_path(request),
            metadata=request.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _result_to_response(skill.run(skill_request))


@router.post("/skills/{skill_name}/tasks", response_model=SkillTaskCreateResponse, status_code=202)
def submit_skill_task(skill_name: str, request: SkillRunRequest) -> SkillTaskCreateResponse:
    """Submit one registered skill for asynchronous execution."""
    skill = _get_skill_or_404(skill_name)
    if not skill.spec.supports_async:
        raise HTTPException(status_code=400, detail=f"Skill does not support async: {skill_name}")

    db_path = get_db_path()
    task_id = uuid.uuid4().hex
    payload = {
        "skill_name": skill_name,
        "inputs": request.inputs,
        "context": _request_context_with_db_path(request),
        "metadata": request.metadata,
    }
    create_task_record(
        db_path=db_path,
        task_id=task_id,
        task_name=TASK_SKILLS_RUN_SKILL,
        request=payload,
    )
    async_result = run_skill_task_celery.apply_async(args=[payload], task_id=task_id)
    return SkillTaskCreateResponse(
        task_id=async_result.id,
        skill_name=skill_name,
        status="PENDING",
    )
