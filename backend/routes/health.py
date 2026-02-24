from __future__ import annotations

from flask import Blueprint
from flask import current_app, jsonify
from flask import Response

from ..middleware.docker_middleware import docker_status
from ..observability import metrics_snapshot
from ..observability import record_http_request

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.get("/health")
def healthcheck():
    settings = current_app.config["SETTINGS"]
    response = jsonify(
        {
            "status": "ok",
            "service": "genesis-studio",
            "environment": settings.flask_env,
        }
    )
    record_http_request("/api/health", 200)
    return response


@health_bp.get("/health/dependencies")
def dependency_healthcheck():
    settings = current_app.config["SETTINGS"]
    docker = docker_status()
    response = jsonify(
        {
            "docker": docker,
            "neo4j_uri": settings.neo4j_uri,
            "domains_dir": settings.domains_dir,
        }
    )
    record_http_request("/api/health/dependencies", 200)
    return response


@health_bp.get("/metrics")
def metrics_endpoint() -> Response:
    record_http_request("/api/metrics", 200)
    return Response(metrics_snapshot(), mimetype="text/plain")
