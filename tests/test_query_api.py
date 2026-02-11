from __future__ import annotations

from datetime import datetime
from datetime import timezone
from importlib import import_module

flask_app = import_module("backend.app").create_app()
ActionEvent = import_module("backend.ontology.schemas").ActionEvent
ObjectTypeDTO = import_module("backend.ontology.schemas").ObjectTypeDTO
ProjectionSnapshot = import_module("backend.ontology.schemas").ProjectionSnapshot
DispatchTransactionRecord = import_module("backend.ontology.schemas").DispatchTransactionRecord
LogicGateResult = import_module("backend.ontology.schemas").LogicGateResult
TransactionLineage = import_module("backend.ontology.schemas").TransactionLineage
AuthUser = import_module("backend.security.auth").AuthUser
create_access_token = import_module("backend.security.auth").create_access_token
load_settings = import_module("backend.config").load_settings


class FakeQueryRepo:
    def close(self) -> None:
        return None

    def list_object_types(self):
        return [
            ObjectTypeDTO(
                type_uri="com.genesis.unit.Drone",
                display_name="Drone",
                parent_type="com.genesis.unit.AirUnit",
                tags=["air"],
                created_at=datetime.now(timezone.utc),
            )
        ]

    def list_events(self):
        return [
            ActionEvent(
                event_id="evt-1",
                action_id="ACT_SELF_DESTRUCT",
                source_id="entity-1",
                target_id="entity-2",
                payload={"damage": 50},
                created_at=datetime.now(timezone.utc),
            )
        ]

    def latest_projection_snapshot(self):
        return ProjectionSnapshot(
            projection_id="proj-1",
            object_type_count=1,
            event_count=1,
            created_at=datetime.now(timezone.utc),
        )

    def list_dispatch_transactions(self):
        return [
            DispatchTransactionRecord(
                txn_id="txn-1",
                action_id="ACT_SELF_DESTRUCT",
                actor="designer",
                status="committed",
                event_id="evt-1",
                compensation_event_id=None,
                gates=[LogicGateResult(tier="L0", passed=True, detail="ok")],
                created_at=datetime.now(timezone.utc),
                reverted_at=None,
            )
        ]

    def get_transaction_lineage(self, txn_id: str):
        if txn_id != "txn-1":
            return None
        primary = self.list_events()[0]
        return TransactionLineage(
            transaction=self.list_dispatch_transactions()[0],
            primary_event=primary,
            compensation_event=None,
        )


def test_query_endpoints(monkeypatch):
    fake_repo = FakeQueryRepo()

    def fake_create_repository(_settings):
        return fake_repo

    monkeypatch.setattr("backend.routes.ontology_query.create_repository", fake_create_repository)
    monkeypatch.setattr("backend.routes.ontology_query.domain_event_stream_length", lambda: 5)
    monkeypatch.setattr(
        "backend.routes.ontology_query.projection_task_metrics",
        lambda: {
            "refresh_runs": 2,
            "replay_runs": 1,
            "last_refresh_at": "2026-02-11T08:00:00+00:00",
            "last_replay_at": "2026-02-11T08:05:00+00:00",
            "last_replay": {
                "from_event_id": "evt-1",
                "correlation_id": "corr-1",
                "traceparent": None,
                "requested_by": "designer",
            },
        },
    )
    monkeypatch.setattr(
        "backend.routes.ontology_query.list_domain_events",
        lambda txn_id=None, limit=200: [
            {
                "stream_id": "1739250012000-0",
                "event_id": "evt-1",
                "event_type": "ActionDispatched",
                "txn_id": "txn-1",
                "correlation_id": "txn-1",
                "causation_id": "evt-1",
                "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                "actor": "designer",
                "service": "command-api",
                "created_at": "2026-02-11T05:00:12+00:00",
                "payload": {"k": "v"},
            }
        ],
    )

    client = flask_app.test_client()

    object_types_response = client.get("/api/query/object-types")
    assert object_types_response.status_code == 200
    assert len(object_types_response.get_json()) == 1

    events_response = client.get("/api/query/events")
    assert events_response.status_code == 200
    assert len(events_response.get_json()) == 1

    projection_response = client.get("/api/query/projections/latest")
    assert projection_response.status_code == 200
    assert projection_response.get_json()["projection_id"] == "proj-1"

    lag_response = client.get("/api/query/projections/lag")
    assert lag_response.status_code == 200
    lag_payload = lag_response.get_json()
    assert lag_payload["stream_event_count"] == 5
    assert lag_payload["projected_event_count"] == 1
    assert lag_payload["lag"] == 4

    replay_task_response = client.get("/api/query/projections/replay/tasks")
    assert replay_task_response.status_code == 200
    replay_task_payload = replay_task_response.get_json()
    assert replay_task_payload["refresh_runs"] == 2
    assert replay_task_payload["replay_runs"] == 1
    assert replay_task_payload["last_replay"]["correlation_id"] == "corr-1"

    transactions_response = client.get("/api/query/transactions")
    assert transactions_response.status_code == 200
    tx_list = transactions_response.get_json()
    assert len(tx_list) == 1
    assert tx_list[0]["txn_id"] == "txn-1"

    lineage_response = client.get("/api/query/transactions/lineage/txn-1")
    assert lineage_response.status_code == 200
    lineage = lineage_response.get_json()
    assert set(lineage.keys()) == {"transaction", "primary_event", "compensation_event"}
    assert lineage["transaction"]["txn_id"] == "txn-1"
    assert lineage["primary_event"]["event_id"] == "evt-1"

    not_found_lineage_response = client.get("/api/query/transactions/lineage/txn-404")
    assert not_found_lineage_response.status_code == 404

    aggregate_response = client.get("/api/query/transactions/lineage/txn-1/aggregate")
    assert aggregate_response.status_code == 200
    aggregate_payload = aggregate_response.get_json()
    assert set(aggregate_payload.keys()) == {"lineage", "bus_events"}
    assert aggregate_payload["lineage"]["transaction"]["txn_id"] == "txn-1"
    assert aggregate_payload["bus_events"][0]["event_type"] == "ActionDispatched"

    token = create_access_token(AuthUser(username="viewer", role="Viewer"), load_settings())
    secure_headers = {"Authorization": f"Bearer {token}"}

    secure_objects_response = client.get("/api/query/object-types/secure", headers=secure_headers)
    assert secure_objects_response.status_code == 200
    first_object = secure_objects_response.get_json()[0]
    assert "type_uri" in first_object
    assert "tags" not in first_object

    secure_events_response = client.get("/api/query/events/secure", headers=secure_headers)
    assert secure_events_response.status_code == 200
    first_event = secure_events_response.get_json()[0]
    assert "event_id" in first_event
    assert "payload" not in first_event

    secure_transactions_response = client.get("/api/query/transactions/secure", headers=secure_headers)
    assert secure_transactions_response.status_code == 200
    secure_tx = secure_transactions_response.get_json()[0]
    assert "txn_id" in secure_tx
    assert "actor" not in secure_tx
    assert "gates" not in secure_tx

    secure_lineage_response = client.get("/api/query/transactions/lineage/txn-1/secure", headers=secure_headers)
    assert secure_lineage_response.status_code == 200
    secure_lineage = secure_lineage_response.get_json()
    assert secure_lineage["transaction"]["txn_id"] == "txn-1"
    assert "actor" not in secure_lineage["transaction"]
    assert "payload" not in secure_lineage["primary_event"]

    secure_aggregate_response = client.get(
        "/api/query/transactions/lineage/txn-1/aggregate/secure",
        headers=secure_headers,
    )
    assert secure_aggregate_response.status_code == 200
    secure_aggregate = secure_aggregate_response.get_json()
    assert set(secure_aggregate.keys()) == {"lineage", "bus_events"}
    secure_bus_event = secure_aggregate["bus_events"][0]
    assert "event_type" in secure_bus_event
    assert "txn_id" in secure_bus_event
    assert "correlation_id" in secure_bus_event
    assert "actor" not in secure_bus_event
    assert "payload" not in secure_bus_event

    unauthorized_secure_response = client.get("/api/query/transactions/secure")
    assert unauthorized_secure_response.status_code == 401
