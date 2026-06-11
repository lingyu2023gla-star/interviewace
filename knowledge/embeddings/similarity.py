"""Vector similarity utilities."""

from __future__ import annotations

import math


def _normalize_vector(values: list[float], name: str) -> list[float]:
    """Validate and convert a vector to floats."""
    if not values:
        raise ValueError(f"{name} must not be empty")

    normalized: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} values must be numeric")
        normalized.append(float(value))
    return normalized


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity without external dependencies."""
    vector_a = _normalize_vector(a, "a")
    vector_b = _normalize_vector(b, "b")
    if len(vector_a) != len(vector_b):
        raise ValueError("vectors must have the same length")

    dot = sum(left * right for left, right in zip(vector_a, vector_b, strict=True))
    norm_a = math.sqrt(sum(value * value for value in vector_a))
    norm_b = math.sqrt(sum(value * value for value in vector_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
