from __future__ import annotations

import json
from pathlib import Path

from backend.security.audit_signing import append_signed_audit_entry
from backend.security.audit_signing import verify_signed_audit_ledger


def test_signed_audit_ledger_verifies_and_detects_tamper(monkeypatch, tmp_path):
    ledger_path = tmp_path / "signed_ledger.ndjson"
    monkeypatch.setenv("AUDIT_LEDGER_PATH", str(ledger_path))
    monkeypatch.setenv("AUDIT_SIGNING_SECRET", "ledger-secret")

    first = append_signed_audit_entry(
        {
            "event_type": "ActionDispatched",
            "correlation_id": "txn-1",
            "actor": "designer",
            "service": "command-api",
        }
    )
    second = append_signed_audit_entry(
        {
            "event_type": "TransactionReverted",
            "correlation_id": "txn-1",
            "actor": "designer",
            "service": "command-api",
        }
    )

    assert first["entry_id"].startswith("audit-")
    assert second["entry_id"].startswith("audit-")

    healthy = verify_signed_audit_ledger()
    assert healthy["valid"] is True
    assert healthy["entries"] == 2

    rows = ledger_path.read_text(encoding="utf-8").strip().splitlines()
    tampered = json.loads(rows[1])
    tampered["payload"]["event_type"] = "TamperedEvent"
    rows[1] = json.dumps(tampered, separators=(",", ":"), sort_keys=True)
    ledger_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    broken = verify_signed_audit_ledger()
    assert broken["valid"] is False
    assert broken["broken_at"] == 1
    assert broken["reason"] in {"payload hash mismatch", "signature mismatch", "chain hash mismatch"}


def test_audit_verify_endpoint(monkeypatch, tmp_path):
    create_app = __import__("backend.app", fromlist=["create_app"]).create_app
    ledger_path = tmp_path / "audit" / "signed_ledger.ndjson"
    monkeypatch.setenv("AUDIT_LEDGER_PATH", str(ledger_path))
    monkeypatch.setenv("AUDIT_SIGNING_SECRET", "endpoint-secret")

    _ = append_signed_audit_entry(
        {
            "event_type": "ProjectionCreated",
            "correlation_id": "proj-1",
            "actor": "designer",
            "service": "command-api",
        }
    )

    app = create_app()
    client = app.test_client()

    response = client.get("/api/query/audit/verify")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["valid"] is True
    assert payload["entries"] == 1

    entries_response = client.get("/api/query/audit/entries")
    assert entries_response.status_code == 200
    rows = entries_response.get_json()
    assert len(rows) == 1
    assert Path(ledger_path).exists()
