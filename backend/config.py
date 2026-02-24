from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_FILE = BASE_DIR / ".env.example"


@dataclass(frozen=True)
class Settings:
    secret_key: str
    flask_env: str
    flask_debug: bool
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    vite_api_base_url: str
    cors_origins: list[str]
    project_root: str
    domains_dir: str
    command_api_port: int
    auth_jwt_secret: str
    auth_jwt_algorithm: str
    auth_access_token_minutes: int
    auth_refresh_token_minutes: int
    oidc_issuer_url: str
    oidc_client_id: str
    oidc_client_secret: str
    oidc_redirect_uri: str
    oidc_scope: str
    oidc_token_endpoint: str
    oidc_userinfo_endpoint: str
    search_backend_url: str
    timeseries_backend_url: str


def _to_bool(value: str, default: bool = False) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def load_settings() -> Settings:
    env_path = Path(os.getenv("ENV_FILE", str(DEFAULT_ENV_FILE))).expanduser().resolve()
    if env_path.exists():
        _ = load_dotenv(dotenv_path=env_path, override=False)

    cors = [item.strip() for item in os.getenv("CORS_ORIGINS", "").split(",") if item.strip()]
    return Settings(
        secret_key=os.getenv("SECRET_KEY", "dev-secret"),
        flask_env=os.getenv("FLASK_ENV", "development"),
        flask_debug=_to_bool(os.getenv("FLASK_DEBUG", "false"), default=False),
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "neo4j"),
        vite_api_base_url=os.getenv("VITE_API_BASE_URL", "http://localhost:5000/api"),
        cors_origins=cors,
        project_root=os.getenv("PROJECT_ROOT", str(BASE_DIR)),
        domains_dir=os.getenv("DOMAINS_DIR", "domains"),
        command_api_port=int(os.getenv("COMMAND_API_PORT", "8000")),
        auth_jwt_secret=os.getenv("AUTH_JWT_SECRET", "genesis-dev-jwt-secret"),
        auth_jwt_algorithm=os.getenv("AUTH_JWT_ALGORITHM", "HS256"),
        auth_access_token_minutes=int(os.getenv("AUTH_ACCESS_TOKEN_MINUTES", "30")),
        auth_refresh_token_minutes=int(os.getenv("AUTH_REFRESH_TOKEN_MINUTES", "10080")),
        oidc_issuer_url=os.getenv("OIDC_ISSUER_URL", ""),
        oidc_client_id=os.getenv("OIDC_CLIENT_ID", ""),
        oidc_client_secret=os.getenv("OIDC_CLIENT_SECRET", ""),
        oidc_redirect_uri=os.getenv("OIDC_REDIRECT_URI", ""),
        oidc_scope=os.getenv("OIDC_SCOPE", "openid profile email offline_access"),
        oidc_token_endpoint=os.getenv("OIDC_TOKEN_ENDPOINT", ""),
        oidc_userinfo_endpoint=os.getenv("OIDC_USERINFO_ENDPOINT", ""),
        search_backend_url=os.getenv("SEARCH_BACKEND_URL", ""),
        timeseries_backend_url=os.getenv("TIMESERIES_BACKEND_URL", ""),
    )
