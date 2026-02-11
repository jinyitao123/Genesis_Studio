from __future__ import annotations

from importlib import import_module


def test_compliance_export_delete_and_records(monkeypatch, tmp_path):
    create_app = import_module("backend.app").create_app
    AuthUser = import_module("backend.security.auth").AuthUser
    create_access_token = import_module("backend.security.auth").create_access_token
    load_settings = import_module("backend.config").load_settings

    ledger_path = tmp_path / "audit" / "signed_ledger.ndjson"
    monkeypatch.setenv("AUDIT_LEDGER_PATH", str(ledger_path))
    monkeypatch.setenv("AUDIT_SIGNING_SECRET", "compliance-secret")

    app = create_app()
    client = app.test_client()

    token = create_access_token(AuthUser(username="designer", role="Designer"), load_settings())
    headers = {"Authorization": f"Bearer {token}"}

    export_response = client.post("/api/compliance/export", json={"subject_id": "user-123"}, headers=headers)
    assert export_response.status_code == 200
    export_payload = export_response.get_json()
    assert export_payload["status"] == "accepted"
    assert export_payload["subject_id"] == "user-123"

    delete_response = client.post("/api/compliance/delete", json={"subject_id": "user-123"}, headers=headers)
    assert delete_response.status_code == 200
    delete_payload = delete_response.get_json()
    assert delete_payload["status"] == "accepted"
    assert delete_payload["subject_id"] == "user-123"

    records_response = client.get("/api/compliance/records", headers=headers)
    assert records_response.status_code == 200
    records = records_response.get_json()
    assert len(records) >= 2
    assert {"export", "delete"}.issubset({item["action"] for item in records})

    verify_response = client.get("/api/query/audit/verify")
    assert verify_response.status_code == 200
    verify_payload = verify_response.get_json()
    assert verify_payload["valid"] is True
    assert verify_payload["entries"] >= 2


def test_compliance_requires_authentication():
    create_app = import_module("backend.app").create_app
    app = create_app()
    client = app.test_client()

    response = client.post("/api/compliance/export", json={"subject_id": "user-123"})
    assert response.status_code == 401


def test_compliance_export_forbidden_for_viewer():
    create_app = import_module("backend.app").create_app
    AuthUser = import_module("backend.security.auth").AuthUser
    create_access_token = import_module("backend.security.auth").create_access_token
    load_settings = import_module("backend.config").load_settings

    app = create_app()
    client = app.test_client()

    token = create_access_token(AuthUser(username="viewer", role="Viewer"), load_settings())
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/compliance/export", json={"subject_id": "user-123"}, headers=headers)
    assert response.status_code == 403
