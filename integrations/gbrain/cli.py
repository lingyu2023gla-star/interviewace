"""Command line interface for GBrain Markdown export."""

from __future__ import annotations

import argparse

from integrations.gbrain.exporter import export_gbrain_markdown
from integrations.gbrain.schemas import GBrainExportOptions


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Export InterviewAce knowledge chunks to Markdown.")
    parser.add_argument("--db", required=True, help="Path to the SQLite database.")
    parser.add_argument("--out", required=True, help="Output directory for Markdown files.")
    parser.add_argument("--no-chunks", action="store_true", help="Do not export per-chunk files.")
    parser.add_argument("--no-topics", action="store_true", help="Do not export topic aggregate files.")
    parser.add_argument("--no-sessions", action="store_true", help="Do not export session aggregate files.")
    parser.add_argument(
        "--max-content-chars",
        type=int,
        default=4000,
        help="Maximum content characters per chunk export.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the GBrain Markdown export CLI."""
    args = build_parser().parse_args(argv)
    result = export_gbrain_markdown(
        GBrainExportOptions(
            db_path=args.db,
            output_dir=args.out,
            include_chunks=not args.no_chunks,
            include_topics=not args.no_topics,
            include_sessions=not args.no_sessions,
            max_content_chars=args.max_content_chars,
        )
    )

    print(f"output_dir: {result.output_dir}")
    print(f"chunks_exported: {result.chunks_exported}")
    print(f"topics_exported: {result.topics_exported}")
    print(f"sessions_exported: {result.sessions_exported}")
    print(f"files_written: {len(result.files_written)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
