"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    """Return API health status."""
    return {"status": "ok", "service": "interviewace-api"}
