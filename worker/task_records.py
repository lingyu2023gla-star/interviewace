"""SQLite persistence for asynchronous task records."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator


@contextmanager
def _connect(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """Open a SQLite connection with row dict support."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _now_utc() -> str:
    """Return a UTC ISO timestamp string."""
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: Any) -> str | None:
    """Serialize a value to JSON with safe fallback."""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def _json_loads(value: str | None) -> Any:
    """Parse a JSON field, falling back to the raw string."""
    if value is None:
        return None
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def init_task_records_table(db_path: str) -> None:
    """Create task_records table if it does not exist."""
    with _connect(db_path) as conn:
        conn.execute(
            """
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
            )
            """
        )


def create_task_record(
    db_path: str,
    task_id: str,
    task_name: str,
    request: dict | None = None,
) -> None:
    """Create or replace a pending task record."""
    init_task_records_table(db_path)
    now = _now_utc()
    with _connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO task_records
               (task_id, task_name, status, request_json, result_json,
                error_message, created_at, started_at, finished_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_id,
                task_name,
                "PENDING",
                _json_dumps(request),
                None,
                None,
                now,
                None,
                None,
                now,
            ),
        )


def mark_task_started(db_path: str, task_id: str) -> None:
    """Mark a task as started."""
    init_task_records_table(db_path)
    now = _now_utc()
    with _connect(db_path) as conn:
        conn.execute(
            """UPDATE task_records
               SET status = ?, started_at = COALESCE(started_at, ?), updated_at = ?
               WHERE task_id = ?""",
            ("STARTED", now, now, task_id),
        )


def mark_task_success(
    db_path: str,
    task_id: str,
    result: dict | list | str | None = None,
) -> None:
    """Mark a task as successful and store its result."""
    init_task_records_table(db_path)
    now = _now_utc()
    with _connect(db_path) as conn:
        conn.execute(
            """UPDATE task_records
               SET status = ?, result_json = ?, error_message = NULL,
                   finished_at = ?, updated_at = ?
               WHERE task_id = ?""",
            ("SUCCESS", _json_dumps(result), now, now, task_id),
        )


def mark_task_failure(
    db_path: str,
    task_id: str,
    error_message: str,
    result: dict | list | str | None = None,
) -> None:
    """Mark a task as failed and store its error message."""
    init_task_records_table(db_path)
    now = _now_utc()
    with _connect(db_path) as conn:
        conn.execute(
            """UPDATE task_records
               SET status = ?, result_json = ?, error_message = ?,
                   finished_at = ?, updated_at = ?
               WHERE task_id = ?""",
            ("FAILURE", _json_dumps(result), error_message, now, now, task_id),
        )


def get_task_record(db_path: str, task_id: str) -> dict | None:
    """Return a task record dict, parsing request/result JSON when possible."""
    init_task_records_table(db_path)
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM task_records WHERE task_id = ?",
            (task_id,),
        ).fetchone()
    if row is None:
        return None

    record = dict(row)
    record["request"] = _json_loads(record.pop("request_json"))
    record["result"] = _json_loads(record.pop("result_json"))
    return record
