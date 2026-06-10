#!/usr/bin/env bash
set -euo pipefail

export INTERVIEWACE_DB_PATH="${INTERVIEWACE_DB_PATH:-data/interviews.db}"
export CELERY_BROKER_URL="${CELERY_BROKER_URL:-redis://localhost:6379/0}"
export CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-redis://localhost:6379/1}"

celery -A worker.celery_app.celery_app worker --loglevel=info
