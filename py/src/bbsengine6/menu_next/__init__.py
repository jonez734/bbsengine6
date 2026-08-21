"""
bbsengine6/menu_next -- menu-option registry for bbsengine6 clients.

Exports the four primitives every consumer needs:

  - ``MenuOption``           -- the dataclass that describes an option.
  - ``register_menu_options`` -- append options under a registrar name.
  - ``registered_options``    -- read the full set (sorted by registrar)
                                or filter by registrar name.
  - ``visible_options``       -- duck-typed filter against player state.

This subpackage is the new registry. The legacy ``bbsengine6.menu``
module (an interactive bordered ``Menu``/``Item`` UI) is still
importable as ``bbsengine6.menu``; the two coexist because their
names differ (``menu`` vs ``menu_next``).

Import policy:
  - No ``bbsengine6.util``, no ``bbsengine6.database`` -- both transitively
    import ``psycopg`` at module load. This subpackage stays pure.

Example:

    # In a game module's __init__.py:
    from bbsengine6.menu_next import MenuOption, register_menu_options

    def init(args, **kw):
        register_module(name="casino.blackjack", ...)
        register_menu_options(
            "casino.blackjack",
            MenuOption("b", "Blackjack", "blackjack.play",
                       hide_if_seated_type=frozenset({"blackjack"})),
        )

    # In a consumer (door-mode main menu or WS-client menu):
    from bbsengine6 import menu_next

    options = tuple(menu_next.registered_options())
    visible = menu_next.visible_options(options, state)
"""

from .options import MenuOption
from .registry import register_menu_options, registered_options
from .visibility import visible_options

__all__ = [
    "MenuOption",
    "register_menu_options",
    "registered_options",
    "visible_options",
]
