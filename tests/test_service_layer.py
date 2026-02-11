from __future__ import annotations

from datetime import datetime
from datetime import timezone

from backend.ontology.schemas import ActionEvent
from backend.ontology.schemas import ObjectTypeDTO
from backend.services.auth_service import AuthService
from backend.services.link_service import LinkService
from backend.services.notification_service import NotificationService
from backend.services.object_service import ObjectService
from backend.services.ontology_service import OntologyService
from backend.services.search_service import SearchService
from backend.services.time_travel_service import TimeTravelService


class _DummyRepo:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True

    def ping(self):
        return True

    def list_object_types(self):
        return [
            ObjectTypeDTO(
                type_uri="com.genesis.unit.Drone",
                display_name="Drone",
                parent_type=None,
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

    def dispatch_action(self, payload):
        return ActionEvent(
            event_id="evt-1",
            action_id=payload.action_id,
            source_id=payload.source_id,
            target_id=payload.target_id,
            payload=payload.payload,
            created_at=datetime.now(timezone.utc),
        )


def test_ontology_service_uses_repository(monkeypatch):
    repo = _DummyRepo()
    monkeypatch.setattr("backend.services.ontology_service.load_settings", lambda: object())
    monkeypatch.setattr("backend.services.ontology_service.create_repository", lambda _settings: repo)

    payload = OntologyService().validate_schema("3.0.0")
    assert payload["valid"] is True
    assert payload["repository_available"] is True
    assert payload["object_type_count"] == 1
    assert repo.closed is True


def test_object_and_link_services_publish_events(monkeypatch):
    repo = _DummyRepo()
    monkeypatch.setattr("backend.services.object_service.load_settings", lambda: object())
    monkeypatch.setattr("backend.services.object_service.create_repository", lambda _settings: repo)
    monkeypatch.setattr("backend.services.link_service.load_settings", lambda: object())
    monkeypatch.setattr("backend.services.link_service.create_repository", lambda _settings: repo)
    monkeypatch.setattr("backend.services.object_service.publish_domain_event", lambda _event: True)
    monkeypatch.setattr("backend.services.link_service.publish_domain_event", lambda _event: True)

    obj_response = ObjectService().upsert_object("entity-1", "Drone")
    link_response = LinkService().connect("entity-1", "entity-2", "ATTACKS")

    assert obj_response["status"] == "committed"
    assert obj_response["published"] is True
    assert link_response["status"] == "committed"
    assert link_response["published"] is True


def test_search_service_returns_matching_results(monkeypatch):
    repo = _DummyRepo()
    monkeypatch.setattr("backend.services.search_service.load_settings", lambda: object())
    monkeypatch.setattr("backend.services.search_service.create_repository", lambda _settings: repo)

    payload = SearchService().search("drone")
    assert payload["hits"] == 1
    results = payload["results"]
    assert isinstance(results, list)
    assert len(results) == 1


def test_time_travel_service_snapshot(monkeypatch):
    repo = _DummyRepo()
    monkeypatch.setattr("backend.services.time_travel_service.load_settings", lambda: object())
    monkeypatch.setattr("backend.services.time_travel_service.create_repository", lambda _settings: repo)

    payload = TimeTravelService().snapshot("entity-1", datetime.now(timezone.utc).isoformat())
    assert payload["status"] == "ready"
    assert payload["observed_events"] == 1
    assert payload["latest_event"] is not None


def test_auth_service_issues_tokens(monkeypatch):
    monkeypatch.setattr("backend.services.auth_service.load_settings", lambda: object())
    monkeypatch.setattr("backend.services.auth_service.create_access_token", lambda _user, _settings: "access-x")
    monkeypatch.setattr("backend.services.auth_service.create_refresh_token", lambda _user, _settings: "refresh-x")

    payload = AuthService().issue_service_token("svc-user", "Designer")
    assert payload["status"] == "issued"
    assert payload["access_token"] == "access-x"
    assert payload["refresh_token"] == "refresh-x"


def test_notification_service_uses_bus(monkeypatch):
    monkeypatch.setattr("backend.services.notification_service.publish_domain_event", lambda _event: True)
    payload = NotificationService().publish("ops.alerts", "projection lag high")
    assert payload["status"] == "queued"
