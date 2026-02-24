from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .rag import RAGPipeline


class BaseAgent(ABC):
    """Base class for all Copilot agents."""

    name: str = "base"
    description: str = "Base agent"

    def __init__(self, rag_pipeline: RAGPipeline | None = None) -> None:
        self.rag = rag_pipeline
        self.confidence_threshold = 0.85

    @abstractmethod
    async def process(
        self, intent: str, prompt: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Process the user request and return a response."""
        pass

    def _get_relevant_context(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Retrieve relevant context from RAG pipeline."""
        if self.rag:
            return self.rag.similarity_search(query, top_k=top_k)
        return []


class OntologyArchitectAgent(BaseAgent):
    """OAA: Generates and validates ontology schemas (OTD/LTD)."""

    name = "OAA"
    description = "Ontology Architect - Schema generation and migration"

    async def process(
        self, intent: str, prompt: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        relevant = self._get_relevant_context(f"ontology schema {prompt}")

        # Build system prompt with context
        system_prompt = self._build_system_prompt(relevant)

        return {
            "agent": self.name,
            "confidence": 0.92,
            "plan": [
                "Analyze existing ontology patterns",
                "Generate OTD schema definition",
                "Generate LTD for relationships",
                "Validate inheritance hierarchy",
                "Create migration plan if needed",
            ],
            "system_prompt": system_prompt,
            "output_type": "ontology_schema",
            "requires_approval": True,
        }

    def _build_system_prompt(self, context: list[dict[str, Any]]) -> str:
        ctx_str = "\n".join([f"- {c.get('content', '')}" for c in context[:3]])
        return f"""You are an Ontology Architect. Generate Object Type Definitions (OTD) and Link Type Definitions (LTD).

Context from existing schemas:
{ctx_str}

Rules:
- Use reverse domain naming: com.genesis.domain.Entity
- Define properties with types: static, time_series, computed
- Include lifecycle hooks where appropriate
- Ensure Liskov substitution for inheritance
- Add proper access_control fields

Output valid JSON matching the OTD/LTD schema."""


class LogicSynapserAgent(BaseAgent):
    """LSA: Generates actions, rules, and Cypher queries."""

    name = "LSA"
    description = "Logic Synapser - Action and rule generation"

    async def process(
        self, intent: str, prompt: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        relevant = self._get_relevant_context(f"action rule logic {prompt}")

        return {
            "agent": self.name,
            "confidence": 0.9,
            "plan": [
                "Parse rule intent",
                "Identify pre-conditions (L1-L3)",
                "Generate effect chain",
                "Write Cypher for graph operations",
                "Add post-assertions",
                "Define compensation strategy",
            ],
            "requires_guardrails": True,
            "output_type": "action_definition",
            "cypher_validation": True,
        }


class WorldFillerAgent(BaseAgent):
    """WFA: Bulk entity generation and seed data creation."""

    name = "WFA"
    description = "World Filler - Bulk entity generation"

    async def process(
        self, intent: str, prompt: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "agent": self.name,
            "confidence": 0.88,
            "plan": [
                "Parse generation criteria",
                "Determine entity type and count",
                "Generate spatial distribution",
                "Create property variations",
                "Generate Cypher UNWIND batch query",
                "Estimate execution time",
            ],
            "output_type": "seed_data",
            "batch_operation": True,
        }


class DataAnalystAgent(BaseAgent):
    """DAA: Query optimization and analytics."""

    name = "DAA"
    description = "Data Analyst - Query optimization and insights"

    async def process(
        self, intent: str, prompt: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "agent": self.name,
            "confidence": 0.86,
            "plan": [
                "Analyze query intent",
                "Optimize Cypher query plan",
                "Suggest indexes if needed",
                "Generate aggregation pipeline",
                "Create visualization config",
            ],
            "output_type": "analytics_query",
        }


class DebugAssistantAgent(BaseAgent):
    """DBA: Error diagnosis and lineage tracing."""

    name = "DBA"
    description = "Debug Assistant - Error diagnosis and tracing"

    async def process(
        self, intent: str, prompt: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "agent": self.name,
            "confidence": 0.8,
            "plan": [
                "Parse error symptoms",
                "Query audit logs for context",
                "Trace transaction lineage",
                "Identify root cause",
                "Suggest remediation steps",
            ],
            "output_type": "debug_analysis",
            "read_only": True,
        }


class SupervisorAgent:
    """Routes requests to appropriate specialized agents."""

    def __init__(self, rag_pipeline: RAGPipeline | None = None) -> None:
        self.rag = rag_pipeline
        self.agents: dict[str, BaseAgent] = {
            "OAA": OntologyArchitectAgent(rag_pipeline),
            "LSA": LogicSynapserAgent(rag_pipeline),
            "WFA": WorldFillerAgent(rag_pipeline),
            "DAA": DataAnalystAgent(rag_pipeline),
            "DBA": DebugAssistantAgent(rag_pipeline),
        }

    async def route(
        self, intent: str, prompt: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """Route request to best agent based on intent classification."""

        # Intent classification
        agent_key = self._classify_intent(intent, prompt)
        agent = self.agents.get(agent_key, self.agents["DBA"])

        # Process with selected agent
        result = await agent.process(intent, prompt, context)
        result["selected_by_supervisor"] = True
        result["available_agents"] = list(self.agents.keys())

        return result

    def _classify_intent(self, intent: str, prompt: str) -> str:
        """Classify intent to determine best agent."""
        text = f"{intent} {prompt}".lower()

        # OAA patterns
        if any(kw in text for kw in ["ontology", "schema", "entity type", "object type", "inheritance", "parent"]):
            return "OAA"

        # LSA patterns
        if any(kw in text for kw in ["logic", "rule", "action", "behavior", "trigger", "condition", "effect"]):
            return "LSA"

        # WFA patterns
        if any(kw in text for kw in ["generate", "create many", "bulk", "populate", "seed", "random"]):
            return "WFA"

        # DAA patterns
        if any(kw in text for kw in ["analyze", "query", "statistics", "metrics", "performance", "optimize"]):
            return "DAA"

        # Default to DBA for debugging/unknown
        return "DBA"
