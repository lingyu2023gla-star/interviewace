# Skill API

V10.3 exposes the Skill Layer through FastAPI and Celery-backed async tasks.

## 1. Purpose

The Skill API lets clients discover and run registered skills without knowing their internal implementation. The first registered skill is:

- `interview_preparation`

The API does not implement a natural language Skill Router. Clients must call a concrete skill name.

## 2. Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/skills` | List registered skill specs. |
| `GET` | `/api/skills/{skill_name}` | Get one skill spec. |
| `POST` | `/api/skills/{skill_name}/run` | Run a skill synchronously. |
| `POST` | `/api/skills/{skill_name}/tasks` | Submit a skill async task. |
| `GET` | `/api/tasks/{task_id}` | Query async task status through the existing task API. |

## 3. List Skills

```bash
curl -s http://127.0.0.1:8000/api/skills | python -m json.tool
```

Example response:

```json
{
  "skills": [
    {
      "name": "interview_preparation",
      "description": "Generate an evidence-based structured interview preparation plan.",
      "supported_retriever_types": ["keyword", "fts", "embedding", "hybrid"],
      "requires_evidence": true,
      "supports_async": true,
      "tags": ["interview", "preparation", "rag", "structured-output"]
    }
  ]
}
```

## 4. Get One Skill

```bash
curl -s http://127.0.0.1:8000/api/skills/interview_preparation | python -m json.tool
```

Unknown skills return `404`.

## 5. Run Skill Synchronously

```bash
curl -s -X POST http://127.0.0.1:8000/api/skills/interview_preparation/run \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "user_goal": "准备 Agent/RAG 应用工程师面试",
      "job_direction": "大模型应用工程师",
      "query": "Agent RAG",
      "retriever_type": "keyword",
      "plan_days": 3
    },
    "metadata": {
      "source": "curl"
    }
  }' | python -m json.tool
```

The API injects `context.db_path` from `INTERVIEWACE_DB_PATH` when callers do not provide it.

## 6. Submit Async Skill Task

```bash
curl -s -X POST http://127.0.0.1:8000/api/skills/interview_preparation/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "user_goal": "准备 Agent/RAG 应用工程师面试",
      "job_direction": "大模型应用工程师",
      "query": "Agent RAG",
      "retriever_type": "keyword",
      "plan_days": 3
    }
  }' | python -m json.tool
```

Example response:

```json
{
  "task_id": "abc123",
  "skill_name": "interview_preparation",
  "status": "PENDING"
}
```

Query status through the existing task endpoint:

```bash
curl -s http://127.0.0.1:8000/api/tasks/<task_id> | python -m json.tool
```

## 7. Async Task Flow

```text
POST /api/skills/{skill_name}/tasks
  -> create task_records PENDING
  -> Celery task skills.run_skill
  -> create_default_skill_registry()
  -> SkillRequest
  -> skill.run(...)
  -> SkillResult dict
  -> task_records SUCCESS / FAILURE
  -> GET /api/tasks/{task_id}
```

`task_records.request` stores:

```json
{
  "skill_name": "interview_preparation",
  "inputs": {},
  "context": {},
  "metadata": {}
}
```

`task_records.result` stores a JSON-compatible `SkillResult`.

## 8. Current Scope

V10.3 intentionally does not:

- implement a Skill Router;
- add `skill_runs`;
- add `ProjectPitchSkill`;
- add `MockInterviewQuestionSkill`;
- replace existing preparation APIs;
- change retriever defaults;
- change Evidence Context format.

## 9. Testing

```bash
.venv/bin/python -m pytest tests/test_api_skills.py tests/test_skill_tasks.py -v
```

Tests monkeypatch service calls and Celery submission. Default pytest does not require real Redis, Celery worker, Docker, network, real LLM calls, or real embedding APIs.
