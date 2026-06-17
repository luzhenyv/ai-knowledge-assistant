from __future__ import annotations

from typing import Protocol, runtime_checkable

from aka.domain.models import Answer, Chunk


@runtime_checkable
class AnswerGenerator(Protocol):
    """Produces a grounded Answer (text + citations) from retrieved chunks.

    Citation and confidence live *inside* the returned Answer so later stages
    never reconstruct them. Implementations MUST answer only from the supplied
    chunks and return ``grounded=False`` when the context is insufficient.
    """

    def generate(self, question: str, chunks: list[Chunk]) -> Answer:
        ...
