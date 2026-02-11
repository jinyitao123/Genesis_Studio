from __future__ import annotations

from .guardrails import apply_guardrails
from .schemas import CopilotRouteRequest
from .schemas import CopilotRouteResponse


def _agent_for_intent(intent: str) -> tuple[str, float, list[str]]:
    lowered = intent.lower()
    if any(token in lowered for token in ["ontology", "schema", "entity"]):
        return "OAA", 0.92, ["analyze ontology delta", "propose schema-safe changes", "emit migration recommendation"]
    if any(token in lowered for token in ["logic", "rule", "action"]):
        return "LSA", 0.9, ["parse rule graph", "validate action constraints", "propose executable rule set"]
    if any(token in lowered for token in ["workflow", "pipeline", "delivery"]):
        return "WFA", 0.88, ["map workflow states", "check transition guards", "generate execution steps"]
    if any(token in lowered for token in ["data", "analytics", "query"]):
        return "DAA", 0.86, ["inspect query intent", "optimize read path", "prepare analytics prompt"]
    return "DBA", 0.8, ["inspect runtime signals", "triage operational risks", "prepare debug plan"]


def route_copilot_request(payload: CopilotRouteRequest) -> CopilotRouteResponse:
    guardrail = apply_guardrails(payload.prompt)
    agent, confidence, plan = _agent_for_intent(payload.intent)

    if not guardrail.allowed:
        return CopilotRouteResponse(
            agent="DBA",
            confidence=0.4,
            guardrail=guardrail,
            plan=["request blocked by guardrails", "ask user to rephrase safely"],
        )

    return CopilotRouteResponse(
        agent=agent,
        confidence=confidence,
        guardrail=guardrail,
        plan=plan,
    )
