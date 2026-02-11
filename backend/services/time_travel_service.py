from __future__ import annotations

from datetime import datetime
from datetime import timezone

from ..config import load_settings
from ..ontology.deps import create_repository


class TimeTravelService:
    service_name = "time-travel-service"

    def snapshot(self, entity_id: str, at_ts: str) -> dict[str, object]:
        normalized = at_ts.replace("Z", "+00:00")
        try:
            at_dt = datetime.fromisoformat(normalized)
        except ValueError:
            at_dt = datetime.now(timezone.utc)

        settings = load_settings()
        repo = create_repository(settings)
        try:
            all_events = repo.list_events()
        finally:
            repo.close()

        matched = [
            event
            for event in all_events
            if (event.source_id == entity_id or event.target_id == entity_id) and event.created_at <= at_dt
        ]
        matched.sort(key=lambda item: item.created_at, reverse=True)

        latest = matched[0] if matched else None

        return {
            "service": self.service_name,
            "entity_id": entity_id,
            "at_ts": at_dt.isoformat(),
            "status": "ready",
            "observed_events": len(matched),
            "latest_event": latest.model_dump(mode="json") if latest else None,
        }
