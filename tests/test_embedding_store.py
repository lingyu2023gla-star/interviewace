"""knowledge.embedding_store tests."""

from __future__ import annotations

import sqlite3

import pytest

from knowledge.embedding_store import (
    get_chunk_embedding,
    init_chunk_embeddings_table,
    is_chunk_embedding_stale,
    delete_chunk_embedding,
    list_chunk_embeddings,
    upsert_chunk_embedding,
)


def test_init_chunk_embeddings_table_creates_table(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")

    init_chunk_embeddings_table(db_path)

    conn = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    conn.close()
    assert "chunk_embeddings" in tables


def test_upsert_chunk_embedding_inserts_new_record(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")

    record = upsert_chunk_embedding(
        db_path,
        chunk_id=1,
        embedding=[0.1, 0.2, 0.3],
        embedding_model="fake-embedding-v1",
        content_hash="hash-a",
    )

    assert record.chunk_id == 1
    assert record.embedding == [0.1, 0.2, 0.3]
    assert record.embedding_model == "fake-embedding-v1"
    assert record.embedding_dimension == 3
    assert record.content_hash == "hash-a"
    assert record.created_at
    assert record.updated_at


def test_get_chunk_embedding_reads_record(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")
    upsert_chunk_embedding(db_path, 1, [1, 2, 3], "fake-embedding-v1", "hash-a")

    record = get_chunk_embedding(db_path, 1)

    assert record is not None
    assert record.chunk_id == 1
    assert record.embedding == [1.0, 2.0, 3.0]


def test_get_chunk_embedding_missing_record_returns_none(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")

    assert get_chunk_embedding(db_path, 999) is None


def test_upsert_chunk_embedding_updates_existing_record(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")
    first = upsert_chunk_embedding(db_path, 1, [0.1, 0.2], "fake-embedding-v1", "hash-a")
    second = upsert_chunk_embedding(db_path, 1, [0.3, 0.4, 0.5], "fake-embedding-v2", "hash-b")

    rows = list_chunk_embeddings(db_path)

    assert len(rows) == 1
    assert second.chunk_id == first.chunk_id
    assert second.created_at == first.created_at
    assert second.embedding == [0.3, 0.4, 0.5]
    assert second.embedding_model == "fake-embedding-v2"
    assert second.embedding_dimension == 3
    assert second.content_hash == "hash-b"


def test_embedding_dimension_equals_embedding_length(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")

    record = upsert_chunk_embedding(db_path, 1, [0.1, 0.2, 0.3, 0.4], "fake-embedding-v1")

    assert record.embedding_dimension == len(record.embedding)


def test_embedding_values_are_converted_to_float(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")

    record = upsert_chunk_embedding(db_path, 1, [1, 2.5, 3], "fake-embedding-v1")

    assert record.embedding == [1.0, 2.5, 3.0]
    assert all(isinstance(value, float) for value in record.embedding)


def test_upsert_chunk_embedding_empty_embedding_raises(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")

    with pytest.raises(ValueError, match="embedding must not be empty"):
        upsert_chunk_embedding(db_path, 1, [], "fake-embedding-v1")


@pytest.mark.parametrize("embedding", [["bad"], [0.1, None], [True, 0.2]])
def test_upsert_chunk_embedding_non_numeric_embedding_raises(tmp_path, embedding) -> None:
    db_path = str(tmp_path / "embeddings.db")

    with pytest.raises(ValueError, match="embedding values must be numeric"):
        upsert_chunk_embedding(db_path, 1, embedding, "fake-embedding-v1")


@pytest.mark.parametrize("chunk_id", [0, -1, True, "1"])
def test_upsert_chunk_embedding_invalid_chunk_id_raises(tmp_path, chunk_id) -> None:
    db_path = str(tmp_path / "embeddings.db")

    with pytest.raises(ValueError, match="chunk_id must be a positive integer"):
        upsert_chunk_embedding(db_path, chunk_id, [0.1], "fake-embedding-v1")


@pytest.mark.parametrize("embedding_model", ["", "   "])
def test_upsert_chunk_embedding_empty_model_raises(tmp_path, embedding_model) -> None:
    db_path = str(tmp_path / "embeddings.db")

    with pytest.raises(ValueError, match="embedding_model must not be empty"):
        upsert_chunk_embedding(db_path, 1, [0.1], embedding_model)


def test_list_chunk_embeddings_returns_multiple_records(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")
    upsert_chunk_embedding(db_path, 2, [0.2], "fake-embedding-v1")
    upsert_chunk_embedding(db_path, 1, [0.1], "fake-embedding-v1")

    records = list_chunk_embeddings(db_path)

    assert [record.chunk_id for record in records] == [1, 2]


def test_list_chunk_embeddings_filters_by_model(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")
    upsert_chunk_embedding(db_path, 1, [0.1], "fake-embedding-v1")
    upsert_chunk_embedding(db_path, 2, [0.2], "fake-embedding-v2")

    records = list_chunk_embeddings(db_path, embedding_model="fake-embedding-v2")

    assert len(records) == 1
    assert records[0].chunk_id == 2


def test_list_chunk_embeddings_supports_limit(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")
    for chunk_id in range(1, 5):
        upsert_chunk_embedding(db_path, chunk_id, [float(chunk_id)], "fake-embedding-v1")

    records = list_chunk_embeddings(db_path, limit=2)

    assert [record.chunk_id for record in records] == [1, 2]


@pytest.mark.parametrize("limit", [0, -1])
def test_list_chunk_embeddings_invalid_limit_raises(tmp_path, limit) -> None:
    db_path = str(tmp_path / "embeddings.db")

    with pytest.raises(ValueError, match="limit must be a positive integer"):
        list_chunk_embeddings(db_path, limit=limit)


def test_delete_chunk_embedding_existing_record_returns_true(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")
    upsert_chunk_embedding(db_path, 1, [0.1], "fake-embedding-v1")

    assert delete_chunk_embedding(db_path, 1) is True
    assert get_chunk_embedding(db_path, 1) is None


def test_delete_chunk_embedding_missing_record_returns_false(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")

    assert delete_chunk_embedding(db_path, 1) is False


def test_is_chunk_embedding_stale_missing_record_returns_true(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")

    assert is_chunk_embedding_stale(db_path, 1, content_hash="hash-a") is True


def test_is_chunk_embedding_stale_same_hash_returns_false(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")
    upsert_chunk_embedding(db_path, 1, [0.1], "fake-embedding-v1", "hash-a")

    assert is_chunk_embedding_stale(db_path, 1, content_hash="hash-a") is False


def test_is_chunk_embedding_stale_changed_hash_returns_true(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")
    upsert_chunk_embedding(db_path, 1, [0.1], "fake-embedding-v1", "hash-a")

    assert is_chunk_embedding_stale(db_path, 1, content_hash="hash-b") is True


def test_is_chunk_embedding_stale_changed_model_returns_true(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")
    upsert_chunk_embedding(db_path, 1, [0.1], "fake-embedding-v1", "hash-a")

    assert (
        is_chunk_embedding_stale(
            db_path,
            1,
            content_hash="hash-a",
            embedding_model="fake-embedding-v2",
        )
        is True
    )


def test_is_chunk_embedding_stale_ignores_hash_when_content_hash_is_none(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")
    upsert_chunk_embedding(db_path, 1, [0.1], "fake-embedding-v1", "hash-a")

    assert (
        is_chunk_embedding_stale(
            db_path,
            1,
            content_hash=None,
            embedding_model="fake-embedding-v1",
        )
        is False
    )


def test_get_chunk_embedding_invalid_embedding_json_raises_value_error(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")
    init_chunk_embeddings_table(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO chunk_embeddings
           (chunk_id, embedding_json, embedding_model, embedding_dimension,
            content_hash, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (1, "not-json", "fake-embedding-v1", 3, "hash-a", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
    )
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="invalid embedding_json"):
        get_chunk_embedding(db_path, 1)


def test_get_chunk_embedding_dimension_mismatch_raises_value_error(tmp_path) -> None:
    db_path = str(tmp_path / "embeddings.db")
    init_chunk_embeddings_table(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO chunk_embeddings
           (chunk_id, embedding_json, embedding_model, embedding_dimension,
            content_hash, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (1, "[0.1, 0.2]", "fake-embedding-v1", 3, "hash-a", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
    )
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="embedding_dimension mismatch"):
        get_chunk_embedding(db_path, 1)
