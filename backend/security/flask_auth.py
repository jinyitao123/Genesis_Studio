from __future__ import annotations

from flask import current_app
from flask import request

from .auth import AuthUser
from .auth import decode_access_token


def current_user_from_request() -> AuthUser:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise ValueError("missing bearer token")

    token = auth_header.removeprefix("Bearer ").strip()
    settings = current_app.config["SETTINGS"]
    return decode_access_token(token, settings)
