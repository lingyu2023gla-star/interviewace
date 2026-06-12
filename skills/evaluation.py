"""Lightweight evaluation helpers for SkillResult quality checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from skills.registry import SkillRegistry
from skills.schemas import SkillRequest, SkillResult


@dataclass(frozen=True)
class SkillEvalCase:
    """A deterministic evaluation case for a skill result."""

    name: str
    skill_name: str
    request: SkillRequest
    required_output_keys: tuple[str, ...] = ()
    required_metadata_keys: tuple[str, ...] = ()
    require_success: bool = True
    require_evidence_validation: bool = False
    require_valid_evidence: bool = False

    def __post_init__(self) -> None:
        """Validate case shape."""
        if not self.name or not self.name.strip():
            raise ValueError("name must be non-empty")
        if not self.skill_name or not self.skill_name.strip():
            raise ValueError("skill_name must be non-empty")
        if not isinstance(self.request, SkillRequest):
            raise ValueError("request must be a SkillRequest")
        object.__setattr__(self, "required_output_keys", tuple(self.required_output_keys))
        object.__setattr__(self, "required_metadata_keys", tuple(self.required_metadata_keys))


@dataclass(frozen=True)
class SkillEvalMetric:
    """One deterministic evaluation metric outcome."""

    name: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillEvalResult:
    """Evaluation result for one skill eval case."""

    case_name: str
    skill_name: str
    passed: bool
    metrics: list[SkillEvalMetric]
    result: SkillResult | None = None
    error_message: str | None = None


def _metric(name: str, passed: bool, message: str, details: dict[str, Any] | None = None) -> SkillEvalMetric:
    """Create a metric with normalized details."""
    return SkillEvalMetric(
        name=name,
        passed=passed,
        message=message,
        details=details or {},
    )


def _find_evidence_validation(result: SkillResult) -> dict[str, Any] | None:
    """Return evidence_validation from metadata first, then output."""
    metadata_value = result.metadata.get("evidence_validation")
    if isinstance(metadata_value, dict):
        return metadata_value

    output_value = result.output.get("evidence_validation")
    if isinstance(output_value, dict):
        return output_value
    return None


def evaluate_skill_result(case: SkillEvalCase, result: SkillResult) -> SkillEvalResult:
    """Evaluate whether a SkillResult satisfies deterministic case requirements."""
    metrics: list[SkillEvalMetric] = []

    metrics.append(
        _metric(
            name="skill_name",
            passed=result.skill_name == case.skill_name,
            message="Skill name matches expected value."
            if result.skill_name == case.skill_name
            else "Skill name does not match expected value.",
            details={"expected": case.skill_name, "actual": result.skill_name},
        )
    )

    if case.require_success:
        metrics.append(
            _metric(
                name="success",
                passed=result.success is True,
                message="Skill result succeeded." if result.success is True else "Skill result did not succeed.",
                details={"actual": result.success},
            )
        )
        metrics.append(
            _metric(
                name="error_message",
                passed=result.error_message is None,
                message="Skill result has no error message."
                if result.error_message is None
                else "Skill result has an error message.",
                details={"error_message": result.error_message},
            )
        )

    missing_output_keys = [key for key in case.required_output_keys if key not in result.output]
    metrics.append(
        _metric(
            name="required_output_keys",
            passed=not missing_output_keys,
            message="All required output keys are present."
            if not missing_output_keys
            else "Required output keys are missing.",
            details={"missing": missing_output_keys},
        )
    )

    missing_metadata_keys = [key for key in case.required_metadata_keys if key not in result.metadata]
    metrics.append(
        _metric(
            name="required_metadata_keys",
            passed=not missing_metadata_keys,
            message="All required metadata keys are present."
            if not missing_metadata_keys
            else "Required metadata keys are missing.",
            details={"missing": missing_metadata_keys},
        )
    )

    evidence_validation = _find_evidence_validation(result)
    if case.require_evidence_validation or case.require_valid_evidence:
        metrics.append(
            _metric(
                name="evidence_validation_present",
                passed=evidence_validation is not None,
                message="evidence_validation is present."
                if evidence_validation is not None
                else "evidence_validation is missing.",
            )
        )

    if case.require_valid_evidence:
        is_valid = evidence_validation.get("is_valid") if isinstance(evidence_validation, dict) else None
        metrics.append(
            _metric(
                name="evidence_validation_valid",
                passed=is_valid is True,
                message="evidence_validation is valid."
                if is_valid is True
                else "evidence_validation is not valid.",
                details={"is_valid": is_valid},
            )
        )

    return SkillEvalResult(
        case_name=case.name,
        skill_name=case.skill_name,
        passed=all(metric.passed for metric in metrics),
        metrics=metrics,
        result=result,
    )


def run_skill_eval_case(registry: SkillRegistry, case: SkillEvalCase) -> SkillEvalResult:
    """Run a skill eval case and convert exceptions into a failed eval result."""
    try:
        skill = registry.get(case.skill_name)
        result = skill.run(case.request)
    except Exception as exc:
        return SkillEvalResult(
            case_name=case.name,
            skill_name=case.skill_name,
            passed=False,
            metrics=[
                _metric(
                    name="run",
                    passed=False,
                    message="Skill eval case raised an exception.",
                    details={"error": str(exc)},
                )
            ],
            result=None,
            error_message=str(exc),
        )
    return evaluate_skill_result(case, result)


def run_skill_eval_cases(registry: SkillRegistry, cases: list[SkillEvalCase]) -> list[SkillEvalResult]:
    """Run multiple skill eval cases in input order without short-circuiting."""
    return [run_skill_eval_case(registry, case) for case in cases]
