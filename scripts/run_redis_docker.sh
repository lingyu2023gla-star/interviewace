#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found. Use local Redis with: brew install redis && ./scripts/run_redis_local.sh" >&2
  echo "Alternatively install Docker Desktop and retry ./scripts/run_redis_docker.sh" >&2
  exit 1
fi

docker run --rm \
  --name interviewace-redis \
  -p 6379:6379 \
  redis:7
