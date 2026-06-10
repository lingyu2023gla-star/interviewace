"""Build citation-ready evidence context from knowledge search results."""

from __future__ import annotations

from knowledge.schemas import EvidenceContextBlock, KnowledgeSearchResult


_METADATA_KEYS = ("question", "answer", "difficulty", "mastery")


def truncate_text(text: str | None, max_chars: int = 600) -> str:
    """Truncate text to max_chars and append ellipsis when needed."""
    if text is None or max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}..."


def _display(value: object) -> str:
    """Format missing values as N/A for evidence context."""
    if value is None or value == "":
        return "N/A"
    return str(value)


def build_evidence_blocks(
    results: list[KnowledgeSearchResult],
    max_chunks: int = 5,
    max_content_chars: int = 600,
) -> list[EvidenceContextBlock]:
    """Convert search results to stable E1/E2 evidence blocks."""
    if max_chunks <= 0:
        return []

    blocks = []
    for index, result in enumerate(results[:max_chunks], start=1):
        content = result.snippet or result.content
        blocks.append(
            EvidenceContextBlock(
                evidence_id=f"E{index}",
                chunk_id=result.chunk_id,
                source_type=result.source_type,
                source_id=result.source_id,
                content=truncate_text(content, max_content_chars),
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
            )
        )
    return blocks


def _format_metadata(metadata: dict) -> str:
    """Format selected metadata fields for a readable prompt context."""
    lines = []
    for key in _METADATA_KEYS:
        value = metadata.get(key)
        if value is not None and value != "":
            lines.append(f"{key}：{truncate_text(str(value), 180)}")
    return "\n".join(lines) if lines else "N/A"


def format_evidence_block(block: EvidenceContextBlock) -> str:
    """Format one evidence block as citation-ready plain text."""
    return "\n".join(
        [
            f"[{block.evidence_id}]",
            f"来源类型：{_display(block.source_type)}",
            f"来源ID：{_display(block.source_id)}",
            f"会话ID：{_display(block.session_id)}",
            f"轮次ID：{_display(block.turn_id)}",
            f"题目ID：{_display(block.question_id)}",
            f"主题：{_display(block.topic)}",
            f"维度：{_display(block.dimension_key)}",
            f"标题：{_display(block.title)}",
            f"关键元数据：\n{_format_metadata(block.metadata)}",
            "证据内容：",
            block.content,
        ]
    )


def build_evidence_context(
    results: list[KnowledgeSearchResult],
    max_chunks: int = 5,
    max_content_chars: int = 600,
) -> str:
    """Build a prompt-ready evidence context from search results."""
    blocks = build_evidence_blocks(
        results=results,
        max_chunks=max_chunks,
        max_content_chars=max_content_chars,
    )
    if not blocks:
        return "无可用历史证据。"
    return "\n\n".join(format_evidence_block(block) for block in blocks)
