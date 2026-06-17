from __future__ import annotations

from typing import Protocol, runtime_checkable

from aka.domain.models import Chunk


@runtime_checkable
class Retriever(Protocol):
    """Returns the chunks most relevant to a query. Relevance scores are stashed
    on ``Chunk.metadata['score']`` so downstream stages can apply a floor without
    a second contract.
    """

    def retrieve(self, query: str, k: int, filters: dict | None = None) -> list[Chunk]:
        ...
