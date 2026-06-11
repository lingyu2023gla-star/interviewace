"""Schemas for GBrain Markdown export."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GBrainExportOptions:
    """Options for exporting InterviewAce knowledge chunks to Markdown."""

    db_path: str
    output_dir: str
    include_chunks: bool = True
    include_topics: bool = True
    include_sessions: bool = True
    max_content_chars: int = 4000


@dataclass(frozen=True)
class GBrainExportResult:
    """Summary of a GBrain Markdown export."""

    output_dir: str
    files_written: list[str]
    chunks_exported: int
    topics_exported: int
    sessions_exported: int
