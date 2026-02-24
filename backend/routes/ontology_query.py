from __future__ import annotations

import json

from flask import Blueprint
from flask import Response
from flask import current_app, jsonify
from flask import request
from flask import stream_with_context

from ..async_bus import domain_event_stream_length
from ..async_bus import list_domain_events
from ..ontology.deps import create_repository
from ..observability import record_http_request
from ..security.audit_signing import list_signed_audit_entries
from ..security.audit_signing import verify_signed_audit_ledger
from ..security.abac import filter_read_fields
from ..security.flask_auth import current_user_from_request
from ..workers.tasks import projection_task_metrics

ontology_query_bp = Blueprint("ontology_query", __name__, url_prefix="/api")


def _notification_feed_events(limit: int = 100) -> list[dict[str, object]]:
    notification_types = {
        "NotificationQueued",
        "ActionDispatched",
        "TransactionReverted",
        "ProposalStateChanged",
    }
    rows = list_domain_events(limit=limit)
    payload: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        event_type = str(row.get("event_type") or "")
        if event_type in notification_types:
            payload.append(row)
    return payload


def _filter_transaction_lineage(role: str, lineage_payload: dict[str, object]) -> dict[str, object]:
    transaction_raw = lineage_payload.get("transaction")
    primary_event_raw = lineage_payload.get("primary_event")
    compensation_event_raw = lineage_payload.get("compensation_event")

    transaction = (
        filter_read_fields(role, "transaction", transaction_raw)
        if isinstance(transaction_raw, dict)
        else None
    )
    primary_event = (
        filter_read_fields(role, "event", primary_event_raw)
        if isinstance(primary_event_raw, dict)
        else None
    )
    compensation_event = (
        filter_read_fields(role, "event", compensation_event_raw)
        if isinstance(compensation_event_raw, dict)
        else None
    )

    return {
        "transaction": transaction,
        "primary_event": primary_event,
        "compensation_event": compensation_event,
    }


@ontology_query_bp.get("/query/object-types")
def list_object_types():
    settings = current_app.config["SETTINGS"]
    repo = create_repository(settings)
    try:
        object_types = repo.list_object_types()
        response = jsonify([item.model_dump(mode="json") for item in object_types])
        record_http_request("/api/query/object-types", 200)
        return response
    finally:
        repo.close()


@ontology_query_bp.get("/query/events")
def list_events():
    settings = current_app.config["SETTINGS"]
    repo = create_repository(settings)
    try:
        events = repo.list_events()
        response = jsonify([item.model_dump(mode="json") for item in events])
        record_http_request("/api/query/events", 200)
        return response
    finally:
        repo.close()


@ontology_query_bp.get("/query/graph")
def graph_snapshot():
    settings = current_app.config["SETTINGS"]
    repo = create_repository(settings)
    try:
        nodes: list[dict[str, str]] = []
        edges: list[dict[str, str]] = []
        if hasattr(repo, "list_graph_nodes") and hasattr(repo, "list_graph_edges"):
            nodes = repo.list_graph_nodes()
            edges = repo.list_graph_edges()

        if not nodes and not edges:
            object_types = repo.list_object_types()
            events = repo.list_events()
            nodes = [{"node_id": item.type_uri, "label": item.display_name} for item in object_types]
            edges = [
                {
                    "edge_id": row.event_id,
                    "source_id": str(row.source_id),
                    "target_id": str(row.target_id),
                    "label": row.action_id,
                }
                for row in events
                if row.source_id and row.target_id
            ]
        response = jsonify({"nodes": nodes, "edges": edges})
        record_http_request("/api/query/graph", 200)
        return response
    finally:
        repo.close()


@ontology_query_bp.get("/query/projections/latest")
def latest_projection():
    settings = current_app.config["SETTINGS"]
    repo = create_repository(settings)
    try:
        projection = repo.latest_projection_snapshot()
        if projection is None:
            response = jsonify({})
            record_http_request("/api/query/projections/latest", 200)
            return response
        response = jsonify(projection.model_dump(mode="json"))
        record_http_request("/api/query/projections/latest", 200)
        return response
    finally:
        repo.close()


@ontology_query_bp.get("/query/projections/lag")
def projection_lag():
    settings = current_app.config["SETTINGS"]
    repo = create_repository(settings)
    try:
        projection = repo.latest_projection_snapshot()
        projected_event_count = int(projection.event_count) if projection else 0
        stream_event_count = int(domain_event_stream_length())
        lag = max(stream_event_count - projected_event_count, 0)
        response = jsonify(
            {
                "projection_id": projection.projection_id if projection else None,
                "stream_event_count": stream_event_count,
                "projected_event_count": projected_event_count,
                "lag": lag,
            }
        )
        record_http_request("/api/query/projections/lag", 200)
        return response
    finally:
        repo.close()


@ontology_query_bp.get("/query/projections/replay/tasks")
def projection_replay_tasks():
    payload = projection_task_metrics()
    record_http_request("/api/query/projections/replay/tasks", 200)
    return jsonify(payload)


@ontology_query_bp.get("/query/transactions")
def list_transactions():
    settings = current_app.config["SETTINGS"]
    repo = create_repository(settings)
    try:
        rows = repo.list_dispatch_transactions()
        response = jsonify([item.model_dump(mode="json") for item in rows])
        record_http_request("/api/query/transactions", 200)
        return response
    finally:
        repo.close()


@ontology_query_bp.get("/query/transactions/lineage/<txn_id>")
def transaction_lineage(txn_id: str):
    settings = current_app.config["SETTINGS"]
    repo = create_repository(settings)
    try:
        lineage = repo.get_transaction_lineage(txn_id)
        if lineage is None:
            response = jsonify({"detail": "transaction not found"})
            record_http_request("/api/query/transactions/lineage", 404)
            return response, 404
        response = jsonify(lineage.model_dump(mode="json"))
        record_http_request("/api/query/transactions/lineage", 200)
        return response
    finally:
        repo.close()


@ontology_query_bp.get("/query/transactions/lineage/<txn_id>/aggregate")
def transaction_lineage_aggregate(txn_id: str):
    settings = current_app.config["SETTINGS"]
    repo = create_repository(settings)
    try:
        lineage = repo.get_transaction_lineage(txn_id)
        if lineage is None:
            response = jsonify({"detail": "transaction not found"})
            record_http_request("/api/query/transactions/lineage/aggregate", 404)
            return response, 404

        payload = {
            "lineage": lineage.model_dump(mode="json"),
            "bus_events": list_domain_events(txn_id=txn_id),
        }
        response = jsonify(payload)
        record_http_request("/api/query/transactions/lineage/aggregate", 200)
        return response
    finally:
        repo.close()


@ontology_query_bp.get("/query/object-types/secure")
def list_object_types_secure():
    try:
        user = current_user_from_request()
    except Exception:
        return jsonify({"detail": "missing or invalid authorization"}), 401

    settings = current_app.config["SETTINGS"]
    repo = create_repository(settings)
    try:
        rows = repo.list_object_types()
        payload = [filter_read_fields(user.role, "object_type", row.model_dump(mode="json")) for row in rows]
        response = jsonify(payload)
        record_http_request("/api/query/object-types/secure", 200)
        return response
    finally:
        repo.close()


@ontology_query_bp.get("/query/events/secure")
def list_events_secure():
    try:
        user = current_user_from_request()
    except Exception:
        return jsonify({"detail": "missing or invalid authorization"}), 401

    settings = current_app.config["SETTINGS"]
    repo = create_repository(settings)
    try:
        rows = repo.list_events()
        payload = [filter_read_fields(user.role, "event", row.model_dump(mode="json")) for row in rows]
        response = jsonify(payload)
        record_http_request("/api/query/events/secure", 200)
        return response
    finally:
        repo.close()


@ontology_query_bp.get("/query/transactions/secure")
def list_transactions_secure():
    try:
        user = current_user_from_request()
    except Exception:
        return jsonify({"detail": "missing or invalid authorization"}), 401

    settings = current_app.config["SETTINGS"]
    repo = create_repository(settings)
    try:
        rows = repo.list_dispatch_transactions()
        payload = [filter_read_fields(user.role, "transaction", row.model_dump(mode="json")) for row in rows]
        response = jsonify(payload)
        record_http_request("/api/query/transactions/secure", 200)
        return response
    finally:
        repo.close()


@ontology_query_bp.get("/query/transactions/lineage/<txn_id>/secure")
def transaction_lineage_secure(txn_id: str):
    try:
        user = current_user_from_request()
    except Exception:
        return jsonify({"detail": "missing or invalid authorization"}), 401

    settings = current_app.config["SETTINGS"]
    repo = create_repository(settings)
    try:
        lineage = repo.get_transaction_lineage(txn_id)
        if lineage is None:
            response = jsonify({"detail": "transaction not found"})
            record_http_request("/api/query/transactions/lineage/secure", 404)
            return response, 404
        filtered = _filter_transaction_lineage(user.role, lineage.model_dump(mode="json"))
        response = jsonify(filtered)
        record_http_request("/api/query/transactions/lineage/secure", 200)
        return response
    finally:
        repo.close()


@ontology_query_bp.get("/query/transactions/lineage/<txn_id>/aggregate/secure")
def transaction_lineage_aggregate_secure(txn_id: str):
    try:
        user = current_user_from_request()
    except Exception:
        return jsonify({"detail": "missing or invalid authorization"}), 401

    settings = current_app.config["SETTINGS"]
    repo = create_repository(settings)
    try:
        lineage = repo.get_transaction_lineage(txn_id)
        if lineage is None:
            response = jsonify({"detail": "transaction not found"})
            record_http_request("/api/query/transactions/lineage/aggregate/secure", 404)
            return response, 404

        lineage_payload = _filter_transaction_lineage(user.role, lineage.model_dump(mode="json"))
        bus_payload = [filter_read_fields(user.role, "bus_event", event) for event in list_domain_events(txn_id=txn_id)]
        response = jsonify({"lineage": lineage_payload, "bus_events": bus_payload})
        record_http_request("/api/query/transactions/lineage/aggregate/secure", 200)
        return response
    finally:
        repo.close()


@ontology_query_bp.get("/query/audit/verify")
def verify_audit_ledger():
    payload = verify_signed_audit_ledger()
    record_http_request("/api/query/audit/verify", 200)
    return jsonify(payload)


@ontology_query_bp.get("/query/audit/entries")
def list_audit_entries():
    payload = list_signed_audit_entries(limit=200)
    record_http_request("/api/query/audit/entries", 200)
    return jsonify(payload)


@ontology_query_bp.get("/query/notifications")
def list_notifications():
    limit = int(request.args.get("limit", "100"))
    payload = _notification_feed_events(limit=max(1, min(limit, 500)))
    record_http_request("/api/query/notifications", 200)
    return jsonify(payload)


@ontology_query_bp.get("/query/notifications/secure")
def list_notifications_secure():
    try:
        user = current_user_from_request()
    except Exception:
        return jsonify({"detail": "missing or invalid authorization"}), 401

    limit = int(request.args.get("limit", "100"))
    rows = _notification_feed_events(limit=max(1, min(limit, 500)))
    payload = [filter_read_fields(user.role, "bus_event", item) for item in rows]
    record_http_request("/api/query/notifications/secure", 200)
    return jsonify(payload)


@ontology_query_bp.get("/query/notifications/stream/secure")
def list_notifications_stream_secure():
    try:
        user = current_user_from_request()
    except Exception:
        return jsonify({"detail": "missing or invalid authorization"}), 401

    rows = _notification_feed_events(limit=50)
    payload = [filter_read_fields(user.role, "bus_event", item) for item in rows]

    def _events():
        yield "event: notifications\n"
        yield f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"

    record_http_request("/api/query/notifications/stream/secure", 200)
    return Response(stream_with_context(_events()), mimetype="text/event-stream")
