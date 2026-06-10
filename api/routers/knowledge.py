"""Knowledge search and evidence context endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from api.deps import get_db_path
from api.schemas import (
    EvidenceContextRequest,
    EvidenceContextResponse,
    KnowledgeSearchItem,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from knowledge.context_builder import build_evidence_context
from knowledge.search import search_knowledge_chunks


router = APIRouter()


def _to_search_item(result) -> KnowledgeSearchItem:
    """Convert a knowledge search result dataclass to API schema."""
    return KnowledgeSearchItem(
        chunk_id=result.chunk_id,
        source_type=result.source_type,
        source_id=result.source_id,
        content=result.content,
        title=result.title,
        snippet=result.snippet,
        session_id=result.session_id,
        turn_id=result.turn_id,
        question_id=result.question_id,
        job_direction=result.job_direction,
        topic=result.topic,
        dimension_key=result.dimension_key,
        tags=result.tags,
        metadata=result.metadata,
        score=result.score,
    )


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(request: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
    """Search indexed knowledge chunks."""
    results = search_knowledge_chunks(
        db_path=get_db_path(),
        query=request.query,
        session_id=request.session_id,
        source_type=request.source_type,
        topic=request.topic,
        dimension_key=request.dimension_key,
        top_k=request.top_k,
    )
    return KnowledgeSearchResponse(
        query=request.query,
        total=len(results),
        results=[_to_search_item(result) for result in results],
    )


@router.post("/evidence-context", response_model=EvidenceContextResponse)
def build_context(request: EvidenceContextRequest) -> EvidenceContextResponse:
    """Build prompt-ready evidence context from search results."""
    results = search_knowledge_chunks(
        db_path=get_db_path(),
        query=request.query,
        session_id=request.session_id,
        source_type=request.source_type,
        topic=request.topic,
        dimension_key=request.dimension_key,
        top_k=request.top_k,
    )
    evidence_context = build_evidence_context(
        results,
        max_chunks=request.top_k,
        max_content_chars=request.max_content_chars,
    )
    return EvidenceContextResponse(
        query=request.query,
        used_evidence_count=len(results),
        evidence_context=evidence_context,
    )
