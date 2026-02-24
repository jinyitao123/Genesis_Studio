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


@dataclass(frozen=True)
class ABACPolicy:
    read: dict[str, dict[str, set[str]]]
    write: dict[str, dict[str, set[str]]]


_READ_FIELD_POLICY = _POLICY["read"]
_WRITE_FIELD_POLICY = _POLICY["write"]


def check_write_fields(
    role_or_payload: str | dict[str, object] | None = None,
    resource_or_role: str | None = None,
    input_fields: set[str] | list[str] | None = None,
    *,
    role: str | None = None,
    resource: str | None = None,
) -> AbacDecision:
    if role is not None or resource is not None:
        resolved_role = role or ""
        resolved_resource = resource or ""
        field_set = set(input_fields or set())
        allowed_fields = _WRITE_FIELD_POLICY.get(resolved_resource, {}).get(resolved_role, set())
        denied = sorted(field_set - allowed_fields)
        return AbacDecision(allowed=len(denied) == 0, denied_fields=denied)

    if role_or_payload is None or resource_or_role is None:
        return AbacDecision(allowed=False, denied_fields=[])

    if isinstance(role_or_payload, dict):
        payload = role_or_payload
        resolved_role = resource_or_role
        allowed_fields = set(input_fields or set())
        denied = sorted(set(payload.keys()) - allowed_fields)
        role_allowed = resolved_role in {"Admin", "Designer", "Operator"}
        return AbacDecision(allowed=role_allowed and len(denied) == 0, denied_fields=denied)

    role = role_or_payload
    resource = resource_or_role
    field_set = set(input_fields or set())
    allowed_fields = _WRITE_FIELD_POLICY.get(resource, {}).get(role, set())
    denied = sorted(field_set - allowed_fields)
    return AbacDecision(allowed=len(denied) == 0, denied_fields=denied)


def filter_read_fields(
    role_or_row: str | dict[str, object] | None = None,
    resource_or_role: str | None = None,
    row: dict[str, object] | None = None,
    *,
    role: str | None = None,
    resource: str | None = None,
) -> dict[str, object]:
    if role is not None or resource is not None:
        if row is None:
            return {}
        resolved_role = role or ""
        resolved_resource = resource or ""
        allowed_fields = _READ_FIELD_POLICY.get(resolved_resource, {}).get(resolved_role, set())
        if not allowed_fields:
            return {}
        return {key: value for key, value in row.items() if key in allowed_fields}

    if role_or_row is None or resource_or_role is None:
        return {}

    if isinstance(role_or_row, dict):
        source = role_or_row
        role = resource_or_role
        allowed_fields = _READ_FIELD_POLICY.get("object_type", {}).get(role, set())
        if not allowed_fields:
            return {}
        return {key: value for key, value in source.items() if key in allowed_fields}

    role = role_or_row
    resource = resource_or_role
    if row is None:
        return {}
    allowed_fields = _READ_FIELD_POLICY.get(resource, {}).get(role, set())
    if not allowed_fields:
        return {}
    return {key: value for key, value in row.items() if key in allowed_fields}
