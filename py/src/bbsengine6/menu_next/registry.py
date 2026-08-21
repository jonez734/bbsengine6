"""
bbsengine6/menu_next/registry.py
Thread-safe in-process menu-option registry.

Each module that wants menu options calls
``register_menu_options("<registrar_name>", *options)`` from inside
its ``init(args, **kw)`` hook (next to its existing
``register_module(...)`` call). The consumer reads the full set via
``registered_options()`` (sorted by registrar name for deterministic
menu ordering) or per-registrar via ``registered_options(name="...")``.

Registrar names are owned by the calling module. Naming conventions:

  - game modules:  ``"casino.blackjack"``, ``"casino.poker"``,
                   ``"casino.slots"``, ``"casino.yahtzee"``,
                   ``"casino.tictactoe"``
  - command hubs:   ``"casino.commands.game"`` (shared seat-gated ops)
  - core casino:   ``"casino.core"`` (auth, table, bank, chat, admin, maint)

The lock is an ``RLock`` so a registrar can call
``register_menu_options`` re-entrantly from inside another
registration block if needed.
"""

from __future__ import annotations

import threading
from typing import Optional

from .options import MenuOption


_lock = threading.RLock()
_registry: dict[str, list[MenuOption]] = {}


def register_menu_options(name: str, *options: MenuOption) -> None:
    """Append ``options`` to the registry under ``name``.

    Multiple calls with the same ``name`` are allowed; subsequent calls
    extend the registrar's option list (insertion order preserved).
    Passing an empty ``options`` tuple is a no-op.

    Args:
        name: registrar identifier; conventionally the importing
            module's dotted path (e.g. ``"casino.blackjack"``).
        options: zero or more ``MenuOption`` instances to register.
    """
    if not options:
        return
    with _lock:
        bucket = _registry.setdefault(name, [])
        bucket.extend(options)


def registered_options(name: Optional[str] = None) -> list[MenuOption]:
    """Return the registered options.

    With ``name=None`` (default) returns the flat list across all
    registrars, sorted by registrar name so the resulting menu draw
    is deterministic across processes. Each registrar's options keep
    their insertion order within the bucket.

    With ``name="<registrar>"`` returns just that registrar's options
    in insertion order.

    Args:
        name: optional registrar filter; ``None`` returns all.

    Returns:
        List of ``MenuOption`` instances. Returns a fresh list each
        call; callers may sort / filter / mutate the result without
        affecting the registry.
    """
    with _lock:
        if name is not None:
            return list(_registry.get(name, ()))
        out: list[MenuOption] = []
        for registrar in sorted(_registry):
            out.extend(_registry[registrar])
        return out


def clear_registry() -> None:
    """Drop every registered option.

    Test-only helper. Not exported from ``bbsengine6.menu_next.__init__``
    so production code cannot accidentally wipe the registry.
    """
    with _lock:
        _registry.clear()
