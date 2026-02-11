from __future__ import annotations

from datetime import datetime
from datetime import timezone
from importlib import import_module

from fastapi.testclient import TestClient


command_app = import_module("backend.command_app").command_app
ActionDispatch = import_module("backend.ontology.schemas").ActionDispatch
ActionEvent = import_module("backend.ontology.schemas").ActionEvent
ObjectTypeCreate = import_module("backend.ontology.schemas").ObjectTypeCreate
ObjectTypeDTO = import_module("backend.ontology.schemas").ObjectTypeDTO
ProjectionSnapshot = import_module("backend.ontology.schemas").ProjectionSnapshot
DispatchTransactionRecord = import_module("backend.ontology.schemas").DispatchTransactionRecord


class FakeRepo:
    def __init__(self):
        self.object_types = []
        self.events = []
        self._event_counter = 0
        self.transactions = []

    def close(self) -> None:
        return None

    def ping(self) -> bool:
        return True

    def create_object_type(self, payload):
        item = ObjectTypeDTO(
            type_uri=payload.type_uri,
            display_name=payload.display_name,
            parent_type=payload.parent_type,
            tags=payload.tags,
            created_at=datetime.now(timezone.utc),
        )
        self.object_types.append(item)
        return item

    def list_object_types(self):
        return self.object_types

    def dispatch_action(self, payload):
        self._event_counter += 1
        event = ActionEvent(
            event_id=f"evt-{self._event_counter}",
            action_id=payload.action_id,
            source_id=payload.source_id,
            target_id=payload.target_id,
            payload=payload.payload,
            created_at=datetime.now(timezone.utc),
        )
        self.events.append(event)
        return event

    def list_events(self):
        return self.events

    def append_audit_log(self, actor, operation, detail):
        return None

    def create_projection_snapshot(self):
        return ProjectionSnapshot(
            projection_id="proj-1",
            object_type_count=len(self.object_types),
            event_count=len(self.events),
            created_at=datetime.now(timezone.utc),
        )

    def create_dispatch_transaction(
        self,
        *,
        txn_id,
        action_id,
        actor,
        status,
        event_id,
        compensation_event_id,
        gates,
    ):
        item = DispatchTransactionRecord(
            txn_id=txn_id,
            action_id=action_id,
            actor=actor,
            status=status,
            event_id=event_id,
            compensation_event_id=compensation_event_id,
            gates=gates,
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
        updated = []
        selected = None
        for item in self.transactions:
            if item.txn_id == txn_id:
                selected = item.model_copy(
                    update={
                        "status": "reverted",
                        "compensation_event_id": compensation_event_id,
                        "reverted_at": datetime.now(timezone.utc),
                    }
                )
                updated.append(selected)
            else:
                updated.append(item)
        self.transactions = updated
        if selected is None:
            raise RuntimeError("transaction not found")
        return selected


def test_command_endpoints(monkeypatch):
    fake_repo = FakeRepo()
    published_events = []

    def fake_create_repository(_settings):
        return fake_repo

    class FakeTask:
        id = "task-1"

    def fake_send_task(_name, kwargs=None):
        _ = kwargs
        return FakeTask()

    def fake_publish_domain_event(event):
        published_events.append(event)
        return True

    def fake_grpc_projection(actor):
        return f"grpc-{actor}"

    monkeypatch.setattr("backend.command_app.create_repository", fake_create_repository)
    monkeypatch.setattr("backend.command_app.celery_app.send_task", fake_send_task)
    monkeypatch.setattr("backend.command_app.call_create_projection", fake_grpc_projection)
    monkeypatch.setattr("backend.command_app.publish_domain_event", fake_publish_domain_event)

    client = TestClient(command_app)
    command_health_response = client.get("/api/command/health")
    assert command_health_response.status_code == 200

    login_response = client.post(
        "/api/auth/token",
        json={"username": "designer", "password": "designer"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    pair_response = client.post(
        "/api/auth/token/pair",
        json={"username": "designer", "password": "designer"},
    )
    assert pair_response.status_code == 200
    pair_payload = pair_response.json()
    assert "refresh_token" in pair_payload

    refresh_response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": pair_payload["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    refresh_payload = refresh_response.json()
    assert "access_token" in refresh_payload
    assert "refresh_token" in refresh_payload
    assert refresh_payload["refresh_token"] != pair_payload["refresh_token"]

    logout_response = client.post(
        "/api/auth/logout",
        json={"refresh_token": refresh_payload["refresh_token"]},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()["status"] == "ok"

    revoked_refresh_response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_payload["refresh_token"]},
    )
    assert revoked_refresh_response.status_code == 401

    oidc_config_response = client.get("/api/auth/oidc/config")
    assert oidc_config_response.status_code == 200
    assert oidc_config_response.json()["enabled"] is False

    oidc_authorize_unconfigured = client.get("/api/auth/authorize")
    assert oidc_authorize_unconfigured.status_code == 503

    monkeypatch.setenv("OIDC_ISSUER_URL", "https://issuer.example.com")
    monkeypatch.setenv("OIDC_CLIENT_ID", "genesis-client")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "http://localhost:18080/callback")

    oidc_authorize_response = client.get("/api/auth/authorize")
    assert oidc_authorize_response.status_code == 200
    assert "authorize?" in oidc_authorize_response.json()["authorize_url"]
    oidc_state = oidc_authorize_response.json()["state"]

    oidc_callback_response = client.post(
        "/api/auth/callback",
        json={"code": "demo-code", "state": oidc_state},
    )
    assert oidc_callback_response.status_code == 200
    assert oidc_callback_response.json()["status"] == "pending"

    create_response = client.post(
        "/api/command/object-types",
        json={
            "type_uri": "com.genesis.unit.Drone",
            "display_name": "Drone",
            "parent_type": "com.genesis.unit.AirUnit",
            "tags": ["air", "light"],
        },
        headers=headers,
    )
    assert create_response.status_code == 200

    list_response = client.get("/api/command/object-types", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    dispatch_response = client.post(
        "/api/command/dispatch",
        json={
            "action_id": "ACT_SELF_DESTRUCT",
            "source_id": "entity-1",
            "target_id": "entity-2",
            "payload": {"damage": 50},
        },
        headers=headers,
    )
    assert dispatch_response.status_code == 200
    assert dispatch_response.json()["action_id"] == "ACT_SELF_DESTRUCT"

    events_response = client.get("/api/command/events", headers=headers)
    assert events_response.status_code == 200
    assert len(events_response.json()) == 1

    projection_response = client.post("/api/command/project", headers=headers)
    assert projection_response.status_code == 200
    assert projection_response.json()["projection_id"] == "proj-1"

    otd_validation_response = client.post(
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
                {"name": "battery_level", "value_type": "float", "storage": "time_series", "required": True},
                {"name": "location", "value_type": "coordinate", "storage": "time_series", "required": True},
                {"name": "current_speed", "value_type": "float", "storage": "time_series", "required": True},
                {"name": "max_speed", "value_type": "float", "storage": "static", "required": True},
            ],
            "bound_actions": ["ACT_MOVE", "ACT_STOP"],
        },
        headers=headers,
    )
    assert otd_validation_response.status_code == 200
    assert otd_validation_response.json()["valid"] is True
    assert len(otd_validation_response.json()["hooks"]) >= 2
    assert {"hook", "passed", "detail"}.issubset(otd_validation_response.json()["hooks"][0].keys())

    ltd_validation_response = client.post(
        "/api/command/ontology/ltd/validate",
        json={
            "link_type_uri": "com.genesis.mil.rel.COMMANDS",
            "display_name": "Commands",
            "source_type_constraint": "Officer",
            "target_type_constraint": "Unit",
            "directionality": "directed",
            "cardinality": "ONE_TO_MANY",
        },
        headers=headers,
    )
    assert ltd_validation_response.status_code == 200
    assert ltd_validation_response.json()["valid"] is True
    assert len(ltd_validation_response.json()["hooks"]) >= 2

    migration_plan_response = client.post(
        "/api/command/ontology/migration/plan",
        json={
            "from_schema_version": "3.0.0",
            "to_schema_version": "3.1.0",
            "changed_fields": ["add_optional", "rename"],
            "mode": "batch",
        },
        headers=headers,
    )
    assert migration_plan_response.status_code == 200
    plan_id = migration_plan_response.json()["plan_id"]

    migration_apply_response = client.post(
        "/api/command/ontology/migration/apply",
        json={"plan_id": plan_id},
        headers=headers,
    )
    assert migration_apply_response.status_code == 200
    assert migration_apply_response.json()["success"] is True
    assert migration_apply_response.json()["processed_entities"] > 0
    assert migration_apply_response.json()["executed_steps"] == 4

    proposals_response = client.get("/api/command/proposals", headers=headers)
    assert proposals_response.status_code == 200
    assert len(proposals_response.json()) >= 2
    proposal_id = proposals_response.json()[0]["proposal_id"]

    proposal_apply = client.post(f"/api/command/proposals/{proposal_id}/apply", headers=headers)
    assert proposal_apply.status_code == 200
    assert proposal_apply.json()["status"] == "applied"

    proposal_rollback = client.post(f"/api/command/proposals/{proposal_id}/rollback", headers=headers)
    assert proposal_rollback.status_code == 200
    assert proposal_rollback.json()["status"] == "rolled_back"

    proposal_reject = client.post(f"/api/command/proposals/{proposal_id}/reject", headers=headers)
    assert proposal_reject.status_code == 200
    assert proposal_reject.json()["status"] == "rejected"

    async_projection_response = client.post("/api/command/project/async", headers=headers)
    assert async_projection_response.status_code == 200
    assert async_projection_response.json()["task_id"] == "task-1"

    replay_projection_response = client.post(
        "/api/command/project/replay",
        json={
            "from_event_id": "evt-1",
            "correlation_id": "corr-1",
            "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        },
        headers=headers,
    )
    assert replay_projection_response.status_code == 200
    assert replay_projection_response.json()["task_id"] == "task-1"

    copilot_response = client.post(
        "/api/copilot/route",
        json={
            "intent": "optimize ontology schema migration",
            "prompt": "Suggest a safe migration plan for schema update",
            "context": {"domain": "ontology"},
        },
        headers=headers,
    )
    assert copilot_response.status_code == 200
    assert copilot_response.json()["agent"] == "OAA"

    grpc_response = client.post(
        "/api/command/grpc/projection",
        json={"actor": "designer"},
        headers=headers,
    )
    assert grpc_response.status_code == 200
    assert grpc_response.json()["projection_id"] == "grpc-designer"

    dry_run_response = client.post(
        "/api/command/dispatch/dry-run",
        json={
            "action_id": "ACT_SELF_DESTRUCT",
            "source_id": "entity-1",
            "target_id": "entity-2",
            "payload": {"damage": 50},
        },
        headers=headers,
    )
    assert dry_run_response.status_code == 200
    assert dry_run_response.json()["allowed"] is True
    assert len(dry_run_response.json()["gates"]) == 5

    tx_list_response = client.get("/api/command/transactions", headers=headers)
    assert tx_list_response.status_code == 200
    transactions = tx_list_response.json()
    assert len(transactions) == 1
    txn_id = transactions[0]["txn_id"]

    saga_before_revert = client.get(f"/api/command/transactions/{txn_id}/saga", headers=headers)
    assert saga_before_revert.status_code == 200
    assert saga_before_revert.json()["state"] == "DISPATCHED"
    assert saga_before_revert.json()["recoverable"] is True

    revert_response = client.post(f"/api/command/revert/{txn_id}", headers=headers)
    assert revert_response.status_code == 200
    assert revert_response.json()["status"] == "reverted"
    assert revert_response.json()["compensation_event_id"] is not None

    revert_response_idempotent = client.post(f"/api/command/revert/{txn_id}", headers=headers)
    assert revert_response_idempotent.status_code == 200
    assert revert_response_idempotent.json()["status"] == "reverted"

    saga_after_revert = client.get(f"/api/command/transactions/{txn_id}/saga", headers=headers)
    assert saga_after_revert.status_code == 200
    assert saga_after_revert.json()["state"] == "COMPENSATED"
    assert saga_after_revert.json()["recoverable"] is False
    assert saga_after_revert.json()["compensation_event_id"] is not None

    dispatch_bus_event = next(item for item in published_events if item.get("event_type") == "ActionDispatched")
    assert dispatch_bus_event["txn_id"] == txn_id
    assert dispatch_bus_event["correlation_id"] == txn_id
    assert dispatch_bus_event["event_id"] == "evt-1"


def test_otd_validation_rejects_unknown_interface(monkeypatch):
    client = TestClient(command_app)
    token = client.post("/api/auth/token", json={"username": "designer", "password": "designer"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    otd_validation_response = client.post(
        "/api/command/ontology/otd/validate",
        json={
            "type_uri": "com.genesis.mil.unit.Drone",
            "schema_version": "3.0.0",
            "display_name": "Drone",
            "parent_type": "com.genesis.mil.unit.AirUnit",
            "implements": ["IUnknown"],
            "sealed": False,
            "abstract": False,
            "properties": [
                {"name": "battery_level", "value_type": "float", "storage": "time_series", "required": True}
            ],
            "bound_actions": ["ACT_MOVE"],
        },
        headers=headers,
    )
    assert otd_validation_response.status_code == 200
    assert otd_validation_response.json()["valid"] is False
    assert any("unknown interface contract" in item for item in otd_validation_response.json()["errors"])


def test_grpc_projection_returns_503_on_unavailable(monkeypatch):
    def fake_grpc_projection(_actor):
        raise RuntimeError("channel unavailable")

    monkeypatch.setattr("backend.command_app.call_create_projection", fake_grpc_projection)

    client = TestClient(command_app)
    token = client.post("/api/auth/token", json={"username": "designer", "password": "designer"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    grpc_response = client.post(
        "/api/command/grpc/projection",
        json={"actor": "designer"},
        headers=headers,
    )
    assert grpc_response.status_code == 503
    assert "grpc projection unavailable" in grpc_response.json()["detail"]
