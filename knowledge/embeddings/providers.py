"""Embedding provider abstractions for local retriever tests."""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """Abstract embedding provider interface."""

    model_name: str

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Return an embedding vector for text."""


class FakeEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic local embedding provider for tests and demos."""

    def __init__(self, dimension: int = 8, model_name: str = "fake-embedding-v1") -> None:
        """Create a deterministic fake embedding provider."""
        if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension <= 0:
            raise ValueError("dimension must be a positive integer")
        if not model_name or not model_name.strip():
            raise ValueError("model_name must not be empty")
        self.dimension = dimension
        self.model_name = model_name

    def embed_text(self, text: str) -> list[float]:
        """Build a deterministic normalized embedding from text tokens."""
        tokens = text.split() or [""]
        vector = [0.0 for _ in range(self.dimension)]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index, byte in enumerate(digest):
                dim = index % self.dimension
                sign = 1.0 if index % 2 == 0 else -1.0
                vector[dim] += sign * (float(byte) / 255.0)

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            vector[0] = 1.0
            return vector
        return [value / norm for value in vector]
