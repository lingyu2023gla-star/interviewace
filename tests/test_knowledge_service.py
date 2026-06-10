"""knowledge.service tests."""

from __future__ import annotations

import sqlite3

from knowledge.repository import list_knowledge_chunks
from knowledge.service import (
    SOURCE_QUESTION_BANK,
    SOURCE_SESSION_SUMMARY,
    SOURCE_TURN_FEEDBACK,
    build_chunks_from_session,
    index_interview_session,
)


def _create_business_tables(db_path: str) -> None:
    """Create minimal existing business tables for knowledge service tests."""
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            job_direction TEXT NOT NULL,
            created_at TEXT NOT NULL,
            summary TEXT
        );

        CREATE TABLE turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            turn_index INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            feedback TEXT,
            topic TEXT DEFAULT ''
        );

        CREATE TABLE questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_session_id INTEGER,
            topic TEXT NOT NULL,
            question TEXT NOT NULL,
            reference_answer TEXT DEFAULT '',
            difficulty TEXT DEFAULT 'medium',
            mastery TEXT DEFAULT 'new',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    conn.close()


def _insert_session_fixture(db_path: str) -> int:
    """Insert one session with two turns and one question."""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        """INSERT INTO sessions (title, job_direction, created_at, summary)
           VALUES (?, ?, ?, ?)""",
        ("Agent 面试", "大模型应用工程师", "2026-06-10 10:00:00", "整体总结内容"),
    )
    session_id = cursor.lastrowid
    conn.executemany(
        """INSERT INTO turns (session_id, turn_index, question, answer, feedback, topic)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [
            (session_id, 1, "什么是 Orchestrator？", "负责调度 Tool。", "Agent 架构反馈", "Agent 架构"),
            (session_id, 2, "如何减少幻觉？", "基于证据和校验。", "Prompt 反馈", "Prompt 工程"),
        ],
    )
    conn.execute(
        """INSERT INTO questions
           (source_session_id, topic, question, reference_answer, difficulty, mastery)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (session_id, "Agent 架构", "如何设计 Agent？", "参考答案框架", "hard", "learning"),
    )
    conn.commit()
    conn.close()
    return session_id


def test_build_chunks_from_session(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge_service.db")
    _create_business_tables(db_path)
    session_id = _insert_session_fixture(db_path)

    chunks = build_chunks_from_session(db_path, session_id)

    assert len(chunks) == 4
    assert all(chunk.content for chunk in chunks)
    assert [chunk.source_type for chunk in chunks].count(SOURCE_SESSION_SUMMARY) == 1
    assert [chunk.source_type for chunk in chunks].count(SOURCE_TURN_FEEDBACK) == 2
    assert [chunk.source_type for chunk in chunks].count(SOURCE_QUESTION_BANK) == 1
    assert all(chunk.session_id == session_id for chunk in chunks)

    turn_chunks = [chunk for chunk in chunks if chunk.source_type == SOURCE_TURN_FEEDBACK]
    assert all({"question", "answer", "turn_index"}.issubset(chunk.metadata.keys()) for chunk in turn_chunks)

    question_chunk = next(chunk for chunk in chunks if chunk.source_type == SOURCE_QUESTION_BANK)
    assert question_chunk.metadata["difficulty"] == "hard"
    assert question_chunk.metadata["mastery"] == "learning"


def test_build_chunks_from_missing_session_returns_empty(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge_service.db")
    _create_business_tables(db_path)

    assert build_chunks_from_session(db_path, 9999) == []


def test_index_interview_session_end_to_end(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge_service.db")
    _create_business_tables(db_path)
    session_id = _insert_session_fixture(db_path)

    first = index_interview_session(db_path, session_id)
    second = index_interview_session(db_path, session_id)
    rows = list_knowledge_chunks(db_path, session_id=session_id)

    assert first.created == 4
    assert first.skipped == 0
    assert first.total == 4
    assert second.created == 0
    assert second.skipped == 4
    assert second.total == 4
    assert len(rows) == 4
