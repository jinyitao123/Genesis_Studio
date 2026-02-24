from __future__ import annotations

import re

from .schemas import GuardrailResult


_BLOCK_PATTERNS = [
    re.compile(r"ignore\s+all\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"exfiltrate|dump\s+secrets|leak\s+token", re.IGNORECASE),
]

_SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN\s+PRIVATE\s+KEY-----"),
]


def apply_guardrails(prompt: str) -> GuardrailResult:
    reasons: list[str] = []
    sanitized = prompt

    for pattern in _BLOCK_PATTERNS:
        if pattern.search(prompt):
            reasons.append(f"blocked_pattern:{pattern.pattern}")

    for pattern in _SECRET_PATTERNS:
        if pattern.search(prompt):
            reasons.append("secret_pattern_detected")
            sanitized = pattern.sub("[REDACTED]", sanitized)

    return GuardrailResult(allowed=len(reasons) == 0, reasons=reasons, sanitized_prompt=sanitized)


def validate_prompt(prompt: str) -> dict[str, object]:
    result = apply_guardrails(prompt)
    return {
        "allowed": result.allowed,
        "reasons": result.reasons,
        "sanitized_prompt": result.sanitized_prompt,
    }


def sanitize_input(value: str) -> str:
    stripped = re.sub(r"<script.*?>.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL)
    stripped = re.sub(r"on\w+\s*=\s*['\"].*?['\"]", "", stripped, flags=re.IGNORECASE)
    return stripped.strip()


def check_cypher_safety(cypher: str) -> dict[str, object]:
    reasons: list[str] = []
    banned = ["DETACH DELETE", "DELETE", "REMOVE", "DROP", "CALL dbms"]
    upper_cypher = cypher.upper()
    for token in banned:
        if token in upper_cypher:
            reasons.append(f"forbidden_token:{token}")

    return {
        "safe": len(reasons) == 0,
        "reasons": reasons,
    }
