"""
bbsengine6/menu_next -- menu options for bbsengine6 clients.

Exports the primitives every consumer needs:

  - ``MenuOption``      -- the dataclass that describes an option.
  - ``Registry``        -- the generic registry (``bbsengine6.registry.Registry``),
                          used as a menu: items are ``MenuOption``s, scoped by
                          registrar name.
  - ``visible_options`` -- duck-typed filter against player state.

There is no process-wide menu registry. A host creates its own ``Registry``
for each menu, so menus do not share state.

This subpackage is the new registry. The legacy ``bbsengine6.menu``
module (an interactive bordered ``Menu``/``Item`` UI) is still
importable as ``bbsengine6.menu``; the two coexist because their
names differ (``menu`` vs ``menu_next``).

Import policy:
  - No ``bbsengine6.util``, no ``bbsengine6.database`` -- both transitively
    import ``psycopg`` at module load. This subpackage stays pure.

Example:

    from bbsengine6.menu_next import MenuOption, Registry, visible_options

    menu = Registry()

    # A game module registers its options under its registrar name:
    menu.add("b", MenuOption("b", "Blackjack", "blackjack.play",
                             hide_if_seated_type=frozenset({"blackjack"})),
             scope="casino.blackjack")

    # A consumer (door-mode main menu or WS-client menu) reads them:
    options = menu.items(all_scopes=True)
    visible = visible_options(options, state)
"""

from ..registry import Registry
from .options import MenuOption
from .read import Choice, read_menu
from .visibility import menu_entries, visible_options

__all__ = [
    "Choice",
    "MenuOption",
    "Registry",
    "menu_entries",
    "read_menu",
    "visible_options",
]
