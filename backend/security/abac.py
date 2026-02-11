from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path


_DEFAULT_POLICY = {
    "read": {
        "object_type": {
            "Admin": ["type_uri", "display_name", "parent_type", "tags", "created_at"],
            "Designer": ["type_uri", "display_name", "parent_type", "tags", "created_at"],
            "Operator": ["type_uri", "display_name", "tags", "created_at"],
            "Viewer": ["type_uri", "display_name", "created_at"],
        },
        "event": {
            "Admin": ["event_id", "action_id", "source_id", "target_id", "payload", "created_at"],
            "Designer": ["event_id", "action_id", "source_id", "target_id", "payload", "created_at"],
            "Operator": ["event_id", "action_id", "source_id", "target_id", "created_at"],
            "Viewer": ["event_id", "action_id", "created_at"],
        },
        "transaction": {
            "Admin": [
                "txn_id",
                "action_id",
                "actor",
                "status",
                "event_id",
                "compensation_event_id",
                "gates",
                "created_at",
                "reverted_at",
            ],
            "Designer": [
                "txn_id",
                "action_id",
                "actor",
                "status",
                "event_id",
                "compensation_event_id",
                "gates",
                "created_at",
                "reverted_at",
            ],
            "Operator": [
                "txn_id",
                "action_id",
                "status",
                "event_id",
                "compensation_event_id",
                "created_at",
                "reverted_at",
            ],
            "Viewer": ["txn_id", "action_id", "status", "created_at", "reverted_at"],
        },
        "bus_event": {
            "Admin": [
                "stream_id",
                "event_id",
                "event_type",
                "txn_id",
                "correlation_id",
                "causation_id",
                "traceparent",
                "actor",
                "service",
                "created_at",
                "payload",
            ],
            "Designer": [
                "stream_id",
                "event_id",
                "event_type",
                "txn_id",
                "correlation_id",
                "causation_id",
                "traceparent",
                "actor",
                "service",
                "created_at",
                "payload",
            ],
            "Operator": [
                "stream_id",
                "event_id",
                "event_type",
                "txn_id",
                "correlation_id",
                "causation_id",
                "service",
                "created_at",
            ],
            "Viewer": ["event_type", "txn_id", "correlation_id", "service", "created_at"],
        },
    },
    "write": {
        "object_type": {
            "Admin": ["type_uri", "display_name", "parent_type", "tags"],
            "Designer": ["type_uri", "display_name", "parent_type", "tags"],
            "Operator": ["type_uri", "display_name", "tags"],
            "Viewer": [],
        }
    },
}


def _policy_path() -> Path:
    configured = os.getenv("ABAC_POLICY_FILE")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().with_name("abac_policy.json")


def _load_policy() -> dict[str, dict[str, dict[str, set[str]]]]:
    source = _DEFAULT_POLICY
    path = _policy_path()
    if path.exists():
        try:
            source = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            source = _DEFAULT_POLICY

    read_raw = source.get("read", {})
    write_raw = source.get("write", {})

    read_policy: dict[str, dict[str, set[str]]] = {}
    for resource, roles in read_raw.items():
        read_policy[resource] = {role: set(fields) for role, fields in roles.items()}

    write_policy: dict[str, dict[str, set[str]]] = {}
    for resource, roles in write_raw.items():
        write_policy[resource] = {role: set(fields) for role, fields in roles.items()}

    return {"read": read_policy, "write": write_policy}


_POLICY = _load_policy()


@dataclass(frozen=True)
class AbacDecision:
    allowed: bool
    denied_fields: list[str]


_READ_FIELD_POLICY = _POLICY["read"]
_WRITE_FIELD_POLICY = _POLICY["write"]


def check_write_fields(role: str, resource: str, input_fields: set[str]) -> AbacDecision:
    allowed_fields = _WRITE_FIELD_POLICY.get(resource, {}).get(role, set())
    denied = sorted(input_fields - allowed_fields)
    return AbacDecision(allowed=len(denied) == 0, denied_fields=denied)


def filter_read_fields(role: str, resource: str, row: dict[str, object]) -> dict[str, object]:
    allowed_fields = _READ_FIELD_POLICY.get(resource, {}).get(role, set())
    if not allowed_fields:
        return {}
    return {key: value for key, value in row.items() if key in allowed_fields}
