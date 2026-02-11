from __future__ import annotations

from typing import TYPE_CHECKING

from ..config import load_settings
from ..ontology.deps import create_repository

if TYPE_CHECKING:
    from ..ontology.repository import Neo4jOntologyRepository


class OntologyService:
    service_name = "ontology-service"

    def validate_schema(self, schema_version: str) -> dict[str, str | bool | int]:
        settings = load_settings()
        repo: Neo4jOntologyRepository = create_repository(settings)
        try:
            repository_available = repo.ping()
            object_type_count = len(repo.list_object_types())
        except Exception:
            repository_available = False
            object_type_count = 0
        finally:
            repo.close()

        segments = schema_version.split(".")
        version_valid = len(segments) == 3 and all(part.isdigit() for part in segments)

        return {
            "service": self.service_name,
            "schema_version": schema_version,
            "valid": version_valid and repository_available,
            "repository_available": repository_available,
            "object_type_count": object_type_count,
        }
