"""Skill evaluation tests."""

from __future__ import annotations

from skills import (
    BaseSkill,
    SkillEvalCase,
    SkillRegistry,
    SkillRequest,
    SkillResult,
    SkillSpec,
    evaluate_skill_result,
    run_skill_eval_case,
    run_skill_eval_cases,
)


class DummySkill(BaseSkill):
    """A deterministic skill for evaluation tests."""

    @property
    def spec(self) -> SkillSpec:
        return SkillSpec(
            name="dummy",
            description="Dummy skill for evaluation tests.",
            input_schema={"text": "str"},
            output_schema={"text": "str"},
            supported_retriever_types=("keyword",),
        )

    def run(self, request: SkillRequest) -> SkillResult:
        return SkillResult(
            skill_name=self.name,
            output={
                "text": request.inputs.get("text", ""),
                "evidence_validation": {"is_valid": True, "issues": []},
            },
            metadata={"source": "dummy"},
        )


class FailingSkill(DummySkill):
    """A skill that always fails during execution."""

    def run(self, request: SkillRequest) -> SkillResult:
        raise RuntimeError("skill failed")


def _request(skill_name: str = "dummy") -> SkillRequest:
    return SkillRequest(skill_name=skill_name, inputs={"text": "hello"})


def _case(**kwargs) -> SkillEvalCase:
    values = {
        "name": "dummy-case",
        "skill_name": "dummy",
        "request": _request(),
        "required_output_keys": ("text",),
        "required_metadata_keys": ("source",),
    }
    values.update(kwargs)
    return SkillEvalCase(**values)


def _result(**kwargs) -> SkillResult:
    values = {
        "skill_name": "dummy",
        "output": {"text": "hello"},
        "metadata": {"source": "test"},
    }
    values.update(kwargs)
    return SkillResult(**values)


def _metric(result, name: str):
    return next(metric for metric in result.metrics if metric.name == name)


def test_evaluate_skill_result_success_passes() -> None:
    result = evaluate_skill_result(_case(), _result())

    assert result.passed is True
    assert all(metric.passed for metric in result.metrics)


def test_evaluate_skill_result_missing_output_key_fails() -> None:
    result = evaluate_skill_result(_case(required_output_keys=("missing",)), _result())

    metric = _metric(result, "required_output_keys")
    assert result.passed is False
    assert metric.passed is False
    assert metric.details["missing"] == ["missing"]


def test_evaluate_skill_result_missing_metadata_key_fails() -> None:
    result = evaluate_skill_result(_case(required_metadata_keys=("missing",)), _result())

    metric = _metric(result, "required_metadata_keys")
    assert result.passed is False
    assert metric.passed is False
    assert metric.details["missing"] == ["missing"]


def test_evaluate_skill_result_unsuccessful_fails() -> None:
    result = evaluate_skill_result(_case(), _result(success=False))

    metric = _metric(result, "success")
    assert result.passed is False
    assert metric.passed is False


def test_evaluate_skill_result_error_message_fails() -> None:
    result = evaluate_skill_result(_case(), _result(error_message="failed"))

    metric = _metric(result, "error_message")
    assert result.passed is False
    assert metric.passed is False
    assert metric.details["error_message"] == "failed"


def test_evaluate_skill_result_skill_name_mismatch_fails() -> None:
    result = evaluate_skill_result(_case(skill_name="expected"), _result(skill_name="actual"))

    metric = _metric(result, "skill_name")
    assert result.passed is False
    assert metric.passed is False
    assert metric.details == {"expected": "expected", "actual": "actual"}


def test_evaluate_skill_result_missing_evidence_validation_fails() -> None:
    result = evaluate_skill_result(_case(require_evidence_validation=True), _result())

    metric = _metric(result, "evidence_validation_present")
    assert result.passed is False
    assert metric.passed is False


def test_evaluate_skill_result_invalid_evidence_validation_fails() -> None:
    result = evaluate_skill_result(
        _case(require_valid_evidence=True),
        _result(metadata={"source": "test", "evidence_validation": {"is_valid": False}}),
    )

    metric = _metric(result, "evidence_validation_valid")
    assert result.passed is False
    assert metric.passed is False
    assert metric.details["is_valid"] is False


def test_evaluate_skill_result_finds_evidence_validation_in_metadata() -> None:
    result = evaluate_skill_result(
        _case(require_valid_evidence=True),
        _result(metadata={"source": "test", "evidence_validation": {"is_valid": True}}),
    )

    assert result.passed is True
    assert _metric(result, "evidence_validation_valid").passed is True


def test_evaluate_skill_result_finds_evidence_validation_in_output() -> None:
    result = evaluate_skill_result(
        _case(require_valid_evidence=True),
        _result(output={"text": "hello", "evidence_validation": {"is_valid": True}}),
    )

    assert result.passed is True
    assert _metric(result, "evidence_validation_present").passed is True


def test_run_skill_eval_case_runs_dummy_skill() -> None:
    registry = SkillRegistry()
    registry.register(DummySkill())
    case = _case(require_valid_evidence=True)

    result = run_skill_eval_case(registry, case)

    assert result.passed is True
    assert result.result is not None
    assert result.result.output["text"] == "hello"


def test_run_skill_eval_case_catches_skill_error() -> None:
    registry = SkillRegistry()
    registry.register(FailingSkill())
    case = _case()

    result = run_skill_eval_case(registry, case)

    assert result.passed is False
    assert result.result is None
    assert result.error_message == "skill failed"
    assert _metric(result, "run").passed is False


def test_run_skill_eval_cases_preserves_order() -> None:
    registry = SkillRegistry()
    registry.register(DummySkill())
    cases = [
        _case(name="case-1"),
        _case(name="case-2", required_output_keys=("missing",)),
    ]

    results = run_skill_eval_cases(registry, cases)

    assert [result.case_name for result in results] == ["case-1", "case-2"]
    assert results[0].passed is True
    assert results[1].passed is False
