"""A small persisted NumPy cosine store implementing the VectorStore contract.

Deliberately simple: vectors in an .npz, chunk payloads in a .json. Good enough
for a single-SOP demo and easy to reason about. Swap for Chroma/FAISS by writing
a new VectorStore impl and changing one line in the container — nothing else moves.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from aka.contracts.embedder import Vector
from aka.contracts.vectorstore import ScoredChunkId
from aka.domain.models import Chunk, ImageRef

_VECTORS = "vectors.npz"
_CHUNKS = "chunks.json"


class NumpyVectorStore:
    def __init__(self, index_dir: str | Path) -> None:
        self._dir = Path(index_dir)
        self._ids: list[str] = []
        self._chunks: dict[str, Chunk] = {}
        self._matrix: np.ndarray | None = None  # shape (n, dim), L2-normalised rows

    # ---- write path (ingestion) ----------------------------------------
    def add(self, chunks: list[Chunk], vectors: list[Vector]) -> None:
        self._ids = [c.id for c in chunks]
        self._chunks = {c.id: c for c in chunks}
        self._matrix = _normalise(np.asarray(vectors, dtype=np.float32))
        self._persist()

    def _persist(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        np.savez(self._dir / _VECTORS, matrix=self._matrix, ids=np.array(self._ids, dtype=object))
        payload = [_chunk_to_dict(self._chunks[i]) for i in self._ids]
        (self._dir / _CHUNKS).write_text(json.dumps(payload, indent=2))

    # ---- read path (serving) -------------------------------------------
    def load(self) -> "NumpyVectorStore":
        vec_path = self._dir / _VECTORS
        chunk_path = self._dir / _CHUNKS
        if not vec_path.exists() or not chunk_path.exists():
            raise FileNotFoundError(f"No index found in {self._dir}. Run `aka build` first.")
        data = np.load(vec_path, allow_pickle=True)
        self._matrix = data["matrix"]
        self._ids = list(data["ids"])
        payload = json.loads(chunk_path.read_text())
        self._chunks = {d["id"]: _chunk_from_dict(d) for d in payload}
        return self

    def query(self, vector: Vector, k: int, filters: dict | None = None) -> list[ScoredChunkId]:
        if self._matrix is None or not self._ids:
            return []
        q = _normalise(np.asarray([vector], dtype=np.float32))[0]
        scores = self._matrix @ q  # cosine, since rows + query are normalised
        order = np.argsort(-scores)
        results: list[ScoredChunkId] = []
        for idx in order:
            cid = self._ids[idx]
            if filters and not _matches(self._chunks[cid], filters):
                continue
            results.append((cid, float(scores[idx])))
            if len(results) >= k:
                break
        return results

    def get(self, chunk_id: str) -> Chunk:
        return self._chunks[chunk_id]

    def count(self) -> int:
        return len(self._ids)


def _normalise(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _matches(chunk: Chunk, filters: dict) -> bool:
    return all(chunk.metadata.get(key) == value for key, value in filters.items())


def _chunk_to_dict(c: Chunk) -> dict:
    return {
        "id": c.id,
        "doc_id": c.doc_id,
        "doc_title": c.doc_title,
        "text": c.text,
        "section_path": c.section_path,
        "images": [{"path": im.path, "alt": im.alt} for im in c.images],
        "metadata": c.metadata,
    }


def _chunk_from_dict(d: dict) -> Chunk:
    return Chunk(
        id=d["id"],
        doc_id=d["doc_id"],
        doc_title=d["doc_title"],
        text=d["text"],
        section_path=d["section_path"],
        images=tuple(ImageRef(path=im["path"], alt=im.get("alt", "")) for im in d.get("images", [])),
        metadata=d.get("metadata", {}),
    )
