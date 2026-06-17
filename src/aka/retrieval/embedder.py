"""Embedder implementations behind the Embedder Protocol.

* SentenceTransformerEmbedder — local, free, real (default).
* HashingEmbedder — deterministic, dependency-free; powers offline/CI runs and
  tests without downloading a model or hitting a network.
"""

from __future__ import annotations

import hashlib
import math
import re

from aka.contracts.embedder import Vector


class SentenceTransformerEmbedder:
    """Wraps a local sentence-transformers model. The heavy import is lazy so the
    package loads (and the fake path runs) without torch installed.
    """

    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer  # lazy

        self._model = SentenceTransformer(model)
        self._dim = int(self._model.get_sentence_embedding_dimension())

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[Vector]:
        arr = self._model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return [row.tolist() for row in arr]


# Common words carry no topic signal; counting them makes every query look similar
# to every document. Dropping them lets the relevance floor actually discriminate.
_STOPWORDS = frozenset(
    """a an and the of to in on for is are be do does did how what when where which
    who why with from this that these those i you it my your our as at by or if can
    should would will into out up down app""".split()
)
_TOKEN = re.compile(r"[a-z0-9]+")


class HashingEmbedder:
    """Deterministic bag-of-tokens hashing embedder. Not semantically strong, but
    stable and offline — ideal for tests and demos without model downloads.
    """

    def __init__(self, dim: int = 64) -> None:
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[Vector]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> Vector:
        vec = [0.0] * self._dim
        for token in _TOKEN.findall(text.lower()):
            if len(token) <= 2 or token in _STOPWORDS:
                continue
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            vec[h % self._dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec
