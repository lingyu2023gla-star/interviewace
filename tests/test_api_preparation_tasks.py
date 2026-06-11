"""Preparation task submission API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_submit_preparation_plan_task(monkeypatch) -> None:
    captured = {}

    class FakeAsyncResult:
        def __init__(self, task_id):
            self.id = task_id

    def fake_apply_async(args=None, task_id=None):
        captured["payload"] = args[0]
        captured["task_id"] = task_id
        return FakeAsyncResult(task_id)

    class FakeUUID:
        hex = "fake-task-id"

    monkeypatch.setenv("INTERVIEWACE_DB_PATH", "/tmp/test.db")
    monkeypatch.setattr("api.routers.preparation.uuid.uuid4", lambda: FakeUUID())
    monkeypatch.setattr(
        "api.routers.preparation.generate_preparation_plan_task.apply_async",
        fake_apply_async,
    )
    client = TestClient(app)

    response = client.post(
        "/api/preparation/plan-tasks",
        json={
            "user_goal": "准备 Agent/RAG 应用工程师面试",
            "job_direction": "大模型应用工程师",
            "query": "Agent",
            "retriever_type": "hybrid",
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
    assert captured["payload"]["retriever_type"] == "hybrid"
    assert captured["payload"]["include_prompt"] is False
    assert captured["task_id"] == data["task_id"]


def test_submit_preparation_plan_task_validation_error() -> None:
    client = TestClient(app)

    bad_goal = client.post("/api/preparation/plan-tasks", json={"user_goal": ""})
    bad_days = client.post(
        "/api/preparation/plan-tasks",
        json={"user_goal": "准备面试", "plan_days": 0},
    )
    bad_retriever_type = client.post(
        "/api/preparation/plan-tasks",
        json={"user_goal": "准备面试", "retriever_type": "unknown"},
    )

    assert bad_goal.status_code == 422
    assert bad_days.status_code == 422
    assert bad_retriever_type.status_code == 422


def test_submit_preparation_plan_task_creates_task_record(tmp_path, monkeypatch) -> None:
    captured = {}

    class FakeAsyncResult:
        def __init__(self, task_id):
            self.id = task_id

    def fake_apply_async(args=None, task_id=None):
        captured["task_id"] = task_id
        return FakeAsyncResult(task_id)

    class FakeUUID:
        hex = "record-task-id"

    db_path = str(tmp_path / "tasks.db")
    monkeypatch.setenv("INTERVIEWACE_DB_PATH", db_path)
    monkeypatch.setattr("api.routers.preparation.uuid.uuid4", lambda: FakeUUID())
    monkeypatch.setattr(
        "api.routers.preparation.generate_preparation_plan_task.apply_async",
        fake_apply_async,
    )
    client = TestClient(app)

    response = client.post(
        "/api/preparation/plan-tasks",
        json={"user_goal": "准备面试"},
    )
    data = response.json()

    from worker.task_records import get_task_record

    record = get_task_record(db_path, data["task_id"])
    assert record["status"] == "PENDING"
    assert record["task_name"] == "preparation.generate_plan"
    assert record["request"]["user_goal"] == "准备面试"
    assert record["request"]["retriever_type"] == "keyword"


def test_submit_structured_preparation_plan_task_creates_task_record(tmp_path, monkeypatch) -> None:
    captured = {}

    class FakeAsyncResult:
        def __init__(self, task_id):
            self.id = task_id

    def fake_apply_async(args=None, task_id=None):
        captured["payload"] = args[0]
        return FakeAsyncResult(task_id)

    class FakeUUID:
        hex = "structured-task-id"

    db_path = str(tmp_path / "tasks.db")
    monkeypatch.setenv("INTERVIEWACE_DB_PATH", db_path)
    monkeypatch.setattr("api.routers.preparation.uuid.uuid4", lambda: FakeUUID())
    monkeypatch.setattr(
        "api.routers.preparation.generate_structured_preparation_plan_task.apply_async",
        fake_apply_async,
    )
    client = TestClient(app)

    response = client.post(
        "/api/preparation/structured-plan-tasks",
        json={"user_goal": "准备结构化面试计划", "retriever_type": "embedding"},
    )
    data = response.json()

    from worker.task_records import get_task_record

    assert response.status_code == 202
    record = get_task_record(db_path, data["task_id"])
    assert record["status"] == "PENDING"
    assert record["task_name"] == "preparation.generate_structured_plan"
    assert record["request"]["user_goal"] == "准备结构化面试计划"
    assert record["request"]["retriever_type"] == "embedding"
    assert captured["payload"]["retriever_type"] == "embedding"
