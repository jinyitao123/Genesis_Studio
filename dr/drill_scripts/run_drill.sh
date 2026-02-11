#!/usr/bin/env bash
set -euo pipefail

echo "[dr-drill] start"
docker compose up -d --build query-api command-api worker neo4j redis postgres
sleep 5

python - <<'PY'
import requests

query_health = requests.get("http://localhost:5000/api/health", timeout=10)
command_health = requests.get("http://localhost:8000/health", timeout=10)
assert query_health.status_code == 200
assert command_health.status_code == 200
print("dr drill passed")
PY

echo "[dr-drill] complete"
