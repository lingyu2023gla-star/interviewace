# Task Records

InterviewAce uses Celery + Redis for asynchronous task execution. Redis remains the broker and result backend. `task_records` adds a lightweight SQLite persistence layer so task requests, status transitions, results, and failures can be inspected after Redis results expire.

## 1. Why task_records

Redis result backend is good for short-lived task polling, but it is not a durable audit trail. `task_records` gives InterviewAce a local, queryable history for async tasks:

- task submission payload
- current persisted status
- started / finished timestamps
- success result JSON
- failure reason

This is useful for debugging, later UI task history, and future result persistence.

## 2. Relationship with Redis

`task_records` does not replace Redis.

```text
FastAPI
  ↓ create PENDING task_records row
Celery apply_async(task_id=...)
  ↓
Redis broker
  ↓
Celery worker
  ↓ update STARTED / SUCCESS / FAILURE in task_records
Redis result backend
  ↓
GET /api/tasks/{task_id}
```

`GET /api/tasks/{task_id}` still reads Celery / Redis status first and preserves the existing response fields. It now also attaches `task_record` when a SQLite record exists.

## 3. Table Structure

```sql
CREATE TABLE IF NOT EXISTS task_records (
    task_id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL,
    status TEXT NOT NULL,
    request_json TEXT,
    result_json TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    updated_at TEXT NOT NULL
);
```

Supported statuses:

- `PENDING`
- `STARTED`
- `SUCCESS`
- `FAILURE`

Timestamps are stored as UTC ISO strings.

## 4. Status Flow

```text
API submit
  ↓
PENDING
  ↓
worker starts
  ↓
STARTED
  ↓
SUCCESS + result_json

or

FAILURE + error_message
```

If task record updates fail inside a worker, the worker does not swallow or replace the original business task result. On task failure, the original exception is re-raised so Celery still records `FAILURE` in Redis.

## 5. API Query

```bash
curl -s http://127.0.0.1:8000/api/tasks/<task_id> | python -m json.tool
```

Response keeps the original fields and adds `task_record`:

```json
{
  "task_id": "example",
  "status": "SUCCESS",
  "ready": true,
  "successful": true,
  "result": {
    "plan": "..."
  },
  "error": null,
  "task_record": {
    "task_id": "example",
    "task_name": "preparation.generate_plan",
    "status": "SUCCESS",
    "request": {
      "user_goal": "准备面试"
    },
    "result": {
      "plan": "..."
    },
    "error_message": null,
    "created_at": "...",
    "started_at": "...",
    "finished_at": "...",
    "updated_at": "..."
  }
}
```

## 6. Current Limitations

- Redis is still required for real Celery execution.
- `task_records` is local SQLite persistence, not a distributed task store.
- There is no task cancel / revoke API yet.
- There is no retention policy or cleanup job yet.
- `task_records` stores JSON with `default=str`; unusual unserializable values may be stringified.
