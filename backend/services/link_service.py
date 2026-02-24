from __future__ import annotations

from typing import Any
from uuid import uuid4

from ..async_bus import publish_domain_event
from ..config import load_settings
from ..ontology.deps import create_repository
from ..ontology.schemas import ActionDispatch
from ..ontology.repository import Neo4jOntologyRepository


class LinkService:
    """LinkService handles entity relationship operations.
    
    Implements PRP v3.0 requirements:
    - connect (forge_connection): Create links between entities
    - sever_connection: Remove links between entities
    - get_topology: Get graph topology for entities
    - find_shortest_path: Find shortest path between entities
    - compute_centrality: Calculate centrality metrics
    """
    
    service_name = "link-service"

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

    def connect(
        self,
        source_id: str,
        target_id: str,
        link_type: str = "RELATED",
        properties: dict[str, str] | None = None,
        actor: str = "system",
    ) -> dict[str, Any]:
        """Forge a connection (link) between two entities.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            link_type: Type of link (e.g., "ATTACKS", "COMMANDS", "SUPPORTS")
            properties: Optional link properties
            actor: Actor performing the action
            
        Returns:
            Dict with link details and status
        """
        payload = ActionDispatch(
            action_id="ACT_FORGE_LINK",
            source_id=source_id,
            target_id=target_id,
            actor=actor,
            payload={"link_type": link_type, "source_id": source_id, "target_id": target_id},
        )

        repo = self._get_repo()
        try:
            event = repo.dispatch_action(payload)
        finally:
            self._close_repo()

        published = publish_domain_event(
            {
                "event_id": event.event_id,
                "event_type": "LinkForged",
                "actor": actor,
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

    def sever(
        self,
        source_id: str,
        target_id: str,
        link_type: str | None = None,
        actor: str = "system",
    ) -> dict[str, Any]:
        """Sever a connection between two entities.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            link_type: Optional link type filter
            actor: Actor performing the action
            
        Returns:
            Dict with operation result
        """
        payload = ActionDispatch(
            action_id="ACT_SEVER_LINK",
            source_id=source_id,
            target_id=target_id,
            actor=actor,
            payload={"link_type": link_type or "ALL", "source_id": source_id, "target_id": target_id},
        )

        repo = self._get_repo()
        try:
            event = repo.dispatch_action(payload)
        finally:
            self._close_repo()

        published = publish_domain_event(
            {
                "event_id": event.event_id,
                "event_type": "LinkSevered",
                "actor": actor,
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

    def get_topology(
        self,
        entity_id: str,
        depth: int = 2,
        link_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get the topology (connected graph) for an entity.
        
        Args:
            entity_id: Entity to get topology for
            depth: Maximum traversal depth
            link_types: Optional link type filters
            
        Returns:
            Dict with nodes and edges in the topology
        """
        repo = self._get_repo()
        try:
            with repo._driver.session() as session:
                # Get connected entities
                rows = session.run(
                    """
                    MATCH (e:Entity {object_id: $entity_id})-[r]->(n:Entity)
                    RETURN n.object_id AS node_id, n.object_type AS node_type, type(r) AS link_type, r
                    UNION
                    MATCH (n:Entity)-[r]->(e:Entity {object_id: $entity_id})
                    RETURN n.object_id AS node_id, n.object_type AS node_type, type(r) AS link_type, r
                    """,
                    {"entity_id": entity_id},
                )
                
                nodes = set()
                edges = []
                for row in rows:
                    nodes.add((row["node_id"], row["node_type"]))
                    edges.append({
                        "source": entity_id,
                        "target": row["node_id"],
                        "link_type": row["link_type"],
                    })
                
                return {
                    "center": entity_id,
                    "depth": depth,
                    "nodes": [{"object_id": n[0], "object_type": n[1]} for n in nodes],
                    "edges": edges,
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                }
        finally:
            self._close_repo()

    def find_shortest_path(
        self,
        source_id: str,
        target_id: str,
        link_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Find the shortest path between two entities.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            link_types: Optional link type filters
            
        Returns:
            Dict with path details or error if no path exists
        """
        repo = self._get_repo()
        try:
            with repo._driver.session() as session:
                result = session.run(
                    """
                    MATCH (start:Entity {object_id: $source_id}), (end:Entity {object_id: $target_id})
                    CALL apoc.algo.dijkstra(start, end, 'r>', 'weight')
                    YIELD path, weight
                    RETURN nodes(path) AS nodes, relationships(path) AS edges, weight
                    """,
                    {"source_id": source_id, "target_id": target_id},
                ).single()
                
                if result:
                    nodes = [n["object_id"] for n in result["nodes"]]
                    edges = [
                        {
                            "source": e.start_node["object_id"],
                            "target": e.end_node["object_id"],
                            "link_type": type(e).name,
                        }
                        for e in result["edges"]
                    ]
                    return {
                        "source_id": source_id,
                        "target_id": target_id,
                        "path": nodes,
                        "edges": edges,
                        "length": len(nodes) - 1,
                        "weight": result["weight"],
                        "found": True,
                    }
                
                return {
                    "source_id": source_id,
                    "target_id": target_id,
                    "path": [],
                    "edges": [],
                    "length": 0,
                    "weight": None,
                    "found": False,
                }
        finally:
            self._close_repo()

    def compute_centrality(
        self,
        entity_ids: list[str] | None = None,
        metric: str = "degree",
    ) -> list[dict[str, Any]]:
        """Compute centrality metrics for entities.
        
        Args:
            entity_ids: Optional entity filter
            metric: Centrality metric (degree, betweenness, closeness)
            
        Returns:
            List of entities with centrality scores
        """
        repo = self._get_repo()
        try:
            with repo._driver.session() as session:
                if entity_ids:
                    # Filtered centrality
                    rows = session.run(
                        """
                        UNWIND $entity_ids AS eid
                        MATCH (e:Entity {object_id: eid})
                        WITH e, size((e)-->()) AS out_degree, size((e)<--()) AS in_degree
                        RETURN e.object_id AS object_id, out_degree, in_degree, out_degree + in_degree AS total_degree
                        ORDER BY total_degree DESC
                        """,
                        {"entity_ids": entity_ids},
                    )
                else:
                    # Global centrality
                    rows = session.run(
                        """
                        MATCH (e:Entity)
                        WITH e, size((e)-->()) AS out_degree, size((e)<--()) AS in_degree
                        RETURN e.object_id AS object_id, out_degree, in_degree, out_degree + in_degree AS total_degree
                        ORDER BY total_degree DESC
                        LIMIT 100
                        """,
                    )
                
                return [
                    {
                        "object_id": row["object_id"],
                        "out_degree": row["out_degree"],
                        "in_degree": row["in_degree"],
                        "total_degree": row["total_degree"],
                        "centrality_score": row["total_degree"],
                    }
                    for row in rows
                ]
        finally:
            self._close_repo()

    def list_links(
        self,
        entity_id: str,
        direction: str = "both",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List all links for an entity.
        
        Args:
            entity_id: Entity to list links for
            direction: "out" (outgoing), "in" (incoming), or "both"
            limit: Maximum results
            
        Returns:
            List of link dicts
        """
        repo = self._get_repo()
        try:
            with repo._driver.session() as session:
                if direction == "out":
                    rows = session.run(
                        """
                        MATCH (e:Entity {object_id: $entity_id})-[r]->(n:Entity)
                        RETURN n.object_id AS target_id, type(r) AS link_type, r AS properties
                        """,
                        {"entity_id": entity_id},
                    )
                elif direction == "in":
                    rows = session.run(
                        """
                        MATCH (n:Entity)-[r]->(e:Entity {object_id: $entity_id})
                        RETURN n.object_id AS source_id, type(r) AS link_type, r AS properties
                        """,
                        {"entity_id": entity_id},
                    )
                else:
                    rows = session.run(
                        """
                        MATCH (e:Entity {object_id: $entity_id})-[r]->(n:Entity)
                        RETURN n.object_id AS target_id, type(r) AS link_type, r AS properties, 'outgoing' AS direction
                        UNION ALL
                        MATCH (n:Entity)-[r]->(e:Entity {object_id: $entity_id})
                        RETURN n.object_id AS source_id, type(r) AS link_type, r AS properties, 'incoming' AS direction
                        """,
                        {"entity_id": entity_id},
                    )
                
                return [
                    {
                        "link_type": row["link_type"],
                        "source_id": row.get("source_id") or entity_id,
                        "target_id": row.get("target_id") or entity_id,
                        "direction": row.get("direction", direction),
                        "properties": dict(row["properties"] or {}),
                    }
                    for row in rows
                ][:limit]
        finally:
            self._close_repo()

    # -------------------------------------------------------------------------
    # Legacy method
    # -------------------------------------------------------------------------

    def connect_old(self, source_id: str, target_id: str, link_type: str) -> dict[str, str | bool]:
        """Legacy connect method - use connect() instead."""
        return self.connect(
            source_id=source_id,
            target_id=target_id,
            link_type=link_type,
            actor=self.service_name,
        )
