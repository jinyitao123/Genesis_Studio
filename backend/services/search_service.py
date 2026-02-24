from __future__ import annotations

from ..config import load_settings
from ..ontology.deps import create_repository
from .backend_clients import SearchBackendClient


class SearchService:
    service_name = "search-service"

    def __init__(self) -> None:
        self._backend = SearchBackendClient()

    def search(self, query: str) -> dict[str, str | int | list[dict[str, str]]]:
        # Try external backend first if configured
        if self._backend.is_configured():
            external_result = self._backend.search(query)
            if external_result is not None:
                return {
                    "service": self.service_name,
                    "query": query,
                    "hits": external_result["hits"],
                    "results": external_result["results"],
                }

        # Fall back to local repository search
        needle = query.strip().lower()
        settings = load_settings()
        repo = create_repository(settings)
        try:
            object_rows = repo.list_object_types()
            event_rows = repo.list_events()
        finally:
            repo.close()

        type_hits = [
            {
                "kind": "object_type",
                "id": row.type_uri,
                "label": row.display_name,
            }
            for row in object_rows
            if needle and (needle in row.type_uri.lower() or needle in row.display_name.lower())
        ]

        event_hits = [
            {
                "kind": "event",
                "id": row.event_id,
                "label": row.action_id,
            }
            for row in event_rows
            if needle and (needle in row.action_id.lower() or needle in row.event_id.lower())
        ]

        hits = [*type_hits, *event_hits][:50]
        return {
            "service": self.service_name,
            "query": query,
            "hits": len(hits),
            "results": hits,
        }
