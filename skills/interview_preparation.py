"""Interview preparation skill backed by the structured preparation service."""

from __future__ import annotations

from typing import Any

from preparation.structured_parser import structured_plan_to_dict
from preparation.structured_service import generate_structured_preparation_plan
from skills.base import BaseSkill
from skills.registry import SkillRegistry
from skills.schemas import SkillRequest, SkillResult, SkillSpec


SKILL_NAME = "interview_preparation"


class InterviewPreparationSkill(BaseSkill):
    """Generate an evidence-based structured interview preparation plan."""

    @property
    def spec(self) -> SkillSpec:
        """Return skill metadata."""
        return SkillSpec(
            name=SKILL_NAME,
            description="Generate an evidence-based structured interview preparation plan.",
            input_schema={
                "user_goal": "str, required",
                "job_direction": "str, optional",
                "query": "str, optional",
                "plan_days": "int, optional, default 3",
                "daily_minutes": "int, optional, default 60",
                "max_tasks_per_day": "int, optional, default 3",
                "top_k": "int, optional, default 5",
                "retriever_type": "keyword | fts | embedding | hybrid, default keyword",
                "include_prompt": "bool, optional, default false",
            },
            output_schema={
                "structured_plan": "dict",
                "raw_output": "str",
                "evidence_context": "str",
                "prompt": "str | None",
                "used_evidence_count": "int",
                "metadata": "dict",
            },
            supported_retriever_types=("keyword", "fts", "embedding", "hybrid"),
            requires_evidence=True,
            supports_async=True,
            tags=("interview", "preparation", "rag", "structured-output"),
        )

    def run(self, request: SkillRequest) -> SkillResult:
        """Run structured interview preparation through the existing service."""
        if request.skill_name != self.name:
            raise ValueError(f"SkillRequest skill_name must be {self.name}")

        inputs = request.inputs
        context = request.context
        user_goal = str(inputs.get("user_goal", "")).strip()
        if not user_goal:
            raise ValueError("user_goal is required")

        db_path = str(context.get("db_path", "")).strip()
        if not db_path:
            raise ValueError("context.db_path is required")

        retriever_type = str(inputs.get("retriever_type", "keyword")).strip() or "keyword"
        result = generate_structured_preparation_plan(
            db_path=db_path,
            user_goal=user_goal,
            job_direction=str(inputs.get("job_direction", "")),
            query=str(inputs.get("query", "")),
            plan_days=int(inputs.get("plan_days", 3)),
            daily_minutes=int(inputs.get("daily_minutes", 60)),
            max_tasks_per_day=int(inputs.get("max_tasks_per_day", 3)),
            top_k=int(inputs.get("top_k", 5)),
            retriever_type=retriever_type,
            include_prompt=bool(inputs.get("include_prompt", False)),
        )

        structured_plan = structured_plan_to_dict(result.structured_plan)
        plan_metadata = structured_plan.get("metadata", {})
        output: dict[str, Any] = {
            "structured_plan": structured_plan,
            "raw_output": result.raw_output,
            "evidence_context": result.evidence_context,
            "prompt": result.prompt,
            "used_evidence_count": result.used_evidence_count,
        }
        metadata: dict[str, Any] = {
            "source": "structured_preparation_service",
            "retriever_type": retriever_type,
            "job_direction": result.job_direction,
            "plan_days": int(inputs.get("plan_days", 3)),
            "daily_minutes": int(inputs.get("daily_minutes", 60)),
            "used_evidence_count": result.used_evidence_count,
        }
        if isinstance(plan_metadata, dict) and "evidence_validation" in plan_metadata:
            metadata["evidence_validation"] = plan_metadata["evidence_validation"]

        return SkillResult(
            skill_name=self.name,
            output=output,
            metadata=metadata,
        )


def create_default_skill_registry() -> SkillRegistry:
    """Create a registry containing the currently implemented business skills."""
    from skills.project_pitch import ProjectPitchSkill

    registry = SkillRegistry()
    registry.register(InterviewPreparationSkill())
    registry.register(ProjectPitchSkill())
    return registry
