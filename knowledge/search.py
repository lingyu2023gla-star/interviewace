"""Keyword search over knowledge_chunks with FTS5 and LIKE fallback."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from knowledge.repository import init_knowledge_tables
from knowledge.schemas import KnowledgeSearchResult


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


def init_fts_table(db_path: str) -> bool:
    """Create the FTS5 table for knowledge_chunks if SQLite supports FTS5."""
    init_knowledge_tables(db_path)
    try:
        with _connect(db_path) as conn:
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunks_fts
                USING fts5(
                    title,
                    content,
                    topic,
                    job_direction,
                    dimension_key,
                    source_type,
                    tokenize='unicode61'
                )
                """
            )
    except sqlite3.OperationalError:
        return False
    return True


def rebuild_fts_index(db_path: str) -> bool:
    """Rebuild the FTS5 index from knowledge_chunks."""
    if not init_fts_table(db_path):
        return False

    with _connect(db_path) as conn:
        conn.execute("DELETE FROM knowledge_chunks_fts")
        rows = conn.execute(
            """SELECT id, title, content, topic, job_direction, dimension_key, source_type
               FROM knowledge_chunks
               ORDER BY id ASC"""
        ).fetchall()
        conn.executemany(
            """INSERT INTO knowledge_chunks_fts
               (rowid, title, content, topic, job_direction, dimension_key, source_type)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    row["id"],
                    row["title"],
                    row["content"],
                    row["topic"],
                    row["job_direction"],
                    row["dimension_key"],
                    row["source_type"],
                )
                for row in rows
            ],
        )
    return True


def build_snippet(content: str, query: str, max_length: int = 160) -> str:
    """Build a short content snippet around the query when possible."""
    if not content:
        return ""

    clean_query = query.strip()
    content_lower = content.lower()
    query_lower = clean_query.lower()
    index = content_lower.find(query_lower) if query_lower else -1

    if index < 0:
        snippet = content[:max_length]
        return f"{snippet}..." if len(content) > max_length else snippet

    half_window = max(0, (max_length - len(clean_query)) // 2)
    start = max(0, index - half_window)
    end = min(len(content), start + max_length)
    if end - start < max_length:
        start = max(0, end - max_length)

    snippet = content[start:end]
    if start > 0:
        snippet = f"...{snippet}"
    if end < len(content):
        snippet = f"{snippet}..."
    return snippet


def parse_json_field(value: str | None, default):
    """Parse a JSON DB field and return default on invalid values."""
    if value is None:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _fts_query(query: str) -> str:
    """Convert free text into a conservative FTS5 MATCH expression."""
    tokens = re.findall(r"[\w]+", query, flags=re.UNICODE)
    return " OR ".join(tokens)


def _optional_filters(
    session_id: int | None,
    source_type: str | None,
    topic: str | None,
    dimension_key: str | None,
    table_alias: str = "kc",
) -> tuple[str, list[object]]:
    """Build SQL for optional knowledge chunk filters."""
    clauses = []
    params: list[object] = []
    if session_id is not None:
        clauses.append(f"{table_alias}.session_id = ?")
        params.append(session_id)
    if source_type is not None:
        clauses.append(f"{table_alias}.source_type = ?")
        params.append(source_type)
    if topic is not None:
        clauses.append(f"{table_alias}.topic = ?")
        params.append(topic)
    if dimension_key is not None:
        clauses.append(f"{table_alias}.dimension_key = ?")
        params.append(dimension_key)

    if not clauses:
        return "", params
    return " AND " + " AND ".join(clauses), params


def _row_to_result(row: sqlite3.Row, query: str, score: float | None) -> KnowledgeSearchResult:
    """Convert a knowledge_chunks row to a search result dataclass."""
    tags = parse_json_field(row["tags"], [])
    metadata = parse_json_field(row["metadata_json"], {})
    if not isinstance(tags, list):
        tags = []
    if not isinstance(metadata, dict):
        metadata = {}

    return KnowledgeSearchResult(
        chunk_id=row["id"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        content=row["content"],
        title=row["title"],
        snippet=build_snippet(row["content"], query),
        session_id=row["session_id"],
        turn_id=row["turn_id"],
        question_id=row["question_id"],
        job_direction=row["job_direction"],
        topic=row["topic"],
        dimension_key=row["dimension_key"],
        tags=tags,
        metadata=metadata,
        score=score,
    )


def _search_with_fts(
    db_path: str,
    query: str,
    session_id: int | None,
    source_type: str | None,
    topic: str | None,
    dimension_key: str | None,
    top_k: int,
) -> list[KnowledgeSearchResult]:
    """Search using SQLite FTS5."""
    match_query = _fts_query(query)
    if not match_query:
        return []

    filter_sql, filter_params = _optional_filters(
        session_id=session_id,
        source_type=source_type,
        topic=topic,
        dimension_key=dimension_key,
    )
    with _connect(db_path) as conn:
        rows = conn.execute(
            f"""SELECT
                    kc.*,
                    bm25(knowledge_chunks_fts) AS rank
                FROM knowledge_chunks_fts
                JOIN knowledge_chunks kc ON kc.id = knowledge_chunks_fts.rowid
                WHERE knowledge_chunks_fts MATCH ?
                {filter_sql}
                ORDER BY rank ASC
                LIMIT ?""",
            [match_query, *filter_params, top_k],
        ).fetchall()

    return [
        _row_to_result(row, query, score=1.0 / (1.0 + abs(float(row["rank"] or 0.0))))
        for row in rows
    ]


def _like_score(row: sqlite3.Row, query: str) -> float:
    """Compute a simple deterministic LIKE fallback score."""
    query_lower = query.lower()
    title = (row["title"] or "").lower()
    topic = (row["topic"] or "").lower()
    content = (row["content"] or "").lower()
    score = 0.0
    if query_lower in title:
        score += 3.0
    if query_lower in topic:
        score += 2.0
    if query_lower in content:
        score += 1.0
        score += content.count(query_lower) * 0.1
    return score


def _search_with_like(
    db_path: str,
    query: str,
    session_id: int | None,
    source_type: str | None,
    topic: str | None,
    dimension_key: str | None,
    top_k: int,
) -> list[KnowledgeSearchResult]:
    """Search using LIKE and deterministic Python-side scoring."""
    filter_sql, filter_params = _optional_filters(
        session_id=session_id,
        source_type=source_type,
        topic=topic,
        dimension_key=dimension_key,
    )
    like_query = f"%{query}%"
    like_params = [like_query] * 6

    with _connect(db_path) as conn:
        rows = conn.execute(
            f"""SELECT *
                FROM knowledge_chunks kc
                WHERE (
                    kc.title LIKE ?
                    OR kc.content LIKE ?
                    OR kc.topic LIKE ?
                    OR kc.job_direction LIKE ?
                    OR kc.dimension_key LIKE ?
                    OR kc.source_type LIKE ?
                )
                {filter_sql}
                ORDER BY kc.id DESC""",
            [*like_params, *filter_params],
        ).fetchall()

    scored_rows = sorted(
        ((row, _like_score(row, query)) for row in rows),
        key=lambda item: (item[1], item[0]["id"]),
        reverse=True,
    )
    return [_row_to_result(row, query, score=score) for row, score in scored_rows[:top_k]]


def search_knowledge_chunks(
    db_path: str,
    query: str,
    session_id: int | None = None,
    source_type: str | None = None,
    topic: str | None = None,
    dimension_key: str | None = None,
    top_k: int = 5,
) -> list[KnowledgeSearchResult]:
    """Search knowledge chunks by keyword with FTS5 and LIKE fallback."""
    clean_query = query.strip()
    if not clean_query or top_k <= 0:
        return []

    init_knowledge_tables(db_path)
    try:
        if rebuild_fts_index(db_path):
            results = _search_with_fts(
                db_path=db_path,
                query=clean_query,
                session_id=session_id,
                source_type=source_type,
                topic=topic,
                dimension_key=dimension_key,
                top_k=top_k,
            )
            if results:
                return results
    except sqlite3.OperationalError:
        pass

    return _search_with_like(
        db_path=db_path,
        query=clean_query,
        session_id=session_id,
        source_type=source_type,
        topic=topic,
        dimension_key=dimension_key,
        top_k=top_k,
    )
