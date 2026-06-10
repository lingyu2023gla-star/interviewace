# Redis / Celery local integration

## 1. Install dependencies

```bash
.venv/bin/pip install -r requirements.txt
```

## 2. Start Redis

### A. Docker

```bash
./scripts/run_redis_docker.sh
```

If port 6379 is already in use, stop the existing Redis process or container first.

If you see `docker: command not found`, use local Redis instead or install Docker Desktop.

### B. Local Redis

```bash
brew install redis
./scripts/run_redis_local.sh
redis-cli ping
```

`redis-cli ping` should print `PONG`.

## 3. Start API

In a new terminal:

```bash
./scripts/run_api.sh
```

## 4. Start Celery Worker

In a new terminal:

```bash
./scripts/run_worker.sh
```

## 5. Submit Ping Task

```bash
curl -s -X POST http://127.0.0.1:8000/api/tasks/ping | python -m json.tool
```

Use the returned `task_id`:

```bash
curl -s http://127.0.0.1:8000/api/tasks/<task_id> | python -m json.tool
```

Expected final result:

```json
{
  "status": "SUCCESS",
  "ready": true,
  "successful": true,
  "result": {
    "status": "ok",
    "message": "pong",
    "payload": {
      "source": "api"
    }
  },
  "error": null
}
```

## 6. Optional Integration Test

After Redis and the worker are running:

```bash
RUN_CELERY_INTEGRATION=1 .venv/bin/python -m pytest tests/test_celery_redis_integration.py -v
```

## 7. Submit Preparation Plan Task

This calls the real LLM. Run it only after API keys and network access are configured.

```bash
curl -s -X POST http://127.0.0.1:8000/api/preparation/plan-tasks \
  -H "Content-Type: application/json" \
  -d '{
    "user_goal": "准备 Agent/RAG 应用工程师面试",
    "job_direction": "大模型应用工程师",
    "query": "Agent RAG",
    "plan_days": 7,
    "daily_minutes": 60,
    "max_tasks_per_day": 3,
    "top_k": 5,
    "include_prompt": false
  }' | python -m json.tool
```

Then poll:

```bash
curl -s http://127.0.0.1:8000/api/tasks/<task_id> | python -m json.tool
```

## 8. Troubleshooting

- If `./scripts/run_redis_docker.sh` fails with `docker: command not found`:
  - Use local Redis with `brew install redis` and `./scripts/run_redis_local.sh`.
  - Or install Docker Desktop and retry the Docker script.
- If the worker logs `Connection refused`:
  - Redis is usually not running.
  - Redis may be listening on a port other than 6379.
  - Check that `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` point to the running Redis instance.
- If `POST /api/tasks/ping` hangs or fails:
  - Check whether Redis is running.
  - Check that `CELERY_BROKER_URL` is the same for API and worker.
  - Check whether the worker is running.
  - Check whether the worker log receives the task.
- If `GET /api/tasks/{task_id}` stays `PENDING`:
  - The worker may not be running.
  - API and worker may be using different Redis DBs.
  - The task name may not be included by the worker.
- If a preparation task cannot find knowledge chunks:
  - `INTERVIEWACE_DB_PATH` must match between API and worker.
  - Avoid running the API with `/tmp/test.db` while the worker uses `data/interviews.db`.
- If a preparation task is `FAILURE`:
  - Check worker logs.
  - The LLM API key may be missing.
  - The database path may be wrong.
  - Network or proxy settings may be incorrect.
