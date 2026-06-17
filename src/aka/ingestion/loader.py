"""Reads markdown documents from the docs directory into Document objects.

Markdown is the only loader in the MVP. New sources (PDF, Confluence, ...) become
new loader functions returning Document — no existing code changes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from aka.domain.models import Document


def _doc_id(rel_path: str) -> str:
    return hashlib.sha1(rel_path.encode()).hexdigest()[:12]


def _title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def load_documents(docs_dir: str | Path) -> list[Document]:
    """Load every ``*.md`` file under ``docs_dir`` (recursively)."""
    docs_dir = Path(docs_dir)
    documents: list[Document] = []
    for md_path in sorted(docs_dir.rglob("*.md")):
        rel = md_path.relative_to(docs_dir).as_posix()
        text = md_path.read_text(encoding="utf-8")
        documents.append(
            Document(
                id=_doc_id(rel),
                title=_title(text, fallback=md_path.stem),
                source=rel,
                text=text,
                # Directory of the markdown file, so image refs resolve relative to it.
                metadata={"base_dir": md_path.parent.as_posix()},
            )
        )
    return documents
