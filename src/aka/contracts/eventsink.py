from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EventSink(Protocol):
    """Receives domain events after a request completes. Append-only in the MVP."""

    def emit(self, event: object) -> None:
        ...
