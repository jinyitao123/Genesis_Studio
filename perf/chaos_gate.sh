#!/usr/bin/env bash
set -euo pipefail

echo "[chaos-gate] Simulating service restart scenario"
for svc in query-api command-api redis neo4j; do
  echo "[chaos-gate] Restarting ${svc}"
  docker compose restart "${svc}"
  sleep 3
done

python - <<'PY'
import time
import requests


def wait_ok(url: str, timeout_s: int = 60) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(1)
    raise AssertionError(f"timeout waiting for {url}")


def wait_post(url: str, *, json_body: dict, headers: dict[str, str], timeout_s: int = 60) -> requests.Response:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            resp = requests.post(url, json=json_body, headers=headers, timeout=5)
            if resp.status_code == 200:
                return resp
        except Exception:
            pass
        time.sleep(1)
    raise AssertionError(f"timeout waiting successful POST to {url}")


wait_ok('http://localhost:5000/api/health')
wait_ok('http://localhost:8000/health')

login = requests.post(
    'http://localhost:8000/api/auth/token',
    json={'username': 'designer', 'password': 'designer'},
    timeout=10,
)
assert login.status_code == 200
token = login.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

dispatch = wait_post(
    'http://localhost:8000/api/command/dispatch',
    json_body={
        'action_id': 'ACT_CHAOS_GATE',
        'source_id': 'chaos-a',
        'target_id': 'chaos-b',
        'payload': {'check': True},
    },
    headers=headers,
)

wait_ok('http://localhost:5000/api/query/transactions')
print('chaos gate passed')
PY
