from __future__ import annotations

from ..async_bus import publish_domain_event
from ..config import load_settings
from ..ontology.deps import create_repository
from ..ontology.schemas import ActionDispatch


class LinkService:
    service_name = "link-service"

    def connect(self, source_id: str, target_id: str, link_type: str) -> dict[str, str | bool]:
        payload = ActionDispatch(
            action_id="ACT_FORGE_LINK",
            source_id=source_id,
            target_id=target_id,
            actor=self.service_name,
            payload={"link_type": link_type},
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
                "event_type": "LinkForged",
                "actor": self.service_name,
                "source_id": source_id,
                "target_id": target_id,
                "link_type": link_type,
                "correlation_id": event.event_id,
                "causation_id": event.event_id,
            }
        )

        return {
            "service": self.service_name,
            "source_id": source_id,
            "target_id": target_id,
            "link_type": link_type,
            "event_id": event.event_id,
            "status": "committed" if published else "event_publish_failed",
            "published": published,
        }
