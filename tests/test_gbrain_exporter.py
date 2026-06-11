"""GBrain Markdown exporter tests."""

from __future__ import annotations

from pathlib import Path

from integrations.gbrain.cli import main
from integrations.gbrain.exporter import (
    export_gbrain_markdown,
    format_chunk_markdown,
    slugify,
)
from integrations.gbrain.schemas import GBrainExportOptions
from knowledge.repository import upsert_knowledge_chunks
from knowledge.schemas import KnowledgeChunk


def _seed_chunks(db_path: str) -> None:
    """Insert knowledge chunks for exporter tests."""
    upsert_knowledge_chunks(
        db_path,
        [
            KnowledgeChunk(
                source_type="turn_feedback",
                source_id="turn:1:feedback",
                session_id=1,
                turn_id=1,
                title="Agent 架构复盘",
                content="候选人讲到了 Orchestrator、ToolResult 和降级策略。",
                job_direction="大模型应用工程师",
                topic="Agent 架构",
                dimension_key="agent_architecture",
                tags=["Agent", "架构"],
                metadata={"question": "请介绍 Agent 架构"},
            ),
            KnowledgeChunk(
                source_type="turn_feedback",
                source_id="turn:2:feedback",
                session_id=1,
                turn_id=2,
                title="RAG 能力复盘",
                content="候选人说明 RAG 尚未完整实现，只是后续规划方向。",
                job_direction="大模型应用工程师",
                topic="RAG",
                dimension_key="rag_capability",
                tags=["RAG"],
                metadata={"question": "你这个项目里面有 RAG 吗"},
            ),
        ],
    )


def test_slugify() -> None:
    assert slugify(None) == "uncategorized"
    assert slugify("") == "uncategorized"

    agent_slug = slugify("Agent 架构")
    assert "agent" in agent_slug
    assert not any(char in agent_slug for char in '/\\:*?"<>|')

    unsafe_slug = slugify("a/b:c")
    assert "/" not in unsafe_slug
    assert ":" not in unsafe_slug


def test_format_chunk_markdown() -> None:
    chunk = {
        "id": 1,
        "source_type": "turn_feedback",
        "source_id": "turn:1:feedback",
        "session_id": 10,
        "turn_id": 1,
        "question_id": None,
        "title": "Agent 架构复盘",
        "content": "候选人讲到了 Orchestrator。",
        "job_direction": "大模型应用工程师",
        "topic": "Agent 架构",
        "dimension_key": "agent_architecture",
        "tags": ["Agent"],
        "metadata": {"question": "请介绍 Agent 架构"},
    }

    markdown = format_chunk_markdown(chunk)

    assert "# Agent 架构复盘" in markdown
    assert "Chunk ID: 1" in markdown
    assert "Source Type: turn_feedback" in markdown
    assert "Session ID: 10" in markdown
    assert "Topic: Agent 架构" in markdown
    assert "候选人讲到了 Orchestrator。" in markdown
    assert "Raw Metadata" in markdown


def test_export_gbrain_markdown_writes_files(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge.db")
    output_dir = tmp_path / "gbrain"
    _seed_chunks(db_path)

    result = export_gbrain_markdown(
        GBrainExportOptions(db_path=db_path, output_dir=str(output_dir))
    )

    assert result.chunks_exported == 2
    assert result.topics_exported >= 2
    assert result.sessions_exported >= 1
    assert (output_dir / "index.md").exists()
    assert len(list((output_dir / "chunks").glob("chunk-*.md"))) == 2
    assert list((output_dir / "topics").glob("*.md"))
    assert list((output_dir / "interviews").glob("*.md"))
    assert "InterviewAce GBrain Export" in (output_dir / "index.md").read_text(encoding="utf-8")


def test_export_gbrain_markdown_respects_flags(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge.db")
    output_dir = tmp_path / "gbrain"
    _seed_chunks(db_path)

    result = export_gbrain_markdown(
        GBrainExportOptions(
            db_path=db_path,
            output_dir=str(output_dir),
            include_chunks=False,
        )
    )

    assert result.chunks_exported == 0
    assert not (output_dir / "chunks").exists()
    assert (output_dir / "index.md").exists()


def test_export_empty_db(tmp_path) -> None:
    db_path = str(tmp_path / "empty.db")
    output_dir = tmp_path / "gbrain"

    result = export_gbrain_markdown(
        GBrainExportOptions(db_path=db_path, output_dir=str(output_dir))
    )

    assert result.chunks_exported == 0
    assert result.topics_exported == 0
    assert result.sessions_exported == 0
    assert (output_dir / "index.md").exists()


def test_cli_export(tmp_path) -> None:
    db_path = str(tmp_path / "knowledge.db")
    output_dir = tmp_path / "gbrain"
    _seed_chunks(db_path)

    exit_code = main(["--db", db_path, "--out", str(output_dir)])

    assert exit_code == 0
    assert Path(output_dir / "index.md").exists()
