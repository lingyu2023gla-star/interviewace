# InterviewPreparationSkill

V10.2 adds the first real InterviewAce business skill: `InterviewPreparationSkill`.

## 1. Purpose

`InterviewPreparationSkill` wraps the existing structured preparation service as a reusable skill. It generates an evidence-based structured interview preparation plan from a generic `SkillRequest`.

It does not reimplement retrieval, Evidence Context, prompt building, LLM calls, parsing, or evidence validation. Those remain in the existing preparation and knowledge layers.

## 2. Relationship To Structured Preparation Service

The skill is a thin adapter:

```text
SkillRequest
  -> InterviewPreparationSkill.run(...)
  -> generate_structured_preparation_plan(...)
  -> SkillResult
```

The structured preparation service still owns:

- retrieval through `retriever_type`;
- Evidence Context building;
- structured prompt construction;
- LLM text generation;
- JSON parsing;
- evidence reference validation.

## 3. Skill Spec

```text
name: interview_preparation
description: Generate an evidence-based structured interview preparation plan.
supported_retriever_types: keyword / fts / embedding / hybrid
requires_evidence: true
supports_async: true
tags: interview / preparation / rag / structured-output
```

## 4. Inputs

`SkillRequest.inputs` supports:

| Field | Required | Default | Description |
| --- | --- | --- | --- |
| `user_goal` | yes | N/A | Preparation goal. |
| `job_direction` | no | `""` | Target job direction. |
| `query` | no | `""` | Retrieval query. Empty query falls back inside the service. |
| `plan_days` | no | `3` | Number of preparation days for skill execution. |
| `daily_minutes` | no | `60` | Daily available time. |
| `max_tasks_per_day` | no | `3` | Maximum tasks per day. |
| `top_k` | no | `5` | Evidence retrieval count. |
| `retriever_type` | no | `keyword` | `keyword`, `fts`, `embedding`, or `hybrid`. |
| `include_prompt` | no | `false` | Whether to return the generated prompt. |

`SkillRequest.context` requires:

| Field | Required | Description |
| --- | --- | --- |
| `db_path` | yes | SQLite database path used by the structured preparation service. |

## 5. Output

`SkillResult.output` contains:

- `structured_plan`
- `raw_output`
- `evidence_context`
- `prompt`
- `used_evidence_count`

`SkillResult.metadata` contains:

- `source: structured_preparation_service`
- `retriever_type`
- `job_direction`
- `plan_days`
- `daily_minutes`
- `used_evidence_count`
- `evidence_validation` when available from structured plan metadata

## 6. Current Scope

V10.2 / V10.3 intentionally do not:

- add a Skill Router;
- write `skill_runs`;
- call a real LLM in tests;
- call a real embedding API;
- change the preparation service behavior;
- change retriever defaults;
- change Evidence Context format.

## 7. Default Registry

`create_default_skill_registry()` creates a registry and registers `InterviewPreparationSkill`.

It is not a global mutable singleton and does not execute the skill at import time.

## 8. Tests

```bash
.venv/bin/python -m pytest tests/test_interview_preparation_skill.py -v
```

Tests monkeypatch the structured preparation service and do not require network, Redis, Docker, Celery worker, real LLM calls, or a real embedding API.

## 9. API And Async Task

V10.3 exposes this skill through:

- `POST /api/skills/interview_preparation/run`
- `POST /api/skills/interview_preparation/tasks`

The async task uses Celery task `skills.run_skill` and persists state through existing `task_records`.

Details: [skill_api.md](skill_api.md)

## 10. Next Step

V10.4 can add skill result persistence without changing the skill interface.
