# Skill Layer

V10 starts the InterviewAce Skill Layer. V10.1 defined the common skill specification and registry. V10.2 adds the first business skill: `InterviewPreparationSkill`.

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

- add FastAPI skill routes;
- add Celery skill tasks;
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
| `supports_async` | `false` |
| `supported_retriever_types` | `keyword`, `fts`, `embedding`, `hybrid` |
| `tags` | `interview`, `preparation`, `rag`, `structured-output` |

The skill reuses:

- retriever selection via `retriever_type`;
- Evidence Context generation;
- structured preparation plan output;
- evidence reference validation metadata.

Details: [interview_preparation_skill.md](interview_preparation_skill.md)

## 10. Testing

```bash
.venv/bin/python -m pytest tests/test_skills_registry.py -v
.venv/bin/python -m pytest tests/test_interview_preparation_skill.py -v
```

Tests use local dummy skills or monkeypatched services and do not require Redis, Docker, Celery worker, network, real LLM calls, or embedding APIs.

## 11. Roadmap

Planned V10 work:

- V10.3: Skill API / async task integration
- V10.4: Skill result persistence
- V10.5: Skill evaluation
