from __future__ import annotations

from typing import Protocol, runtime_checkable

from aka.domain.models import Chunk


@runtime_checkable
class Recommender(Protocol):
    """Suggests related topics. MVP uses a static topic graph; the interface is
    stable enough to later back with analytics or a learned graph.
    """

    def recommend(self, question: str, matched_chunks: list[Chunk]) -> list[str]:
        ...
