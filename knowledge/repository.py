"""SQLite repository for knowledge_chunks."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

from knowledge.schemas import IndexResult, KnowledgeChunk


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


def _now_text() -> str:
    """Return a timestamp string matching SQLite CURRENT_TIMESTAMP style."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_knowledge_tables(db_path: str) -> None:
    """Create the knowledge_chunks table and indexes if missing."""
    with _connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,

                session_id INTEGER,
                turn_id INTEGER,
                question_id INTEGER,

                title TEXT,
                content TEXT NOT NULL,

                job_direction TEXT,
                topic TEXT,
                dimension_key TEXT,

                tags TEXT,
                metadata_json TEXT,

                content_hash TEXT NOT NULL UNIQUE,

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_session_id
            ON knowledge_chunks(session_id);

            CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_source
            ON knowledge_chunks(source_type, source_id);

            CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_topic
            ON knowledge_chunks(topic);

            CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_dimension
            ON knowledge_chunks(dimension_key);

            CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_job_direction
            ON knowledge_chunks(job_direction);
            """
        )


def compute_content_hash(
    source_type: str,
    source_id: str,
    content: str,
) -> str:
    """Compute a stable hash for a knowledge chunk identity and content."""
    raw = "\x1f".join([source_type, source_id, content])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _result_session_id(chunks: list[KnowledgeChunk]) -> int:
    """Return the first non-empty session id in a chunk list."""
    for chunk in chunks:
        if chunk.session_id is not None:
            return chunk.session_id
    return 0


def upsert_knowledge_chunks(
    db_path: str,
    chunks: list[KnowledgeChunk],
) -> IndexResult:
    """Insert new knowledge chunks and skip existing chunks by content_hash."""
    if not chunks:
        return IndexResult(session_id=0, created=0, skipped=0, total=0)

    init_knowledge_tables(db_path)
    created = 0
    skipped = 0
    now = _now_text()

    with _connect(db_path) as conn:
        for chunk in chunks:
            content_hash = compute_content_hash(
                source_type=chunk.source_type,
                source_id=chunk.source_id,
                content=chunk.content,
            )
            exists = conn.execute(
                "SELECT 1 FROM knowledge_chunks WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()
            if exists is not None:
                skipped += 1
                continue

            conn.execute(
                """INSERT INTO knowledge_chunks
                   (source_type, source_id, session_id, turn_id, question_id,
                    title, content, job_direction, topic, dimension_key,
                    tags, metadata_json, content_hash, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    chunk.source_type,
                    chunk.source_id,
                    chunk.session_id,
                    chunk.turn_id,
                    chunk.question_id,
                    chunk.title,
                    chunk.content,
                    chunk.job_direction,
                    chunk.topic,
                    chunk.dimension_key,
                    json.dumps(chunk.tags, ensure_ascii=False),
                    json.dumps(chunk.metadata, ensure_ascii=False),
                    content_hash,
                    now,
                    now,
                ),
            )
            created += 1

    return IndexResult(
        session_id=_result_session_id(chunks),
        created=created,
        skipped=skipped,
        total=len(chunks),
    )


def list_knowledge_chunks(
    db_path: str,
    session_id: int | None = None,
    source_type: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """List knowledge chunks ordered by newest first."""
    init_knowledge_tables(db_path)
    clauses = []
    params: list[object] = []
    if session_id is not None:
        clauses.append("session_id = ?")
        params.append(session_id)
    if source_type is not None:
        clauses.append("source_type = ?")
        params.append(source_type)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    with _connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM knowledge_chunks {where_sql} ORDER BY id DESC LIMIT ?",
            params,
        ).fetchall()
    return [dict(row) for row in rows]
