import warnings

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
        from . import screen

        return screen
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
