from __future__ import annotations

import hashlib
import importlib
import json
import os
from datetime import datetime, timezone
from typing import Any

chromadb = None
Settings = None
SentenceTransformer = None


class RAGPipeline:
    """RAG Pipeline for Copilot context retrieval."""

    def __init__(
        self,
        persist_dir: str | None = None,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.persist_dir = persist_dir or os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
        self.model_name = model_name
        self._client: Any = None
        self._collection: Any = None
        self._embedder: Any = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize ChromaDB client with persistence."""
        global chromadb, Settings, SentenceTransformer
        if chromadb is None or Settings is None or SentenceTransformer is None:
            try:
                chromadb = importlib.import_module("chromadb")
                config_module = importlib.import_module("chromadb.config")
                sentence_transformers_module = importlib.import_module("sentence_transformers")
                Settings = getattr(config_module, "Settings")
                SentenceTransformer = getattr(sentence_transformers_module, "SentenceTransformer")
            except Exception:
                return

        settings = Settings(
            persist_directory=self.persist_dir,
            anonymized_telemetry=False,
        )
        self._client = chromadb.Client(settings)
        if self._client is None:
            return
        self._collection = self._client.get_or_create_collection(
            name="genesis_ontology",
            metadata={"hnsw:space": "cosine"},
        )
        self._embedder = SentenceTransformer(self.model_name)

    def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        """Add documents to the vector store."""
        if not documents:
            return

        if ids is None:
            ids = [self._hash_doc(doc) for doc in documents]

        if metadatas is None:
            metadatas = [{} for _ in documents]

        # Add timestamp to metadata
        for meta in metadatas:
            meta["indexed_at"] = datetime.now(timezone.utc).isoformat()

        if self._collection is None:
            return
        self._collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

    def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        filter_criteria: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar documents."""
        if self._embedder is None or self._collection is None:
            return []

        query_embedding = self._embedder.encode(query).tolist()

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_criteria,
            include=["documents", "metadatas", "distances"],
        )

        output: list[dict[str, Any]] = []
        if results["ids"] and len(results["ids"]) > 0:
            for i, doc_id in enumerate(results["ids"][0]):
                output.append({
                    "id": doc_id,
                    "content": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 1.0,
                })

        return output

    def delete_document(self, doc_id: str) -> None:
        """Delete a document by ID."""
        if self._collection is None:
            return
        self._collection.delete(ids=[doc_id])

    def get_collection_stats(self) -> dict[str, Any]:
        """Get statistics about the collection."""
        count = 0
        if self._collection is not None:
            count = int(self._collection.count())
        return {
            "count": count,
            "persist_dir": self.persist_dir,
            "model": self.model_name,
        }

    def index_schema_file(self, file_path: str, schema_type: str) -> None:
        """Index a schema file (OTD or LTD)."""
        if not os.path.exists(file_path):
            return

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        try:
            schema = json.loads(content)
            doc_text = self._schema_to_text(schema, schema_type)
            doc_id = f"{schema_type}:{schema.get('type_uri', schema.get('link_type_uri', 'unknown'))}"

            self.add_documents(
                documents=[doc_text],
                metadatas=[{
                    "type": schema_type,
                    "file_path": file_path,
                    "uri": schema.get("type_uri") or schema.get("link_type_uri"),
                }],
                ids=[doc_id],
            )
        except json.JSONDecodeError:
            pass

    def _schema_to_text(self, schema: dict[str, Any], schema_type: str) -> str:
        """Convert schema JSON to searchable text."""
        parts = []

        if schema_type == "OTD":
            parts.append(f"Object Type: {schema.get('display_name', '')}")
            parts.append(f"URI: {schema.get('type_uri', '')}")
            parts.append(f"Parent: {schema.get('parent_type', 'none')}")
            parts.append(f"Implements: {', '.join(schema.get('implements', []))}")

            props = schema.get("properties", {})
            for prop_name, prop_def in props.items():
                parts.append(f"Property {prop_name}: {prop_def.get('type', 'unknown')} ({prop_def.get('storage', 'static')})")

            actions = schema.get("bound_actions", [])
            parts.append(f"Actions: {', '.join(actions)}")

        elif schema_type == "LTD":
            parts.append(f"Link Type: {schema.get('display_name', '')}")
            parts.append(f"URI: {schema.get('link_type_uri', '')}")
            parts.append(f"Source: {schema.get('source_type_constraint', '')}")
            parts.append(f"Target: {schema.get('target_type_constraint', '')}")
            parts.append(f"Direction: {schema.get('directionality', 'directed')}")

        return "\n".join(parts)

    @staticmethod
    def _hash_doc(doc: str) -> str:
        """Generate hash for document ID."""
        return hashlib.sha256(doc.encode()).hexdigest()[:16]

    def build_context_prompt(self, query: str, top_k: int = 5) -> str:
        """Build a prompt with relevant context."""
        results = self.similarity_search(query, top_k=top_k)

        if not results:
            return "No relevant context found."

        context_parts = []
        for i, result in enumerate(results, 1):
            meta = result.get("metadata", {})
            context_parts.append(
                f"[{i}] {meta.get('type', 'Unknown')}: {result.get('content', '')[:500]}"
            )

        return "\n\n".join(context_parts)
