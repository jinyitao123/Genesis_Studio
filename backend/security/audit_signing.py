from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _ledger_path() -> Path:
    configured = os.getenv("AUDIT_LEDGER_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    default_root = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[2]))
    return default_root / "audit" / "signed_ledger.ndjson"


def _signing_secret() -> str:
    return os.getenv("AUDIT_SIGNING_SECRET") or os.getenv("AUTH_JWT_SECRET") or os.getenv("SECRET_KEY") or "dev-secret"


def _payload_digest(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _compute_signature(prev_hash: str, payload_hash: str, created_at: str, secret: str) -> str:
    message = f"{prev_hash}|{payload_hash}|{created_at}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _read_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    entries: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue
            if isinstance(item, dict):
                entries.append(item)
    return entries


def append_signed_audit_entry(payload: dict[str, Any]) -> dict[str, str]:
    path = _ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    entries = _read_entries(path)
    prev_hash = "GENESIS" if not entries else str(entries[-1].get("chain_hash") or "GENESIS")
    created_at = datetime.now(timezone.utc).isoformat()
    payload_hash = _payload_digest(payload)
    signature = _compute_signature(prev_hash, payload_hash, created_at, _signing_secret())
    chain_hash = hashlib.sha256(f"{prev_hash}|{payload_hash}|{signature}".encode("utf-8")).hexdigest()

    record = {
        "entry_id": f"audit-{uuid4().hex}",
        "created_at": created_at,
        "prev_hash": prev_hash,
        "payload_hash": payload_hash,
        "signature": signature,
        "chain_hash": chain_hash,
        "event_type": payload.get("event_type"),
        "correlation_id": payload.get("correlation_id"),
        "actor": payload.get("actor"),
        "service": payload.get("service"),
        "payload": payload,
    }

    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":"), sort_keys=True))
        handle.write("\n")

    return {
        "entry_id": str(record["entry_id"]),
        "chain_hash": str(chain_hash),
    }


def list_signed_audit_entries(limit: int = 200, event_prefix: str | None = None) -> list[dict[str, Any]]:
    path = _ledger_path()
    entries = _read_entries(path)
    if event_prefix:
        entries = [item for item in entries if str(item.get("event_type", "")).startswith(event_prefix)]
    if limit <= 0:
        return []
    return entries[-limit:]


def verify_signed_audit_ledger() -> dict[str, Any]:
    path = _ledger_path()
    entries = _read_entries(path)
    if not entries:
        return {
            "valid": True,
            "entries": 0,
            "reason": "ledger empty",
            "broken_at": None,
        }

    secret = _signing_secret()
    expected_prev = "GENESIS"
    for index, item in enumerate(entries):
        payload = item.get("payload")
        created_at = str(item.get("created_at") or "")
        prev_hash = str(item.get("prev_hash") or "")
        payload_hash = str(item.get("payload_hash") or "")
        signature = str(item.get("signature") or "")
        chain_hash = str(item.get("chain_hash") or "")

        if not isinstance(payload, dict):
            return {
                "valid": False,
                "entries": len(entries),
                "reason": "missing payload",
                "broken_at": index,
            }

        if prev_hash != expected_prev:
            return {
                "valid": False,
                "entries": len(entries),
                "reason": "chain discontinuity",
                "broken_at": index,
            }

        computed_payload_hash = _payload_digest(payload)
        if computed_payload_hash != payload_hash:
            return {
                "valid": False,
                "entries": len(entries),
                "reason": "payload hash mismatch",
                "broken_at": index,
            }

        computed_signature = _compute_signature(prev_hash, payload_hash, created_at, secret)
        if not hmac.compare_digest(computed_signature, signature):
            return {
                "valid": False,
                "entries": len(entries),
                "reason": "signature mismatch",
                "broken_at": index,
            }

        computed_chain = hashlib.sha256(f"{prev_hash}|{payload_hash}|{signature}".encode("utf-8")).hexdigest()
        if computed_chain != chain_hash:
            return {
                "valid": False,
                "entries": len(entries),
                "reason": "chain hash mismatch",
                "broken_at": index,
            }

        expected_prev = chain_hash

    return {
        "valid": True,
        "entries": len(entries),
        "reason": "ok",
        "broken_at": None,
    }


def sign_audit_entry(entry: dict[str, Any]) -> dict[str, Any]:
    payload_hash = _payload_digest(entry)
    signature = hmac.new(_signing_secret().encode("utf-8"), payload_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    signed = dict(entry)
    signed["signature"] = signature
    signed["payload_hash"] = payload_hash
    return signed


def verify_audit_entry(entry: dict[str, Any]) -> bool:
    payload_hash = entry.get("payload_hash")
    signature = entry.get("signature")
    if not isinstance(payload_hash, str) or not isinstance(signature, str):
        return False

    payload = {key: value for key, value in entry.items() if key not in {"signature", "payload_hash"}}
    computed_hash = _payload_digest(payload)
    if computed_hash != payload_hash:
        return False

    expected = hmac.new(_signing_secret().encode("utf-8"), payload_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
