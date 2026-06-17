"""Embeds the query, asks the vector store for neighbours, hydrates Chunks.

The cosine score is stored on ``Chunk.metadata['score']`` so the grounding stage
can apply a relevance floor without another contract.
"""

from __future__ import annotations

from dataclasses import replace

from aka.contracts.embedder import Embedder
from aka.contracts.vectorstore import VectorStore
from aka.domain.models import Chunk


class VectorRetriever:
    def __init__(self, embedder: Embedder, store: VectorStore) -> None:
        self._embedder = embedder
        self._store = store

    def retrieve(self, query: str, k: int, filters: dict | None = None) -> list[Chunk]:
        query_vec = self._embedder.embed([query])[0]
        scored = self._store.query(query_vec, k=k, filters=filters)
        chunks: list[Chunk] = []
        for chunk_id, score in scored:
            chunk = self._store.get(chunk_id)
            chunks.append(replace(chunk, metadata={**chunk.metadata, "score": score}))
        return chunks
