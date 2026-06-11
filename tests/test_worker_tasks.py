"""Worker task tests without Redis or Celery worker."""

from __future__ import annotations

import pytest

from worker.task_records import create_task_record, get_task_record
from worker.tasks import (
    generate_preparation_plan_task,
    ping_task,
    run_generate_preparation_plan_task,
    run_generate_structured_preparation_plan_task,
    run_ping_task,
)


def test_run_ping_task() -> None:
    assert run_ping_task()["status"] == "ok"
    assert run_ping_task()["message"] == "pong"
    assert run_ping_task({"x": 1})["payload"]["x"] == 1


def _payload() -> dict:
    """Return a valid preparation task payload."""
    return {
        "db_path": "/tmp/test.db",
        "user_goal": "准备面试",
        "job_direction": "大模型应用工程师",
        "query": "Agent",
        "retriever_type": "hybrid",
        "plan_days": 7,
        "daily_minutes": 60,
        "max_tasks_per_day": 3,
        "top_k": 5,
        "include_prompt": False,
    }


def test_run_generate_preparation_plan_task_returns_dict(monkeypatch) -> None:
    captured = {}

    class FakeResult:
        user_goal = "准备面试"
        job_direction = "大模型应用工程师"
        query = "Agent"
        plan = "mock plan"
        evidence_context = "[E1]\n证据内容"
        used_evidence_count = 1
        prompt = None

    def fake_generate_preparation_plan(db_path, request, include_prompt=False):
        captured["db_path"] = db_path
        captured["request"] = request
        captured["include_prompt"] = include_prompt
        return FakeResult()

    monkeypatch.setattr("worker.tasks.generate_preparation_plan", fake_generate_preparation_plan)

    result = run_generate_preparation_plan_task(_payload())

    assert result["plan"] == "mock plan"
    assert result["used_evidence_count"] == 1
    assert result["prompt"] is None
    assert captured["request"].user_goal == "准备面试"
    assert captured["request"].retriever_type == "hybrid"
    assert captured["db_path"] == "/tmp/test.db"


@pytest.mark.parametrize("db_path", [None, ""])
def test_run_generate_preparation_plan_task_requires_db_path(db_path) -> None:
    payload = _payload()
    if db_path is None:
        del payload["db_path"]
    else:
        payload["db_path"] = db_path

    with pytest.raises(ValueError):
        run_generate_preparation_plan_task(payload)


def test_run_generate_preparation_plan_task_propagates_error(monkeypatch) -> None:
    def fail_generate_preparation_plan(db_path, request, include_prompt=False):
        raise RuntimeError("LLM failed")

    monkeypatch.setattr("worker.tasks.generate_preparation_plan", fail_generate_preparation_plan)

    with pytest.raises(RuntimeError, match="LLM failed"):
        run_generate_preparation_plan_task(_payload())


def test_run_generate_structured_preparation_plan_task_returns_dict(monkeypatch) -> None:
    captured = {}

    class FakePlan:
        def model_dump(self):
            return {"summary": "structured summary"}

    class FakeResult:
        user_goal = "准备面试"
        job_direction = "大模型应用工程师"
        query = "Agent"
        structured_plan = FakePlan()
        raw_output = '{"summary":"structured summary"}'
        evidence_context = "[E1]\n证据内容"
        used_evidence_count = 1
        prompt = None

    def fake_generate_structured_preparation_plan(**kwargs):
        captured.update(kwargs)
        return FakeResult()

    monkeypatch.setattr(
        "worker.tasks.generate_structured_preparation_plan",
        fake_generate_structured_preparation_plan,
    )

    result = run_generate_structured_preparation_plan_task(_payload())

    assert result["structured_plan"]["summary"] == "structured summary"
    assert result["raw_output"] == '{"summary":"structured summary"}'
    assert result["used_evidence_count"] == 1
    assert captured["retriever_type"] == "hybrid"


def test_worker_task_success_writes_task_record(tmp_path) -> None:
    db_path = str(tmp_path / "tasks.db")
    task_id = "ping-success"
    create_task_record(db_path, task_id, "system.ping", {"source": "api"})

    result = ping_task.apply(
        args=[{"source": "api", "db_path": db_path}],
        task_id=task_id,
    )
    record = get_task_record(db_path, task_id)

    assert result.successful()
    assert record["status"] == "SUCCESS"
    assert record["started_at"]
    assert record["finished_at"]
    assert record["result"]["status"] == "ok"


def test_worker_task_failure_writes_task_record_and_reraises(tmp_path, monkeypatch) -> None:
    db_path = str(tmp_path / "tasks.db")
    task_id = "plan-failure"
    payload = _payload()
    payload["db_path"] = db_path
    create_task_record(db_path, task_id, "preparation.generate_plan", payload)

    def fail_generate_preparation_plan(db_path, request, include_prompt=False):
        raise RuntimeError("LLM failed")

    monkeypatch.setattr("worker.tasks.generate_preparation_plan", fail_generate_preparation_plan)

    result = generate_preparation_plan_task.apply(args=[payload], task_id=task_id)
    record = get_task_record(db_path, task_id)

    assert result.failed()
    with pytest.raises(RuntimeError, match="LLM failed"):
        result.get(propagate=True)
    assert record["status"] == "FAILURE"
    assert record["error_message"] == "LLM failed"
    assert record["finished_at"]
