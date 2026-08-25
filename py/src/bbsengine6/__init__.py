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

# ``menu_next`` is the new menu-option registry (dataclass +
# in-process registry + visibility filter). The legacy ``menu``
# module is the bordered terminal ``Menu``/``Item`` UI -- the two
# coexist because their names differ. ``from bbsengine6 import
# menu_next`` enables qualified access (``menu_next.registered_options()``);
# the symbols are also re-exported flat below for callers that prefer
# ``from bbsengine6 import MenuOption``.
from . import menu_next
from .menu_next import MenuOption, register_menu_options, registered_options, visible_options
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
    "register_menu_options",
    "registered_options",
    "visible_options",
] 
