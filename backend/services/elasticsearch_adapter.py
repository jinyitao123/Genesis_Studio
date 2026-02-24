from __future__ import annotations

import logging
from typing import Any

try:
    from elasticsearch import Elasticsearch  # type: ignore[import]
    from elasticsearch.helpers import bulk  # type: ignore[import]
except ImportError:
    Elasticsearch = None  # type: ignore[assignment]
    bulk = None  # type: ignore[assignment]

from ..config import load_settings

logger = logging.getLogger(__name__)


class ElasticsearchAdapter:
    """Production-grade Elasticsearch adapter for Genesis Studio search backend."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ElasticsearchAdapter._initialized:
            return
        
        self._settings = load_settings()
        self._client: Any = None
        self._index_name = "genesis_events"
        ElasticsearchAdapter._initialized = True

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.search_backend_url)

    def _get_client(self) -> Any | None:
        """Lazy initialization of ES client."""
        if not self.is_configured or Elasticsearch is None:
            return None
        
        if self._client is None:
            try:
                hosts = [self._settings.search_backend_url]
                self._client = Elasticsearch(hosts=hosts, retry_on_timeout=True, max_retries=3)
                if self._client is None:
                    return None
                # Verify connection
                if not self._client.ping():
                    logger.warning("Elasticsearch ping failed")
                    self._client = None
            except Exception as e:
                logger.warning(f"Failed to connect to Elasticsearch: {e}")
                self._client = None
        
        return self._client

    def ensure_index(self) -> bool:
        """Create index if not exists."""
        client = self._get_client()
        if not client:
            return False
        
        try:
            if not client.indices.exists(index=self._index_name):
                mapping = {
                    "mappings": {
                        "properties": {
                            "event_id": {"type": "keyword"},
                            "event_type": {"type": "keyword"},
                            "action_id": {"type": "keyword"},
                            "source_id": {"type": "keyword"},
                            "target_id": {"type": "keyword"},
                            "actor": {"type": "keyword"},
                            "created_at": {"type": "date"},
                            "payload": {"type": "object"},
                            "correlation_id": {"type": "keyword"},
                            "causation_id": {"type": "keyword"},
                        }
                    },
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                    }
                }
                client.indices.create(index=self._index_name, body=mapping)
                logger.info(f"Created Elasticsearch index: {self._index_name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to create ES index: {e}")
            return False

    def index_event(self, event: dict[str, Any]) -> bool:
        """Index a single event document."""
        client = self._get_client()
        if not client:
            return False
        
        try:
            doc_id = event.get("event_id")
            client.index(index=self._index_name, id=doc_id, document=event)
            return True
        except Exception as e:
            logger.warning(f"Failed to index event: {e}")
            return False

    def bulk_index_events(self, events: list[dict[str, Any]]) -> int:
        """Bulk index multiple events. Returns count of successfully indexed docs."""
        client = self._get_client()
        if not client or not events:
            return 0
        
        try:
            actions = [
                {
                    "_index": self._index_name,
                    "_id": event.get("event_id"),
                    "_source": event,
                }
                for event in events
            ]
            if bulk is None:
                return 0
            success, _ = bulk(client, actions, raise_on_error=False)
            return success
        except Exception as e:
            logger.warning(f"Failed to bulk index events: {e}")
            return 0

    def search(self, query: str, size: int = 50) -> dict[str, Any] | None:
        """Search events using multi-match query."""
        client = self._get_client()
        if not client:
            return None
        
        try:
            es_query = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["event_id^3", "action_id^2", "source_id", "target_id", "actor"],
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                    }
                },
                "size": size,
                "sort": [{"created_at": {"order": "desc"}}],
            }
            
            response = client.search(index=self._index_name, body=es_query)
            
            hits = response.get("hits", {}).get("hits", [])
            return {
                "backend": "elasticsearch",
                "hits": len(hits),
                "total": response.get("hits", {}).get("total", {}).get("value", 0),
                "results": [
                    {
                        "kind": hit.get("_source", {}).get("event_type", "event"),
                        "id": hit.get("_id", ""),
                        "label": hit.get("_source", {}).get("action_id", ""),
                        "score": hit.get("_score", 0),
                        "source": {
                            "event_type": hit.get("_source", {}).get("event_type"),
                            "action_id": hit.get("_source", {}).get("action_id"),
                            "source_id": hit.get("_source", {}).get("source_id"),
                            "target_id": hit.get("_source", {}).get("target_id"),
                            "actor": hit.get("_source", {}).get("actor"),
                            "created_at": hit.get("_source", {}).get("created_at"),
                        }
                    }
                    for hit in hits
                ],
            }
        except Exception as e:
            logger.warning(f"ES search failed: {e}")
            return None

    def get_stats(self) -> dict[str, Any]:
        """Get index statistics."""
        client = self._get_client()
        if not client:
            return {"connected": False, "doc_count": 0}
        
        try:
            stats = client.indices.stats(index=self._index_name)
            return {
                "connected": True,
                "doc_count": stats.get("indices", {}).get(self._index_name, {}).get("total", {}).get("docs", {}).get("count", 0),
                "index": self._index_name,
            }
        except Exception as e:
            return {"connected": False, "error": str(e), "doc_count": 0}


def get_elasticsearch_adapter() -> ElasticsearchAdapter:
    """Factory function to get singleton ES adapter instance."""
    return ElasticsearchAdapter()
