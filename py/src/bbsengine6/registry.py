"""bbsengine6/registry.py

A generic, instance-based, thread-safe registry of items grouped by scope.

Nothing about the items is interpreted here: no visibility, no tiers, no
letters. Callers supply those rules. Each menu, shell, or host creates its
own ``Registry`` so there is no process-wide state to share or reset.

A scope is an optional name that groups items (for example, a registrar
name such as ``"casino.lib"``). Items without a scope live under ``None``.

Ordering:

  - ``items(scope)`` returns one scope's items in insertion order.
  - ``items()`` returns every item, grouped by scope in sorted scope name
    order (unscoped items first), each group in insertion order. That keeps
    menu drawing deterministic.

``items()`` and ``items(scope)`` return fresh lists, so callers may sort or
filter the result without changing the registry.

Keys are unique within a scope. Adding an existing key in the same scope
replaces the item and keeps its original position.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, Hashable, List, Optional, Tuple


class Registry:
    """Items keyed by ``(scope, key)``. Thread-safe. No global state."""

    def __init__(self) -> None:
        # scope -> {key: item}; dict insertion order gives per-scope ordering.
        self._scopes: Dict[Optional[str], Dict[Hashable, Any]] = {}
        self._lock = threading.RLock()

    def add(self, key: Hashable, item: Any, scope: Optional[str] = None) -> None:
        """Store ``item`` under ``key`` in ``scope``, replacing any item already there."""
        with self._lock:
            self._scopes.setdefault(scope, {})[key] = item

    def remove(self, key: Hashable, scope: Optional[str] = None) -> None:
        """Drop ``key`` from ``scope``. Raises ``KeyError`` if it is not there."""
        with self._lock:
            bucket = self._scopes.get(scope)
            if bucket is None or key not in bucket:
                raise KeyError((scope, key))
            del bucket[key]
            if not bucket:
                del self._scopes[scope]

    def get(self, key: Hashable, scope: Optional[str] = None, default: Any = None) -> Any:
        """Return the item under ``key`` in ``scope``, or ``default`` when absent."""
        with self._lock:
            return self._scopes.get(scope, {}).get(key, default)

    def __contains__(self, key: Hashable) -> bool:
        """True when ``key`` is present in any scope."""
        with self._lock:
            return any(key in bucket for bucket in self._scopes.values())

    def scopes(self) -> List[Optional[str]]:
        """Scope names that currently hold items, unscoped (``None``) first, then sorted."""
        with self._lock:
            return sorted(self._scopes, key=lambda s: (s is not None, s or ""))

    def items(self, scope: Optional[str] = None, *, all_scopes: bool = False) -> List[Any]:
        """Items in one scope, or every item grouped by scope when ``all_scopes`` is set.

        ``items(scope)`` returns that scope's items in insertion order.
        ``items(all_scopes=True)`` returns every item, scopes in sorted order.
        """
        with self._lock:
            if all_scopes:
                out: List[Any] = []
                for name in self.scopes():
                    out.extend(self._scopes[name].values())
                return out
            return list(self._scopes.get(scope, {}).values())

    def keys(self, scope: Optional[str] = None) -> List[Hashable]:
        """Keys in one scope, in insertion order."""
        with self._lock:
            return list(self._scopes.get(scope, {}).keys())

    def clear(self) -> None:
        """Drop every item in every scope."""
        with self._lock:
            self._scopes.clear()

    def __len__(self) -> int:
        with self._lock:
            return sum(len(bucket) for bucket in self._scopes.values())
