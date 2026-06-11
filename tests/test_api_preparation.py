"""Preparation API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from knowledge.repository import upsert_knowledge_chunks
from knowledge.schemas import KnowledgeChunk


def _client_with_db(tmp_path, monkeypatch) -> tuple[TestClient, str]:
    """Create an API client backed by a temporary DB."""
    db_path = str(tmp_path / "api_preparation.db")
    monkeypatch.setenv("INTERVIEWACE_DB_PATH", db_path)
    return TestClient(app), db_path


def _seed_agent_chunk(db_path: str) -> None:
    """Insert one Agent chunk for API tests."""
    upsert_knowledge_chunks(
        db_path,
        [
            KnowledgeChunk(
                source_type="turn_feedback",
                source_id="turn:1:feedback",
                title="Agent 架构复盘",
                content="候选人讲到了 Agent Orchestrator 和 ToolResult。",
                topic="Agent 架构",
            )
        ],
    )


def test_preparation_plan_returns_mock_plan(tmp_path, monkeypatch) -> None:
    client, db_path = _client_with_db(tmp_path, monkeypatch)
    _seed_agent_chunk(db_path)
    monkeypatch.setattr("core.analyzer.generate_text", lambda prompt: "mock preparation plan")

    response = client.post(
        "/api/preparation/plan",
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

    assert response.status_code == 200
    assert data["plan"] == "mock preparation plan"
    assert data["used_evidence_count"] >= 1
    assert "[E1]" in data["evidence_context"]
    assert data["prompt"] is None


def test_preparation_plan_include_prompt(tmp_path, monkeypatch) -> None:
    client, db_path = _client_with_db(tmp_path, monkeypatch)
    _seed_agent_chunk(db_path)
    monkeypatch.setattr("core.analyzer.generate_text", lambda prompt: "mock plan")

    response = client.post(
        "/api/preparation/plan",
        json={
            "user_goal": "准备 Agent/RAG 应用工程师面试",
            "query": "Agent",
            "include_prompt": True,
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["prompt"] is not None
    assert "只能基于【历史证据】" in data["prompt"]
    assert "准备 Agent/RAG 应用工程师面试" in data["prompt"]


def test_preparation_plan_validation_error(tmp_path, monkeypatch) -> None:
    client, _ = _client_with_db(tmp_path, monkeypatch)

    bad_goal = client.post("/api/preparation/plan", json={"user_goal": ""})
    bad_days = client.post("/api/preparation/plan", json={"user_goal": "准备面试", "plan_days": 0})
    bad_minutes = client.post("/api/preparation/plan", json={"user_goal": "准备面试", "daily_minutes": 0})

    assert bad_goal.status_code == 422
    assert bad_days.status_code == 422
    assert bad_minutes.status_code == 422


def test_preparation_plan_empty_evidence(tmp_path, monkeypatch) -> None:
    client, _ = _client_with_db(tmp_path, monkeypatch)
    monkeypatch.setattr("core.analyzer.generate_text", lambda prompt: "mock plan without evidence")

    response = client.post(
        "/api/preparation/plan",
        json={
            "user_goal": "准备 Agent/RAG 应用工程师面试",
            "query": "不存在的关键词",
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["used_evidence_count"] == 0
    assert "无可用历史证据" in data["evidence_context"]
    assert data["plan"] == "mock plan without evidence"


def test_preparation_plan_passes_retriever_type_to_service(tmp_path, monkeypatch) -> None:
    client, _ = _client_with_db(tmp_path, monkeypatch)
    captured = {}

    class FakeResult:
        user_goal = "准备 Agent/RAG 应用工程师面试"
        job_direction = "大模型应用工程师"
        query = "Agent"
        plan = "mock plan"
        evidence_context = "无可用历史证据。"
        used_evidence_count = 0
        prompt = None

    def fake_generate_preparation_plan(db_path, request, include_prompt=False):
        captured["db_path"] = db_path
        captured["request"] = request
        captured["include_prompt"] = include_prompt
        return FakeResult()

    monkeypatch.setattr(
        "api.routers.preparation.generate_preparation_plan",
        fake_generate_preparation_plan,
    )

    response = client.post(
        "/api/preparation/plan",
        json={
            "user_goal": "准备 Agent/RAG 应用工程师面试",
            "job_direction": "大模型应用工程师",
            "query": "Agent",
            "retriever_type": "hybrid",
            "include_prompt": False,
        },
    )

    assert response.status_code == 200
    assert captured["request"].retriever_type == "hybrid"


def test_preparation_plan_retriever_type_defaults_to_keyword(tmp_path, monkeypatch) -> None:
    client, _ = _client_with_db(tmp_path, monkeypatch)
    captured = {}

    class FakeResult:
        user_goal = "准备面试"
        job_direction = ""
        query = "准备面试"
        plan = "mock plan"
        evidence_context = "无可用历史证据。"
        used_evidence_count = 0
        prompt = None

    def fake_generate_preparation_plan(db_path, request, include_prompt=False):
        captured["request"] = request
        return FakeResult()

    monkeypatch.setattr(
        "api.routers.preparation.generate_preparation_plan",
        fake_generate_preparation_plan,
    )

    response = client.post("/api/preparation/plan", json={"user_goal": "准备面试"})

    assert response.status_code == 200
    assert captured["request"].retriever_type == "keyword"


def test_preparation_plan_invalid_retriever_type_returns_422(tmp_path, monkeypatch) -> None:
    client, _ = _client_with_db(tmp_path, monkeypatch)

    response = client.post(
        "/api/preparation/plan",
        json={"user_goal": "准备面试", "retriever_type": "unknown"},
    )

    assert response.status_code == 422
