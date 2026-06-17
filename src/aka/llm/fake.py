"""Deterministic LLM for offline runs and tests. It does not call any network.

It echoes a short grounded-looking answer built from the first context passage and
cites [1], which is enough to exercise the whole pipeline (citations, events, eval)
without a model. If no context is present it emits the refusal sentinel.
"""

from __future__ import annotations

from aka.contracts.llm import Message
from aka.generation.prompts import REFUSAL_SENTINEL


class FakeLLM:
    def complete(self, system: str, messages: list[Message]) -> str:
        user = messages[-1]["content"] if messages else ""
        if "Context passages:" not in user or "[1]" not in user:
            return REFUSAL_SENTINEL
        # Pull the first passage body as a stand-in answer.
        first = user.split("[1]", 1)[1].split("\n\n", 1)[0]
        snippet = first.split("\n", 1)[-1].strip()[:200]
        return f"Based on the documentation: {snippet} [1]"
