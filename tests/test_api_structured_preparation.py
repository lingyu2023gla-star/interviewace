"""Structured preparation API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


class FakeStructuredPlan:
    """Fake Pydantic v2-style structured plan."""

    def model_dump(self) -> dict:
        return {
            "summary": "mock summary",
            "evidence_based_judgments": [
                {
                    "type": "strength",
                    "content": "候选人能讲清 Agent 架构",
                    "evidence_refs": ["E1"],
                }
            ],
            "daily_plan": [
                {
                    "day": 1,
                    "goal": "整理 Agent 架构回答",
                    "tasks": [
                        {
                            "task": "补充 Orchestrator 和 ToolResult 说明",
                            "estimated_minutes": 30,
                            "output": "回答模板",
                            "evidence_refs": ["E1"],
                        }
                    ],
                }
            ],
            "question_templates": [],
            "abilities_to_show": [],
            "risk_warnings": [],
            "metadata": {
                "user_goal": "准备 Agent/RAG 应用工程师面试",
            },
        }


class FakeStructuredPlanV1:
    """Fake Pydantic v1-style structured plan."""

    def dict(self) -> dict:
        return {
            "summary": "v1 summary",
            "evidence_based_judgments": [],
            "daily_plan": [],
            "question_templates": [],
            "abilities_to_show": [],
            "risk_warnings": [],
            "metadata": {},
        }


class FakeResult:
    """Fake structured service result."""

    user_goal = "准备 Agent/RAG 应用工程师面试"
    job_direction = "大模型应用工程师"
    query = "Agent"
    structured_plan = FakeStructuredPlan()
    raw_output = '{"summary":"mock summary"}'
    evidence_context = "[E1]\n证据内容"
    used_evidence_count = 1
    prompt = None


def test_structured_preparation_plan_returns_structured_json(monkeypatch) -> None:
    monkeypatch.setattr(
        "api.routers.preparation.generate_structured_preparation_plan",
        lambda **kwargs: FakeResult(),
    )
    client = TestClient(app)

    response = client.post(
        "/api/preparation/structured-plan",
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
    assert data["user_goal"] == "准备 Agent/RAG 应用工程师面试"
    assert data["structured_plan"]["summary"] == "mock summary"
    assert data["structured_plan"]["evidence_based_judgments"][0]["evidence_refs"] == ["E1"]
    assert data["used_evidence_count"] == 1
    assert data["prompt"] is None


def test_structured_preparation_plan_include_prompt(monkeypatch) -> None:
    class FakeResultWithPrompt(FakeResult):
        prompt = "mock prompt"

    monkeypatch.setattr(
        "api.routers.preparation.generate_structured_preparation_plan",
        lambda **kwargs: FakeResultWithPrompt(),
    )
    client = TestClient(app)

    response = client.post(
        "/api/preparation/structured-plan",
        json={
            "user_goal": "准备 Agent/RAG 应用工程师面试",
            "include_prompt": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["prompt"] == "mock prompt"


def test_structured_preparation_plan_passes_request_params(monkeypatch) -> None:
    captured = {}

    def fake_generate_structured_preparation_plan(**kwargs):
        captured.update(kwargs)
        return FakeResult()

    monkeypatch.setenv("INTERVIEWACE_DB_PATH", "/tmp/test.db")
    monkeypatch.setattr(
        "api.routers.preparation.generate_structured_preparation_plan",
        fake_generate_structured_preparation_plan,
    )
    client = TestClient(app)

    response = client.post(
        "/api/preparation/structured-plan",
        json={
            "user_goal": "准备面试",
            "job_direction": "大模型应用工程师",
            "query": "",
            "retriever_type": "embedding",
            "plan_days": 3,
            "daily_minutes": 30,
            "max_tasks_per_day": 2,
            "top_k": 4,
            "include_prompt": True,
        },
    )

    assert response.status_code == 200
    assert captured["db_path"] == "/tmp/test.db"
    assert captured["user_goal"] == "准备面试"
    assert captured["job_direction"] == "大模型应用工程师"
    assert captured["query"] == ""
    assert captured["retriever_type"] == "embedding"
    assert captured["plan_days"] == 3
    assert captured["daily_minutes"] == 30
    assert captured["max_tasks_per_day"] == 2
    assert captured["top_k"] == 4
    assert captured["include_prompt"] is True


def test_structured_preparation_plan_validation_error() -> None:
    client = TestClient(app)

    bad_goal = client.post("/api/preparation/structured-plan", json={"user_goal": ""})
    bad_days = client.post(
        "/api/preparation/structured-plan",
        json={"user_goal": "准备面试", "plan_days": 0},
    )
    bad_minutes = client.post(
        "/api/preparation/structured-plan",
        json={"user_goal": "准备面试", "daily_minutes": 0},
    )
    bad_top_k = client.post(
        "/api/preparation/structured-plan",
        json={"user_goal": "准备面试", "top_k": 0},
    )
    bad_retriever_type = client.post(
        "/api/preparation/structured-plan",
        json={"user_goal": "准备面试", "retriever_type": "unknown"},
    )

    assert bad_goal.status_code == 422
    assert bad_days.status_code == 422
    assert bad_minutes.status_code == 422
    assert bad_top_k.status_code == 422
    assert bad_retriever_type.status_code == 422


def test_structured_preparation_plan_retriever_type_defaults_to_keyword(monkeypatch) -> None:
    captured = {}

    def fake_generate_structured_preparation_plan(**kwargs):
        captured.update(kwargs)
        return FakeResult()

    monkeypatch.setattr(
        "api.routers.preparation.generate_structured_preparation_plan",
        fake_generate_structured_preparation_plan,
    )
    client = TestClient(app)

    response = client.post(
        "/api/preparation/structured-plan",
        json={"user_goal": "准备 Agent/RAG 应用工程师面试"},
    )

    assert response.status_code == 200
    assert captured["retriever_type"] == "keyword"


def test_structured_preparation_plan_supports_pydantic_v1_dict(monkeypatch) -> None:
    class FakeResultV1(FakeResult):
        structured_plan = FakeStructuredPlanV1()
        raw_output = '{"summary":"v1 summary"}'

    monkeypatch.setattr(
        "api.routers.preparation.generate_structured_preparation_plan",
        lambda **kwargs: FakeResultV1(),
    )
    client = TestClient(app)

    response = client.post(
        "/api/preparation/structured-plan",
        json={"user_goal": "准备 Agent/RAG 应用工程师面试"},
    )

    assert response.status_code == 200
    assert response.json()["structured_plan"]["summary"] == "v1 summary"
