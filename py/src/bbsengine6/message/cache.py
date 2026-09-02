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

from threading import Lock
from typing import Dict, Optional


_local_unread: Dict[str, int] = {}
_local_lock: Optional[Lock] = None


def _ensure_lock() -> Lock:
    global _local_lock
    if _local_lock is None:
        _local_lock = Lock()
    return _local_lock


def get_local_unread_count(moniker: str) -> int:
    with _ensure_lock():
        return _local_unread.get(moniker, -1)


def set_local_unread_count(moniker: str, count: int) -> None:
    with _ensure_lock():
        _local_unread[moniker] = max(0, int(count))


def bump_local_unread_count(moniker: str, delta: int = 1) -> None:
    with _ensure_lock():
        current = _local_unread.get(moniker, 0)
        _local_unread[moniker] = max(0, current + int(delta))


def clear_local_unread_cache() -> None:
    with _ensure_lock():
        _local_unread.clear()
