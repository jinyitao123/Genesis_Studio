from __future__ import annotations

from datetime import datetime
from datetime import timezone

from ..async_bus import publish_domain_event


class NotificationService:
    service_name = "notification-service"

    def publish(self, channel: str, message: str) -> dict[str, str]:
        timestamp = datetime.now(timezone.utc).isoformat()
        delivered = publish_domain_event(
            {
                "event_type": "NotificationQueued",
                "service": self.service_name,
                "channel": channel,
                "payload": message,
                "correlation_id": f"notify:{channel}",
                "causation_id": f"notify:{timestamp}",
                "created_at": timestamp,
            }
        )

        return {
            "service": self.service_name,
            "channel": channel,
            "message": message,
            "status": "queued" if delivered else "publish_failed",
        }
