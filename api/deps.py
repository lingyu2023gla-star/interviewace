"""API dependencies and configuration helpers."""

from __future__ import annotations

import os


def get_db_path() -> str:
    """Return the SQLite database path for API requests."""
    return os.getenv("INTERVIEWACE_DB_PATH", "data/interviews.db")
