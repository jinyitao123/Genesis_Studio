from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from uuid import uuid4

from ..config import Settings


@dataclass(frozen=True)
class AuthUser:
    username: str
    role: str


_USERS: dict[str, tuple[str, str]] = {
    "admin": ("admin", "Admin"),
    "designer": ("designer", "Designer"),
    "operator": ("operator", "Operator"),
    "viewer": ("viewer", "Viewer"),
}


_REFRESH_TOKENS: dict[str, int] = {}


def authenticate_user(username: str, password: str) -> AuthUser | None:
    user = _USERS.get(username)
    if user is None:
        return None
    expected_password, role = user
    if password != expected_password:
        return None
    return AuthUser(username=username, role=role)


def _encode_token(payload: dict[str, Any], secret: str) -> str:
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_encoded = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")
    signature = hmac.new(
        secret.encode("utf-8"),
        payload_encoded.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_encoded}.{signature}"


def _decode_token_payload(token: str, secret: str) -> dict[str, Any]:
    try:
        payload_encoded, signature = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("invalid token format") from exc

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        payload_encoded.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("token signature mismatch")

    padding = "=" * (-len(payload_encoded) % 4)
    payload_json = base64.urlsafe_b64decode((payload_encoded + padding).encode("utf-8"))
    payload = json.loads(payload_json.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("invalid token payload")
    return payload


def create_access_token(user: AuthUser, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "typ": "access",
        "sub": user.username,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.auth_access_token_minutes)).timestamp()),
    }
    return _encode_token(payload, settings.auth_jwt_secret)


def create_refresh_token(user: AuthUser, settings: Settings) -> str:
    now = datetime.now(timezone.utc)
    exp = int((now + timedelta(minutes=settings.auth_refresh_token_minutes)).timestamp())
    payload = {
        "typ": "refresh",
        "sub": user.username,
        "role": user.role,
        "jti": uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": exp,
    }
    token = _encode_token(payload, settings.auth_jwt_secret)
    _REFRESH_TOKENS[token] = exp
    return token


def rotate_refresh_token(token: str, settings: Settings) -> tuple[AuthUser, str]:
    user = decode_refresh_token(token, settings)
    _ = _REFRESH_TOKENS.pop(token, None)
    new_token = create_refresh_token(user, settings)
    return user, new_token


def revoke_refresh_token(token: str) -> None:
    _ = _REFRESH_TOKENS.pop(token, None)


def decode_access_token(token: str, settings: Settings) -> AuthUser:
    payload = _decode_token_payload(token, settings.auth_jwt_secret)

    token_type = str(payload.get("typ", ""))
    if token_type != "access":
        raise ValueError("invalid access token type")

    exp = int(payload.get("exp", 0))
    if exp <= int(datetime.now(timezone.utc).timestamp()):
        raise ValueError("token expired")

    username = str(payload.get("sub", ""))
    role = str(payload.get("role", ""))
    if not username or not role:
        raise ValueError("invalid token payload")
    return AuthUser(username=username, role=role)


def decode_refresh_token(token: str, settings: Settings) -> AuthUser:
    payload = _decode_token_payload(token, settings.auth_jwt_secret)

    token_type = str(payload.get("typ", ""))
    if token_type != "refresh":
        raise ValueError("invalid refresh token type")

    if token not in _REFRESH_TOKENS:
        raise ValueError("refresh token revoked or unknown")

    exp = int(payload.get("exp", 0))
    if exp <= int(datetime.now(timezone.utc).timestamp()):
        _ = _REFRESH_TOKENS.pop(token, None)
        raise ValueError("refresh token expired")

    username = str(payload.get("sub", ""))
    role = str(payload.get("role", ""))
    if not username or not role:
        raise ValueError("invalid token payload")
    return AuthUser(username=username, role=role)
