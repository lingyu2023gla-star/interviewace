.PHONY: run-api run-worker run-redis test test-integration

run-api:
	./scripts/run_api.sh

run-worker:
	./scripts/run_worker.sh

run-redis:
	./scripts/run_redis_docker.sh

test:
	.venv/bin/python -m pytest tests/ -v

test-integration:
	RUN_CELERY_INTEGRATION=1 .venv/bin/python -m pytest tests/test_celery_redis_integration.py -v
