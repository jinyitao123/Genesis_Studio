#!/usr/bin/env bash
set -euo pipefail

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  echo "[runbook] dry-run: would restart query-api and validate /api/health"
  exit 0
fi

docker compose restart query-api
python - <<'PY'
import time
import requests

deadline = time.time() + 60
while time.time() < deadline:
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=5)
        if response.status_code == 200:
            print("query-api recovered")
            raise SystemExit(0)
    except Exception:
        pass
    time.sleep(1)

raise SystemExit("query-api recovery failed")
PY
