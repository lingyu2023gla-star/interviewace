"""knowledge.repository tests."""

from __future__ import annotations

import sqlite3

from knowledge.repository import (
    compute_content_hash,
    init_knowledge_tables,
    list_knowledge_chunks,
    upsert_knowledge_chunks,
)
from knowledge.schemas import KnowledgeChunk


def test_init_knowledge_tables_creates_table(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge.db")

    init_knowledge_tables(db_path)

    conn = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    conn.close()
    assert "knowledge_chunks" in tables


def test_compute_content_hash_is_stable() -> None:
    hash_a = compute_content_hash("turn_feedback", "turn:1:feedback", "反馈内容")
    hash_b = compute_content_hash("turn_feedback", "turn:1:feedback", "反馈内容")
    hash_c = compute_content_hash("turn_feedback", "turn:1:feedback", "不同反馈")

    assert hash_a == hash_b
    assert hash_a != hash_c


def test_upsert_knowledge_chunks_inserts_rows(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge.db")
    chunks = [
        KnowledgeChunk(source_type="session_summary", source_id="session:1:summary", session_id=1, content="总结"),
        KnowledgeChunk(source_type="turn_feedback", source_id="turn:1:feedback", session_id=1, content="反馈"),
    ]

    result = upsert_knowledge_chunks(db_path, chunks)
    rows = list_knowledge_chunks(db_path)

    assert result.created == 2
    assert result.skipped == 0
    assert result.total == 2
    assert len(rows) == 2


def test_upsert_knowledge_chunks_is_idempotent(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge.db")
    chunks = [
        KnowledgeChunk(source_type="session_summary", source_id="session:1:summary", session_id=1, content="总结"),
        KnowledgeChunk(source_type="turn_feedback", source_id="turn:1:feedback", session_id=1, content="反馈"),
    ]

    first = upsert_knowledge_chunks(db_path, chunks)
    second = upsert_knowledge_chunks(db_path, chunks)
    rows = list_knowledge_chunks(db_path)

    assert first.created == 2
    assert first.skipped == 0
    assert second.created == 0
    assert second.skipped == 2
    assert len(rows) == 2


def test_list_knowledge_chunks_filters(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge.db")
    chunks = [
        KnowledgeChunk(source_type="session_summary", source_id="session:1:summary", session_id=1, content="总结1"),
        KnowledgeChunk(source_type="turn_feedback", source_id="turn:1:feedback", session_id=1, content="反馈1"),
        KnowledgeChunk(source_type="session_summary", source_id="session:2:summary", session_id=2, content="总结2"),
    ]
    upsert_knowledge_chunks(db_path, chunks)

    session_rows = list_knowledge_chunks(db_path, session_id=1)
    source_rows = list_knowledge_chunks(db_path, source_type="session_summary")

    assert len(session_rows) == 2
    assert {row["session_id"] for row in session_rows} == {1}
    assert len(source_rows) == 2
    assert {row["source_type"] for row in source_rows} == {"session_summary"}
