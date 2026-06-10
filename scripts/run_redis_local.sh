#!/usr/bin/env bash
set -euo pipefail

if ! command -v redis-server >/dev/null 2>&1; then
  echo "redis-server not found. Install Redis with: brew install redis" >&2
  exit 1
fi

redis-server
