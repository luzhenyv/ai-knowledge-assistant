"""Heading-aware splitter.

Procedural SOPs must not be split by fixed character windows — that severs steps
from their screenshots and headings. We split on markdown headings, keep a section
breadcrumb (``section_path``), and attach every image that appears inside a section
to that section's chunk. Images are first-class content.
"""

from __future__ import annotations

import re

from aka.domain.models import Chunk, Document, ImageRef

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def _images_in(text: str) -> tuple[ImageRef, ...]:
    return tuple(ImageRef(path=m.group(2).strip(), alt=m.group(1).strip()) for m in _IMAGE.finditer(text))


def split_document(doc: Document) -> list[Chunk]:
    """Split one Document into section chunks.

    A chunk is the body under a heading, up to the next heading. The breadcrumb is
    built from the live heading stack (e.g. "Acme Field App SOP > 2. Authorization").
    Content before the first heading is kept as a preamble chunk.
    """
    lines = doc.text.splitlines()
    chunks: list[Chunk] = []
    stack: list[tuple[int, str]] = []  # (heading level, title)
    buf: list[str] = []
    current_path = doc.title  # preamble breadcrumb
    seq = 0

    def flush(path: str) -> None:
        nonlocal seq, buf
        body = "\n".join(buf).strip()
        buf = []
        if not body:
            return
        chunks.append(
            Chunk(
                id=f"{doc.id}::n{seq:03d}",
                doc_id=doc.id,
                doc_title=doc.title,
                text=body,
                section_path=path,
                images=_images_in(body),
                metadata={"source": doc.source, "base_dir": doc.metadata.get("base_dir", "")},
            )
        )
        seq += 1

    for line in lines:
        m = _HEADING.match(line)
        if not m:
            buf.append(line)
            continue
        # New heading: flush the section we were accumulating under the old path.
        flush(current_path)
        level = len(m.group(1))
        title = m.group(2).strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        # Breadcrumb excludes the document's own H1 title (already on the chunk).
        crumbs = [t for lvl, t in stack if not (lvl == 1 and t == doc.title)]
        current_path = " > ".join(crumbs) if crumbs else doc.title

    flush(current_path)
    return chunks
