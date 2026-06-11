"""Celery task status API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_submit_ping_task(monkeypatch) -> None:
    class FakeAsyncResult:
        def __init__(self, task_id):
            self.id = task_id

    captured = {}

    def fake_apply_async(args=None, task_id=None):
        captured["payload"] = args[0]
        captured["task_id"] = task_id
        return FakeAsyncResult(task_id)

    class FakeUUID:
        hex = "fake-ping-task-id"

    monkeypatch.setattr("api.routers.tasks.uuid.uuid4", lambda: FakeUUID())
    monkeypatch.setattr(
        "api.routers.tasks.ping_task.apply_async",
        fake_apply_async,
    )
    monkeypatch.setenv("INTERVIEWACE_DB_PATH", "/tmp/test.db")
    client = TestClient(app)

    response = client.post("/api/tasks/ping")
    data = response.json()

    assert response.status_code == 202
    assert data["task_id"] == "fake-ping-task-id"
    assert data["status"] == "PENDING"
    assert captured["payload"]["source"] == "api"
    assert captured["task_id"] == data["task_id"]


def test_submit_ping_task_creates_task_record(tmp_path, monkeypatch) -> None:
    class FakeAsyncResult:
        def __init__(self, task_id):
            self.id = task_id

    def fake_apply_async(args=None, task_id=None):
        return FakeAsyncResult(task_id)

    class FakeUUID:
        hex = "record-ping-task-id"

    db_path = str(tmp_path / "tasks.db")
    monkeypatch.setenv("INTERVIEWACE_DB_PATH", db_path)
    monkeypatch.setattr("api.routers.tasks.uuid.uuid4", lambda: FakeUUID())
    monkeypatch.setattr("api.routers.tasks.ping_task.apply_async", fake_apply_async)
    client = TestClient(app)

    response = client.post("/api/tasks/ping")
    data = response.json()

    from worker.task_records import get_task_record

    record = get_task_record(db_path, data["task_id"])
    assert record["status"] == "PENDING"
    assert record["task_name"] == "system.ping"
    assert record["request"]["source"] == "api"


def test_get_task_status_pending(tmp_path, monkeypatch) -> None:
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
    monkeypatch.setenv("INTERVIEWACE_DB_PATH", str(tmp_path / "tasks.db"))
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
    assert data["task_record"] is None


def test_get_task_status_success(tmp_path, monkeypatch) -> None:
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
    monkeypatch.setenv("INTERVIEWACE_DB_PATH", str(tmp_path / "tasks.db"))
    client = TestClient(app)

    response = client.get("/api/tasks/fake-task-id")
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "SUCCESS"
    assert data["ready"] is True
    assert data["successful"] is True
    assert data["result"]["plan"] == "mock plan"
    assert data["error"] is None


def test_get_task_status_failure(tmp_path, monkeypatch) -> None:
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
    monkeypatch.setenv("INTERVIEWACE_DB_PATH", str(tmp_path / "tasks.db"))
    client = TestClient(app)

    response = client.get("/api/tasks/fake-task-id")
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "FAILURE"
    assert data["ready"] is True
    assert data["successful"] is False
    assert data["result"] is None
    assert "LLM failed" in data["error"]


def test_get_task_status_includes_task_record(tmp_path, monkeypatch) -> None:
    class FakeAsyncResult:
        status = "PENDING"
        result = None

        def __init__(self, task_id, app=None):
            self.task_id = task_id

        def ready(self):
            return False

        def successful(self):
            return False

    db_path = str(tmp_path / "tasks.db")
    monkeypatch.setenv("INTERVIEWACE_DB_PATH", db_path)
    monkeypatch.setattr("api.routers.tasks.AsyncResult", FakeAsyncResult)

    from worker.task_records import create_task_record

    create_task_record(db_path, "task-with-record", "system.ping", {"source": "api"})
    client = TestClient(app)

    response = client.get("/api/tasks/task-with-record")
    data = response.json()

    assert response.status_code == 200
    assert data["task_record"]["task_id"] == "task-with-record"
    assert data["task_record"]["status"] == "PENDING"
    assert data["task_record"]["request"]["source"] == "api"
