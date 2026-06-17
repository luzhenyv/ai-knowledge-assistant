from __future__ import annotations

from typing import Protocol, runtime_checkable

from aka.domain.models import ChatContext


@runtime_checkable
class Stage(Protocol):
    """A single pipeline step. Reads and writes ChatContext and nothing else.
    Stages never import or call each other.
    """

    def execute(self, ctx: ChatContext) -> ChatContext:
        ...
