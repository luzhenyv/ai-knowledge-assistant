from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str = ""


@runtime_checkable
class Guardrail(Protocol):
    """Decides whether a question is in scope. This is a *thin* layer; the primary
    scope guard is KB-grounding (no relevant docs -> escalate) in the pipeline.
    """

    def check(self, question: str) -> Decision:
        ...
