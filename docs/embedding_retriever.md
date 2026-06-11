# Embedding Retriever

V9.3 adds a local, testable `EmbeddingRetriever` on top of the V9.1 retriever abstraction and the V9.2 SQLite `chunk_embeddings` store.

## 1. Purpose

The goal is to prove the embedding retrieval flow without adding external infrastructure:

```text
query
  -> FakeEmbeddingProvider.embed_text(query)
  -> load chunk_embeddings from SQLite
  -> JOIN knowledge_chunks
  -> cosine similarity
  -> KnowledgeSearchResult[]
```

This step prepares the codebase for a future real embedding provider while keeping default tests deterministic and offline.

## 2. Location

```text
knowledge/embeddings/
├── __init__.py
├── providers.py
└── similarity.py

knowledge/retrievers/
└── embedding.py
```

`get_retriever("embedding")` returns `EmbeddingRetriever`.

## 3. FakeEmbeddingProvider

`FakeEmbeddingProvider` is a deterministic local provider:

- no network calls;
- no real embedding API;
- stable output for the same input;
- configurable dimension;
- model name defaults to `fake-embedding-v1`.

It uses `hashlib.sha256` over text tokens and normalizes the resulting vector.

## 4. Cosine Similarity

`cosine_similarity(a, b)` is implemented without NumPy.

It validates:

- vectors are non-empty;
- vectors have the same length;
- values are numeric;
- `bool` is not accepted as a numeric value.

If either vector has zero norm, the function returns `0.0`.

## 5. How EmbeddingRetriever Uses chunk_embeddings

`EmbeddingRetriever`:

1. embeds the query with its provider;
2. reads rows from `chunk_embeddings`;
3. filters embeddings by `embedding_model = provider.model_name`;
4. joins `knowledge_chunks` by `knowledge_chunks.id = chunk_embeddings.chunk_id`;
5. applies optional filters on `knowledge_chunks`:
   - `session_id`
   - `source_type`
   - `topic`
   - `dimension_key`
6. scores candidates with cosine similarity;
7. returns `KnowledgeSearchResult` objects ordered by score descending.

It ignores orphan embeddings that do not have a matching `knowledge_chunks` row.

## 6. Current Scope

V9.3 intentionally does not implement:

- OpenAI / DeepSeek / BGE embedding provider;
- network embedding calls;
- `HybridRetriever`;
- rerank;
- vector database integration;
- preparation service integration.

The existing preparation services still use the default keyword / FTS retrieval path.

## 7. Relationship To V9.1 And V9.2

- V9.1 introduced `BaseRetriever`, `KeywordRetriever`, and `get_retriever(...)`.
- V9.2 introduced SQLite `chunk_embeddings`.
- V9.3 adds `EmbeddingRetriever` and a local fake provider for deterministic tests.

## 8. Testing

```bash
.venv/bin/python -m pytest tests/test_embedding_provider.py tests/test_embedding_retriever.py -v
```

Default tests do not require network, Redis, Docker, Celery worker, real LLM calls, or a real embedding API.

## 9. Next Step

V9.4 can add `HybridRetriever`, combining keyword / FTS scores and embedding similarity while keeping the current preparation flow opt-in until explicitly switched.
