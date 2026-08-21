"""
bbsengine6/menu_next/options.py
``MenuOption`` dataclass for the new menu registry.

Verbatim port of ``casino.menu_lib.MenuOption`` into bbsengine6 so
modules outside casino can declare menu options without depending
on the casino package. The dataclass is frozen so registered
options cannot be mutated after construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MenuOption:
    """A single menu option.

    Attributes:
        letter: single lowercase letter; consumer displays ``letter.upper()``.
        label: short label fragment for the inline prompt (e.g. ``"et"``),
            or full label for the help screen (e.g. ``"Blackjack"``).
        module_path: dispatch target (e.g. ``"blackjack.play"``).
        requires_seated: True when the player must be at a table
            (``state.current_table_moniker`` set) for the option to be
            shown.
        allowed_game_types: optional frozenset of game types for which
            the option is meaningful. When set and ``requires_seated``
            is True, the option is hidden unless
            ``state.current_table_game_type`` is in the set (including
            the post-join window when the game type is still ``None``).
        hide_if_seated_type: optional frozenset of game types; when the
            player is seated at a table whose ``game_type`` is in this
            set, the option is hidden. Used to hide game launchers for
            the game the player is already playing.
        requires_connected: True when the player must be connected
            (``state.connected`` truthy) for the option to be shown.
            Typical use: hide ``Disconnect`` when no connection exists.
    """

    letter: str
    label: str
    module_path: Optional[str] = None
    requires_seated: bool = False
    allowed_game_types: Optional[frozenset] = None
    hide_if_seated_type: Optional[frozenset] = None
    requires_connected: bool = False
