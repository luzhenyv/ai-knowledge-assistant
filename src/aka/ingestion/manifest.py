"""Build manifest: records content hashes so ``aka build`` can detect a no-op
rebuild. Reproducible and cheap to diff.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aka.domain.models import Document

MANIFEST_NAME = "manifest.json"


def document_hash(doc: Document) -> str:
    return hashlib.sha256(doc.text.encode("utf-8")).hexdigest()


def fingerprint(documents: list[Document], embedding_model: str) -> dict:
    """A stable description of the inputs that produced the current index."""
    return {
        "embedding_model": embedding_model,
        "documents": {doc.source: document_hash(doc) for doc in sorted(documents, key=lambda d: d.source)},
    }


def read_manifest(index_dir: str | Path) -> dict | None:
    path = Path(index_dir) / MANIFEST_NAME
    if not path.exists():
        return None
    return json.loads(path.read_text())


def write_manifest(index_dir: str | Path, fp: dict, chunk_count: int, timestamp: str) -> None:
    path = Path(index_dir) / MANIFEST_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**fp, "chunk_count": chunk_count, "built_at": timestamp}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def is_up_to_date(index_dir: str | Path, fp: dict) -> bool:
    existing = read_manifest(index_dir)
    if existing is None:
        return False
    return existing.get("embedding_model") == fp["embedding_model"] and existing.get("documents") == fp["documents"]
