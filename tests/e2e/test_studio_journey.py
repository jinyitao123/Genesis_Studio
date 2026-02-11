from __future__ import annotations

from datetime import datetime
from datetime import timezone
from importlib import import_module

from fastapi.testclient import TestClient


def test_studio_core_journey(monkeypatch):
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
            record = DispatchTransactionRecord(
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
            self.transactions = [record]
            return record

        def list_dispatch_transactions(self, limit=100):
            return self.transactions[:limit]

        def get_dispatch_transaction(self, txn_id):
            for row in self.transactions:
                if row.txn_id == txn_id:
                    return row
            return None

        def get_transaction_lineage(self, txn_id):
            item = self.get_dispatch_transaction(txn_id)
            if item is None:
                return None
            return TransactionLineage(transaction=item, primary_event=None, compensation_event=None)

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
    monkeypatch.setattr("backend.command_app.create_repository", lambda _settings: fake_repo)
    monkeypatch.setattr("backend.routes.ontology_query.create_repository", lambda _settings: fake_repo)
    monkeypatch.setattr("backend.command_app.publish_domain_event", lambda event: True)
    monkeypatch.setattr("backend.routes.ontology_query.domain_event_stream_length", lambda: 1)

    command_client = TestClient(command_app)
    query_client = query_app.test_client()

    token = command_client.post("/api/auth/token", json={"username": "designer", "password": "designer"}).json()[
        "access_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}

    dispatch = command_client.post(
        "/api/command/dispatch",
        json={"action_id": "ACT_STUDIO", "source_id": "a", "target_id": "b", "payload": {}},
        headers=headers,
    )
    assert dispatch.status_code == 200

    transactions = command_client.get("/api/command/transactions", headers=headers)
    assert transactions.status_code == 200
    assert len(transactions.json()) == 1
    txn_id = transactions.json()[0]["txn_id"]

    lineage = query_client.get(f"/api/query/transactions/lineage/{txn_id}")
    assert lineage.status_code in {200, 404}
