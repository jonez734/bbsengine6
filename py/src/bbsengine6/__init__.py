# from . import util
# from . import database
# from . import session
# from . import module
# `screen` is the canonical home for the bottombar / screen-positioning
# back-compat shims. bbsengine6.io.screen is pre-registered as an alias
# for this module in bbsengine6/io/__init__.py so every access path
# (bbsengine6.screen, bbsengine6.io.screen, from-import, mock.patch)
# lands on the same module object.
from . import screen
# from . import blurb
# from . import folder
# from . import menu
# from . import listbox
# from . import input
# from . import io

# ``menu_next`` is the menu-option layer: ``MenuOption``, ``visible_options``,
# and ``Registry`` (the generic registry, used as a menu). There is no global
# menu registry; each menu is a ``Registry`` instance. The legacy ``menu``
# module is the bordered terminal ``Menu``/``Item`` UI -- the two coexist
# because their names differ.
from . import menu_next
from .menu_next import MenuOption, visible_options
from .registry import Registry
from .module import (
    register_module,
    unregister_module,
    is_module_registered,
    get_module,
    get_module_api,
    set_require_registration,
    get_require_registration,
    get_all_modules,
    files,
    folder,
)

__all__ = [
    "screen",
    "register_module",
    "unregister_module",
    "is_module_registered",
    "get_module",
    "get_module_api",
    "set_require_registration",
    "get_require_registration",
    "get_all_modules",
    "files",
    "folder",
    "menu_next",
    "MenuOption",
    "Registry",
    "visible_options",
] 
