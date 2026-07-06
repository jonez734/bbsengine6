"""Console entry point.

Routes ``console <subcommand>`` to the right module. Subcommands
listed in ``bbsengine6.console.lib.BACKEND_SUBCOMMANDS`` are dispatched
to ``bbsengine6.backend.<subcommand>``; all others go to
``bbsengine6.console.<subcommand>``. With no subcommand, the
interactive menu (``bbsengine6.console.main``) is shown.
"""

import sys

from bbsengine6 import io, screen

try:
    import argcomplete

    ARGCOMPLETE_AVAILABLE = True
except ImportError:
    ARGCOMPLETE_AVAILABLE = False

from . import lib


def _terminal_height_safe() -> int:
    getter = getattr(getattr(io, "terminal", None), "height", None)
    if not callable(getter):
        return 24
    try:
        h = getter()
    except Exception:
        return 24
    return h if isinstance(h, int) and h > 0 else 24


if __name__ == "__main__":
    parser, subparsers = lib.build_subcommand_parser()

    if ARGCOMPLETE_AVAILABLE:
        argcomplete.autocomplete(parser)

    args = parser.parse_args()

    try:
        screen.init(args)
        lib.setbottombar(args, "con")
    except SystemExit:
        raise
    except Exception as e:
        io.echo(f"console init failed: {e}", level="error")
        sys.exit(2)

    rc = 0
    try:
        if args.subcommand:
            if lib.handle_subcommand(args, args.subcommand) is False:
                io.echo(f"error running module {args.subcommand}", level="error")
                rc = 1
        else:
            if lib.runmodule(args, "main") is False:
                io.echo("error running module main", level="error")
                rc = 1
    except EOFError:
        io.echo("**EOF**")
    except KeyboardInterrupt:
        io.echo("**INTR**")
    finally:
        io.echo(
            f"{{decsc}}{{curpos:{_terminal_height_safe()},0}}{{el}}{{reset}}{{decrc}}"
        )

    if rc != 0:
        sys.exit(rc)
