"""Optional Docker Compose config check for CI or local smoke validation."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.docker

ROOT = Path(__file__).resolve().parents[1]


def test_docker_compose_config_optional() -> None:
    """Run docker compose config only when explicitly enabled."""
    if os.getenv("RUN_DOCKER_COMPOSE_CHECK") != "1":
        pytest.skip("set RUN_DOCKER_COMPOSE_CHECK=1 to run docker compose config")
    if shutil.which("docker") is None:
        pytest.skip("docker not found")

    result = subprocess.run(
        ["docker", "compose", "config"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "redis:" in result.stdout
    assert "api:" in result.stdout
    assert "worker:" in result.stdout
