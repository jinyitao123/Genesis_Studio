from __future__ import annotations

from importlib import import_module

from datetime import datetime
from datetime import timezone

from fastapi.testclient import TestClient


def test_command_api_contract_shape():
    command_app = import_module("backend.command_app").command_app
    client = TestClient(command_app)

    login_response = client.post("/api/auth/token", json={"username": "designer", "password": "designer"})
    assert login_response.status_code == 200
    payload = login_response.json()
    assert set(payload.keys()) == {"access_token", "token_type", "role"}
    assert payload["token_type"] == "bearer"


def test_copilot_route_contract_shape():
    command_app = import_module("backend.command_app").command_app
    client = TestClient(command_app)

    token = client.post("/api/auth/token", json={"username": "designer", "password": "designer"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/copilot/route",
        json={
            "intent": "build workflow pipeline",
            "prompt": "Plan workflow migration safely",
            "context": {"domain": "workflow"},
        },
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"agent", "confidence", "guardrail", "plan"}
    assert set(body["guardrail"].keys()) == {"allowed", "reasons", "sanitized_prompt"}


def test_validation_contract_includes_hooks():
    command_app = import_module("backend.command_app").command_app
    client = TestClient(command_app)

    token = client.post("/api/auth/token", json={"username": "designer", "password": "designer"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/command/ontology/otd/validate",
        json={
            "type_uri": "com.genesis.mil.unit.Drone",
            "schema_version": "3.0.0",
            "display_name": "Drone",
            "parent_type": "com.genesis.mil.unit.AirUnit",
            "implements": ["IMovable"],
            "sealed": False,
            "abstract": False,
            "properties": [
                {"name": "location", "value_type": "coordinate", "storage": "time_series", "required": True},
                {"name": "current_speed", "value_type": "float", "storage": "time_series", "required": True},
                {"name": "max_speed", "value_type": "float", "storage": "static", "required": True},
            ],
            "bound_actions": ["ACT_MOVE", "ACT_STOP"],
        },
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"valid", "errors", "hooks"}
    assert {"hook", "passed", "detail"}.issubset(payload["hooks"][0].keys())


def test_proposal_and_saga_contract_shapes(monkeypatch):
    command_app = import_module("backend.command_app").command_app
    ActionEvent = import_module("backend.ontology.schemas").ActionEvent
    DispatchTransactionRecord = import_module("backend.ontology.schemas").DispatchTransactionRecord

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

        def get_dispatch_transaction(self, txn_id):
            for item in self.transactions:
                if item.txn_id == txn_id:
                    return item
            return None

        def list_dispatch_transactions(self, limit=100):
            return self.transactions[:limit]

        def append_audit_log(self, actor, operation, detail):
            return None

    fake_repo = FakeRepo()
    monkeypatch.setattr("backend.command_app.create_repository", lambda _settings: fake_repo)

    client = TestClient(command_app)
    token = client.post("/api/auth/token", json={"username": "designer", "password": "designer"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    proposals = client.get("/api/command/proposals", headers=headers)
    assert proposals.status_code == 200
    proposal = proposals.json()[0]
    assert set(proposal.keys()) == {"proposal_id", "title", "intent", "status", "created_at", "updated_at"}

    apply_response = client.post(f"/api/command/proposals/{proposal['proposal_id']}/apply", headers=headers)
    assert apply_response.status_code == 200
    assert set(apply_response.json().keys()) == {"proposal_id", "status"}

    dispatch = client.post(
        "/api/command/dispatch",
        json={"action_id": "ACT_TEST", "source_id": "a", "target_id": "b", "payload": {}},
        headers=headers,
    )
    assert dispatch.status_code == 200
    txn_id = client.get("/api/command/transactions", headers=headers).json()[0]["txn_id"]

    saga = client.get(f"/api/command/transactions/{txn_id}/saga", headers=headers)
    assert saga.status_code == 200
    assert set(saga.json().keys()) == {"txn_id", "state", "steps", "recoverable", "compensation_event_id"}


def test_dispatch_transaction_contract_shapes(monkeypatch):
    command_app = import_module("backend.command_app").command_app
    ActionEvent = import_module("backend.ontology.schemas").ActionEvent
    DispatchTransactionRecord = import_module("backend.ontology.schemas").DispatchTransactionRecord

    class FakeRepo:
        def __init__(self):
            self.events = []
            self.transactions = []

        def close(self):
            return None

        def dispatch_action(self, payload):
            event = ActionEvent(
                event_id=f"evt-{len(self.events) + 1}",
                action_id=payload.action_id,
                source_id=payload.source_id,
                target_id=payload.target_id,
                payload=payload.payload,
                created_at=datetime.now(timezone.utc),
            )
            self.events.append(event)
            return event

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
            self.transactions.append(item)
            return item

        def list_dispatch_transactions(self, limit=100):
            return self.transactions[:limit]

        def get_dispatch_transaction(self, txn_id):
            for item in self.transactions:
                if item.txn_id == txn_id:
                    return item
            return None

        def mark_dispatch_transaction_reverted(self, txn_id, compensation_event_id):
            for index, item in enumerate(self.transactions):
                if item.txn_id == txn_id:
                    updated = item.model_copy(
                        update={
                            "status": "reverted",
                            "compensation_event_id": compensation_event_id,
                            "reverted_at": datetime.now(timezone.utc),
                        }
                    )
                    self.transactions[index] = updated
                    return updated
            raise RuntimeError("transaction not found")

        def append_audit_log(self, actor, operation, detail):
            return None

    fake_repo = FakeRepo()
    monkeypatch.setattr("backend.command_app.create_repository", lambda _settings: fake_repo)

    client = TestClient(command_app)
    token = client.post("/api/auth/token", json={"username": "designer", "password": "designer"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    dispatch_response = client.post(
        "/api/command/dispatch",
        json={"action_id": "ACT_TEST", "source_id": "a", "target_id": "b", "payload": {}},
        headers=headers,
    )
    assert dispatch_response.status_code == 200

    transactions_response = client.get("/api/command/transactions", headers=headers)
    assert transactions_response.status_code == 200
    body = transactions_response.json()
    assert len(body) == 1
    assert set(body[0].keys()) == {
        "txn_id",
        "action_id",
        "actor",
        "status",
        "event_id",
        "compensation_event_id",
        "gates",
        "created_at",
        "reverted_at",
    }


def test_query_transaction_lineage_contract_shape(monkeypatch):
    flask_app = import_module("backend.app").create_app()
    DispatchTransactionRecord = import_module("backend.ontology.schemas").DispatchTransactionRecord
    ActionEvent = import_module("backend.ontology.schemas").ActionEvent
    LogicGateResult = import_module("backend.ontology.schemas").LogicGateResult
    TransactionLineage = import_module("backend.ontology.schemas").TransactionLineage

    class FakeQueryRepo:
        def close(self):
            return None

        def get_transaction_lineage(self, txn_id):
            if txn_id != "txn-1":
                return None
            return TransactionLineage(
                transaction=DispatchTransactionRecord(
                    txn_id="txn-1",
                    action_id="ACT_TEST",
                    actor="designer",
                    status="committed",
                    event_id="evt-1",
                    compensation_event_id=None,
                    gates=[LogicGateResult(tier="L0", passed=True, detail="ok")],
                    created_at=datetime.now(timezone.utc),
                    reverted_at=None,
                ),
                primary_event=ActionEvent(
                    event_id="evt-1",
                    action_id="ACT_TEST",
                    source_id="a",
                    target_id="b",
                    payload={},
                    created_at=datetime.now(timezone.utc),
                ),
                compensation_event=None,
            )

    monkeypatch.setattr("backend.routes.ontology_query.create_repository", lambda _settings: FakeQueryRepo())
    client = flask_app.test_client()

    response = client.get("/api/query/transactions/lineage/txn-1")
    assert response.status_code == 200
    body = response.get_json()
    assert set(body.keys()) == {"transaction", "primary_event", "compensation_event"}
    assert set(body["transaction"].keys()) == {
        "txn_id",
        "action_id",
        "actor",
        "status",
        "event_id",
        "compensation_event_id",
        "gates",
        "created_at",
        "reverted_at",
    }


def test_query_transaction_aggregate_secure_contract_shape(monkeypatch):
    flask_app = import_module("backend.app").create_app()
    DispatchTransactionRecord = import_module("backend.ontology.schemas").DispatchTransactionRecord
    ActionEvent = import_module("backend.ontology.schemas").ActionEvent
    LogicGateResult = import_module("backend.ontology.schemas").LogicGateResult
    TransactionLineage = import_module("backend.ontology.schemas").TransactionLineage
    AuthUser = import_module("backend.security.auth").AuthUser
    create_access_token = import_module("backend.security.auth").create_access_token
    load_settings = import_module("backend.config").load_settings

    class FakeQueryRepo:
        def close(self):
            return None

        def get_transaction_lineage(self, txn_id):
            if txn_id != "txn-1":
                return None
            return TransactionLineage(
                transaction=DispatchTransactionRecord(
                    txn_id="txn-1",
                    action_id="ACT_TEST",
                    actor="designer",
                    status="committed",
                    event_id="evt-1",
                    compensation_event_id=None,
                    gates=[LogicGateResult(tier="L0", passed=True, detail="ok")],
                    created_at=datetime.now(timezone.utc),
                    reverted_at=None,
                ),
                primary_event=ActionEvent(
                    event_id="evt-1",
                    action_id="ACT_TEST",
                    source_id="a",
                    target_id="b",
                    payload={"secret": "x"},
                    created_at=datetime.now(timezone.utc),
                ),
                compensation_event=None,
            )

    monkeypatch.setattr("backend.routes.ontology_query.create_repository", lambda _settings: FakeQueryRepo())
    monkeypatch.setattr(
        "backend.routes.ontology_query.list_domain_events",
        lambda txn_id=None, limit=200: [
            {
                "stream_id": "1739250012000-0",
                "event_type": "ActionDispatched",
                "txn_id": "txn-1",
                "actor": "designer",
                "service": "command-api",
                "created_at": "2026-02-11T05:00:12+00:00",
                "payload": {"secret": "x"},
            }
        ],
    )

    client = flask_app.test_client()
    token = create_access_token(AuthUser(username="viewer", role="Viewer"), load_settings())
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/query/transactions/lineage/txn-1/aggregate/secure", headers=headers)
    assert response.status_code == 200
    body = response.get_json()
    assert set(body.keys()) == {"lineage", "bus_events"}
    assert set(body["lineage"].keys()) == {"transaction", "primary_event", "compensation_event"}
    assert "actor" not in body["lineage"]["transaction"]
    assert "payload" not in body["lineage"]["primary_event"]
    assert "payload" not in body["bus_events"][0]


def test_projection_lag_contract_shape(monkeypatch):
    flask_app = import_module("backend.app").create_app()
    ProjectionSnapshot = import_module("backend.ontology.schemas").ProjectionSnapshot

    class FakeRepo:
        def close(self):
            return None

        def latest_projection_snapshot(self):
            return ProjectionSnapshot(
                projection_id="proj-1",
                object_type_count=2,
                event_count=3,
                created_at=datetime.now(timezone.utc),
            )

    monkeypatch.setattr("backend.routes.ontology_query.create_repository", lambda _settings: FakeRepo())
    monkeypatch.setattr("backend.routes.ontology_query.domain_event_stream_length", lambda: 10)
    client = flask_app.test_client()

    response = client.get("/api/query/projections/lag")
    assert response.status_code == 200
    body = response.get_json()
    assert set(body.keys()) == {"projection_id", "stream_event_count", "projected_event_count", "lag"}


def test_service_adapter_contract_shapes(monkeypatch):
    command_app = import_module("backend.command_app").command_app

    monkeypatch.setattr(
        "backend.command_app.OntologyService.validate_schema",
        lambda _self, schema_version: {
            "service": "ontology-service",
            "schema_version": schema_version,
            "valid": True,
        },
    )
    monkeypatch.setattr(
        "backend.command_app.SearchService.search",
        lambda _self, query: {
            "service": "search-service",
            "query": query,
            "hits": 1,
            "results": [{"kind": "object_type", "id": "com.genesis.unit.Drone", "label": "Drone"}],
        },
    )
    monkeypatch.setattr("backend.command_app._record_service_adapter_audit", lambda **_kwargs: None)
    monkeypatch.setattr("backend.command_app.publish_domain_event", lambda _event: True)

    client = TestClient(command_app)
    token = client.post("/api/auth/token", json={"username": "designer", "password": "designer"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    ontology = client.post(
        "/api/command/services/ontology/validate",
        json={"schema_version": "3.0.0"},
        headers=headers,
    )
    assert ontology.status_code == 200
    ontology_body = ontology.json()
    assert set(ontology_body.keys()) == {"operation", "status", "service", "result"}

    search = client.post(
        "/api/command/services/search",
        json={"query": "drone"},
        headers=headers,
    )
    assert search.status_code == 200
    search_body = search.json()
    assert set(search_body.keys()) == {"operation", "status", "service", "result"}
