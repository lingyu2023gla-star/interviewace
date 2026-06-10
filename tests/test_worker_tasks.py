"""Worker task tests without Redis or Celery worker."""

from __future__ import annotations

import pytest

from worker.tasks import run_generate_preparation_plan_task


def _payload() -> dict:
    """Return a valid preparation task payload."""
    return {
        "db_path": "/tmp/test.db",
        "user_goal": "准备面试",
        "job_direction": "大模型应用工程师",
        "query": "Agent",
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
