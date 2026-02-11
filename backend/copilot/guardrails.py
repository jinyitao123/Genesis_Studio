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
