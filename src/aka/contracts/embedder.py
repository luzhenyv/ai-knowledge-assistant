from __future__ import annotations

from typing import Protocol, runtime_checkable

Vector = list[float]


@runtime_checkable
class Embedder(Protocol):
    """Turns text into vectors. Used both offline (indexing) and online (query)."""

    @property
    def dim(self) -> int:
        """Embedding dimensionality, so the vector store can validate inputs."""
        ...

    def embed(self, texts: list[str]) -> list[Vector]:
        ...
