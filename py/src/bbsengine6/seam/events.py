"""Event and the event queue (ui-seam.md, section 5).

The queue is the only channel for game progress. Message kinds are the five generic kinds; a game
kind is any other name, and may not reuse a message kind. ``debug`` events are kept only when the
member's debug setting is on, so the queue is quiet by default.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from typing import Any, List, Mapping

MESSAGE_KINDS = frozenset({"debug", "info", "ok", "warning", "error"})
FRAGMENT_KIND = "fragment"
_GAME_KINDS: set[str] = set()


@dataclass(frozen=True)
class Event:
    kind: str
    table: str
    moniker: str | None
    payload: Mapping[str, Any]


def game_kind(name: str) -> str:
    """Validate a game-specific event kind: it must not reuse a message kind's name."""
    if name in MESSAGE_KINDS or name == FRAGMENT_KIND:
        raise ValueError(f"game event kind {name!r} reuses a generic kind")
    return name


def register_game_kind(name: str) -> str:
    """Register a game event kind so the queue accepts it. Returns the name."""
    _GAME_KINDS.add(game_kind(name))
    return name


def _known_kind(kind: str) -> bool:
    return kind in MESSAGE_KINDS or kind == FRAGMENT_KIND or kind in _GAME_KINDS


class EventQueue:
    """FIFO queue of events. Order is preserved per table, and across tables by arrival."""

    def __init__(self, *, debug: bool = False) -> None:
        self._debug = debug
        self._items: deque[Event] = deque()
        self._lock = threading.Lock()

    def put(self, event: Event) -> None:
        if event.kind == "warn":
            raise ValueError("'warn' is not a message kind; use 'warning'")
        if not _known_kind(event.kind):
            raise ValueError(f"unknown event kind: {event.kind!r}")
        if event.kind == "debug" and not self._debug:
            return
        with self._lock:
            self._items.append(event)

    def drain(self) -> List[Event]:
        with self._lock:
            items = list(self._items)
            self._items.clear()
        return items
