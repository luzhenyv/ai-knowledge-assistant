"""Event sinks implementing the EventSink contract.

* JsonlEventSink — appends one JSON line per event to a file (durable, greppable).
* MemoryEventSink — keeps events in a list (tests).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path


def _to_record(event: object) -> dict:
    record = {"event": type(event).__name__}
    if dataclasses.is_dataclass(event):
        record.update(dataclasses.asdict(event))
    return record


class JsonlEventSink:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def emit(self, event: object) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(_to_record(event), default=str) + "\n")


class MemoryEventSink:
    def __init__(self) -> None:
        self.events: list[object] = []

    def emit(self, event: object) -> None:
        self.events.append(event)
