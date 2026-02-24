from __future__ import annotations

from ..config import Settings
from .repository import Neo4jOntologyRepository


def create_repository(settings: Settings) -> Neo4jOntologyRepository:
    return Neo4jOntologyRepository(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )
