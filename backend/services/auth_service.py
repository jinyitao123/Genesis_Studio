from __future__ import annotations

from ..config import load_settings
from ..security.auth import AuthUser
from ..security.auth import create_access_token
from ..security.auth import create_refresh_token


class AuthService:
    service_name = "auth-service"

    def issue_service_token(self, subject: str, role: str) -> dict[str, str]:
        normalized_role = role.strip().capitalize()
        if normalized_role not in {"Admin", "Designer", "Operator", "Viewer"}:
            normalized_role = "Viewer"

        settings = load_settings()
        user = AuthUser(username=subject, role=normalized_role)

        access_token = create_access_token(user, settings)
        refresh_token = create_refresh_token(user, settings)

        return {
            "service": self.service_name,
            "subject": subject,
            "role": normalized_role,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "status": "issued",
        }
