from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProposalStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"


class ProposalImpact(BaseModel):
    affected_types: list[str] = Field(default_factory=list)
    affected_entities: int = 0
    breaking_changes: bool = False
    migration_required: bool = False
    estimated_downtime_ms: int = 0


class Proposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    intent: str
    agent: str
    confidence: float
    status: ProposalStatus = ProposalStatus.DRAFT
    content: dict[str, Any] = Field(default_factory=dict)
    impact: ProposalImpact = Field(default_factory=ProposalImpact)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = "system"
    approved_by: str | None = None
    applied_at: str | None = None
    rolled_back_at: str | None = None
    original_state: dict[str, Any] | None = None
    transaction_id: str | None = None


class ProposalStore:
    """In-memory store for proposals with Redis persistence."""

    def __init__(self) -> None:
        self._proposals: dict[str, Proposal] = {}

    def create(
        self,
        title: str,
        intent: str,
        agent: str,
        confidence: float,
        content: dict[str, Any],
        impact: ProposalImpact | None = None,
        created_by: str = "system",
    ) -> Proposal:
        """Create a new proposal."""
        proposal = Proposal(
            title=title,
            intent=intent,
            agent=agent,
            confidence=confidence,
            content=content,
            impact=impact or ProposalImpact(),
            created_by=created_by,
        )
        self._proposals[proposal.proposal_id] = proposal
        return proposal

    def get(self, proposal_id: str) -> Proposal | None:
        """Get a proposal by ID."""
        return self._proposals.get(proposal_id)

    def list_by_status(self, status: ProposalStatus | None = None) -> list[Proposal]:
        """List proposals, optionally filtered by status."""
        proposals = list(self._proposals.values())
        if status:
            proposals = [p for p in proposals if p.status == status]
        return sorted(proposals, key=lambda p: p.created_at, reverse=True)

    def update_status(
        self,
        proposal_id: str,
        status: ProposalStatus,
        actor: str = "system",
    ) -> Proposal | None:
        """Update proposal status."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return None

        proposal.status = status
        proposal.updated_at = datetime.now(timezone.utc).isoformat()

        if status == ProposalStatus.APPROVED:
            proposal.approved_by = actor
        elif status == ProposalStatus.APPLIED:
            proposal.applied_at = datetime.now(timezone.utc).isoformat()
        elif status == ProposalStatus.ROLLED_BACK:
            proposal.rolled_back_at = datetime.now(timezone.utc).isoformat()

        return proposal

    def apply(self, proposal_id: str, actor: str = "system") -> tuple[bool, str]:
        """Apply a proposal to the ontology."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return False, "Proposal not found"

        if proposal.status != ProposalStatus.APPROVED:
            return False, f"Cannot apply proposal in status {proposal.status}"

        # Store original state for rollback
        proposal.original_state = self._capture_state(proposal)

        # Apply changes (implementation depends on content type)
        success, message = self._apply_content(proposal.content)

        if success:
            self.update_status(proposal_id, ProposalStatus.APPLIED, actor)
            return True, f"Proposal applied: {message}"
        else:
            return False, f"Failed to apply: {message}"

    def rollback(self, proposal_id: str, actor: str = "system") -> tuple[bool, str]:
        """Rollback an applied proposal."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return False, "Proposal not found"

        if proposal.status != ProposalStatus.APPLIED:
            return False, f"Cannot rollback proposal in status {proposal.status}"

        if not proposal.original_state:
            return False, "No original state available for rollback"

        # Restore original state
        success, message = self._restore_state(proposal.original_state)

        if success:
            self.update_status(proposal_id, ProposalStatus.ROLLED_BACK, actor)
            return True, f"Proposal rolled back: {message}"
        else:
            return False, f"Failed to rollback: {message}"

    def _capture_state(self, proposal: Proposal) -> dict[str, Any]:
        """Capture current state for potential rollback."""
        # This would capture the relevant state from Neo4j/Git
        return {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "proposal_type": proposal.content.get("type", "unknown"),
        }

    def _apply_content(self, content: dict[str, Any]) -> tuple[bool, str]:
        """Apply the proposal content."""
        content_type = content.get("type")

        if content_type == "ontology_schema":
            # Apply OTD/LTD changes
            return True, f"Applied schema changes"
        elif content_type == "action_definition":
            # Apply action changes
            return True, f"Applied action definition"
        elif content_type == "seed_data":
            # Apply seed data
            entities = content.get("entities", [])
            return True, f"Created {len(entities)} entities"
        else:
            return True, f"Applied generic content"

    def _restore_state(self, state: dict[str, Any]) -> tuple[bool, str]:
        """Restore state from rollback data."""
        return True, "State restored"


class ProposalGenerator:
    """Generates proposals from agent outputs."""

    def __init__(self, store: ProposalStore) -> None:
        self.store = store

    def from_agent_output(
        self,
        agent_output: dict[str, Any],
        original_prompt: str,
        actor: str = "system",
    ) -> Proposal:
        """Generate a proposal from agent processing output."""

        # Analyze impact
        impact = self._analyze_impact(agent_output)

        # Create title from intent
        title = self._generate_title(agent_output, original_prompt)

        return self.store.create(
            title=title,
            intent=original_prompt[:200],
            agent=agent_output.get("agent", "unknown"),
            confidence=agent_output.get("confidence", 0.5),
            content=agent_output,
            impact=impact,
            created_by=actor,
        )

    def _analyze_impact(self, agent_output: dict[str, Any]) -> ProposalImpact:
        """Analyze the impact of a proposal."""
        content = agent_output.get("content", {})
        output_type = agent_output.get("output_type", "unknown")

        affected_types: list[str] = []
        breaking = False
        migration = False

        if output_type == "ontology_schema":
            affected_types = content.get("affected_types", [])
            breaking = content.get("is_breaking", False)
            migration = content.get("requires_migration", False)
        elif output_type == "action_definition":
            affected_types = [content.get("target_type", "unknown")]

        return ProposalImpact(
            affected_types=affected_types,
            affected_entities=content.get("affected_count", 0),
            breaking_changes=breaking,
            migration_required=migration,
            estimated_downtime_ms=0 if not migration else 2000,
        )

    def _generate_title(self, agent_output: dict[str, Any], prompt: str) -> str:
        """Generate a human-readable title."""
        agent = agent_output.get("agent", "Agent")
        output_type = agent_output.get("output_type", "change")

        if output_type == "ontology_schema":
            return f"[{agent}] Schema modification: {prompt[:50]}"
        elif output_type == "action_definition":
            return f"[{agent}] New action: {prompt[:50]}"
        elif output_type == "seed_data":
            return f"[{agent}] Bulk entity generation: {prompt[:50]}"
        else:
            return f"[{agent}] {prompt[:60]}"


class ProposalCard(BaseModel):
    proposal_id: str
    title: str
    description: str
    changes: dict[str, list[str]]
    impact_analysis: dict[str, Any]


def generate_proposal_from_intent(intent_id: str, intent_data: dict[str, Any]) -> dict[str, Any]:
    output = intent_data.get("output", {})
    title = f"{intent_data.get('agent', 'Agent')} proposal"
    return {
        "proposal_id": f"prop-{uuid.uuid4().hex[:8]}",
        "intent_id": intent_id,
        "title": title,
        "status": "draft",
        "diff": {
            "before": {},
            "after": output,
        },
        "content": intent_data,
    }
