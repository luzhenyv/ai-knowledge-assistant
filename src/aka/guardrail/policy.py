"""Config-driven scope guard. Deliberately thin: the primary scope enforcement is
KB grounding (no relevant docs -> escalate). This catches clearly off-topic asks
early (investment, politics, medical) via configurable regex — no code changes.
"""

from __future__ import annotations

import re

from aka.contracts.guardrail import Decision


class PolicyGuardrail:
    def __init__(self, deny_patterns: list[str], enabled: bool = True) -> None:
        self._enabled = enabled
        self._patterns = [re.compile(p, re.IGNORECASE) for p in deny_patterns]

    def check(self, question: str) -> Decision:
        if not self._enabled:
            return Decision(allowed=True)
        for pat in self._patterns:
            if pat.search(question):
                return Decision(
                    allowed=False,
                    reason="This assistant only answers internal SOP and tool-usage questions.",
                )
        return Decision(allowed=True)
