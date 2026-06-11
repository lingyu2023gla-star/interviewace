# Retriever Abstraction

V9.1 adds a small retriever abstraction layer for knowledge retrieval. It is a preparation step for future `EmbeddingRetriever` and `HybridRetriever` work.

## 1. Purpose

The current production retrieval path is still keyword / SQLite FTS search. V9.1 only adds an interface around that behavior so future retrievers can share the same call shape.

## 2. Files

```text
knowledge/retrievers/
├── __init__.py
├── base.py
├── factory.py
└── keyword.py
```

## 3. BaseRetriever

`BaseRetriever` defines one method:

```python
retrieve(
    db_path: str,
    query: str,
    session_id: int | None = None,
    source_type: str | None = None,
    topic: str | None = None,
    dimension_key: str | None = None,
    top_k: int = 5,
)
```

The return value is `list[KnowledgeSearchResult]`.

## 4. KeywordRetriever

`KeywordRetriever` delegates directly to the existing `search_knowledge_chunks(...)` function.

It does not copy SQL and does not change the current FTS / LIKE fallback implementation in `knowledge/search.py`.

## 5. Factory

`get_retriever(...)` currently supports:

- `keyword`
- `fts` as an alias for `keyword`

Unknown retriever types raise `ValueError`.

## 6. Current Scope

V9.1 does not implement:

- `EmbeddingRetriever`
- `HybridRetriever`
- embedding API calls
- vector search
- changes to preparation service

The preparation plan services still use the existing keyword retrieval behavior.

## 7. Tests

```bash
.venv/bin/python -m pytest tests/test_retrievers.py -v
```

The tests monkeypatch `search_knowledge_chunks` to verify that `KeywordRetriever` passes parameters through correctly.
