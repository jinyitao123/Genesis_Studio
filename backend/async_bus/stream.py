from __future__ import annotations

import json
import os
from datetime import datetime
from datetime import timezone

from typing import Any
from uuid import uuid4

from redis import Redis

from ..security.audit_signing import append_signed_audit_entry


def publish_domain_event(event: dict[str, str | int | float | bool | None]) -> bool:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:16379/0")
    service_name = os.getenv("SERVICE_NAME", "unknown")

    event_payload: dict[str, Any] = dict(event)
    generated_event_id = str(event_payload.get("event_id") or uuid4())
    event_payload["event_id"] = generated_event_id
    event_payload["service"] = event_payload.get("service") or service_name
    event_payload["created_at"] = event_payload.get("created_at") or datetime.now(timezone.utc).isoformat()
    correlation_id = event_payload.get("correlation_id") or event_payload.get("txn_id") or generated_event_id
    event_payload["correlation_id"] = str(correlation_id)
    event_payload["causation_id"] = str(event_payload.get("causation_id") or generated_event_id)
    traceparent = event_payload.get("traceparent")
    if traceparent is not None:
        event_payload["traceparent"] = str(traceparent)

    client = Redis.from_url(redis_url, decode_responses=True)
    try:
        payload = json.dumps(event_payload)
        _ = client.execute_command("XADD", "genesis:domain-events", "*", "event", payload)
        _ = append_signed_audit_entry(event_payload)
        return True
    except Exception:
        return False
    finally:
        client.close()


def list_domain_events(limit: int = 200, txn_id: str | None = None) -> list[dict[str, Any]]:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:16379/0")
    client = Redis.from_url(redis_url, decode_responses=True)
    try:
        rows = client.execute_command("XREVRANGE", "genesis:domain-events", "+", "-", "COUNT", limit)
    except Exception:
        return []
    finally:
        client.close()

    events: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            continue
        stream_id = row[0]
        payload_map = row[1] if isinstance(row[1], dict) else {}
        raw_event = payload_map.get("event")
        if not isinstance(raw_event, str):
            continue

        try:
            event_obj = json.loads(raw_event)
        except Exception:
            continue

        if not isinstance(event_obj, dict):
            continue

        if txn_id and event_obj.get("txn_id") != txn_id and event_obj.get("original_txn_id") != txn_id:
            continue

        created_at = None
        if isinstance(stream_id, str) and "-" in stream_id:
            millis_part = stream_id.split("-", 1)[0]
            if millis_part.isdigit():
                created_at = datetime.fromtimestamp(int(millis_part) / 1000, tz=timezone.utc).isoformat()

        payload_value = event_obj.get("payload")
        if not isinstance(payload_value, dict):
            payload_value = None

        item = {
            "stream_id": stream_id,
            "event_id": event_obj.get("event_id"),
            "event_type": event_obj.get("event_type"),
            "txn_id": event_obj.get("txn_id") or event_obj.get("original_txn_id"),
            "correlation_id": event_obj.get("correlation_id"),
            "causation_id": event_obj.get("causation_id"),
            "traceparent": event_obj.get("traceparent"),
            "actor": event_obj.get("actor"),
            "service": event_obj.get("service") or "unknown",
            "created_at": event_obj.get("created_at") or created_at,
            "payload": payload_value,
        }
        events.append(item)

    return events


def domain_event_stream_length() -> int:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:16379/0")
    client = Redis.from_url(redis_url, decode_responses=True)
    try:
        size = client.execute_command("XLEN", "genesis:domain-events")
        if isinstance(size, int):
            return size
        if isinstance(size, str) and size.isdigit():
            return int(size)
        return 0
    except Exception:
        return 0
    finally:
        client.close()
