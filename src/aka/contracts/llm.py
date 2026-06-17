from __future__ import annotations

from typing import Protocol, runtime_checkable

# A chat message: {"role": "user"|"assistant", "content": "..."}.
Message = dict[str, str]


@runtime_checkable
class LLM(Protocol):
    """A thin text-completion seam. The generator depends on this, not on any
    specific provider SDK, so Claude/Ollama/etc. are swappable.
    """

    def complete(self, system: str, messages: list[Message]) -> str:
        ...
