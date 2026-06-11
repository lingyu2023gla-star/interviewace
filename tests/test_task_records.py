"""Task record repository tests."""

from __future__ import annotations

import sqlite3

from worker.task_records import (
    create_task_record,
    get_task_record,
    init_task_records_table,
    mark_task_failure,
    mark_task_started,
    mark_task_success,
)


def test_init_task_records_table_creates_table(tmp_path) -> None:
    db_path = str(tmp_path / "tasks.db")

    init_task_records_table(db_path)

    conn = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    conn.close()
    assert "task_records" in tables


def test_create_task_record_creates_pending(tmp_path) -> None:
    db_path = str(tmp_path / "tasks.db")

    create_task_record(db_path, "task-1", "system.ping", {"source": "api"})
    record = get_task_record(db_path, "task-1")

    assert record is not None
    assert record["status"] == "PENDING"
    assert record["task_name"] == "system.ping"
    assert record["request"]["source"] == "api"
    assert record["created_at"]
    assert record["updated_at"]


def test_mark_task_started_updates_status_and_started_at(tmp_path) -> None:
    db_path = str(tmp_path / "tasks.db")
    create_task_record(db_path, "task-1", "system.ping")

    mark_task_started(db_path, "task-1")
    record = get_task_record(db_path, "task-1")

    assert record["status"] == "STARTED"
    assert record["started_at"]


def test_mark_task_success_updates_result_and_finished_at(tmp_path) -> None:
    db_path = str(tmp_path / "tasks.db")
    create_task_record(db_path, "task-1", "system.ping")

    mark_task_success(db_path, "task-1", {"status": "ok"})
    record = get_task_record(db_path, "task-1")

    assert record["status"] == "SUCCESS"
    assert record["result"]["status"] == "ok"
    assert record["finished_at"]
    assert record["error_message"] is None


def test_mark_task_failure_updates_error_and_finished_at(tmp_path) -> None:
    db_path = str(tmp_path / "tasks.db")
    create_task_record(db_path, "task-1", "system.ping")

    mark_task_failure(db_path, "task-1", "LLM failed", {"phase": "generate"})
    record = get_task_record(db_path, "task-1")

    assert record["status"] == "FAILURE"
    assert record["error_message"] == "LLM failed"
    assert record["result"]["phase"] == "generate"
    assert record["finished_at"]


def test_get_task_record_parses_request_and_result_json(tmp_path) -> None:
    db_path = str(tmp_path / "tasks.db")
    create_task_record(db_path, "task-1", "system.ping", {"x": 1})
    mark_task_success(db_path, "task-1", ["ok"])

    record = get_task_record(db_path, "task-1")

    assert record["request"] == {"x": 1}
    assert record["result"] == ["ok"]


def test_get_task_record_invalid_json_falls_back(tmp_path) -> None:
    db_path = str(tmp_path / "tasks.db")
    create_task_record(db_path, "task-1", "system.ping", {"x": 1})
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE task_records SET request_json = ?, result_json = ? WHERE task_id = ?",
        ("{bad", "{bad-result", "task-1"),
    )
    conn.commit()
    conn.close()

    record = get_task_record(db_path, "task-1")

    assert record["request"] == "{bad"
    assert record["result"] == "{bad-result"
