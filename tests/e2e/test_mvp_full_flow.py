from __future__ import annotations

from datetime import datetime
from datetime import timezone
from importlib import import_module

from fastapi.testclient import TestClient


def test_mvp_gateway_level_journey(monkeypatch, tmp_path):
    command_app = import_module("backend.command_app").command_app
    query_app = import_module("backend.app").create_app()
    ActionEvent = import_module("backend.ontology.schemas").ActionEvent
    DispatchTransactionRecord = import_module("backend.ontology.schemas").DispatchTransactionRecord
    LogicGateResult = import_module("backend.ontology.schemas").LogicGateResult
    TransactionLineage = import_module("backend.ontology.schemas").TransactionLineage

    class FakeRepo:
        def __init__(self):
            self.transactions = []

        def close(self):
            return None

        def dispatch_action(self, payload):
            return ActionEvent(
                event_id="evt-1",
                action_id=payload.action_id,
                source_id=payload.source_id,
                target_id=payload.target_id,
                payload=payload.payload,
                created_at=datetime.now(timezone.utc),
            )

        def create_dispatch_transaction(self, **kwargs):
            item = DispatchTransactionRecord(
                txn_id=kwargs["txn_id"],
                action_id=kwargs["action_id"],
                actor=kwargs["actor"],
                status=kwargs["status"],
                event_id=kwargs["event_id"],
                compensation_event_id=kwargs["compensation_event_id"],
                gates=kwargs["gates"],
                created_at=datetime.now(timezone.utc),
                reverted_at=None,
            )
            self.transactions = [item]
            return item

        def list_dispatch_transactions(self, limit=100):
            return self.transactions[:limit]

        def get_dispatch_transaction(self, txn_id):
            for item in self.transactions:
                if item.txn_id == txn_id:
                    return item
            return None

        def get_transaction_lineage(self, txn_id):
            item = self.get_dispatch_transaction(txn_id)
            if item is None:
                return None
            return TransactionLineage(
                transaction=item,
                primary_event=ActionEvent(
                    event_id="evt-1",
                    action_id=item.action_id,
                    source_id="entity-1",
                    target_id="entity-2",
                    payload={"damage": 50},
                    created_at=datetime.now(timezone.utc),
                ),
                compensation_event=None,
            )

        def list_object_types(self):
            return []

        def list_events(self):
            return []

        def latest_projection_snapshot(self):
            return None

        def append_audit_log(self, actor, operation, detail):
            _ = (actor, operation, detail)
            return None

    fake_repo = FakeRepo()

    monkeypatch.setenv("AUDIT_LEDGER_PATH", str(tmp_path / "audit.ndjson"))
    monkeypatch.setattr("backend.command_app.create_repository", lambda _settings: fake_repo)
    monkeypatch.setattr("backend.routes.ontology_query.create_repository", lambda _settings: fake_repo)
    monkeypatch.setattr("backend.command_app.publish_domain_event", lambda _event: True)
    monkeypatch.setattr(
        "backend.routes.ontology_query.list_domain_events",
        lambda limit=200, txn_id=None: [
            {
                "event_type": "NotificationQueued",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "service": "notification-service",
                "correlation_id": "notify:ops.alerts",
                "txn_id": txn_id,
            }
        ],
    )
    monkeypatch.setattr("backend.command_app._record_service_adapter_audit", lambda **_kwargs: None)
    monkeypatch.setattr(
        "backend.command_app.SearchService.search",
        lambda _self, query: {
            "service": "search-service",
            "query": query,
            "hits": 1,
            "results": [{"kind": "object_type", "id": "com.genesis.unit.Drone", "label": "Drone"}],
        },
    )
    monkeypatch.setattr(
        "backend.command_app.NotificationService.publish",
        lambda _self, channel, message: {
            "service": "notification-service",
            "channel": channel,
            "message": message,
            "status": "queued",
        },
    )

    command_client = TestClient(command_app)
    query_client = query_app.test_client()

    login = command_client.post("/api/auth/token", json={"username": "designer", "password": "designer"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    dispatch = command_client.post(
        "/api/command/dispatch",
        json={"action_id": "ACT_MVP", "source_id": "entity-1", "target_id": "entity-2", "payload": {"damage": 50}},
        headers=headers,
    )
    assert dispatch.status_code == 200

    tx_list = command_client.get("/api/command/transactions", headers=headers)
    assert tx_list.status_code == 200
    txn_id = tx_list.json()[0]["txn_id"]

    lineage = query_client.get(f"/api/query/transactions/lineage/{txn_id}/aggregate")
    assert lineage.status_code == 200
    assert set(lineage.get_json().keys()) == {"lineage", "bus_events"}

    proposals = command_client.get("/api/command/proposals", headers=headers)
    assert proposals.status_code == 200
    proposal_id = proposals.json()[0]["proposal_id"]

    proposal_apply = command_client.post(f"/api/command/proposals/{proposal_id}/apply", headers=headers)
    assert proposal_apply.status_code == 200

    service_search = command_client.post(
        "/api/command/services/search",
        json={"query": "drone"},
        headers=headers,
    )
    assert service_search.status_code == 200
    assert set(service_search.json().keys()) == {"operation", "status", "service", "result"}

    service_notify = command_client.post(
        "/api/command/services/notification/publish",
        json={"channel": "ops.alerts", "message": "mvp alive"},
        headers=headers,
    )
    assert service_notify.status_code == 200

    compliance_export = query_client.post("/api/compliance/export", json={"subject_id": "user-123"}, headers=headers)
    assert compliance_export.status_code == 200

    compliance_records = query_client.get("/api/compliance/records", headers=headers)
    assert compliance_records.status_code == 200
    assert len(compliance_records.get_json()) >= 1

    notifications = query_client.get("/api/query/notifications/secure", headers=headers)
    assert notifications.status_code == 200
    assert len(notifications.get_json()) >= 1
