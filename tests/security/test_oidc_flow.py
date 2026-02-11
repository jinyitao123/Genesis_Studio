from __future__ import annotations

from importlib import import_module
from urllib.parse import parse_qs
from urllib.parse import urlparse

from fastapi.testclient import TestClient


def test_oidc_callback_exchange_and_local_token_issue(monkeypatch):
    command_module = import_module("backend.command_app")
    client = TestClient(command_module.command_app)

    monkeypatch.setenv("OIDC_ISSUER_URL", "https://issuer.example.com")
    monkeypatch.setenv("OIDC_CLIENT_ID", "genesis-client")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "genesis-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "http://localhost:18080/callback")

    monkeypatch.setattr(
        command_module,
        "_oidc_exchange_code",
        lambda settings, code, code_verifier: {
            "access_token": f"idp-token-{code}",
            "id_token_claims": {
                "sub": "oidc-designer",
                "nonce": "from-authorize",
                "iss": settings.oidc_issuer_url,
            },
            "code_verifier_echo": code_verifier,
        },
    )
    monkeypatch.setattr(
        command_module,
        "_oidc_fetch_userinfo",
        lambda settings, access_token: {"sub": "oidc-designer", "role": "Designer", "token": access_token},
    )

    authorize = client.get("/api/auth/authorize")
    assert authorize.status_code == 200
    payload = authorize.json()
    state = payload["state"]
    query = parse_qs(urlparse(payload["authorize_url"]).query)
    assert query["code_challenge_method"] == ["S256"]
    assert isinstance(query["code_challenge"][0], str) and query["code_challenge"][0]
    assert isinstance(query["nonce"][0], str) and query["nonce"][0]

    original_exchange = command_module._oidc_exchange_code

    def patched_exchange(settings, code, code_verifier):
        base = original_exchange(settings, code, code_verifier)
        base["id_token_claims"]["nonce"] = query["nonce"][0]
        return base

    monkeypatch.setattr(command_module, "_oidc_exchange_code", patched_exchange)

    callback = client.post(
        "/api/auth/callback",
        json={"code": "auth-code-1", "state": state},
    )
    assert callback.status_code == 200
    payload = callback.json()
    assert payload["status"] == "authenticated"
    assert payload["token_type"] == "bearer"
    assert payload["role"] == "Designer"
    assert isinstance(payload["access_token"], str) and payload["access_token"]
    assert isinstance(payload["refresh_token"], str) and payload["refresh_token"]

    refresh = client.post("/api/auth/refresh", json={"refresh_token": payload["refresh_token"]})
    assert refresh.status_code == 200


def test_oidc_callback_rejects_invalid_state(monkeypatch):
    command_module = import_module("backend.command_app")
    client = TestClient(command_module.command_app)

    monkeypatch.setenv("OIDC_ISSUER_URL", "https://issuer.example.com")
    monkeypatch.setenv("OIDC_CLIENT_ID", "genesis-client")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "genesis-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "http://localhost:18080/callback")

    callback = client.post(
        "/api/auth/callback",
        json={"code": "auth-code-2", "state": "invalid-state"},
    )
    assert callback.status_code == 400
    assert "invalid oidc state" in callback.json()["detail"]


def test_oidc_callback_rejects_invalid_issuer(monkeypatch):
    command_module = import_module("backend.command_app")
    client = TestClient(command_module.command_app)

    monkeypatch.setenv("OIDC_ISSUER_URL", "https://issuer.example.com")
    monkeypatch.setenv("OIDC_CLIENT_ID", "genesis-client")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "genesis-secret")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "http://localhost:18080/callback")

    authorize = client.get("/api/auth/authorize")
    state = authorize.json()["state"]

    callback = client.post(
        "/api/auth/callback",
        json={"code": "auth-code-3", "state": state, "iss": "https://malicious-issuer.example.com"},
    )
    assert callback.status_code == 400
    assert "invalid oidc issuer" in callback.json()["detail"]
