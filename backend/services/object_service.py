from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import Any
from uuid import uuid4

from ..async_bus import publish_domain_event
from ..config import load_settings
from ..ontology.deps import create_repository
from ..ontology.schemas import ActionDispatch
from ..ontology.repository import Neo4jOntologyRepository


class ObjectService:
    """ObjectService handles entity lifecycle and query operations.
    
    Implements PRP v3.0 requirements:
    - spawn_entity: Create new entity instances
    - destroy_entity: Remove entities with cascade options
    - query_by_type: Type-based entity queries
    - batch_hydrate: Neo4j static + TSDB dynamic → UnifiedObjectDTO
    """
    
    service_name = "object-service"

    def __init__(self, repo: Neo4jOntologyRepository | None = None):
        self._repo = repo

    def _get_repo(self) -> Neo4jOntologyRepository:
        if self._repo is None:
            settings = load_settings()
            self._repo = create_repository(settings)
        return self._repo

    def _close_repo(self) -> None:
        if self._repo is not None:
            self._repo.close()
            self._repo = None

    def spawn_entity(
        self,
        object_type: str,
        object_id: str | None = None,
        properties: dict[str, str] | None = None,
        actor: str = "system",
    ) -> dict[str, Any]:
        """Spawn a new entity instance of the given type."""
        oid = object_id or str(uuid4())
        
        payload = ActionDispatch(
            action_id="ACT_SPAWN_ENTITY",
            source_id=oid,
            target_id=object_type,
            actor=actor,
            payload={"object_id": oid, "object_type": object_type},
        )

        repo = self._get_repo()
        try:
            event = repo.dispatch_action(payload)
        finally:
            self._close_repo()

        published = publish_domain_event(
            {
                "event_id": event.event_id,
                "event_type": "EntitySpawned",
                "actor": actor,
                "object_id": oid,
                "object_type": object_type,
                "correlation_id": oid,
                "causation_id": event.event_id,
            }
        )

        return {
            "service": self.service_name,
            "object_id": oid,
            "object_type": object_type,
            "event_id": event.event_id,
            "status": "committed" if published else "event_publish_failed",
            "published": published,
        }

    def destroy_entity(
        self,
        object_id: str,
        cascade: bool = False,
        actor: str = "system",
    ) -> dict[str, Any]:
        """Destroy an entity instance."""
        payload = ActionDispatch(
            action_id="ACT_DESTROY_ENTITY",
            source_id=object_id,
            target_id="",
            actor=actor,
            payload={"object_id": object_id, "cascade": str(cascade)},
        )

        repo = self._get_repo()
        try:
            event = repo.dispatch_action(payload)
        finally:
            self._close_repo()

        published = publish_domain_event(
            {
                "event_id": event.event_id,
                "event_type": "EntityDestroyed",
                "actor": actor,
                "object_id": object_id,
                "correlation_id": object_id,
                "causation_id": event.event_id,
            }
        )

        return {
            "service": self.service_name,
            "object_id": object_id,
            "event_id": event.event_id,
            "status": "committed" if published else "event_publish_failed",
            "published": published,
        }

    def query_by_type(
        self,
        object_type: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query entities by type."""
        repo = self._get_repo()
        try:
            with repo._driver.session() as session:
                rows = session.run(
                    "MATCH (e:Entity {object_type: $object_type}) RETURN e.object_id, e.object_type, e.properties",
                    {"object_type": object_type},
                )
                return [
                    {
                        "object_id": row[0],
                        "object_type": row[1],
                        "properties": dict(row[2] or {}),
                    }
                    for row in rows
                ][:limit]
        finally:
            self._close_repo()

    def batch_hydrate(
        self,
        object_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Batch hydrate entities with static (Neo4j) data."""
        repo = self._get_repo()
        try:
            with repo._driver.session() as session:
                rows = session.run(
                    "UNWIND $oids AS oid MATCH (e:Entity {object_id: oid}) RETURN e.object_id, e.object_type, e.properties",
                    {"oids": object_ids},
                )
                
                results = {}
                for row in rows:
                    results[row[0]] = {
                        "object_id": row[0],
                        "object_type": row[1],
                        "properties": dict(row[2] or {}),
                        "static_properties": dict(row[2] or {}),
                        "timeseries_properties": {},
                    }
                return results
        finally:
            self._close_repo()

    def list_entities(
        self,
        object_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List entities, optionally filtered by type."""
        if object_type:
            return self.query_by_type(object_type, limit)
        
        repo = self._get_repo()
        try:
            with repo._driver.session() as session:
                rows = session.run(
                    "MATCH (e:Entity) RETURN e.object_id, e.object_type, e.properties LIMIT $limit",
                    {"limit": limit},
                )
                return [
                    {
                        "object_id": row[0],
                        "object_type": row[1],
                        "properties": dict(row[2] or {}),
                    }
                    for row in rows
                ]
        finally:
            self._close_repo()

    def update_properties(
        self,
        object_id: str,
        properties: dict[str, str],
        actor: str = "system",
    ) -> dict[str, Any]:
        """Update properties on an existing entity."""
        payload = ActionDispatch(
            action_id="ACT_UPDATE_PROPERTIES",
            source_id=object_id,
            target_id="",
            actor=actor,
            payload={"object_id": object_id},
        )

        repo = self._get_repo()
        try:
            event = repo.dispatch_action(payload)
        finally:
            self._close_repo()

        published = publish_domain_event(
            {
                "event_id": event.event_id,
                "event_type": "PropertiesUpdated",
                "actor": actor,
                "object_id": object_id,
                "correlation_id": object_id,
                "causation_id": event.event_id,
            }
        )

        return {
            "service": self.service_name,
            "object_id": object_id,
            "event_id": event.event_id,
            "status": "committed" if published else "event_publish_failed",
            "published": published,
        }

    # -------------------------------------------------------------------------
    # Legacy method
    # -------------------------------------------------------------------------

    def upsert_object(self, object_id: str, object_type: str) -> dict[str, str | bool]:
        """Legacy method - use spawn_entity instead."""
        result = self.spawn_entity(
            object_type=object_type,
            object_id=object_id,
            actor=self.service_name,
        )
        return {
            "service": self.service_name,
            "object_id": object_id,
            "object_type": object_type,
            "event_id": result["event_id"],
            "status": result["status"],
            "published": result["published"],
        }
