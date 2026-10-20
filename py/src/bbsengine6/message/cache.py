# bbsengine6/message/cache.py
#
# In-memory local unread counter for bbsengine6.message.
#
# Process-local state. In a typical BED/TUI deployment there is one
# TUI process per user, so this is fine. Callers that need
# authoritative counts should fall back to
# ``bbsengine6.message.get_unread_count`` (in ``service.py``) which
# queries the database.
#
# Lives at the package root (not under ``dal/``) because it has no
# DB I/O -- the DAL contract is "talks to Postgres only", mirroring
# ``casino/src/casino/dal/__init__.py``.

from __future__ import annotations

import os
from threading import Event, Lock
from typing import Dict, Optional


_local_unread: Dict[str, int] = {}
# Created at import time. A lazily created lock is itself racy: two threads
# can each see None and each create a different Lock.
_local_lock: Lock = Lock()

# Change notification. Every write bumps the generation and wakes waiters.
# getch() selects on the read end of a self-pipe, so a count change wakes an
# idle keypress wait without polling. The Event serves callers that block.
_generation: int = 0
_changed: Event = Event()
_wake_r, _wake_w = os.pipe()
os.set_blocking(_wake_r, False)
os.set_blocking(_wake_w, False)


def _ensure_lock() -> Lock:
    return _local_lock


def _notify_changed_locked() -> None:
    """Record a change. Caller must hold ``_local_lock``."""
    global _generation
    _generation += 1
    _changed.set()
    try:
        os.write(_wake_w, b"\x01")
    except BlockingIOError:
        # Pipe already holds a wake byte; waiters will see it. Nothing lost.
        pass


def change_generation() -> int:
    """Monotonic counter, bumped on every write. Compare to detect changes."""
    with _ensure_lock():
        return _generation


def change_wake_fd() -> int:
    """Read end of the wake pipe. Readable whenever a change is pending.

    Pass it to ``select`` alongside stdin. Call :func:`drain_change_wake`
    after handling the wake so it does not stay readable.
    """
    return _wake_r


def drain_change_wake() -> None:
    """Empty the wake pipe and clear the Event."""
    try:
        while os.read(_wake_r, 4096):
            pass
    except BlockingIOError:
        pass
    _changed.clear()


def wait_for_change(timeout: Optional[float] = None) -> bool:
    """Block until a write happens (or ``timeout``). True if one arrived."""
    return _changed.wait(timeout)


def get_local_unread_count(moniker: str) -> int:
    with _ensure_lock():
        return _local_unread.get(moniker, -1)


def set_local_unread_count(moniker: str, count: int) -> None:
    with _ensure_lock():
        _local_unread[moniker] = max(0, int(count))
        _notify_changed_locked()


def bump_local_unread_count(moniker: str, delta: int = 1) -> None:
    with _ensure_lock():
        current = _local_unread.get(moniker, 0)
        _local_unread[moniker] = max(0, current + int(delta))
        _notify_changed_locked()


def clear_local_unread_cache() -> None:
    with _ensure_lock():
        _local_unread.clear()
        _notify_changed_locked()
