"""Orchestrates the offline build: load -> split -> embed -> persist + manifest.

Depends only on the Embedder and VectorStore *contracts*, so the same code indexes
with local sentence-transformers or the fake embedder.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aka.contracts.embedder import Embedder
from aka.contracts.vectorstore import VectorStore
from aka.ingestion.loader import load_documents
from aka.ingestion.manifest import fingerprint, is_up_to_date, write_manifest
from aka.ingestion.splitter import split_document


@dataclass
class IngestReport:
    documents: int
    chunks: int
    skipped: bool  # True when the index was already up to date


def build_index(
    docs_dir: str | Path,
    index_dir: str | Path,
    embedder: Embedder,
    store: VectorStore,
    embedding_model_id: str,
    timestamp: str,
    force: bool = False,
) -> IngestReport:
    documents = load_documents(docs_dir)
    fp = fingerprint(documents, embedding_model_id)

    if not force and is_up_to_date(index_dir, fp):
        return IngestReport(documents=len(documents), chunks=0, skipped=True)

    chunks = [c for doc in documents for c in split_document(doc)]
    if chunks:
        vectors = embedder.embed([c.text for c in chunks])
        store.add(chunks, vectors)

    write_manifest(index_dir, fp, chunk_count=len(chunks), timestamp=timestamp)
    return IngestReport(documents=len(documents), chunks=len(chunks), skipped=False)
