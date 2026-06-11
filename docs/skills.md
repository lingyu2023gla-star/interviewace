# Skill Layer

V10 starts the InterviewAce Skill Layer. V10.1 only defines the common skill specification and registry. It does not implement any business skill yet.

## 1. Purpose

The Skill Layer provides a stable abstraction for future reusable agent skills, such as:

- interview preparation;
- project pitch generation;
- mock interview question generation;
- evidence-based coaching workflows.

Unlike a normal service function, a skill has a discoverable `SkillSpec`, accepts a generic `SkillRequest`, and returns a structured `SkillResult`. This makes skills easier to list, route, test, and later expose through API or async tasks.

## 2. Current Scope

V10.1 includes:

- `SkillRequest`
- `SkillResult`
- `SkillSpec`
- `BaseSkill`
- `SkillRegistry`

V10.1 does not:

- call LLMs;
- call embedding APIs;
- add FastAPI routes;
- add Celery tasks;
- write database tables;
- implement business skills.

## 3. Files

```text
skills/
├── __init__.py
├── base.py
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

## 9. Testing

```bash
.venv/bin/python -m pytest tests/test_skills_registry.py -v
```

Tests use only local dummy skills and do not require Redis, Docker, Celery worker, network, real LLM calls, or embedding APIs.

## 10. Roadmap

Planned V10 work:

- V10.2: `InterviewPreparationSkill`
- V10.3: Skill API / async task integration
- V10.4: Skill result persistence
- V10.5: Skill evaluation
