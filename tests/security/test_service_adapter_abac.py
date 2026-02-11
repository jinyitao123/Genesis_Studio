from __future__ import annotations

from importlib import import_module

from fastapi.testclient import TestClient


def _login_token(client: TestClient, username: str, password: str) -> str:
    response = client.post("/api/auth/token", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_service_adapter_role_matrix(monkeypatch):
    command_app = import_module("backend.command_app").command_app
    monkeypatch.setattr(
        "backend.command_app.ObjectService.upsert_object",
        lambda _self, object_id, object_type: {
            "service": "object-service",
            "object_id": object_id,
            "object_type": object_type,
            "status": "committed",
            "published": True,
        },
    )
    monkeypatch.setattr(
        "backend.command_app.SearchService.search",
        lambda _self, query: {
            "service": "search-service",
            "query": query,
            "hits": 1,
            "results": [{"kind": "object_type", "id": "com.genesis.unit.Drone", "label": "Drone"}],
        },
    )
    monkeypatch.setattr(
        "backend.command_app.AuthService.issue_service_token",
        lambda _self, subject, role: {
            "service": "auth-service",
            "subject": subject,
            "role": role,
            "access_token": "access-1",
            "refresh_token": "refresh-1",
            "status": "issued",
        },
    )
    monkeypatch.setattr(
        "backend.command_app.NotificationService.publish",
        lambda _self, channel, message: {
            "service": "notification-service",
            "channel": channel,
            "message": message,
            "status": "queued",
        },
    )
    monkeypatch.setattr("backend.command_app._record_service_adapter_audit", lambda **_kwargs: None)
    monkeypatch.setattr("backend.command_app.publish_domain_event", lambda _event: True)

    client = TestClient(command_app)

    viewer_token = _login_token(client, "viewer", "viewer")
    operator_token = _login_token(client, "operator", "operator")
    designer_token = _login_token(client, "designer", "designer")
    admin_token = _login_token(client, "admin", "admin")

    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
    operator_headers = {"Authorization": f"Bearer {operator_token}"}
    designer_headers = {"Authorization": f"Bearer {designer_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    viewer_upsert = client.post(
        "/api/command/services/object/upsert",
        json={"object_id": "entity-1", "object_type": "Drone"},
        headers=viewer_headers,
    )
    assert viewer_upsert.status_code == 403

    operator_upsert = client.post(
        "/api/command/services/object/upsert",
        json={"object_id": "entity-1", "object_type": "Drone"},
        headers=operator_headers,
    )
    assert operator_upsert.status_code == 200

    viewer_search = client.post(
        "/api/command/services/search",
        json={"query": "drone"},
        headers=viewer_headers,
    )
    assert viewer_search.status_code == 200

    designer_issue = client.post(
        "/api/command/services/auth/issue-token",
        json={"subject": "svc", "role": "Operator"},
        headers=designer_headers,
    )
    assert designer_issue.status_code == 403

    admin_issue = client.post(
        "/api/command/services/auth/issue-token",
        json={"subject": "svc", "role": "Operator"},
        headers=admin_headers,
    )
    assert admin_issue.status_code == 200

    viewer_notify = client.post(
        "/api/command/services/notification/publish",
        json={"channel": "ops.alerts", "message": "lag high"},
        headers=viewer_headers,
    )
    assert viewer_notify.status_code == 403
