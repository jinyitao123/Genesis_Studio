from __future__ import annotations

from collections import defaultdict
from threading import Lock


_LOCK = Lock()
_REQUEST_COUNTER: dict[str, int] = defaultdict(int)


def record_http_request(endpoint: str, status_code: int) -> None:
    key = f"{endpoint}|{status_code}"
    with _LOCK:
        _REQUEST_COUNTER[key] += 1


def metrics_snapshot() -> str:
    lines = [
        "# HELP genesis_http_requests_total Total HTTP requests by endpoint and status",
        "# TYPE genesis_http_requests_total counter",
    ]
    with _LOCK:
        for key, value in sorted(_REQUEST_COUNTER.items()):
            endpoint, status = key.split("|", 1)
            lines.append(
                f'genesis_http_requests_total{{endpoint="{endpoint}",status="{status}"}} {value}'
            )
    if len(lines) == 2:
        lines.append('genesis_http_requests_total{endpoint="none",status="0"} 0')
    return "\n".join(lines) + "\n"
