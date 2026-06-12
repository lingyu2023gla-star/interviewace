"""ProjectPitchSkill tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from knowledge.schemas import KnowledgeSearchResult
from skills import ProjectPitchSkill, SkillRequest, SkillResult, create_default_skill_registry
from worker.task_records import get_task_record


class FakeRetriever:
    """Fake retriever that records calls and returns predefined results."""

    def __init__(self, results: list[KnowledgeSearchResult] | None = None):
        self.results = results if results is not None else [_result()]
        self.calls = []

    def retrieve(self, **kwargs):
        self.calls.append(kwargs)
        return self.results


def _result() -> KnowledgeSearchResult:
    return KnowledgeSearchResult(
        chunk_id=1,
        source_type="turn_feedback",
        source_id="turn:1:feedback",
        title="InterviewAce RAG 架构",
        content="InterviewAce 已实现 knowledge_chunks、Evidence Context、FastAPI 和 Celery。",
        snippet="InterviewAce 已实现 knowledge_chunks 和 Evidence Context。",
        session_id=1,
        topic="RAG 架构",
        dimension_key="rag",
        tags=["RAG"],
        metadata={"question": "请介绍项目架构"},
        score=1.0,
    )


def _request(inputs: dict | None = None, context: dict | None = None) -> SkillRequest:
    payload = {
        "project_name": "InterviewAce",
        "target_role": "Agent / RAG 应用工程师",
        "query": "InterviewAce RAG",
    }
    if inputs:
        payload.update(inputs)
    return SkillRequest(
        skill_name="project_pitch",
        inputs=payload,
        context=context if context is not None else {"db_path": "/tmp/test.db"},
    )


def test_project_pitch_skill_spec() -> None:
    spec = ProjectPitchSkill().spec

    assert spec.name == "project_pitch"
    assert spec.description == "Generate an evidence-based project pitch for interviews."
    assert set(spec.supported_retriever_types) == {"keyword", "fts", "embedding", "hybrid"}
    assert spec.requires_evidence is True
    assert spec.supports_async is True
    assert "project" in spec.tags
    assert "project_name" in spec.input_schema
    assert "pitch" in spec.output_schema


def test_project_pitch_skill_missing_project_name_raises() -> None:
    with pytest.raises(ValueError, match="project_name"):
        ProjectPitchSkill().run(_request(inputs={"project_name": ""}))


def test_project_pitch_skill_missing_target_role_raises() -> None:
    with pytest.raises(ValueError, match="target_role"):
        ProjectPitchSkill().run(_request(inputs={"target_role": ""}))


def test_project_pitch_skill_default_retriever_type_is_keyword(monkeypatch) -> None:
    fake_retriever = FakeRetriever()
    captured = {}

    def fake_get_retriever(retriever_type):
        captured["retriever_type"] = retriever_type
        return fake_retriever

    monkeypatch.setattr("skills.project_pitch.get_retriever", fake_get_retriever)
    monkeypatch.setattr("skills.project_pitch.generate_text", lambda prompt: "# 1. 开场一句话\n项目说明 [E1]")

    result = ProjectPitchSkill().run(_request(inputs={"retriever_type": ""}))

    assert captured["retriever_type"] == "keyword"
    assert fake_retriever.calls[0]["db_path"] == "/tmp/test.db"
    assert result.metadata["retriever_type"] == "keyword"


def test_project_pitch_skill_passes_hybrid_retriever_type(monkeypatch) -> None:
    fake_retriever = FakeRetriever()
    captured = {}

    def fake_get_retriever(retriever_type):
        captured["retriever_type"] = retriever_type
        return fake_retriever

    monkeypatch.setattr("skills.project_pitch.get_retriever", fake_get_retriever)
    monkeypatch.setattr("skills.project_pitch.generate_text", lambda prompt: "项目说明 [E1]")

    ProjectPitchSkill().run(_request(inputs={"retriever_type": "hybrid"}))

    assert captured["retriever_type"] == "hybrid"
    assert fake_retriever.calls[0]["query"] == "InterviewAce RAG"
    assert fake_retriever.calls[0]["top_k"] == 5


def test_project_pitch_skill_calls_generate_text(monkeypatch) -> None:
    fake_retriever = FakeRetriever()
    captured = {}

    def fake_generate_text(prompt):
        captured["prompt"] = prompt
        return "# 1. 开场一句话\nInterviewAce 是一个面试复盘系统 [E1]"

    monkeypatch.setattr("skills.project_pitch.get_retriever", lambda retriever_type: fake_retriever)
    monkeypatch.setattr("skills.project_pitch.generate_text", fake_generate_text)

    result = ProjectPitchSkill().run(
        _request(
            inputs={
                "focus_points": ["RAG", "FastAPI"],
                "duration_minutes": 5,
                "language": "zh",
                "include_prompt": True,
            }
        )
    )

    assert "【项目名称】" in captured["prompt"]
    assert "RAG、FastAPI" in captured["prompt"]
    assert result.output["prompt"] is not None
    assert result.output["pitch"].startswith("# 1. 开场一句话")


def test_project_pitch_skill_does_not_call_search_knowledge_chunks(monkeypatch) -> None:
    def fail_search(*args, **kwargs):
        raise AssertionError("search_knowledge_chunks should not be called directly")

    monkeypatch.setattr("knowledge.search.search_knowledge_chunks", fail_search)
    monkeypatch.setattr("skills.project_pitch.get_retriever", lambda retriever_type: FakeRetriever())
    monkeypatch.setattr("skills.project_pitch.generate_text", lambda prompt: "项目说明 [E1]")

    result = ProjectPitchSkill().run(_request())

    assert result.skill_name == "project_pitch"


def test_project_pitch_skill_returns_skill_result(monkeypatch) -> None:
    monkeypatch.setattr("skills.project_pitch.get_retriever", lambda retriever_type: FakeRetriever())
    monkeypatch.setattr(
        "skills.project_pitch.generate_text",
        lambda prompt: "# 1. 开场一句话\nInterviewAce 可沉淀 Evidence Context [E1]",
    )

    result = ProjectPitchSkill().run(_request(inputs={"retriever_type": "hybrid"}))

    assert isinstance(result, SkillResult)
    assert result.skill_name == "project_pitch"
    assert result.success is True
    assert result.output["pitch"].startswith("# 1. 开场一句话")
    assert result.output["evidence_context"].count("[E1]") == 1
    assert result.output["used_evidence_count"] == 1
    assert result.output["evidence_validation"]["is_valid"] is True
    assert result.metadata["project_name"] == "InterviewAce"
    assert result.metadata["target_role"] == "Agent / RAG 应用工程师"
    assert result.metadata["retriever_type"] == "hybrid"


def test_project_pitch_skill_records_unknown_evidence_ref(monkeypatch) -> None:
    monkeypatch.setattr("skills.project_pitch.get_retriever", lambda retriever_type: FakeRetriever())
    monkeypatch.setattr("skills.project_pitch.generate_text", lambda prompt: "项目说明 [E9]")

    result = ProjectPitchSkill().run(_request())

    assert result.output["evidence_validation"]["is_valid"] is False
    assert result.output["evidence_validation"]["issues"][0]["code"] == "unknown_evidence_ref"


def test_create_default_skill_registry_registers_project_pitch() -> None:
    registry = create_default_skill_registry()

    assert registry.has("project_pitch") is True
    assert isinstance(registry.get("project_pitch"), ProjectPitchSkill)


def test_api_list_skills_includes_project_pitch() -> None:
    client = TestClient(app)

    response = client.get("/api/skills")
    names = [skill["name"] for skill in response.json()["skills"]]

    assert response.status_code == 200
    assert "project_pitch" in names


def test_api_run_project_pitch_skill(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INTERVIEWACE_DB_PATH", str(tmp_path / "skills.db"))
    monkeypatch.setattr("skills.project_pitch.get_retriever", lambda retriever_type: FakeRetriever())
    monkeypatch.setattr("skills.project_pitch.generate_text", lambda prompt: "项目说明 [E1]")
    client = TestClient(app)

    response = client.post(
        "/api/skills/project_pitch/run",
        json={
            "inputs": {
                "project_name": "InterviewAce",
                "target_role": "Agent / RAG 应用工程师",
                "retriever_type": "hybrid",
            }
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["skill_name"] == "project_pitch"
    assert data["output"]["pitch"] == "项目说明 [E1]"
    assert data["metadata"]["retriever_type"] == "hybrid"


def test_api_submit_project_pitch_task(monkeypatch, tmp_path) -> None:
    captured = {}

    class FakeAsyncResult:
        def __init__(self, task_id):
            self.id = task_id

    class FakeUUID:
        hex = "project-pitch-task-id"

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
        "/api/skills/project_pitch/tasks",
        json={
            "inputs": {
                "project_name": "InterviewAce",
                "target_role": "Agent / RAG 应用工程师",
                "retriever_type": "hybrid",
            }
        },
    )
    data = response.json()
    record = get_task_record(db_path, data["task_id"])

    assert response.status_code == 202
    assert data["task_id"] == "project-pitch-task-id"
    assert data["skill_name"] == "project_pitch"
    assert captured["task_id"] == "project-pitch-task-id"
    assert captured["payload"]["skill_name"] == "project_pitch"
    assert captured["payload"]["inputs"]["retriever_type"] == "hybrid"
    assert record["status"] == "PENDING"
    assert record["request"]["skill_name"] == "project_pitch"
