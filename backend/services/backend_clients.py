from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

from .elasticsearch_adapter import get_elasticsearch_adapter
from .timescale_adapter import get_timescale_adapter


class SearchBackendClient:
    """Unified search backend client - delegates to Elasticsearch adapter when configured."""

    def __init__(self, base_url: str | None = None) -> None:
        self._adapter = get_elasticsearch_adapter()

    def is_configured(self) -> bool:
        return self._adapter.is_configured

    def search(self, query: str) -> dict[str, Any] | None:
        """Search via Elasticsearch or return None for fallback."""
        if not self.is_configured():
            return None
        
        # Ensure index exists
        self._adapter.ensure_index()
        
        result = self._adapter.search(query)
        if result is None:
            # ES failed, return None to trigger fallback
            return None
        
        # Transform to legacy format
        return {
            "backend": "elasticsearch",
            "hits": result["hits"],
            "results": [
                {
                    "kind": r.get("kind", "event"),
                    "id": r.get("id", ""),
                    "label": r.get("label", ""),
                }
                for r in result.get("results", [])
            ],
        }

    def index_event(self, event: dict[str, Any]) -> bool:
        """Index an event document."""
        if not self.is_configured():
            return False
        self._adapter.ensure_index()
        return self._adapter.index_event(event)

    def bulk_index_events(self, events: list[dict[str, Any]]) -> int:
        """Bulk index events."""
        if not self.is_configured() or not events:
            return 0
        self._adapter.ensure_index()
        return self._adapter.bulk_index_events(events)


class TimeseriesBackendClient:
    """Unified timeseries backend client - delegates to TimescaleDB adapter when configured."""

    def __init__(self, base_url: str | None = None) -> None:
        self._adapter = get_timescale_adapter()

    def is_configured(self) -> bool:
        return self._adapter.is_configured

    def query_events(
        self, entity_id: str, start_ts: str, end_ts: str
    ) -> list[dict[str, Any]] | None:
        """Query timeseries events from TimescaleDB."""
        if not self.is_configured():
            return None
        
        from datetime import datetime
        from datetime import timezone
        
        # Parse timestamps
        try:
            start_dt = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_ts.replace("Z", "+00:00"))
        except ValueError:
            return None
        
        self._adapter.ensure_schema()
        return self._adapter.query_events(entity_id, start_dt, end_dt)

    def insert_event(self, event: dict[str, Any]) -> bool:
        """Insert an event into timeseries."""
        if not self.is_configured():
            return False
        self._adapter.ensure_schema()
        return self._adapter.insert_event(event)

    def bulk_insert_events(self, events: list[dict[str, Any]]) -> int:
        """Bulk insert events."""
        if not self.is_configured() or not events:
            return 0
        self._adapter.ensure_schema()
        return self._adapter.bulk_insert_events(events)
