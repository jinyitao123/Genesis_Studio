from __future__ import annotations

from datetime import datetime
from datetime import timezone

from flask import Blueprint
from flask import jsonify
from flask import request

from ..observability import record_http_request
from ..security.audit_signing import append_signed_audit_entry
from ..security.flask_auth import current_user_from_request


compliance_bp = Blueprint("compliance", __name__, url_prefix="/api/compliance")
_processing_records: list[dict[str, str]] = []


def _require_compliance_actor_role(role: str) -> bool:
    return role in {"Admin", "Designer"}


def _append_record(action: str, subject_id: str, actor: str) -> dict[str, str]:
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "action": action,
        "subject_id": subject_id,
        "actor": actor,
        "recorded_at": now,
    }
    _processing_records.append(record)
    return record


@compliance_bp.post("/export")
def export_subject_data():
    try:
        user = current_user_from_request()
    except Exception:
        return jsonify({"detail": "missing or invalid authorization"}), 401

    if not _require_compliance_actor_role(user.role):
        record_http_request("/api/compliance/export", 403)
        return jsonify({"detail": "insufficient role"}), 403

    payload = request.get_json(silent=True) or {}
    subject_id = str(payload.get("subject_id") or "").strip()
    if not subject_id:
        record_http_request("/api/compliance/export", 400)
        return jsonify({"detail": "subject_id is required"}), 400

    record = _append_record("export", subject_id, user.username)
    _ = append_signed_audit_entry(
        {
            "event_type": "ComplianceExportRequested",
            "correlation_id": f"compliance-export:{subject_id}",
            "actor": user.username,
            "service": "query-api",
            "payload": record,
        }
    )
    record_http_request("/api/compliance/export", 200)
    return jsonify(
        {
            "status": "accepted",
            "subject_id": subject_id,
            "record": record,
            "request_id": f"compliance-export:{subject_id}",
        }
    )


@compliance_bp.post("/delete")
def delete_subject_data():
    try:
        user = current_user_from_request()
    except Exception:
        return jsonify({"detail": "missing or invalid authorization"}), 401

    if not _require_compliance_actor_role(user.role):
        record_http_request("/api/compliance/delete", 403)
        return jsonify({"detail": "insufficient role"}), 403

    payload = request.get_json(silent=True) or {}
    subject_id = str(payload.get("subject_id") or "").strip()
    if not subject_id:
        record_http_request("/api/compliance/delete", 400)
        return jsonify({"detail": "subject_id is required"}), 400

    record = _append_record("delete", subject_id, user.username)
    _ = append_signed_audit_entry(
        {
            "event_type": "ComplianceDeleteRequested",
            "correlation_id": f"compliance-delete:{subject_id}",
            "actor": user.username,
            "service": "query-api",
            "payload": record,
        }
    )
    record_http_request("/api/compliance/delete", 200)
    return jsonify(
        {
            "status": "accepted",
            "subject_id": subject_id,
            "record": record,
            "request_id": f"compliance-delete:{subject_id}",
        }
    )


@compliance_bp.get("/records")
def list_processing_records():
    try:
        _ = current_user_from_request()
    except Exception:
        return jsonify({"detail": "missing or invalid authorization"}), 401

    record_http_request("/api/compliance/records", 200)
    return jsonify(_processing_records[-200:])
