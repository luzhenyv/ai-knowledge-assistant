"""Events published after a request completes. The chat path emits these; the
observability context (and, later, analytics) subscribes. Neither knows the other.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class InteractionLogged:
    """One completed question/answer turn, ready to be persisted."""

    interaction_id: str
    question: str
    answer_text: str
    grounded: bool
    rejected: bool
    citations: tuple[str, ...]  # "doc_title :: section_path"
    chunk_ids: tuple[str, ...]
    recommendations: tuple[str, ...]
    latency_ms: int
    timestamp: str  # ISO-8601, injected (never wall-clock inside the domain)
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class FeedbackSubmitted:
    """User feedback attached to a prior interaction."""

    interaction_id: str
    rating: str  # "yes" | "partial" | "no"
    note: str
    timestamp: str
