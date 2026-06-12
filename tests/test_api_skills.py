"""Skill API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from worker.task_records import get_task_record


class FakeStructuredPlan:
    def model_dump(self) -> dict:
        return {
            "summary": "mock summary",
            "evidence_based_judgments": [],
            "daily_plan": [],
            "question_templates": [],
            "abilities_to_show": [],
            "risk_warnings": [],
            "metadata": {
                "evidence_validation": {
                    "is_valid": True,
                    "valid_evidence_ids": [],
                    "used_evidence_refs": [],
                    "issues": [],
                }
            },
        }


class FakeServiceResult:
    user_goal = "准备 Agent/RAG 应用工程师面试"
    job_direction = "大模型应用工程师"
    query = "Agent"
    structured_plan = FakeStructuredPlan()
    raw_output = '{"summary":"mock summary"}'
    evidence_context = "无可用历史证据。"
    used_evidence_count = 0
    prompt = None


def test_list_skills_returns_interview_preparation() -> None:
    client = TestClient(app)

    response = client.get("/api/skills")
    data = response.json()

    assert response.status_code == 200
    names = [skill["name"] for skill in data["skills"]]
    assert "interview_preparation" in names
    skill = next(item for item in data["skills"] if item["name"] == "interview_preparation")
    assert skill["supports_async"] is True


def test_get_skill_spec_returns_interview_preparation() -> None:
    client = TestClient(app)

    response = client.get("/api/skills/interview_preparation")
    data = response.json()

    assert response.status_code == 200
    assert data["name"] == "interview_preparation"
    assert data["requires_evidence"] is True
    assert set(data["supported_retriever_types"]) == {"keyword", "fts", "embedding", "hybrid"}


def test_get_unknown_skill_returns_404() -> None:
    client = TestClient(app)

    response = client.get("/api/skills/unknown")

    assert response.status_code == 404


def test_run_interview_preparation_skill(monkeypatch, tmp_path) -> None:
    captured = {}

    def fake_generate_structured_preparation_plan(**kwargs):
        captured.update(kwargs)
        return FakeServiceResult()

    db_path = str(tmp_path / "skills.db")
    monkeypatch.setenv("INTERVIEWACE_DB_PATH", db_path)
    monkeypatch.setattr(
        "skills.interview_preparation.generate_structured_preparation_plan",
        fake_generate_structured_preparation_plan,
    )
    client = TestClient(app)

    response = client.post(
        "/api/skills/interview_preparation/run",
        json={
            "inputs": {
                "user_goal": "准备 Agent/RAG 应用工程师面试",
                "job_direction": "大模型应用工程师",
                "query": "Agent",
                "retriever_type": "hybrid",
            },
            "metadata": {"source": "test"},
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["skill_name"] == "interview_preparation"
    assert data["success"] is True
    assert data["output"]["structured_plan"]["summary"] == "mock summary"
    assert data["metadata"]["retriever_type"] == "hybrid"
    assert captured["db_path"] == db_path
    assert captured["retriever_type"] == "hybrid"


def test_run_unknown_skill_returns_404() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/skills/unknown/run",
        json={"inputs": {"user_goal": "准备面试"}},
    )

    assert response.status_code == 404


def test_submit_skill_task_creates_task_record(monkeypatch, tmp_path) -> None:
    captured = {}

    class FakeAsyncResult:
        def __init__(self, task_id):
            self.id = task_id

    class FakeUUID:
        hex = "skill-task-id"

    def fake_apply_async(args=None, task_id=None):
        captured["payload"] = args[0]
        captured["task_id"] = task_id
        return FakeAsyncResult(task_id)

    db_path = str(tmp_path / "skills.db")
    monkeypatch.setenv("INTERVIEWACE_DB_PATH", db_path)
    monkeypatch.setattr("api.routers.skills.uuid.uuid4", lambda: FakeUUID())
    monkeypatch.setattr("api.routers.skills.run_skill_task_celery.apply_async", fake_apply_async)
    client = TestClient(app)

    response = client.post(
        "/api/skills/interview_preparation/tasks",
        json={
            "inputs": {
                "user_goal": "准备 Agent/RAG 应用工程师面试",
                "retriever_type": "hybrid",
            },
            "metadata": {"source": "api-test"},
        },
    )
    data = response.json()
    record = get_task_record(db_path, data["task_id"])

    assert response.status_code == 202
    assert data["task_id"] == "skill-task-id"
    assert data["skill_name"] == "interview_preparation"
    assert data["status"] == "PENDING"
    assert captured["task_id"] == "skill-task-id"
    assert captured["payload"]["skill_name"] == "interview_preparation"
    assert captured["payload"]["inputs"]["retriever_type"] == "hybrid"
    assert captured["payload"]["context"]["db_path"] == db_path
    assert record["task_name"] == "skills.run_skill"
    assert record["status"] == "PENDING"
    assert record["request"]["skill_name"] == "interview_preparation"


def test_submit_unknown_skill_task_returns_404() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/skills/unknown/tasks",
        json={"inputs": {"user_goal": "准备面试"}},
    )

    assert response.status_code == 404
