from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import TypedDict

from ..async_bus import list_domain_events
from ..config import load_settings
from ..ontology.deps import create_repository
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
    last_snapshot_id: str | None
    last_projected_event_count: int
    last_replayed_event_count: int


_projection_metrics: ProjectionMetrics = {
    "refresh_runs": 0,
    "replay_runs": 0,
    "last_refresh_at": None,
    "last_replay_at": None,
    "last_replay": None,
    "last_snapshot_id": None,
    "last_projected_event_count": 0,
    "last_replayed_event_count": 0,
}


def projection_task_metrics() -> ProjectionMetrics:
    return {
        "refresh_runs": _projection_metrics["refresh_runs"],
        "replay_runs": _projection_metrics["replay_runs"],
        "last_refresh_at": _projection_metrics["last_refresh_at"],
        "last_replay_at": _projection_metrics["last_replay_at"],
        "last_replay": _projection_metrics["last_replay"],
        "last_snapshot_id": _projection_metrics["last_snapshot_id"],
        "last_projected_event_count": _projection_metrics["last_projected_event_count"],
        "last_replayed_event_count": _projection_metrics["last_replayed_event_count"],
    }


def _create_projection_snapshot() -> tuple[str | None, int]:
    settings = load_settings()
    repo = create_repository(settings)
    try:
        snapshot = repo.create_projection_snapshot()
        return snapshot.projection_id, snapshot.event_count
    finally:
        repo.close()


def _ordered_domain_events() -> list[dict[str, object]]:
    rows = list_domain_events(limit=5000)
    if not rows:
        return []
    return list(reversed(rows))


def _filter_replay_events(
    rows: list[dict[str, object]],
    *,
    from_event_id: str | None,
    correlation_id: str | None,
) -> list[dict[str, object]]:
    filtered = rows

    if correlation_id:
        filtered = [
            row
            for row in filtered
            if str(row.get("correlation_id") or "") == correlation_id
            or str(row.get("txn_id") or "") == correlation_id
        ]

    if from_event_id:
        start_index = -1
        for index, row in enumerate(filtered):
            if str(row.get("event_id") or "") == from_event_id:
                start_index = index
                break
        if start_index == -1:
            return []
        filtered = filtered[start_index:]

    return filtered


@celery_app.task(name="genesis.projection.refresh")
def refresh_projection_task() -> dict[str, str]:
    now = datetime.now(timezone.utc).isoformat()
    projection_id, projected_event_count = _create_projection_snapshot()
    _projection_metrics["refresh_runs"] = _projection_metrics["refresh_runs"] + 1
    _projection_metrics["last_refresh_at"] = now
    _projection_metrics["last_snapshot_id"] = projection_id
    _projection_metrics["last_projected_event_count"] = projected_event_count
    return {
        "status": "ok",
        "task": "projection.refresh",
        "executed_at": now,
        "projection_id": projection_id or "",
        "projected_event_count": str(projected_event_count),
    }


@celery_app.task(name="genesis.projection.replay")
def replay_projection_task(
    from_event_id: str | None = None,
    correlation_id: str | None = None,
    traceparent: str | None = None,
    requested_by: str | None = None,
) -> dict[str, str | None]:
    now = datetime.now(timezone.utc).isoformat()
    replay_candidates = _ordered_domain_events()
    replay_events = _filter_replay_events(
        replay_candidates,
        from_event_id=from_event_id,
        correlation_id=correlation_id,
    )
    projection_id, projected_event_count = _create_projection_snapshot()

    _projection_metrics["replay_runs"] = _projection_metrics["replay_runs"] + 1
    _projection_metrics["last_replay_at"] = now
    _projection_metrics["last_replay"] = {
        "from_event_id": from_event_id,
        "correlation_id": correlation_id,
        "traceparent": traceparent,
        "requested_by": requested_by,
    }
    _projection_metrics["last_snapshot_id"] = projection_id
    _projection_metrics["last_projected_event_count"] = projected_event_count
    _projection_metrics["last_replayed_event_count"] = len(replay_events)
    return {
        "status": "ok",
        "task": "projection.replay",
        "from_event_id": from_event_id,
        "correlation_id": correlation_id,
        "traceparent": traceparent,
        "requested_by": requested_by,
        "executed_at": now,
        "projection_id": projection_id,
        "projected_event_count": str(projected_event_count),
        "replayed_event_count": str(len(replay_events)),
    }


# Data plane projection tasks
@celery_app.task(name="genesis.projection.sync.elasticsearch")
def sync_events_to_elasticsearch(limit: int = 1000) -> dict[str, object]:
    """Sync events from event store to Elasticsearch for full-text search."""
    from ..services.backend_clients import SearchBackendClient

    now = datetime.now(timezone.utc).isoformat()
    client = SearchBackendClient()

    if not client.is_configured():
        return {
            "status": "skipped",
            "reason": "elasticsearch_not_configured",
            "executed_at": now,
        }

    # Fetch recent events from event store
    events = _ordered_domain_events()[:limit]
    if not events:
        return {
            "status": "ok",
            "indexed": 0,
            "executed_at": now,
        }

    # Bulk index to Elasticsearch
    indexed_count = client.bulk_index_events(events)

    return {
        "status": "ok",
        "indexed": indexed_count,
        "total_events": len(events),
        "executed_at": now,
    }


@celery_app.task(name="genesis.projection.sync.timescale")
def sync_events_to_timescale(limit: int = 1000) -> dict[str, object]:
    """Sync events from event store to TimescaleDB for time-series analytics."""
    from ..services.backend_clients import TimeseriesBackendClient

    now = datetime.now(timezone.utc).isoformat()
    client = TimeseriesBackendClient()

    if not client.is_configured():
        return {
            "status": "skipped",
            "reason": "timescaledb_not_configured",
            "executed_at": now,
        }

    # Fetch recent events from event store
    events = _ordered_domain_events()[:limit]
    if not events:
        return {
            "status": "ok",
            "inserted": 0,
            "executed_at": now,
        }

    # Bulk insert to TimescaleDB
    inserted_count = client.bulk_insert_events(events)

    return {
        "status": "ok",
        "inserted": inserted_count,
        "total_events": len(events),
        "executed_at": now,
    }
