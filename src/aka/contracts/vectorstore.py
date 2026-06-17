from __future__ import annotations

from typing import Protocol, runtime_checkable

from aka.contracts.embedder import Vector
from aka.domain.models import Chunk

# (chunk_id, similarity_score) — score in [0, 1] for cosine.
ScoredChunkId = tuple[str, float]


@runtime_checkable
class VectorStore(Protocol):
    """Persists chunks + vectors and answers nearest-neighbour queries.

    The store owns chunk persistence so the retriever can hydrate full Chunk
    objects from ids without a second datastore.
    """

    def add(self, chunks: list[Chunk], vectors: list[Vector]) -> None:
        ...

    def query(
        self, vector: Vector, k: int, filters: dict | None = None
    ) -> list[ScoredChunkId]:
        ...

    def get(self, chunk_id: str) -> Chunk:
        ...

    def count(self) -> int:
        ...
