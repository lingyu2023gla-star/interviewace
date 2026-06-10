"""Knowledge API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from knowledge.repository import upsert_knowledge_chunks
from knowledge.schemas import KnowledgeChunk


def _client_with_db(tmp_path, monkeypatch) -> tuple[TestClient, str]:
    """Create an API client backed by a temporary DB."""
    db_path = str(tmp_path / "api_knowledge.db")
    monkeypatch.setenv("INTERVIEWACE_DB_PATH", db_path)
    return TestClient(app), db_path


def test_knowledge_search_returns_results(tmp_path, monkeypatch) -> None:
    client, db_path = _client_with_db(tmp_path, monkeypatch)
    upsert_knowledge_chunks(
        db_path,
        [
            KnowledgeChunk(
                source_type="turn_feedback",
                source_id="turn:1:feedback",
                title="Agent 架构复盘",
                content="候选人讲到了 Orchestrator、ToolResult 和降级策略。",
                topic="Agent 架构",
            )
        ],
    )

    response = client.post("/api/knowledge/search", json={"query": "Orchestrator", "top_k": 5})
    data = response.json()

    assert response.status_code == 200
    assert data["total"] >= 1
    assert "Agent" in data["results"][0]["title"]
    assert data["results"][0]["snippet"]
    assert data["results"][0]["source_type"] == "turn_feedback"


def test_knowledge_search_validation_error(tmp_path, monkeypatch) -> None:
    client, _ = _client_with_db(tmp_path, monkeypatch)

    empty_query = client.post("/api/knowledge/search", json={"query": "", "top_k": 5})
    bad_top_k = client.post("/api/knowledge/search", json={"query": "Agent", "top_k": 0})

    assert empty_query.status_code == 422
    assert bad_top_k.status_code == 422


def test_knowledge_search_filters(tmp_path, monkeypatch) -> None:
    client, db_path = _client_with_db(tmp_path, monkeypatch)
    upsert_knowledge_chunks(
        db_path,
        [
            KnowledgeChunk(
                "turn_feedback",
                "turn:1:feedback",
                "Agent Orchestrator 反馈",
                session_id=1,
                topic="Agent 架构",
                dimension_key="agent_architecture",
            ),
            KnowledgeChunk(
                "question_bank",
                "question:1:reference_answer",
                "Agent 参考答案",
                session_id=2,
                topic="Prompt 工程",
                dimension_key="prompt_engineering",
            ),
        ],
    )

    response = client.post(
        "/api/knowledge/search",
        json={
            "query": "Agent",
            "session_id": 1,
            "source_type": "turn_feedback",
            "topic": "Agent 架构",
            "dimension_key": "agent_architecture",
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["total"] >= 1
    assert all(item["session_id"] == 1 for item in data["results"])
    assert all(item["source_type"] == "turn_feedback" for item in data["results"])
    assert all(item["topic"] == "Agent 架构" for item in data["results"])
    assert all(item["dimension_key"] == "agent_architecture" for item in data["results"])


def test_evidence_context_returns_context(tmp_path, monkeypatch) -> None:
    client, db_path = _client_with_db(tmp_path, monkeypatch)
    upsert_knowledge_chunks(
        db_path,
        [
            KnowledgeChunk(
                source_type="turn_feedback",
                source_id="turn:1:feedback",
                title="Agent 架构复盘",
                content="候选人讲到了 Agent Orchestrator。",
                topic="Agent 架构",
            )
        ],
    )

    response = client.post(
        "/api/knowledge/evidence-context",
        json={"query": "Agent", "top_k": 5, "max_content_chars": 600},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["used_evidence_count"] >= 1
    assert "[E1]" in data["evidence_context"]
    assert "来源类型" in data["evidence_context"]
    assert "Agent" in data["evidence_context"]


def test_evidence_context_empty_results(tmp_path, monkeypatch) -> None:
    client, _ = _client_with_db(tmp_path, monkeypatch)

    response = client.post(
        "/api/knowledge/evidence-context",
        json={"query": "不存在的关键词", "top_k": 5},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["used_evidence_count"] == 0
    assert "无可用历史证据" in data["evidence_context"]
