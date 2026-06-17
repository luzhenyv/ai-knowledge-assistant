"""Records user feedback against a prior interaction id as a FeedbackSubmitted
event. No analysis here — just capture, per the MVP scope.
"""

from __future__ import annotations

from aka.contracts.eventsink import EventSink
from aka.domain.events import FeedbackSubmitted

_VALID_RATINGS = {"yes", "partial", "no"}


def record_feedback(
    sink: EventSink,
    interaction_id: str,
    rating: str,
    note: str,
    timestamp: str,
) -> FeedbackSubmitted:
    rating = rating.lower().strip()
    if rating not in _VALID_RATINGS:
        raise ValueError(f"rating must be one of {sorted(_VALID_RATINGS)}, got {rating!r}")
    event = FeedbackSubmitted(
        interaction_id=interaction_id, rating=rating, note=note, timestamp=timestamp
    )
    sink.emit(event)
    return event
