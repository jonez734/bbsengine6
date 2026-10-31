"""Console TUI: the ``bbsengine6.console`` terminal front end.

Launched as ``python -m bbsengine6.console.tui`` or through the ``console``
script. It carries the callables ``module.run`` requires (``init``,
``buildargs``, ``access``, ``main``), so letteredolive's shell can run it too.

``buildargs`` returns the top-level parser: the global console flags, an
optional ``subcommand``, and ``subargs`` (everything after it, unparsed).
``main`` runs the interactive menu (``bbsengine6.console.main``) when there is
no subcommand, and otherwise runs the subcommand through ``module.run``, which
parses ``subargs`` with that subcommand's own ``buildargs``.

Subcommands in ``lib.BACKEND_SUBCOMMANDS`` run from ``bbsengine6.backend``;
the rest run from ``bbsengine6.console``.
"""

import argparse
import sys
from typing import Any, Optional

from bbsengine6 import io, module

from . import lib

PACKAGE = "bbsengine6.console.tui"


def init(args: argparse.Namespace, **kwargs: dict) -> bool | None:
    return True


def access(args: argparse.Namespace, op: str, **kwargs: dict) -> bool | None:
    return True


def help(**kwargs: dict) -> None:
    """Print the TUI's help: the global flags, then every subcommand that can run."""
    parser = buildargs(None)
    io.echo(parser.description or "")
    io.echo("")
    io.echo("global flags:")
    for action in parser._actions:
        if action.option_strings and action.help != argparse.SUPPRESS:
            flags = ", ".join(action.option_strings)
            io.echo(f"  {flags}  {action.help or ''}")
    io.echo("")
    io.echo("subcommands (run without one for the interactive menu):")
    for name in sorted({*lib.CONSOLE_SUBCOMMANDS, *lib.BACKEND_SUBCOMMANDS}):
        io.echo(f"  {name}")


def buildargs(args: argparse.Namespace, **kwargs: dict) -> argparse.ArgumentParser | None:
    """Top-level parser: global flags, an optional subcommand, and its raw words."""
    parser = argparse.ArgumentParser(
        prog="console",
        description="BBS Engine 6 Console - manage your BBS system",
    )
    lib._add_console_args(parser)
    parser.add_argument(
        "subcommand",
        nargs="?",
        default=None,
        help="console module to run; omit for the interactive menu",
    )
    parser.add_argument(
        "subargs",
        nargs=argparse.REMAINDER,
        help="arguments passed to the subcommand",
    )
    return parser


def run_subcommand(args: Any, subcommand: str, subargs: list, **kwargs: Any) -> Optional[bool]:
    """Run one subcommand through ``module.run``, so its own parser and access apply."""
    if subcommand in lib.BACKEND_SUBCOMMANDS:
        return module.run(args, subcommand, package="bbsengine6.backend", argv=subargs, **kwargs)
    if subcommand in lib.CONSOLE_SUBCOMMANDS:
        return module.run(args, f"bbsengine6.console.{subcommand}", argv=subargs, **kwargs)
    io.echo(f"Unknown subcommand: {subcommand}", level="error")
    return False


def run_menu(args: Any, **kwargs: Any) -> Optional[bool]:
    """The interactive console menu, ``bbsengine6.console.main``."""
    from . import main as console_menu

    return console_menu.main(args, **kwargs)


def _terminal_height_safe() -> int:
    getter = getattr(getattr(io, "terminal", None), "height", None)
    if not callable(getter):
        return 24
    try:
        h = getter()
    except Exception:
        return 24
    return h if isinstance(h, int) and h > 0 else 24


def _restore_cursor() -> None:
    """Move the cursor back to the bottom bar and clear it, but only on a real terminal.

    The escape sequences go through ``io.echo``, which raises on a non-TTY stdout.
    A piped or scripted run has nothing to restore.
    """
    if not sys.stdout.isatty():
        return
    io.echo(f"{{decsc}}{{curpos:{_terminal_height_safe()},0}}{{el}}{{reset}}{{decrc}}")


def _dispatch(args: Any, subcommand: Optional[str], subargs: list, **kwargs: Any) -> Optional[bool]:
    if subcommand is None:
        return run_menu(args, **kwargs)
    return run_subcommand(args, subcommand, subargs, **kwargs)


def main(args: argparse.Namespace, **kwargs: dict) -> bool | None:
    """Run the named subcommand, or the interactive menu when none is given.

    Called through ``module.run``, ``args`` is the namespace from :func:`buildargs`,
    so ``subcommand`` and ``subargs`` are already set and the caller owns the
    screen. Returns ``True`` on success and ``False`` when the command failed.

    Called with no arguments, it is the process entry point: :func:`cli` does the
    parsing, bottom-bar setup, and exit code.
    """
    rc = True
    try:
        ok = _dispatch(args, getattr(args, "subcommand", None), list(getattr(args, "subargs", None) or []), **kwargs)
        if ok is False:
            name = getattr(args, "subcommand", None) or "main"
            io.echo(f"error running module {name}", level="error")
            rc = False
    except EOFError:
        io.echo("**EOF**")
    except KeyboardInterrupt:
        io.echo("**INTR**")
    finally:
        _restore_cursor()
    return rc


def cli(argv: list[str] | None = None) -> int:
    """Process entry point for ``python -m`` and the ``console`` script.

    Parses ``argv`` (default ``sys.argv[1:]``), sets up the bottom bar, runs
    :func:`main`, and returns the exit code: 0 on success, 1 when the command
    failed, 2 when the bottom bar could not start.
    """
    from bbsengine6 import bottombar

    parser = buildargs(None)
    try:
        import argcomplete

        argcomplete.autocomplete(parser)
    except ImportError:
        pass
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        bottombar.init(args)
        lib.setbottombar(args, "con")
    except SystemExit:
        raise
    except Exception as e:
        io.echo(f"console init failed: {e}", level="error")
        return 2
    return 0 if main(args) is not False else 1


if __name__ == "__main__":
    sys.exit(cli())
