"""InterviewPreparationSkill tests."""

from __future__ import annotations

import pytest

from skills import InterviewPreparationSkill, SkillRequest, SkillResult, create_default_skill_registry


class FakeStructuredPlan:
    """Fake structured plan compatible with structured_plan_to_dict."""

    def model_dump(self) -> dict:
        return {
            "summary": "mock summary",
            "evidence_based_judgments": [
                {
                    "type": "strength",
                    "content": "候选人讲到了 Agent 架构。",
                    "evidence_refs": ["E1"],
                }
            ],
            "daily_plan": [],
            "question_templates": [],
            "abilities_to_show": [],
            "risk_warnings": [],
            "metadata": {
                "evidence_validation": {
                    "is_valid": True,
                    "valid_evidence_ids": ["E1"],
                    "used_evidence_refs": ["E1"],
                    "issues": [],
                }
            },
        }


class FakeServiceResult:
    """Fake result returned by the structured preparation service."""

    user_goal = "准备 Agent/RAG 应用工程师面试"
    job_direction = "大模型应用工程师"
    query = "Agent"
    structured_plan = FakeStructuredPlan()
    raw_output = '{"summary":"mock summary"}'
    evidence_context = "[E1]\n证据内容"
    used_evidence_count = 1
    prompt = None


def _request(inputs: dict | None = None, context: dict | None = None) -> SkillRequest:
    payload = {
        "user_goal": "准备 Agent/RAG 应用工程师面试",
        "job_direction": "大模型应用工程师",
        "query": "Agent",
    }
    if inputs:
        payload.update(inputs)
    return SkillRequest(
        skill_name="interview_preparation",
        inputs=payload,
        context=context if context is not None else {"db_path": "/tmp/test.db"},
    )


def test_interview_preparation_skill_spec() -> None:
    spec = InterviewPreparationSkill().spec

    assert spec.name == "interview_preparation"
    assert spec.description == "Generate an evidence-based structured interview preparation plan."
    assert set(spec.supported_retriever_types) == {"keyword", "fts", "embedding", "hybrid"}
    assert spec.requires_evidence is True
    assert spec.supports_async is False
    assert "structured-output" in spec.tags
    assert "user_goal" in spec.input_schema
    assert "structured_plan" in spec.output_schema


def test_interview_preparation_skill_run_calls_structured_service(monkeypatch) -> None:
    captured = {}

    def fake_generate_structured_preparation_plan(**kwargs):
        captured.update(kwargs)
        return FakeServiceResult()

    monkeypatch.setattr(
        "skills.interview_preparation.generate_structured_preparation_plan",
        fake_generate_structured_preparation_plan,
    )

    result = InterviewPreparationSkill().run(_request())

    assert captured["db_path"] == "/tmp/test.db"
    assert captured["user_goal"] == "准备 Agent/RAG 应用工程师面试"
    assert captured["job_direction"] == "大模型应用工程师"
    assert captured["query"] == "Agent"
    assert isinstance(result, SkillResult)


def test_interview_preparation_skill_default_retriever_type_is_keyword(monkeypatch) -> None:
    captured = {}

    def fake_generate_structured_preparation_plan(**kwargs):
        captured.update(kwargs)
        return FakeServiceResult()

    monkeypatch.setattr(
        "skills.interview_preparation.generate_structured_preparation_plan",
        fake_generate_structured_preparation_plan,
    )

    InterviewPreparationSkill().run(_request(inputs={"retriever_type": ""}))

    assert captured["retriever_type"] == "keyword"


def test_interview_preparation_skill_passes_hybrid_retriever_type(monkeypatch) -> None:
    captured = {}

    def fake_generate_structured_preparation_plan(**kwargs):
        captured.update(kwargs)
        return FakeServiceResult()

    monkeypatch.setattr(
        "skills.interview_preparation.generate_structured_preparation_plan",
        fake_generate_structured_preparation_plan,
    )

    InterviewPreparationSkill().run(_request(inputs={"retriever_type": "hybrid"}))

    assert captured["retriever_type"] == "hybrid"


def test_interview_preparation_skill_passes_plan_params(monkeypatch) -> None:
    captured = {}

    def fake_generate_structured_preparation_plan(**kwargs):
        captured.update(kwargs)
        return FakeServiceResult()

    monkeypatch.setattr(
        "skills.interview_preparation.generate_structured_preparation_plan",
        fake_generate_structured_preparation_plan,
    )

    InterviewPreparationSkill().run(
        _request(
            inputs={
                "plan_days": 5,
                "daily_minutes": 45,
                "max_tasks_per_day": 2,
                "top_k": 4,
                "include_prompt": True,
            }
        )
    )

    assert captured["plan_days"] == 5
    assert captured["daily_minutes"] == 45
    assert captured["max_tasks_per_day"] == 2
    assert captured["top_k"] == 4
    assert captured["include_prompt"] is True


def test_interview_preparation_skill_returns_skill_result(monkeypatch) -> None:
    monkeypatch.setattr(
        "skills.interview_preparation.generate_structured_preparation_plan",
        lambda **kwargs: FakeServiceResult(),
    )

    result = InterviewPreparationSkill().run(_request(inputs={"retriever_type": "hybrid"}))

    assert result.skill_name == "interview_preparation"
    assert result.success is True
    assert result.output["structured_plan"]["summary"] == "mock summary"
    assert result.output["raw_output"] == '{"summary":"mock summary"}'
    assert result.output["evidence_context"] == "[E1]\n证据内容"
    assert result.output["used_evidence_count"] == 1
    assert result.metadata["retriever_type"] == "hybrid"
    assert result.metadata["source"] == "structured_preparation_service"


def test_interview_preparation_skill_preserves_evidence_validation(monkeypatch) -> None:
    monkeypatch.setattr(
        "skills.interview_preparation.generate_structured_preparation_plan",
        lambda **kwargs: FakeServiceResult(),
    )

    result = InterviewPreparationSkill().run(_request())

    assert result.output["structured_plan"]["metadata"]["evidence_validation"]["is_valid"] is True
    assert result.metadata["evidence_validation"]["is_valid"] is True


def test_interview_preparation_skill_missing_user_goal_raises() -> None:
    request = SkillRequest(
        skill_name="interview_preparation",
        inputs={"job_direction": "大模型应用工程师"},
        context={"db_path": "/tmp/test.db"},
    )

    with pytest.raises(ValueError, match="user_goal"):
        InterviewPreparationSkill().run(request)


def test_interview_preparation_skill_missing_db_path_raises() -> None:
    with pytest.raises(ValueError, match="db_path"):
        InterviewPreparationSkill().run(_request(context={}))


def test_interview_preparation_skill_wrong_request_name_raises() -> None:
    request = SkillRequest(
        skill_name="other_skill",
        inputs={"user_goal": "准备面试"},
        context={"db_path": "/tmp/test.db"},
    )

    with pytest.raises(ValueError, match="interview_preparation"):
        InterviewPreparationSkill().run(request)


def test_create_default_skill_registry_registers_interview_preparation() -> None:
    registry = create_default_skill_registry()

    assert registry.has("interview_preparation") is True
    assert isinstance(registry.get("interview_preparation"), InterviewPreparationSkill)
