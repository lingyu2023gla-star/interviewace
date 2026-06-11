"""Embedding provider and similarity tests."""

from __future__ import annotations

import pytest

from knowledge.embeddings.providers import FakeEmbeddingProvider
from knowledge.embeddings.similarity import cosine_similarity


def test_fake_embedding_provider_dimension() -> None:
    provider = FakeEmbeddingProvider(dimension=6)

    embedding = provider.embed_text("Agent Orchestrator")

    assert len(embedding) == 6
    assert all(isinstance(value, float) for value in embedding)


def test_fake_embedding_provider_is_stable() -> None:
    provider = FakeEmbeddingProvider(dimension=8)

    assert provider.embed_text("Agent RAG") == provider.embed_text("Agent RAG")


def test_fake_embedding_provider_different_text_usually_differs() -> None:
    provider = FakeEmbeddingProvider(dimension=8)

    assert provider.embed_text("Agent") != provider.embed_text("Redis")


def test_fake_embedding_provider_empty_text_is_stable() -> None:
    provider = FakeEmbeddingProvider(dimension=8)

    assert provider.embed_text("") == provider.embed_text("")
    assert len(provider.embed_text("")) == 8


@pytest.mark.parametrize("dimension", [0, -1, True, 1.5])
def test_fake_embedding_provider_invalid_dimension_raises(dimension) -> None:
    with pytest.raises(ValueError, match="dimension must be a positive integer"):
        FakeEmbeddingProvider(dimension=dimension)


def test_fake_embedding_provider_model_name() -> None:
    provider = FakeEmbeddingProvider(dimension=4, model_name="fake-test")

    assert provider.model_name == "fake-test"


def test_cosine_similarity_same_direction() -> None:
    assert cosine_similarity([1.0, 0.0], [2.0, 0.0]) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal() -> None:
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_similarity_opposite_direction() -> None:
    assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def test_cosine_similarity_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="same length"):
        cosine_similarity([1.0], [1.0, 0.0])


def test_cosine_similarity_empty_vector_raises() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        cosine_similarity([], [1.0])


@pytest.mark.parametrize("vector", [[True], ["bad"], [None]])
def test_cosine_similarity_non_numeric_vector_raises(vector) -> None:
    with pytest.raises(ValueError, match="values must be numeric"):
        cosine_similarity(vector, [1.0])


def test_cosine_similarity_zero_norm_returns_zero() -> None:
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
