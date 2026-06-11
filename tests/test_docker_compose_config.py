"""Docker Compose local stack configuration tests."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    """Read a repository text file."""
    return (ROOT / path).read_text(encoding="utf-8")


def test_dockerfile_exists() -> None:
    content = _read("Dockerfile")

    assert "FROM python:" in content
    assert "WORKDIR /app" in content
    assert "requirements.txt" in content
    assert "pip install" in content


def test_docker_compose_exists_with_required_services() -> None:
    content = _read("docker-compose.yml")

    assert "redis:" in content
    assert "api:" in content
    assert "worker:" in content
    assert "redis:7-alpine" in content


def test_docker_compose_api_exposes_8000() -> None:
    content = _read("docker-compose.yml")

    assert '"8000:8000"' in content
    assert "uvicorn api.main:app --host 0.0.0.0 --port 8000" in content


def test_docker_compose_api_and_worker_env_vars() -> None:
    content = _read("docker-compose.yml")

    assert content.count("INTERVIEWACE_DB_PATH: /app/data/interviews.db") >= 2
    assert content.count("CELERY_BROKER_URL: redis://redis:6379/0") >= 2
    assert content.count("CELERY_RESULT_BACKEND: redis://redis:6379/1") >= 2


def test_docker_compose_api_and_worker_mount_data() -> None:
    content = _read("docker-compose.yml")

    assert content.count("./data:/app/data") >= 2
    assert content.count("./outputs:/app/outputs") >= 2
    assert content.count("./exports:/app/exports") >= 2


def test_docker_compose_docs_exist() -> None:
    content = _read("docs/docker_compose.md")

    assert "docker compose up --build" in content
    assert "docker compose up -d --build" in content
    assert "curl http://127.0.0.1:8000/api/health" in content
