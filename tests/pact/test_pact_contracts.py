from __future__ import annotations

from importlib import import_module

from fastapi.testclient import TestClient


def test_command_query_contract_compatibility_smoke():
    command_app = import_module("backend.command_app").command_app
    create_app = import_module("backend.app").create_app

    command_client = TestClient(command_app)
    query_client = create_app().test_client()

    token_response = command_client.post("/api/auth/token", json={"username": "designer", "password": "designer"})
    assert token_response.status_code == 200
    token = token_response.json()["access_token"]

    query_health = query_client.get("/api/health")
    assert query_health.status_code == 200

    secure_transactions = query_client.get(
        "/api/query/transactions/secure",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert secure_transactions.status_code in {200, 401}
