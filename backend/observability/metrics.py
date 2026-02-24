from __future__ import annotations

from collections import defaultdict
from threading import Lock


_LOCK = Lock()
_REQUEST_COUNTER: dict[str, int] = defaultdict(int)
_DURATION_BUCKETS: tuple[float, ...] = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_DURATION_BUCKET_COUNTER: dict[float, int] = {bucket: 0 for bucket in _DURATION_BUCKETS}
_DURATION_COUNT = 0
_DURATION_SUM = 0.0


def record_http_request(endpoint: str, status_code: int) -> None:
    key = f"{endpoint}|{status_code}"
    with _LOCK:
        _REQUEST_COUNTER[key] += 1


def record_http_duration(duration_seconds: float) -> None:
    value = max(duration_seconds, 0.0)
    global _DURATION_COUNT, _DURATION_SUM
    with _LOCK:
        _DURATION_COUNT += 1
        _DURATION_SUM += value
        for bucket in _DURATION_BUCKETS:
            if value <= bucket:
                _DURATION_BUCKET_COUNTER[bucket] += 1


def metrics_snapshot() -> str:
    lines = [
        "# HELP genesis_http_requests_total Total HTTP requests by endpoint and status",
        "# TYPE genesis_http_requests_total counter",
    ]
    has_requests = False
    with _LOCK:
        for key, value in sorted(_REQUEST_COUNTER.items()):
            endpoint, status = key.split("|", 1)
            lines.append(
                f'genesis_http_requests_total{{endpoint="{endpoint}",status="{status}"}} {value}'
            )
            has_requests = True

        lines.extend(
            [
                "# HELP genesis_http_request_duration_seconds HTTP request latency histogram",
                "# TYPE genesis_http_request_duration_seconds histogram",
            ]
        )
        for bucket in _DURATION_BUCKETS:
            count = _DURATION_BUCKET_COUNTER[bucket]
            lines.append(f'genesis_http_request_duration_seconds_bucket{{le="{bucket:g}"}} {count}')
        lines.append(f'genesis_http_request_duration_seconds_bucket{{le="+Inf"}} {_DURATION_COUNT}')
        lines.append(f"genesis_http_request_duration_seconds_sum {_DURATION_SUM}")
        lines.append(f"genesis_http_request_duration_seconds_count {_DURATION_COUNT}")
    if not has_requests:
        lines.append('genesis_http_requests_total{endpoint="none",status="0"} 0')
    return "\n".join(lines) + "\n"
