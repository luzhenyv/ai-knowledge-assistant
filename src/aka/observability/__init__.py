"""Append-only observability: interaction + feedback events. Write-only in the
MVP; a future analytics module reads these events without touching the chat path.
"""

from aka.observability.feedback import record_feedback
from aka.observability.sink import JsonlEventSink, MemoryEventSink

__all__ = ["JsonlEventSink", "MemoryEventSink", "record_feedback"]
