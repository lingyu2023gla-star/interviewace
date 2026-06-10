"""Preparation task submission API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_submit_preparation_plan_task(monkeypatch) -> None:
    captured = {}

    class FakeAsyncResult:
        id = "fake-task-id"

    def fake_delay(payload):
        captured["payload"] = payload
        return FakeAsyncResult()

    monkeypatch.setenv("INTERVIEWACE_DB_PATH", "/tmp/test.db")
    monkeypatch.setattr("api.routers.preparation.generate_preparation_plan_task.delay", fake_delay)
    client = TestClient(app)

    response = client.post(
        "/api/preparation/plan-tasks",
        json={
            "user_goal": "准备 Agent/RAG 应用工程师面试",
            "job_direction": "大模型应用工程师",
            "query": "Agent",
            "plan_days": 7,
            "daily_minutes": 60,
            "max_tasks_per_day": 3,
            "top_k": 5,
            "include_prompt": False,
        },
    )
    data = response.json()

    assert response.status_code == 202
    assert data["task_id"] == "fake-task-id"
    assert data["status"] == "PENDING"
    assert "submitted" in data["message"]
    assert captured["payload"]["db_path"] == "/tmp/test.db"
    assert captured["payload"]["user_goal"] == "准备 Agent/RAG 应用工程师面试"
    assert captured["payload"]["include_prompt"] is False


def test_submit_preparation_plan_task_validation_error() -> None:
    client = TestClient(app)

    bad_goal = client.post("/api/preparation/plan-tasks", json={"user_goal": ""})
    bad_days = client.post(
        "/api/preparation/plan-tasks",
        json={"user_goal": "准备面试", "plan_days": 0},
    )

    assert bad_goal.status_code == 422
    assert bad_days.status_code == 422
