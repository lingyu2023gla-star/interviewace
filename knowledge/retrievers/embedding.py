"""Embedding retriever backed by chunk_embeddings."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from knowledge.embedding_store import init_chunk_embeddings_table
from knowledge.embeddings.providers import BaseEmbeddingProvider, FakeEmbeddingProvider
from knowledge.embeddings.similarity import cosine_similarity
from knowledge.repository import init_knowledge_tables
from knowledge.retrievers.base import BaseRetriever
from knowledge.schemas import KnowledgeSearchResult
from knowledge.search import build_snippet, parse_json_field


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


class EmbeddingRetriever(BaseRetriever):
    """Retrieve knowledge chunks by cosine similarity over stored embeddings."""

    def __init__(self, embedding_provider: BaseEmbeddingProvider | None = None) -> None:
        """Create an embedding retriever with a local provider."""
        self.embedding_provider = embedding_provider or FakeEmbeddingProvider()

    def retrieve(
        self,
        db_path: str,
        query: str,
        session_id: int | None = None,
        source_type: str | None = None,
        topic: str | None = None,
        dimension_key: str | None = None,
        top_k: int = 5,
    ) -> list[KnowledgeSearchResult]:
        """Retrieve chunks by comparing query embedding with stored vectors."""
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")

        init_knowledge_tables(db_path)
        init_chunk_embeddings_table(db_path)
        query_embedding = self.embedding_provider.embed_text(query)
        rows = self._load_candidate_rows(
            db_path=db_path,
            session_id=session_id,
            source_type=source_type,
            topic=topic,
            dimension_key=dimension_key,
        )
        scored_results: list[KnowledgeSearchResult] = []
        for row in rows:
            chunk_embedding = self._parse_embedding(row)
            score = cosine_similarity(query_embedding, chunk_embedding)
            scored_results.append(self._row_to_result(row, query, score))

        scored_results.sort(key=lambda result: (result.score or 0.0, result.chunk_id), reverse=True)
        return scored_results[:top_k]

    def _load_candidate_rows(
        self,
        db_path: str,
        session_id: int | None,
        source_type: str | None,
        topic: str | None,
        dimension_key: str | None,
    ) -> list[sqlite3.Row]:
        """Load chunk rows with stored embeddings for the provider model."""
        clauses = ["ce.embedding_model = ?"]
        params: list[object] = [self.embedding_provider.model_name]
        if session_id is not None:
            clauses.append("kc.session_id = ?")
            params.append(session_id)
        if source_type is not None:
            clauses.append("kc.source_type = ?")
            params.append(source_type)
        if topic is not None:
            clauses.append("kc.topic = ?")
            params.append(topic)
        if dimension_key is not None:
            clauses.append("kc.dimension_key = ?")
            params.append(dimension_key)

        where_sql = " AND ".join(clauses)
        with _connect(db_path) as conn:
            return conn.execute(
                f"""SELECT
                        kc.*,
                        ce.embedding_json,
                        ce.embedding_model,
                        ce.embedding_dimension
                    FROM chunk_embeddings ce
                    JOIN knowledge_chunks kc ON kc.id = ce.chunk_id
                    WHERE {where_sql}
                    ORDER BY kc.id ASC""",
                params,
            ).fetchall()

    @staticmethod
    def _parse_embedding(row: sqlite3.Row) -> list[float]:
        """Parse a row embedding and validate its dimension."""
        try:
            embedding = json.loads(row["embedding_json"])
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid embedding_json for chunk_id={row['id']}") from exc
        if not isinstance(embedding, list):
            raise ValueError(f"embedding_json must be a list for chunk_id={row['id']}")
        dimension = int(row["embedding_dimension"])
        if dimension != len(embedding):
            raise ValueError(
                f"embedding_dimension mismatch for chunk_id={row['id']}: "
                f"stored={dimension}, actual={len(embedding)}"
            )
        return embedding

    @staticmethod
    def _row_to_result(row: sqlite3.Row, query: str, score: float) -> KnowledgeSearchResult:
        """Convert a joined row to KnowledgeSearchResult."""
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
