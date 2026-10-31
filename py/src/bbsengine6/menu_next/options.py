"""
bbsengine6/menu_next/options.py
``MenuOption`` dataclass for the new menu registry.

Verbatim port of ``casino.menu_lib.MenuOption`` into bbsengine6 so
modules outside casino can declare menu options without depending
on the casino package. The dataclass is frozen so registered
options cannot be mutated after construction.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass, field
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
        aliases: other typed names for this option (e.g. ``("hit",)`` on
            ``"game"``). An alias resolves to this option; the stored
            ``letter`` is always what ``read_menu`` returns.
        alias_subcommand: optional mapping of alias name to subcommand name.
            An alias listed here runs that subcommand directly, so ``hit``
            on the ``game`` entry means ``game hit``. Words typed after the
            alias are the subcommand's arguments. Excluded from equality and
            hashing.
        parser: optional ``argparse.ArgumentParser`` built by the owning
            command's ``buildargs()``. ``None`` means the option takes no
            arguments, so extra typed text is rejected. Excluded from
            equality and hashing.
        sysop_only: True when only a sysop may see the option.
        op: access operation name passed to the owning module's
            ``access()`` (e.g. ``"list_tables"``). Used with ``module_path``.
        subcommands: optional mapping of subcommand name to ``MenuOption``.
            Each subcommand carries its own gates. Excluded from equality
            and hashing.
    """

    letter: str
    label: str
    module_path: Optional[str] = None
    requires_seated: bool = False
    allowed_game_types: Optional[frozenset] = None
    hide_if_seated_type: Optional[frozenset] = None
    requires_connected: bool = False
    aliases: tuple = ()
    alias_subcommand: Optional[Mapping] = field(default=None, compare=False)
    parser: Optional[argparse.ArgumentParser] = field(default=None, compare=False)
    sysop_only: bool = False
    op: Optional[str] = None
    subcommands: Optional[Mapping] = field(default=None, compare=False)
