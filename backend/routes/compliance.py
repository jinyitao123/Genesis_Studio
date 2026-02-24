from __future__ import annotations

from flask import Blueprint
from flask import current_app
from flask import jsonify

from ..ontology.deps import create_repository
from ..observability import record_http_request
from ..security.flask_auth import current_user_from_request


compliance_bp = Blueprint("compliance", __name__, url_prefix="/api/compliance")
_processing_records: list[dict[str, str]] = []


@compliance_bp.get("/records")
def list_processing_records():
    try:
        _ = current_user_from_request()
    except Exception:
        return jsonify({"detail": "missing or invalid authorization"}), 401

    settings = current_app.config["SETTINGS"]
    repo = create_repository(settings)
    try:
        if hasattr(repo, "list_compliance_records"):
            rows = repo.list_compliance_records(limit=200)
        else:
            rows = _processing_records[-200:]
    finally:
        repo.close()

    record_http_request("/api/compliance/records", 200)
    return jsonify(rows)
