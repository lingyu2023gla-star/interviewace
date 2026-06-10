"""Service layer for building knowledge chunks from interview data."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from knowledge.repository import init_knowledge_tables, upsert_knowledge_chunks
from knowledge.schemas import IndexResult, KnowledgeChunk


SOURCE_SESSION_SUMMARY = "session_summary"
SOURCE_TURN_FEEDBACK = "turn_feedback"
SOURCE_QUESTION_BANK = "question_bank"
SOURCE_FULL_ANALYSIS = "full_analysis"
SOURCE_EVAL_CASE = "eval_case"


@contextmanager
def _connect(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """Open a SQLite connection with row dict support."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _has_text(value: object) -> bool:
    """Return True when a DB value contains non-empty text."""
    return isinstance(value, str) and bool(value.strip())


def build_chunks_from_session(
    db_path: str,
    session_id: int,
) -> list[KnowledgeChunk]:
    """Build knowledge chunks from one saved interview session."""
    with _connect(db_path) as conn:
        session_row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if session_row is None:
            return []

        session = dict(session_row)
        turn_rows = conn.execute(
            "SELECT * FROM turns WHERE session_id = ? ORDER BY turn_index ASC, id ASC",
            (session_id,),
        ).fetchall()
        question_rows = conn.execute(
            "SELECT * FROM questions WHERE source_session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()

    chunks: list[KnowledgeChunk] = []
    if _has_text(session.get("summary")):
        chunks.append(
            KnowledgeChunk(
                source_type=SOURCE_SESSION_SUMMARY,
                source_id=f"session:{session_id}:summary",
                session_id=session_id,
                title="面试整体复盘总结",
                content=session["summary"],
                job_direction=session.get("job_direction"),
                metadata={
                    "session_title": session.get("title"),
                    "created_at": session.get("created_at"),
                },
            )
        )

    for row in turn_rows:
        turn = dict(row)
        if not _has_text(turn.get("feedback")):
            continue
        chunks.append(
            KnowledgeChunk(
                source_type=SOURCE_TURN_FEEDBACK,
                source_id=f"turn:{turn['id']}:feedback",
                session_id=session_id,
                turn_id=turn["id"],
                title=turn.get("topic"),
                content=turn["feedback"],
                topic=turn.get("topic"),
                job_direction=session.get("job_direction"),
                metadata={
                    "question": turn.get("question"),
                    "answer": turn.get("answer"),
                    "turn_index": turn.get("turn_index"),
                },
            )
        )

    for row in question_rows:
        question = dict(row)
        if not _has_text(question.get("reference_answer")):
            continue
        chunks.append(
            KnowledgeChunk(
                source_type=SOURCE_QUESTION_BANK,
                source_id=f"question:{question['id']}:reference_answer",
                session_id=question.get("source_session_id"),
                question_id=question["id"],
                title=question.get("question"),
                content=question["reference_answer"],
                topic=question.get("topic"),
                metadata={
                    "difficulty": question.get("difficulty"),
                    "mastery": question.get("mastery"),
                },
            )
        )

    return chunks


def index_interview_session(
    db_path: str,
    session_id: int,
) -> IndexResult:
    """Build and idempotently persist knowledge chunks for one session."""
    init_knowledge_tables(db_path)
    chunks = build_chunks_from_session(db_path, session_id)
    return upsert_knowledge_chunks(db_path, chunks)
