from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field


class CopilotRouteRequest(BaseModel):
    intent: str = Field(min_length=3)
    prompt: str = Field(min_length=3)
    context: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class GuardrailResult(BaseModel):
    allowed: bool
    reasons: list[str]
    sanitized_prompt: str


class CopilotRouteResponse(BaseModel):
    agent: str
    confidence: float
    guardrail: GuardrailResult
    plan: list[str]
