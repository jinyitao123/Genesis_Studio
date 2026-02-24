from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import cast

import pytest

from backend.config import load_settings
from backend.security.abac import check_write_fields
from backend.security.abac import filter_read_fields
from backend.security.auth import AuthUser
from backend.security.auth import authenticate_user
from backend.security.auth import create_access_token
from backend.security.auth import create_refresh_token
from backend.security.auth import decode_access_token
from backend.security.auth import decode_refresh_token
from backend.security.audit_signing import sign_audit_entry
from backend.security.audit_signing import verify_audit_entry


@pytest.fixture
def settings():
    return load_settings()


class TestJWTToken:
    @pytest.mark.unit
    def test_create_access_token_success(self, settings) -> None:
        user = AuthUser(username="test_user", role="Designer")
        token = create_access_token(user, settings)

        assert isinstance(token, str)
        assert token

    @pytest.mark.unit
    def test_create_refresh_token_success(self, settings) -> None:
        user = AuthUser(username="test_user", role="Viewer")
        token = create_refresh_token(user, settings)

        assert isinstance(token, str)
        assert token

    @pytest.mark.unit
    def test_decode_access_token_success(self, settings) -> None:
        user = AuthUser(username="test_user", role="Admin")
        token = create_access_token(user, settings)
        decoded = decode_access_token(token, settings)

        assert decoded.username == "test_user"
        assert decoded.role == "Admin"

    @pytest.mark.unit
    def test_decode_invalid_token(self, settings) -> None:
        with pytest.raises(ValueError):
            decode_access_token("invalid_token", settings)


class TestAuthFlow:
    @pytest.mark.unit
    def test_authenticate_user_success(self) -> None:
        user = authenticate_user("designer", "designer")
        assert user is not None
        assert user.role == "Designer"

    @pytest.mark.unit
    def test_refresh_token_decode_success(self, settings) -> None:
        user = AuthUser(username="viewer", role="Viewer")
        token = create_refresh_token(user, settings)
        decoded = decode_refresh_token(token, settings)

        assert decoded.username == "viewer"
        assert decoded.role == "Viewer"


class TestABAC:
    @pytest.mark.unit
    def test_filter_read_fields_with_role_resource(self) -> None:
        row = cast(
            dict[str, object],
            {
            "txn_id": "txn-1",
            "actor": "alice",
            "status": "done",
            "created_at": "2026-02-19T00:00:00Z",
            },
        )
        filtered = filter_read_fields("Viewer", "transaction", row)

        assert "txn_id" in filtered
        assert "status" in filtered
        assert "actor" not in filtered

    @pytest.mark.unit
    def test_filter_read_fields_compat_signature(self) -> None:
        row = cast(
            dict[str, object],
            {
            "type_uri": "com.genesis.test.Unit",
            "display_name": "Unit",
            "internal": "secret",
            },
        )
        filtered = filter_read_fields(row, "Viewer")

        assert "type_uri" in filtered
        assert "display_name" in filtered
        assert "internal" not in filtered

    @pytest.mark.unit
    def test_check_write_fields_decision(self) -> None:
        decision = check_write_fields("Designer", "object_type", {"type_uri", "display_name"})

        if isinstance(decision, bool):
            pytest.fail("expected AbacDecision")
        assert decision.allowed is True
        assert decision.denied_fields == []

    @pytest.mark.unit
    def test_check_write_fields_compat_signature(self) -> None:
        allowed = check_write_fields({"display_name": "Updated"}, "Designer", ["display_name", "tags"])
        denied = check_write_fields({"access_control": {"read": ["*"]}}, "Designer", ["display_name", "tags"])

        assert allowed.allowed is True
        assert denied.allowed is False


class TestAuditSigning:
    @pytest.mark.unit
    def test_sign_and_verify_audit_entry(self) -> None:
        entry = {
            "actor": "test_user",
            "action": "CREATE_ENTITY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": {"entity_id": "ent-1"},
        }

        signed = sign_audit_entry(entry)
        assert "signature" in signed
        assert verify_audit_entry(signed) is True

    @pytest.mark.unit
    def test_verify_tampered_entry_fails(self) -> None:
        entry = {
            "actor": "test_user",
            "action": "CREATE_ENTITY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": {"entity_id": "ent-1"},
        }

        signed = sign_audit_entry(entry)
        signed["detail"]["entity_id"] = "tampered"

        assert verify_audit_entry(signed) is False
