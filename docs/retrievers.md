# Retriever Abstraction

V9.1 added a small retriever abstraction layer for knowledge retrieval. V9.5 adds opt-in retriever selection for preparation plan generation while keeping the default behavior as keyword / FTS retrieval.

## 1. Purpose

The default preparation retrieval path is still keyword / SQLite FTS search. The retriever layer gives callers a shared interface so they can opt into embedding or hybrid retrieval without changing the existing keyword SQL path.

## 2. Files

```text
knowledge/retrievers/
├── __init__.py
├── base.py
├── embedding.py
├── factory.py
├── hybrid.py
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
- `embedding`
- `hybrid`

Unknown retriever types raise `ValueError`.

## 6. Preparation Opt-in

Preparation plan generation accepts an optional `retriever_type`:

- `keyword` default
- `fts` alias of keyword
- `embedding`
- `hybrid`

This is supported by:

- Markdown preparation service
- structured preparation service
- synchronous FastAPI preparation endpoints
- asynchronous Celery preparation task payloads

If callers omit `retriever_type`, behavior remains keyword / FTS. `embedding` and `hybrid` depend on existing rows in SQLite `chunk_embeddings`; the system does not automatically call a real embedding model.

## 7. Current Scope

The retriever layer still does not implement:

- real embedding API calls
- vector database integration
- rerank / `Reranker`
- default preparation flow switch to hybrid

## 8. Tests

```bash
.venv/bin/python -m pytest tests/test_retrievers.py -v
```

The tests monkeypatch `search_knowledge_chunks` to verify that `KeywordRetriever` passes parameters through correctly. Embedding and hybrid retriever tests use local fake providers or fake child retrievers; they do not require network, Redis, Docker, Celery worker, real LLM calls, or a real embedding API.
