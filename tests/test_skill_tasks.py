"""Skill Celery task tests without Redis or a worker process."""

from __future__ import annotations

import pytest

from worker.task_records import create_task_record, get_task_record
from worker.tasks import run_skill_task, run_skill_task_celery


class FakeStructuredPlan:
    def model_dump(self) -> dict:
        return {
            "summary": "mock summary",
            "evidence_based_judgments": [],
            "daily_plan": [],
            "question_templates": [],
            "abilities_to_show": [],
            "risk_warnings": [],
            "metadata": {},
        }


class FakeServiceResult:
    user_goal = "准备面试"
    job_direction = "大模型应用工程师"
    query = "Agent"
    structured_plan = FakeStructuredPlan()
    raw_output = '{"summary":"mock summary"}'
    evidence_context = "无可用历史证据。"
    used_evidence_count = 0
    prompt = None


def _payload(db_path: str = "/tmp/test.db") -> dict:
    return {
        "skill_name": "interview_preparation",
        "inputs": {
            "user_goal": "准备面试",
            "job_direction": "大模型应用工程师",
            "query": "Agent",
            "retriever_type": "hybrid",
        },
        "context": {"db_path": db_path},
        "metadata": {"source": "test"},
    }


def test_run_skill_task_returns_skill_result_dict(monkeypatch) -> None:
    captured = {}

    def fake_generate_structured_preparation_plan(**kwargs):
        captured.update(kwargs)
        return FakeServiceResult()

    monkeypatch.setattr(
        "skills.interview_preparation.generate_structured_preparation_plan",
        fake_generate_structured_preparation_plan,
    )

    result = run_skill_task(_payload())

    assert result["skill_name"] == "interview_preparation"
    assert result["success"] is True
    assert result["output"]["structured_plan"]["summary"] == "mock summary"
    assert result["metadata"]["retriever_type"] == "hybrid"
    assert captured["user_goal"] == "准备面试"
    assert captured["retriever_type"] == "hybrid"


def test_run_skill_task_requires_skill_name() -> None:
    payload = _payload()
    del payload["skill_name"]

    with pytest.raises(ValueError, match="skill_name"):
        run_skill_task(payload)


def test_skill_task_success_writes_task_record(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "tasks.db")
    task_id = "skill-success"
    payload = _payload(db_path)
    create_task_record(db_path, task_id, "skills.run_skill", payload)

    monkeypatch.setattr(
        "skills.interview_preparation.generate_structured_preparation_plan",
        lambda **kwargs: FakeServiceResult(),
    )

    result = run_skill_task_celery.apply(args=[payload], task_id=task_id)
    record = get_task_record(db_path, task_id)

    assert result.successful()
    assert result.result["skill_name"] == "interview_preparation"
    assert record["status"] == "SUCCESS"
    assert record["started_at"]
    assert record["finished_at"]
    assert record["result"]["skill_name"] == "interview_preparation"


def test_skill_task_missing_skill_marks_failure_and_reraises(tmp_path) -> None:
    db_path = str(tmp_path / "tasks.db")
    task_id = "skill-missing"
    payload = _payload(db_path)
    payload["skill_name"] = "unknown"
    create_task_record(db_path, task_id, "skills.run_skill", payload)

    result = run_skill_task_celery.apply(args=[payload], task_id=task_id)
    record = get_task_record(db_path, task_id)

    assert result.failed()
    with pytest.raises(Exception, match="Skill not found"):
        result.get(propagate=True)
    assert record["status"] == "FAILURE"
    assert "Skill not found" in record["error_message"]
    assert record["finished_at"]


def test_skill_task_run_error_marks_failure_and_reraises(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "tasks.db")
    task_id = "skill-error"
    payload = _payload(db_path)
    create_task_record(db_path, task_id, "skills.run_skill", payload)

    def fail_generate_structured_preparation_plan(**kwargs):
        raise RuntimeError("LLM failed")

    monkeypatch.setattr(
        "skills.interview_preparation.generate_structured_preparation_plan",
        fail_generate_structured_preparation_plan,
    )

    result = run_skill_task_celery.apply(args=[payload], task_id=task_id)
    record = get_task_record(db_path, task_id)

    assert result.failed()
    with pytest.raises(RuntimeError, match="LLM failed"):
        result.get(propagate=True)
    assert record["status"] == "FAILURE"
    assert record["error_message"] == "LLM failed"


def test_run_skill_task_passes_inputs_context_metadata(monkeypatch) -> None:
    captured = {}

    def fake_generate_structured_preparation_plan(**kwargs):
        captured.update(kwargs)
        return FakeServiceResult()

    monkeypatch.setattr(
        "skills.interview_preparation.generate_structured_preparation_plan",
        fake_generate_structured_preparation_plan,
    )

    payload = _payload("/tmp/skills.db")
    payload["inputs"]["plan_days"] = 4
    result = run_skill_task(payload)

    assert result["metadata"]["source"] == "structured_preparation_service"
    assert captured["db_path"] == "/tmp/skills.db"
    assert captured["plan_days"] == 4
