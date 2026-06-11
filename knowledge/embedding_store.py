"""SQLite repository for chunk embedding records."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Generator


@dataclass(frozen=True)
class EmbeddingRecord:
    """A stored embedding for one knowledge chunk."""

    chunk_id: int
    embedding: list[float]
    embedding_model: str
    embedding_dimension: int
    content_hash: str | None
    created_at: str
    updated_at: str


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
    """Return a UTC ISO timestamp string."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def _normalize_embedding(embedding: list[float]) -> list[float]:
    """Validate and normalize an embedding vector."""
    if not embedding:
        raise ValueError("embedding must not be empty")

    normalized: list[float] = []
    for value in embedding:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("embedding values must be numeric")
        normalized.append(float(value))
    return normalized


def _validate_chunk_id(chunk_id: int) -> None:
    """Validate that chunk_id is a positive integer."""
    if isinstance(chunk_id, bool) or not isinstance(chunk_id, int) or chunk_id <= 0:
        raise ValueError("chunk_id must be a positive integer")


def _validate_embedding_model(embedding_model: str) -> None:
    """Validate that embedding_model is not empty."""
    if not embedding_model or not embedding_model.strip():
        raise ValueError("embedding_model must not be empty")


def _row_to_record(row: sqlite3.Row) -> EmbeddingRecord:
    """Convert a chunk_embeddings row to an EmbeddingRecord."""
    try:
        embedding = json.loads(row["embedding_json"])
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid embedding_json for chunk_id={row['chunk_id']}") from exc

    if not isinstance(embedding, list):
        raise ValueError(f"embedding_json must be a list for chunk_id={row['chunk_id']}")

    normalized = _normalize_embedding(embedding)
    dimension = int(row["embedding_dimension"])
    if dimension != len(normalized):
        raise ValueError(
            f"embedding_dimension mismatch for chunk_id={row['chunk_id']}: "
            f"stored={dimension}, actual={len(normalized)}"
        )

    return EmbeddingRecord(
        chunk_id=row["chunk_id"],
        embedding=normalized,
        embedding_model=row["embedding_model"],
        embedding_dimension=dimension,
        content_hash=row["content_hash"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def init_chunk_embeddings_table(db_path: str) -> None:
    """Create the chunk_embeddings table if it does not exist."""
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunk_embeddings (
                chunk_id INTEGER PRIMARY KEY,
                embedding_json TEXT NOT NULL,
                embedding_model TEXT NOT NULL,
                embedding_dimension INTEGER NOT NULL,
                content_hash TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def upsert_chunk_embedding(
    db_path: str,
    chunk_id: int,
    embedding: list[float],
    embedding_model: str,
    content_hash: str | None = None,
) -> EmbeddingRecord:
    """Insert or update the active embedding for a knowledge chunk."""
    _validate_chunk_id(chunk_id)
    _validate_embedding_model(embedding_model)
    normalized = _normalize_embedding(embedding)

    init_chunk_embeddings_table(db_path)
    now = _now_text()
    embedding_json = json.dumps(normalized, ensure_ascii=False)
    dimension = len(normalized)

    with _connect(db_path) as conn:
        existing = conn.execute(
            "SELECT chunk_id FROM chunk_embeddings WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()
        if existing is None:
            conn.execute(
                """INSERT INTO chunk_embeddings
                   (chunk_id, embedding_json, embedding_model, embedding_dimension,
                    content_hash, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    chunk_id,
                    embedding_json,
                    embedding_model,
                    dimension,
                    content_hash,
                    now,
                    now,
                ),
            )
        else:
            conn.execute(
                """UPDATE chunk_embeddings
                   SET embedding_json = ?,
                       embedding_model = ?,
                       embedding_dimension = ?,
                       content_hash = ?,
                       updated_at = ?
                   WHERE chunk_id = ?""",
                (
                    embedding_json,
                    embedding_model,
                    dimension,
                    content_hash,
                    now,
                    chunk_id,
                ),
            )

    record = get_chunk_embedding(db_path, chunk_id)
    if record is None:
        raise RuntimeError(f"failed to upsert embedding for chunk_id={chunk_id}")
    return record


def get_chunk_embedding(db_path: str, chunk_id: int) -> EmbeddingRecord | None:
    """Return the embedding record for a chunk, or None when missing."""
    _validate_chunk_id(chunk_id)
    init_chunk_embeddings_table(db_path)
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM chunk_embeddings WHERE chunk_id = ?",
            (chunk_id,),
        ).fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def list_chunk_embeddings(
    db_path: str,
    limit: int | None = None,
    embedding_model: str | None = None,
) -> list[EmbeddingRecord]:
    """List embedding records ordered by chunk_id ascending."""
    init_chunk_embeddings_table(db_path)
    clauses = []
    params: list[object] = []
    if embedding_model is not None:
        clauses.append("embedding_model = ?")
        params.append(embedding_model)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit_sql = ""
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be a positive integer")
        limit_sql = "LIMIT ?"
        params.append(limit)

    with _connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM chunk_embeddings {where_sql} ORDER BY chunk_id ASC {limit_sql}",
            params,
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def delete_chunk_embedding(db_path: str, chunk_id: int) -> bool:
    """Delete one chunk embedding and return whether a row was removed."""
    _validate_chunk_id(chunk_id)
    init_chunk_embeddings_table(db_path)
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM chunk_embeddings WHERE chunk_id = ?",
            (chunk_id,),
        )
    return cursor.rowcount > 0


def is_chunk_embedding_stale(
    db_path: str,
    chunk_id: int,
    content_hash: str | None,
    embedding_model: str | None = None,
) -> bool:
    """Return True when a chunk embedding is missing or no longer current."""
    _validate_chunk_id(chunk_id)
    record = get_chunk_embedding(db_path, chunk_id)
    if record is None:
        return True
    if embedding_model is not None and record.embedding_model != embedding_model:
        return True
    if content_hash is not None and record.content_hash != content_hash:
        return True
    return False
