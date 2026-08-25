import sys as _sys
import warnings

# Unify bbsengine6.io.screen with bbsengine6.screen so every access path
# (attribute access, from-import, mock.patch, monkeypatch.setattr) lands on
# the same module object. Without this pre-registration, pytest's import
# isolation can produce two distinct module objects for the same logical
# path, and patches against one don't reach the other — the same family
# of bug documented for bbsengine6.session in
# casino/tests/test_main_dispatch.py:183-193.
#
# Pre-registering here also lets Python's `from bbsengine6.io.screen
# import X` resolve `X` against the canonical module after
# bbsengine6/io/screen.py is removed (Python's `from X import Y` looks
# `X` up in sys.modules first; without this entry the import would
# raise ModuleNotFoundError).
#
# This MUST run before the eager submodule imports below — some of those
# submodules (notably .getch) do `from . import screen` at module load
# time, which would otherwise trigger a circular import against
# bbsengine6.io's own __init__.py.
from bbsengine6 import screen as _canonical_screen
_sys.modules[__name__ + ".screen"] = _canonical_screen


# Import and expose functions from submodules
# Suppress deprecation warnings during import
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    from .echo import (
        echo,
        echo_file,
        echo_traceback,
        exit_on_db_error,
        fatal_on_db_error,
        rendered_length,
        get_cursor_position,
    )
    from .echo import register_emoji, register_emojis, setvar, getvar
    from .echo import load_template, echo_template

    from .inputstring import inputstring
    from .inputinteger import inputinteger
    from .inputboolean import inputboolean
    from .inputchoice import inputchoice

    inputchar = inputchoice  # alias

    from .getch import getch_str as getch
    from .getch import install_signal_handlers

    from .inputcompleter import inputcompleter


def getterminalwidth() -> int:
    """Return the current terminal width in columns (back-compat shim)."""
    from . import terminal

    return terminal.width()


# For backwards compatibility, also expose as module attributes via __getattr__
def __getattr__(name):
    if name == "terminal":
        from . import terminal

        return terminal
    if name == "const":
        from . import const

        return const
    if name == "screen":
        return _canonical_screen
    if name == "getterminalwidth":
        return getterminalwidth
    if name == "setvariable":
        # Legacy alias for setvar.
        from .echo import setvar

        return setvar
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "terminal",
    "const",
    "echo",
    "echo_file",
    "echo_traceback",
    "exit_on_db_error",
    "fatal_on_db_error",
    "rendered_length",
    "get_cursor_position",
    "setvar",
    "setvariable",
    "getvar",
    "register_emoji",
    "register_emojis",
    "load_template",
    "echo_template",
    "inputstring",
    "inputinteger",
    "inputboolean",
    "inputchoice",
    "inputchar",
    "getch",
    "getterminalwidth",
    "install_signal_handlers",
    "inputcompleter",
]
