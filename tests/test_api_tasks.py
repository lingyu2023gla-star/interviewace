"""Celery task status API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_get_task_status_pending(monkeypatch) -> None:
    class FakeAsyncResult:
        status = "PENDING"
        result = None

        def __init__(self, task_id, app=None):
            self.task_id = task_id

        def ready(self):
            return False

        def successful(self):
            return False

    monkeypatch.setattr("api.routers.tasks.AsyncResult", FakeAsyncResult)
    client = TestClient(app)

    response = client.get("/api/tasks/fake-task-id")
    data = response.json()

    assert response.status_code == 200
    assert data["task_id"] == "fake-task-id"
    assert data["status"] == "PENDING"
    assert data["ready"] is False
    assert data["successful"] is False
    assert data["result"] is None
    assert data["error"] is None


def test_get_task_status_success(monkeypatch) -> None:
    class FakeAsyncResult:
        status = "SUCCESS"
        result = {"plan": "mock plan", "used_evidence_count": 1}

        def __init__(self, task_id, app=None):
            self.task_id = task_id

        def ready(self):
            return True

        def successful(self):
            return True

    monkeypatch.setattr("api.routers.tasks.AsyncResult", FakeAsyncResult)
    client = TestClient(app)

    response = client.get("/api/tasks/fake-task-id")
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "SUCCESS"
    assert data["ready"] is True
    assert data["successful"] is True
    assert data["result"]["plan"] == "mock plan"
    assert data["error"] is None


def test_get_task_status_failure(monkeypatch) -> None:
    class FakeAsyncResult:
        status = "FAILURE"
        result = RuntimeError("LLM failed")

        def __init__(self, task_id, app=None):
            self.task_id = task_id

        def ready(self):
            return True

        def successful(self):
            return False

    monkeypatch.setattr("api.routers.tasks.AsyncResult", FakeAsyncResult)
    client = TestClient(app)

    response = client.get("/api/tasks/fake-task-id")
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "FAILURE"
    assert data["ready"] is True
    assert data["successful"] is False
    assert data["result"] is None
    assert "LLM failed" in data["error"]
