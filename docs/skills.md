# Skill Layer

V10 starts the InterviewAce Skill Layer. V10.1 defined the common skill specification and registry. V10.2 added the first business skill: `InterviewPreparationSkill`. V10.3 exposes skills through FastAPI and Celery-backed async tasks.

## 1. Purpose

The Skill Layer provides a stable abstraction for future reusable agent skills, such as:

- interview preparation;
- project pitch generation;
- mock interview question generation;
- evidence-based coaching workflows.

Unlike a normal service function, a skill has a discoverable `SkillSpec`, accepts a generic `SkillRequest`, and returns a structured `SkillResult`. This makes skills easier to list, route, test, and later expose through API or async tasks.

## 2. Current Scope

The Skill Layer includes:

- `SkillRequest`
- `SkillResult`
- `SkillSpec`
- `BaseSkill`
- `SkillRegistry`
- `InterviewPreparationSkill`

The current layer does not:

- write `skill_runs`;
- implement a Skill Router.

`InterviewPreparationSkill` calls the existing structured preparation service, so production execution may call the configured LLM through that service. Tests monkeypatch the service and do not call a real LLM.

V10.2 does not:

- call embedding APIs;
- write database tables;
- implement `ProjectPitchSkill`;
- implement `MockInterviewQuestionSkill`.

## 3. Files

```text
skills/
├── __init__.py
├── base.py
├── interview_preparation.py
├── registry.py
└── schemas.py
```

## 4. SkillRequest

`SkillRequest` is the generic input object for a skill.

| Field | Type | Description |
| --- | --- | --- |
| `skill_name` | `str` | Skill to execute. Must be non-empty. |
| `inputs` | `dict[str, Any]` | Business input payload. |
| `context` | `dict[str, Any]` | Runtime context such as `db_path`, `retriever_type`, `session_id`. |
| `metadata` | `dict[str, Any]` | Request metadata such as `request_id`, source, debug flags. |

## 5. SkillResult

`SkillResult` is the generic output object from a skill.

| Field | Type | Description |
| --- | --- | --- |
| `skill_name` | `str` | Actual skill that produced the result. |
| `output` | `dict[str, Any]` | Structured skill output. |
| `metadata` | `dict[str, Any]` | Runtime metadata such as retriever type or validation summary. |
| `success` | `bool` | Whether the skill completed successfully. |
| `error_message` | `str | None` | Optional failure reason. |

## 6. SkillSpec

`SkillSpec` describes a skill without executing it.

| Field | Type | Description |
| --- | --- | --- |
| `name` | `str` | Unique skill name. |
| `description` | `str` | Human-readable summary. |
| `input_schema` | `dict[str, Any]` | Lightweight input schema description. |
| `output_schema` | `dict[str, Any]` | Lightweight output schema description. |
| `supported_retriever_types` | `tuple[str, ...]` | Allowed retriever types. |
| `requires_evidence` | `bool` | Whether the skill expects Evidence Context. |
| `supports_async` | `bool` | Whether future async execution is supported. |
| `tags` | `tuple[str, ...]` | Classification tags. |

Supported retriever types are:

- `keyword`
- `fts`
- `embedding`
- `hybrid`

## 7. BaseSkill

`BaseSkill` defines the interface:

```python
class BaseSkill(ABC):
    @property
    @abstractmethod
    def spec(self) -> SkillSpec:
        ...

    @abstractmethod
    def run(self, request: SkillRequest) -> SkillResult:
        ...

    @property
    def name(self) -> str:
        return self.spec.name
```

It does not know about LLMs, API, Celery, or databases.

## 8. SkillRegistry

`SkillRegistry` manages skill registration and lookup:

- `register(skill)`
- `get(name)`
- `has(name)`
- `list_names()`
- `list_specs()`

Behavior:

- duplicate names raise `SkillAlreadyRegisteredError`;
- missing names raise `SkillNotFoundError`;
- `list_names()` and `list_specs()` are sorted by name for stable tests;
- registry does not execute skills automatically.

`create_default_skill_registry()` returns a new registry containing currently implemented business skills:

- `interview_preparation`
- `project_pitch`

This helper is not a global mutable singleton.

## 9. Current Skill: InterviewPreparationSkill

`InterviewPreparationSkill` wraps the existing structured preparation service.

```text
SkillRequest
  -> InterviewPreparationSkill
  -> structured preparation service
  -> SkillResult
```

Spec summary:

| Field | Value |
| --- | --- |
| `name` | `interview_preparation` |
| `requires_evidence` | `true` |
| `supports_async` | `true` |
| `supported_retriever_types` | `keyword`, `fts`, `embedding`, `hybrid` |
| `tags` | `interview`, `preparation`, `rag`, `structured-output` |

The skill reuses:

- retriever selection via `retriever_type`;
- Evidence Context generation;
- structured preparation plan output;
- evidence reference validation metadata.

Details: [interview_preparation_skill.md](interview_preparation_skill.md)

## 10. Current Skill: ProjectPitchSkill

`ProjectPitchSkill` uses the existing retriever layer and Evidence Context builder to generate an evidence-based project pitch for interviews.

```text
SkillRequest
  -> ProjectPitchSkill
  -> get_retriever(retriever_type)
  -> build_evidence_context
  -> generate_text
  -> evidence ref validation
  -> SkillResult
```

Spec summary:

| Field | Value |
| --- | --- |
| `name` | `project_pitch` |
| `requires_evidence` | `true` |
| `supports_async` | `true` |
| `supported_retriever_types` | `keyword`, `fts`, `embedding`, `hybrid` |
| `tags` | `interview`, `project`, `pitch`, `rag` |

The skill reuses:

- retriever selection via `retriever_type`;
- Evidence Context generation;
- existing LLM text generation wrapper;
- evidence reference validation.

It does not introduce a new API route or Celery task; it is called through the generic Skill API.

Details: [project_pitch_skill.md](project_pitch_skill.md)

## 11. Skill API / Async Task

V10.3 adds:

- `GET /api/skills`
- `GET /api/skills/{skill_name}`
- `POST /api/skills/{skill_name}/run`
- `POST /api/skills/{skill_name}/tasks`
- Celery task `skills.run_skill`

Async skill tasks reuse existing `task_records` and are queried through `GET /api/tasks/{task_id}`.

Details: [skill_api.md](skill_api.md)

## 12. Skill Evaluation

V10.5 adds a lightweight Skill Evaluation layer for checking `SkillResult` structure and evidence validation metadata.

It supports:

- required output key checks;
- required metadata key checks;
- `success` / `error_message` checks;
- `evidence_validation` presence checks;
- `evidence_validation.is_valid` checks;
- running one or more eval cases through a `SkillRegistry`.

It does not call LLMs, embedding APIs, Redis, Celery, or databases by itself.

Details: [skill_evaluation.md](skill_evaluation.md)

## 13. Rule-based Skill Router

V10.6 adds a deterministic router for selecting a registered Skill from user intent.

It supports:

- explicit `skill_name` priority;
- rule-based matching on skill name, tags, description, and predefined keywords;
- candidate scores and a readable routing reason.

It does not call LLMs and does not execute `skill.run()`.

Details: [skill_router.md](skill_router.md)

## 14. Testing

```bash
.venv/bin/python -m pytest tests/test_skills_registry.py -v
.venv/bin/python -m pytest tests/test_interview_preparation_skill.py -v
.venv/bin/python -m pytest tests/test_project_pitch_skill.py -v
.venv/bin/python -m pytest tests/test_skill_evaluation.py -v
.venv/bin/python -m pytest tests/test_skill_router.py -v
.venv/bin/python -m pytest tests/test_api_skills.py tests/test_skill_tasks.py -v
```

Tests use local dummy skills or monkeypatched services and do not require Redis, Docker, Celery worker, network, real LLM calls, or embedding APIs.

## 15. Roadmap

Planned V10 work:

- Skill result persistence
- richer RAG Eval and claim verification
