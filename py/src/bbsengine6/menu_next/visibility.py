"""
bbsengine6/menu_next/visibility.py
``visible_options`` filter for the new menu registry.

Verbatim port of ``casino.menu_lib.visible_options`` into bbsengine6.
The helper is duck-typed so consumers (door-mode ``casino.main``,
WS-client ``casino.client.menu``, per-game submenus) can pass any
state object exposing ``current_table_moniker``,
``current_table_game_type``, and ``connected`` attributes.

Import policy:
  - ``bbsengine6.util`` is FORBIDDEN because it transitively imports
    ``bbsengine6.database`` which loads ``psycopg`` at module load.
    Don't add ``from bbsengine6 import util`` to this file; route any
    utility calls through the consumer's already-imported bbsengine6
    symbols. ``bbsengine6.io`` is permitted (psycopg-free at module
    load) but this filter doesn't need it today.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Optional

from .options import MenuOption


def visible_options(
    spec: Iterable[MenuOption],
    state: Any,
    check: Optional[Callable[[str, str], Any]] = None,
) -> list[MenuOption]:
    """Return the subset of ``spec`` the player may currently pick.

    ``check(module_path, op)`` is an optional callable that gates an option
    through its owning module's ``access()``. It is consulted only for an
    option that has both ``module_path`` and ``op``; it must return exactly
    ``True`` for the option to pass. Any other value (``False``, ``None``,
    or an exception) hides the option.

    ``sysop_only`` options are hidden unless ``state.is_sysop`` is truthy.

    The ``state`` object is duck-typed. The helper reads:

    - ``state.current_table_moniker`` (truthy means seated)
    - ``state.current_table_game_type`` (string or ``None``)
    - ``state.connected`` (truthy means a connection is open)

    Missing attributes are treated as ``None`` / ``False`` so partial
    state objects (e.g. a freshly-constructed ``CasinoPlayer`` before
    ``_load()`` finishes) do not raise.

    Gates run in this order:

    1. ``requires_seated`` -- drop if not seated.
    2. ``allowed_game_types`` (combined with ``requires_seated``) --
       drop if the seated table's game type is unknown or outside the
       set. Covers the brief window between ``join_table`` and the
       first ``game_state`` reply.
    3. ``hide_if_seated_type`` -- drop if the player is seated at a
       table whose game type is in the set (e.g. hide the Blackjack
       launcher when already at a blackjack table).
    4. ``requires_connected`` -- drop if no connection.

    The order matters only when multiple gates would fire on the same
    option; any firing gate drops the option.
    """
    seated = bool(state and getattr(state, "current_table_moniker", None))
    gt_raw = getattr(state, "current_table_game_type", None)
    gt = (gt_raw.strip() if isinstance(gt_raw, str) else None) or None
    connected = bool(getattr(state, "connected", False))
    sysop = bool(getattr(state, "is_sysop", False))
    out: list[MenuOption] = []
    for opt in spec:
        if opt.sysop_only and not sysop:
            continue
        if opt.requires_seated and not seated:
            continue
        if opt.requires_seated and opt.allowed_game_types and gt not in opt.allowed_game_types:
            continue
        if opt.hide_if_seated_type and seated and gt in opt.hide_if_seated_type:
            continue
        if opt.requires_connected and not connected:
            continue
        if check is not None and opt.module_path and opt.op:
            if not _passes_check(check, opt.module_path, opt.op):
                continue
        out.append(opt)
    return out


def _passes_check(check: Callable[[str, str], Any], module_path: str, op: str) -> bool:
    """True only when ``check`` returns exactly ``True``. Exceptions count as denied."""
    try:
        return check(module_path, op) is True
    except Exception:
        return False


def menu_entries(
    spec: Iterable[MenuOption],
    state: Any,
    check: Optional[Callable[[str, str], Any]] = None,
) -> list[tuple[MenuOption, bool]]:
    """Return every option with an ``enabled`` flag, for help rendering.

    Unlike :func:`visible_options`, disabled options are kept so a help screen
    can show them dimmed. ``enabled`` follows the same gates as
    :func:`visible_options`.
    """
    items = list(spec)
    enabled = {id(o) for o in visible_options(items, state, check)}
    return [(opt, id(opt) in enabled) for opt in items]
