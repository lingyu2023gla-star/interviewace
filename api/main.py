"""FastAPI entrypoint for InterviewAce."""

from __future__ import annotations

from fastapi import FastAPI

from api.routers import health, knowledge, preparation


app = FastAPI(
    title="InterviewAce API",
    version="0.1.0",
    description="AI interview review and evidence-based preparation API",
)

app.include_router(health.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api/knowledge")
app.include_router(preparation.router, prefix="/api/preparation")
