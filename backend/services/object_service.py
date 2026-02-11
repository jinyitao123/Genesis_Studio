from __future__ import annotations

from ..async_bus import publish_domain_event
from ..config import load_settings
from ..ontology.deps import create_repository
from ..ontology.schemas import ActionDispatch


class ObjectService:
    service_name = "object-service"

    def upsert_object(self, object_id: str, object_type: str) -> dict[str, str | bool]:
        payload = ActionDispatch(
            action_id="ACT_UPSERT_OBJECT",
            source_id=object_id,
            target_id=object_type,
            actor=self.service_name,
            payload={"object_id": object_id, "object_type": object_type},
        )

        settings = load_settings()
        repo = create_repository(settings)
        try:
            event = repo.dispatch_action(payload)
        finally:
            repo.close()

        published = publish_domain_event(
            {
                "event_id": event.event_id,
                "event_type": "ObjectUpserted",
                "actor": self.service_name,
                "object_id": object_id,
                "object_type": object_type,
                "correlation_id": object_id,
                "causation_id": event.event_id,
            }
        )

        return {
            "service": self.service_name,
            "object_id": object_id,
            "object_type": object_type,
            "event_id": event.event_id,
            "status": "committed" if published else "event_publish_failed",
            "published": published,
        }
