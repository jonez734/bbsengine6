"""Events and the event log (front-end-seam.md, section 5).

A domain appends events to one bounded log. Each front end holds a Subscription with its own cursor
and its own debug flag, so one front end reading never removes events another has not read.

The log keeps the most recent ``capacity`` events. A subscription that falls further behind gets one
``lagged`` marker, with the count it missed, and then resumes from the oldest event still kept.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, List, Mapping

from .kinds import FRAGMENT_KIND, LAGGED_KIND, MESSAGE_KINDS

DEFAULT_CAPACITY = 1000


@dataclass(frozen=True)
class Event:
    kind: str
    table: str
    moniker: str | None
    payload: Mapping[str, Any]


class EventLog:
    """Bounded, append-only log. ``base`` is the absolute index of the oldest kept event."""

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self.capacity = capacity
        self._items: List[Event] = []
        self._base = 0  # absolute index of self._items[0]
        self._lock = threading.Lock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)

    @property
    def head(self) -> int:
        """Absolute index one past the newest event."""
        with self._lock:
            return self._base + len(self._items)

    def append(self, event: Event) -> None:
        with self._lock:
            self._items.append(event)
            overflow = len(self._items) - self.capacity
            if overflow > 0:
                del self._items[:overflow]
                self._base += overflow

    def since(self, cursor: int) -> tuple[int, List[Event]]:
        """Return (missed, events) from ``cursor`` to the head. ``missed`` is how many were dropped."""
        with self._lock:
            missed = max(0, self._base - cursor)
            start = max(cursor, self._base) - self._base
            return missed, list(self._items[start:])


class Subscription:
    """One front end's view of a log: its cursor, its debug flag, and when it last read."""

    def __init__(self, cursor: int, *, debug: bool, now: float) -> None:
        self.cursor = cursor
        self.debug = debug
        self.last_read = now
