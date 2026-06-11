# Hybrid Retriever

V9.4 adds `HybridRetriever`, which combines keyword / FTS retrieval and embedding retrieval with Reciprocal Rank Fusion (RRF).

## 1. Purpose

The goal is to support an opt-in hybrid retrieval path without changing the default preparation plan flow.

```text
query
  -> KeywordRetriever
  -> EmbeddingRetriever
  -> Reciprocal Rank Fusion
  -> KnowledgeSearchResult[]
```

## 2. Location

```text
knowledge/retrievers/hybrid.py
```

`get_retriever("hybrid")` returns `HybridRetriever`.

## 3. Why RRF

Keyword retrieval and embedding retrieval produce scores on different scales:

- keyword / FTS may use bm25-derived scores or LIKE fallback scores;
- embedding retrieval uses cosine similarity.

Directly adding these raw scores is unstable because a score of `0.8` does not mean the same thing across retrievers.

RRF uses rank positions instead:

```text
score += 1 / (k + rank)
```

This makes the first hybrid implementation simple, deterministic, and less sensitive to score calibration.

## 4. Retrieval Flow

`HybridRetriever`:

1. calls `KeywordRetriever.retrieve(...)`;
2. calls `EmbeddingRetriever.retrieve(...)`;
3. passes the same filters to both retrievers:
   - `db_path`
   - `query`
   - `session_id`
   - `source_type`
   - `topic`
   - `dimension_key`
   - `top_k`
4. extracts `chunk_id`;
5. computes RRF scores;
6. merges duplicated chunks by `chunk_id`;
7. keeps the first result object as the base result;
8. replaces `score` with the hybrid RRF score;
9. returns top results by hybrid score descending.

## 5. Current Scope

V9.4 intentionally does not implement:

- real embedding API integration;
- OpenAI / DeepSeek / BGE embedding providers;
- rerank or `Reranker`;
- vector database integration;
- preparation service integration.

The default preparation services still use keyword / FTS search directly.

## 6. Relationship To Earlier V9 Work

- V9.1 introduced `BaseRetriever`, `KeywordRetriever`, and retriever factory.
- V9.2 introduced SQLite `chunk_embeddings`.
- V9.3 introduced `EmbeddingRetriever`.
- V9.4 introduces `HybridRetriever` as an opt-in retriever.

## 7. Testing

```bash
.venv/bin/python -m pytest tests/test_hybrid_retriever.py -v
```

The tests use fake child retrievers and do not require network, Redis, Docker, Celery worker, real LLM calls, or a real embedding API.

## 8. Next Step

Later versions can add:

- opt-in preparation service configuration for retriever selection;
- real embedding providers;
- score diagnostics for hybrid retrieval;
- optional reranker after candidate retrieval.
