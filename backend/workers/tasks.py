from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import TypedDict

from .celery_app import celery_app


class ReplayPayload(TypedDict):
    from_event_id: str | None
    correlation_id: str | None
    traceparent: str | None
    requested_by: str | None


class ProjectionMetrics(TypedDict):
    refresh_runs: int
    replay_runs: int
    last_refresh_at: str | None
    last_replay_at: str | None
    last_replay: ReplayPayload | None


_projection_metrics: ProjectionMetrics = {
    "refresh_runs": 0,
    "replay_runs": 0,
    "last_refresh_at": None,
    "last_replay_at": None,
    "last_replay": None,
}


def projection_task_metrics() -> ProjectionMetrics:
    return {
        "refresh_runs": _projection_metrics["refresh_runs"],
        "replay_runs": _projection_metrics["replay_runs"],
        "last_refresh_at": _projection_metrics["last_refresh_at"],
        "last_replay_at": _projection_metrics["last_replay_at"],
        "last_replay": _projection_metrics["last_replay"],
    }


@celery_app.task(name="genesis.projection.refresh")
def refresh_projection_task() -> dict[str, str]:
    now = datetime.now(timezone.utc).isoformat()
    _projection_metrics["refresh_runs"] = _projection_metrics["refresh_runs"] + 1
    _projection_metrics["last_refresh_at"] = now
    return {
        "status": "ok",
        "task": "projection.refresh",
        "executed_at": now,
    }


@celery_app.task(name="genesis.projection.replay")
def replay_projection_task(
    from_event_id: str | None = None,
    correlation_id: str | None = None,
    traceparent: str | None = None,
    requested_by: str | None = None,
) -> dict[str, str | None]:
    now = datetime.now(timezone.utc).isoformat()
    _projection_metrics["replay_runs"] = _projection_metrics["replay_runs"] + 1
    _projection_metrics["last_replay_at"] = now
    _projection_metrics["last_replay"] = {
        "from_event_id": from_event_id,
        "correlation_id": correlation_id,
        "traceparent": traceparent,
        "requested_by": requested_by,
    }
    return {
        "status": "ok",
        "task": "projection.replay",
        "from_event_id": from_event_id,
        "correlation_id": correlation_id,
        "traceparent": traceparent,
        "requested_by": requested_by,
        "executed_at": now,
    }
