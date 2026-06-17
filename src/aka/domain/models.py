"""Core value objects shared across every bounded context.

These are intentionally plain, immutable dataclasses with no behaviour and no
dependencies. Everything else in the system depends *inward* on these types.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ImageRef:
    """A reference image (screenshot) anchored to a piece of text.

    Images are first-class content, not decoration: a procedural step such as
    "tap the button shown below" is meaningless without its screenshot.
    """

    path: str
    alt: str = ""


@dataclass(frozen=True)
class Document:
    """A source document before it is split into chunks."""

    id: str
    title: str
    source: str  # relative path of the markdown file
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    """A retrievable unit of knowledge.

    ``section_path`` is the heading breadcrumb (e.g. "5. Visit > Start checklist")
    so citations and prompts can locate the step precisely. ``images`` are the
    screenshots that appear within this chunk.
    """

    id: str
    doc_id: str
    doc_title: str
    text: str
    section_path: str
    images: tuple[ImageRef, ...] = ()
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Citation:
    """Evidence backing an answer. Assembled from the chunks actually used."""

    doc_title: str
    section_path: str
    chunk_id: str
    images: tuple[ImageRef, ...] = ()


@dataclass(frozen=True)
class Answer:
    """Immutable output of the generator: text + the evidence behind it.

    ``grounded`` is False when the system declined to answer (escalation) so the
    caller never has to reconstruct that state from the text.
    """

    text: str
    citations: tuple[Citation, ...] = ()
    grounded: bool = True


@dataclass
class ChatContext:
    """The mutable bus that flows through the pipeline. Each stage reads and
    writes this object and nothing else. There is no global state.
    """

    question: str
    chunks: list[Chunk] = field(default_factory=list)
    answer: Answer | None = None
    recommendations: list[str] = field(default_factory=list)
    rejected: bool = False
    # Free-form scratch space for cross-stage signals (scores, reasons, ids, latency).
    metadata: dict = field(default_factory=dict)
