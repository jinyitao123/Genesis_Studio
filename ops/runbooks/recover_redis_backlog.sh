#!/usr/bin/env bash
set -euo pipefail

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  echo "[runbook] dry-run: would restart worker and redis"
  exit 0
fi

docker compose restart redis worker
python - <<'PY'
import subprocess

result = subprocess.run(["docker", "compose", "ps", "worker"], capture_output=True, text=True, check=True)
if "worker" not in result.stdout:
    raise SystemExit("worker service not found")
print("redis backlog runbook completed")
PY
