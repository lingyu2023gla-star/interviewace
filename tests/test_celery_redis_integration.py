"""Optional Celery/Redis integration smoke test."""

from __future__ import annotations

import os

import pytest

from worker.tasks import ping_task


pytestmark = pytest.mark.integration


def test_celery_ping_task_with_real_redis() -> None:
    if os.getenv("RUN_CELERY_INTEGRATION") != "1":
        pytest.skip("set RUN_CELERY_INTEGRATION=1 to run Celery/Redis integration test")

    async_result = ping_task.delay({"case": "integration"})
    result = async_result.get(timeout=10)

    assert result["status"] == "ok"
    assert result["message"] == "pong"
    assert result["payload"]["case"] == "integration"
