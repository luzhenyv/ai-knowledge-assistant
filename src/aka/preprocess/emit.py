"""Stage 5 — write the ingestion-ready artifacts.

Produces ``<out>/sop.md`` (the contract aka.ingestion consumes) and
``<out>/source.json`` (provenance). The raw source file is never copied into the
output tree — only its hash is recorded.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def source_sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def write_output(out_dir: Path, markdown: str, provenance: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "sop.md"
    md_path.write_text(markdown, encoding="utf-8")
    (out_dir / "source.json").write_text(json.dumps(provenance, indent=2, sort_keys=True))
    return md_path
