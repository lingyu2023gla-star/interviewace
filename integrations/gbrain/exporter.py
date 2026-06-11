"""Export InterviewAce knowledge chunks as GBrain-friendly Markdown."""

from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from integrations.gbrain.schemas import GBrainExportOptions, GBrainExportResult


_ILLEGAL_FILENAME_CHARS_RE = re.compile(r'[/\\:*?"<>|]+')
_WHITESPACE_RE = re.compile(r"\s+")


def slugify(value: str | None) -> str:
    """Return a safe filename slug for a topic or label."""
    if value is None or not value.strip():
        return "uncategorized"

    slug = value.strip().lower()
    slug = _ILLEGAL_FILENAME_CHARS_RE.sub("-", slug)
    slug = _WHITESPACE_RE.sub("-", slug)
    slug = slug.strip(".- _")
    return slug or "uncategorized"


def truncate_text(text: str | None, max_chars: int) -> str:
    """Truncate text to max_chars and append ellipsis when needed."""
    if text is None or max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def _parse_json_field(value: str | None, default: Any) -> Any:
    """Parse a JSON field, returning default when parsing fails."""
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def load_knowledge_chunks(db_path: str) -> list[dict]:
    """Load knowledge chunks from SQLite in ascending id order."""
    if not Path(db_path).exists():
        return []

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'knowledge_chunks'"
        ).fetchone()
        if exists is None:
            return []

        rows = conn.execute(
            """SELECT id, source_type, source_id, session_id, turn_id, question_id,
                      title, content, job_direction, topic, dimension_key,
                      tags, metadata_json, created_at, updated_at
               FROM knowledge_chunks
               ORDER BY id ASC"""
        ).fetchall()
    finally:
        try:
            conn.close()
        except UnboundLocalError:
            pass

    chunks = []
    for row in rows:
        chunk = dict(row)
        chunk["tags"] = _parse_json_field(chunk.get("tags"), [])
        chunk["metadata"] = _parse_json_field(chunk.get("metadata_json"), {})
        chunks.append(chunk)
    return chunks


def _display(value: Any) -> str:
    """Return a displayable metadata value."""
    if value is None or value == "":
        return "N/A"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "N/A"
    return str(value)


def format_chunk_markdown(chunk: dict, max_content_chars: int = 4000) -> str:
    """Format one knowledge chunk as Markdown."""
    chunk_id = chunk.get("id")
    title = chunk.get("title") or f"Knowledge Chunk {chunk_id}"
    metadata = chunk.get("metadata") or {}
    raw_metadata = json.dumps(metadata, ensure_ascii=False, indent=2)
    content = truncate_text(chunk.get("content"), max_content_chars)

    return f"""# {title}

## Metadata

- Chunk ID: {_display(chunk_id)}
- Source Type: {_display(chunk.get("source_type"))}
- Source ID: {_display(chunk.get("source_id"))}
- Session ID: {_display(chunk.get("session_id"))}
- Turn ID: {_display(chunk.get("turn_id"))}
- Question ID: {_display(chunk.get("question_id"))}
- Job Direction: {_display(chunk.get("job_direction"))}
- Topic: {_display(chunk.get("topic"))}
- Dimension: {_display(chunk.get("dimension_key"))}
- Tags: {_display(chunk.get("tags"))}

## Content

{content}

## Raw Metadata

```json
{raw_metadata}
```
"""


def format_topic_markdown(
    topic: str,
    chunks: list[dict],
    max_content_chars: int = 4000,
) -> str:
    """Format all chunks for one topic as Markdown."""
    chunk_content_limit = max(1, max_content_chars // 2)
    sections = [
        f"# Topic: {topic}",
        "",
        "## Summary",
        "",
        "This page aggregates InterviewAce knowledge chunks for this topic.",
        "",
        "## Chunks",
        "",
    ]
    for chunk in chunks:
        title = chunk.get("title") or f"Knowledge Chunk {chunk.get('id')}"
        sections.extend(
            [
                f"### {title}",
                "",
                f"- Chunk ID: {_display(chunk.get('id'))}",
                f"- Source Type: {_display(chunk.get('source_type'))}",
                f"- Source ID: {_display(chunk.get('source_id'))}",
                f"- Session ID: {_display(chunk.get('session_id'))}",
                f"- Dimension: {_display(chunk.get('dimension_key'))}",
                f"- Tags: {_display(chunk.get('tags'))}",
                "",
                truncate_text(chunk.get("content"), chunk_content_limit),
                "",
            ]
        )
    return "\n".join(sections).rstrip() + "\n"


def format_session_markdown(
    session_id: int | str,
    chunks: list[dict],
    max_content_chars: int = 4000,
) -> str:
    """Format all chunks for one interview session as Markdown."""
    chunk_content_limit = max(1, max_content_chars // 2)
    sections = [
        f"# Interview Session: {session_id}",
        "",
        "## Summary",
        "",
        "This page aggregates InterviewAce knowledge chunks for this interview session.",
        "",
        "## Chunks",
        "",
    ]
    for chunk in chunks:
        title = chunk.get("title") or f"Knowledge Chunk {chunk.get('id')}"
        sections.extend(
            [
                f"### {title}",
                "",
                f"- Chunk ID: {_display(chunk.get('id'))}",
                f"- Source Type: {_display(chunk.get('source_type'))}",
                f"- Source ID: {_display(chunk.get('source_id'))}",
                f"- Topic: {_display(chunk.get('topic'))}",
                f"- Dimension: {_display(chunk.get('dimension_key'))}",
                f"- Tags: {_display(chunk.get('tags'))}",
                "",
                truncate_text(chunk.get("content"), chunk_content_limit),
                "",
            ]
        )
    return "\n".join(sections).rstrip() + "\n"


def write_text_file(path: Path, content: str) -> None:
    """Write UTF-8 text and create parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _relative_path(path: Path, base_dir: Path) -> str:
    """Return a POSIX relative path for index and tests."""
    return path.relative_to(base_dir).as_posix()


def _group_by(chunks: list[dict], key: str, missing_value: Any) -> dict[Any, list[dict]]:
    """Group chunks by a key, replacing missing values."""
    groups: dict[Any, list[dict]] = defaultdict(list)
    for chunk in chunks:
        value = chunk.get(key)
        if value is None or value == "":
            value = missing_value
        groups[value].append(chunk)
    return dict(groups)


def _format_index(
    files_written: list[str],
    chunks_exported: int,
    topics_exported: int,
    sessions_exported: int,
) -> str:
    """Format the export index Markdown."""
    exported_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_lines = "\n".join(f"- [{path}]({path})" for path in files_written if path != "index.md")
    if not file_lines:
        file_lines = "- No knowledge chunk files exported."

    return f"""# InterviewAce GBrain Export

Exported at: {exported_at}

These Markdown files are generated from InterviewAce `knowledge_chunks` and can be used as GBrain / agent long-term knowledge input.

## Summary

- Chunks Exported: {chunks_exported}
- Topics Exported: {topics_exported}
- Sessions Exported: {sessions_exported}

## Files

{file_lines}
"""


def export_gbrain_markdown(options: GBrainExportOptions) -> GBrainExportResult:
    """Export knowledge chunks from SQLite into GBrain-friendly Markdown files."""
    chunks = load_knowledge_chunks(options.db_path)
    output_dir = Path(options.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    files_written: list[str] = []

    chunks_exported = 0
    if options.include_chunks:
        for chunk in chunks:
            path = output_dir / "chunks" / f"chunk-{chunk.get('id')}.md"
            write_text_file(
                path,
                format_chunk_markdown(chunk, max_content_chars=options.max_content_chars),
            )
            files_written.append(_relative_path(path, output_dir))
            chunks_exported += 1

    topics_exported = 0
    if options.include_topics:
        for topic, topic_chunks in _group_by(chunks, "topic", "uncategorized").items():
            topic_label = str(topic)
            path = output_dir / "topics" / f"{slugify(topic_label)}.md"
            write_text_file(
                path,
                format_topic_markdown(
                    topic_label,
                    topic_chunks,
                    max_content_chars=options.max_content_chars,
                ),
            )
            files_written.append(_relative_path(path, output_dir))
            topics_exported += 1

    sessions_exported = 0
    if options.include_sessions:
        for session_id, session_chunks in _group_by(chunks, "session_id", "unknown").items():
            session_label = str(session_id) if session_id != "unknown" else "unknown-session"
            filename = (
                "unknown-session.md"
                if session_label == "unknown-session"
                else f"session-{slugify(session_label)}.md"
            )
            path = output_dir / "interviews" / filename
            write_text_file(
                path,
                format_session_markdown(
                    session_label,
                    session_chunks,
                    max_content_chars=options.max_content_chars,
                ),
            )
            files_written.append(_relative_path(path, output_dir))
            sessions_exported += 1

    index_path = output_dir / "index.md"
    index_rel = _relative_path(index_path, output_dir)
    write_text_file(
        index_path,
        _format_index(files_written, chunks_exported, topics_exported, sessions_exported),
    )
    files_written.append(index_rel)

    return GBrainExportResult(
        output_dir=str(output_dir),
        files_written=files_written,
        chunks_exported=chunks_exported,
        topics_exported=topics_exported,
        sessions_exported=sessions_exported,
    )
