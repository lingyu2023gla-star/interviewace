# Embedding Store

V9.2 adds a small SQLite embedding store for `knowledge_chunks`. It prepares the data layer for a future `EmbeddingRetriever`, but it does not call any real embedding API and does not change the current keyword / FTS retrieval path.

## 1. Purpose

The embedding store saves one active vector representation for each knowledge chunk:

- Keep embeddings traceable to `knowledge_chunks.id`.
- Track which embedding model produced the vector.
- Track vector dimension for later validation.
- Track `content_hash` so stale embeddings can be detected when chunk content changes.

This is data structure work only. Vector search is planned for V9.3.

## 2. Table Schema

```sql
CREATE TABLE IF NOT EXISTS chunk_embeddings (
    chunk_id INTEGER PRIMARY KEY,
    embedding_json TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_dimension INTEGER NOT NULL,
    content_hash TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## 3. Relationship To knowledge_chunks

`chunk_id` corresponds to `knowledge_chunks.id`.

The table currently keeps one active embedding per chunk. It does not enforce a foreign key so existing SQLite tests and local MVP databases remain simple and backward-compatible.

## 4. Field Notes

- `embedding_json`: JSON-encoded `list[float]`.
- `embedding_model`: model name, for example `fake-embedding-v1` or `text-embedding-3-small`.
- `embedding_dimension`: `len(embedding)`, stored for later consistency checks.
- `content_hash`: copied from `knowledge_chunks.content_hash` so the system can detect whether a chunk needs to be re-embedded.
- `created_at` / `updated_at`: UTC ISO timestamp strings.

## 5. Staleness Check

`is_chunk_embedding_stale(...)` returns `True` when:

- no embedding exists for the chunk;
- the requested embedding model differs from the stored model;
- the supplied `content_hash` differs from the stored `content_hash`.

If `content_hash` is `None`, the check only verifies existence and optional model match.

## 6. Current Limits

- No real embedding provider is implemented.
- No OpenAI / DeepSeek / local embedding model is called.
- No `EmbeddingRetriever` or `HybridRetriever` is implemented in this step.
- No vector database is introduced.
- No NumPy dependency is required.
- The existing `search_knowledge_chunks` keyword / FTS path is unchanged.

## 7. Testing

Default tests use temporary SQLite databases only:

```bash
.venv/bin/python -m pytest tests/test_embedding_store.py -v
```

The tests do not require network, Redis, Docker, Celery worker, real LLM calls, or a real embedding API.

## 8. Next Step

V9.3 can build `EmbeddingRetriever` on top of this table:

1. generate embeddings for stale chunks;
2. load vectors from `chunk_embeddings`;
3. compute similarity in Python or via a future vector backend;
4. optionally combine keyword and embedding scores in a `HybridRetriever`.
