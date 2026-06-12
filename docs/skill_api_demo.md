# Skill API Demo

This document shows copy-pasteable Skill API examples for the V10 demo.

## 1. Start API

Preferred project script:

```bash
./scripts/run_api.sh
```

Equivalent direct command:

```bash
.venv/bin/python -m uvicorn api.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## 2. List Skills

This does not call the LLM.

```bash
curl -s http://127.0.0.1:8000/api/skills | python -m json.tool
```

## 3. Get interview_preparation Spec

This does not call the LLM.

```bash
curl -s http://127.0.0.1:8000/api/skills/interview_preparation | python -m json.tool
```

## 4. Get project_pitch Spec

This does not call the LLM.

```bash
curl -s http://127.0.0.1:8000/api/skills/project_pitch | python -m json.tool
```

## 5. Run interview_preparation Synchronously

This can call the real LLM. Use it only when `DEEPSEEK_API_KEY`, network, and local database data are ready.

```bash
curl -s -X POST http://127.0.0.1:8000/api/skills/interview_preparation/run \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "user_goal": "准备后端大模型应用工程师面试",
      "job_direction": "Python 后端 + RAG + Agent",
      "query": "InterviewAce RAG Skill API Evidence Validation",
      "plan_days": 3,
      "daily_minutes": 60,
      "retriever_type": "keyword",
      "include_prompt": false
    },
    "context": {
      "db_path": "data/interviews.db"
    },
    "metadata": {
      "source": "demo"
    }
  }' | python -m json.tool
```

## 6. Run project_pitch Synchronously

This can call the real LLM. Use it only when `DEEPSEEK_API_KEY`, network, and local database data are ready.

```bash
curl -s -X POST http://127.0.0.1:8000/api/skills/project_pitch/run \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "project_name": "InterviewAce",
      "target_role": "后端大模型应用工程师",
      "query": "InterviewAce RAG Skill API Evidence Validation",
      "duration_minutes": 3,
      "language": "zh",
      "retriever_type": "keyword",
      "top_k": 5,
      "include_prompt": false,
      "focus_points": ["RAG", "FastAPI", "Celery", "Evidence Validation"],
      "style": "interview"
    },
    "context": {
      "db_path": "data/interviews.db"
    },
    "metadata": {
      "source": "demo"
    }
  }' | python -m json.tool
```

## 7. Submit project_pitch Async Task

This can call the real LLM when the Celery worker executes the task.

Redis and worker must be running:

```bash
./scripts/run_redis_local.sh
./scripts/run_worker.sh
```

Submit:

```bash
curl -s -X POST http://127.0.0.1:8000/api/skills/project_pitch/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "project_name": "InterviewAce",
      "target_role": "后端大模型应用工程师",
      "query": "InterviewAce RAG Skill API Evidence Validation",
      "duration_minutes": 3,
      "language": "zh",
      "retriever_type": "keyword",
      "top_k": 5
    },
    "context": {
      "db_path": "data/interviews.db"
    },
    "metadata": {
      "source": "demo"
    }
  }' | python -m json.tool
```

## 8. Query Task Status

Replace `<task_id>` with the actual task id returned by the previous command.

```bash
curl -s http://127.0.0.1:8000/api/tasks/<task_id> | python -m json.tool
```

## 9. Safe Smoke Test

The safe smoke test only calls read-only Skill discovery endpoints:

```bash
./scripts/smoke_skill_api.sh
```

It does not call:

- `/run`
- `/tasks`
- LLM APIs
- embedding APIs

## 10. LLM Safety Notes

- `GET /api/skills` does not trigger LLM.
- `GET /api/skills/{skill_name}` does not trigger LLM.
- `POST /api/skills/{skill_name}/run` may trigger LLM.
- `POST /api/skills/{skill_name}/tasks` may trigger LLM when a worker executes the task.
