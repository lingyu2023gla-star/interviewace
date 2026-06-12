#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

print_json() {
  if python -m json.tool >/dev/null 2>&1 <<< '{}'; then
    python -m json.tool
  else
    cat
  fi
}

require_cmd curl

echo "Checking Skill API at ${BASE_URL}"

echo
echo "== GET /api/skills =="
curl -s "${BASE_URL}/api/skills" | print_json

echo
echo "== GET /api/skills/interview_preparation =="
curl -s "${BASE_URL}/api/skills/interview_preparation" | print_json

echo
echo "== GET /api/skills/project_pitch =="
curl -s "${BASE_URL}/api/skills/project_pitch" | print_json

echo
echo "Skill API smoke check completed."
