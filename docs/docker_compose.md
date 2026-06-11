# Docker Compose Local Dev Stack

V8.3 adds a local Docker Compose stack for running the InterviewAce backend services together:

- FastAPI API
- Celery worker
- Redis broker / result backend

The default pytest suite still does not require Docker, Redis, a Celery worker, or a real LLM API key.

## 1. Architecture

```text
Host
  ↓ http://127.0.0.1:8000
api container
  ↓ redis://redis:6379/0
redis container
  ↓ task delivery
worker container
  ↓ redis://redis:6379/1
redis result backend
```

The API and worker share the same mounted SQLite path:

```text
INTERVIEWACE_DB_PATH=/app/data/interviews.db
```

The host `./data` directory is mounted to `/app/data`, so SQLite data survives container rebuilds and restarts.

## 2. Start

```bash
docker compose up --build
```

## 3. Start In Background

```bash
docker compose up -d --build
```

## 4. Logs

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f redis
```

## 5. Stop

```bash
docker compose down
```

## 6. Clean Volumes

```bash
docker compose down -v
```

This removes Docker-managed volumes. The mounted host directories `./data`, `./outputs`, and `./exports` remain on your machine.

## 7. API Verification

```bash
curl http://127.0.0.1:8000/api/health
```

OpenAPI docs:

```text
http://127.0.0.1:8000/docs
```

## 8. Ping Task Verification

Submit a ping task:

```bash
curl -s -X POST http://127.0.0.1:8000/api/tasks/ping | python -m json.tool
```

Use the returned `task_id`:

```bash
curl -s http://127.0.0.1:8000/api/tasks/<task_id> | python -m json.tool
```

Expected final state:

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

The response also includes `task_record` when the SQLite record exists.

## 9. Optional Smoke Flow

Use this flow when you want to verify the full local stack manually:

```bash
docker compose up -d --build
```

Wait until the API and worker are ready, then run:

```bash
curl http://127.0.0.1:8000/api/health
curl -s -X POST http://127.0.0.1:8000/api/tasks/ping | python -m json.tool
```

Poll the returned task id:

```bash
curl -s http://127.0.0.1:8000/api/tasks/<task_id> | python -m json.tool
```

Then inspect logs if needed:

```bash
docker compose logs -f api
docker compose logs -f worker
```

Stop the stack:

```bash
docker compose down
```

## 10. Optional CI-only Config Check

The default pytest suite does not invoke Docker. To validate that Docker Compose can parse the stack configuration without starting services, run:

```bash
RUN_DOCKER_COMPOSE_CHECK=1 .venv/bin/python -m pytest tests/test_docker_compose_ci.py -v
```

This runs:

```bash
docker compose config
```

It is a configuration check only; it does not build images or start containers.

## 11. Environment Variables

Inside Docker Compose:

```text
INTERVIEWACE_DB_PATH=/app/data/interviews.db
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

When running directly on the host, use localhost Redis:

```text
INTERVIEWACE_DB_PATH=data/interviews.db
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

If you call endpoints that invoke the real LLM, also configure the project’s existing LLM API key, for example `DEEPSEEK_API_KEY`. The ping task and `/api/health` do not require a real LLM key.

## 12. Notes

- Redis is available as `redis:6379` inside the compose network.
- API listens on `0.0.0.0:8000` in the container and is exposed as `127.0.0.1:8000` on the host.
- API and worker share `./data:/app/data`, `./outputs:/app/outputs`, and `./exports:/app/exports`.
- Default pytest remains local and mocked; it does not start Docker or Redis.
