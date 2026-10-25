"""Console helpers: argparse builders, subcommand dispatch."""

import argparse

from bbsengine6 import database, io, module

CONSOLE_SUBCOMMANDS = (
    "createdatabase",
    "member",
    "memberapproval",
    "session",
    "showpgrole",
    "channel",
)

BACKEND_SUBCOMMANDS = {
    "bank",
    "checkclasses",
    "checkcreatedb",
    "checkdatabase",
    "checkengine",
    "checkextensions",
    "checkmemberflag",
    "checkfunctions",
    "checkloginid",
    "checkroles",
    "checksuperuser",
    "checkwebserverrole",
}


def _add_console_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")
    parser.add_argument(
        "--require-registration",
        action="store_true",
        dest="require_registration",
        help="Require modules to be registered via ModuleRegistry",
    )

    defaults = {
        "databasename": "zoid6",
        "databasehost": "localhost",
        "databaseuser": None,
        "databaseport": 5432,
        "databasepassword": None,
    }
    database.buildargs(parser, defaults)


# @since 20230518 copied from teos
def buildargs(args=None, **kwargs):
    parser = argparse.ArgumentParser("con")
    _add_console_args(parser)
    return parser


# @since 20230523
def runmodule(args, submodule, *, package="bbsengine6.console", **kwargs):
    return module.runmodule(args, f"{package}.{submodule}", **kwargs)


# @since 20230523 copied from teos
_no_member_warned = False


def _current_moniker(args):
    """The member this process runs as, or None. Read through the member module."""
    from bbsengine6 import member

    return member.getcurrentmoniker(args)


def no_member_right(**kwargs) -> str:
    """Right side of the console bottombar: says when there is no member identity.

    A CLI sysop with no member login has no moniker, so the bar would otherwise be blank.
    This shows "| no member" and logs a single warning per process, so the state is visible
    and the reason is in the log. With a member present it shows nothing extra.
    """
    global _no_member_warned
    args = kwargs.get("args")
    if _current_moniker(args) is not None:
        return ""
    if not _no_member_warned:
        _no_member_warned = True
        io.echo(
            "console: no member identity for this login (no bed or member account matches "
            "the Unix user). Member-only features are unavailable.",
            level="warning",
        )
    return "| no member"


def setbottombar(args, left, **kwargs):
    from bbsengine6 import bottombar

    def _console_right_fragment(**_kw):
        help_suffix = (
            " | F1: Help" if "help" in kwargs and kwargs["help"] is True else ""
        )
        debug_suffix = " | debug" if args is not None and args.debug is True else ""
        member_suffix = no_member_right(args=args)
        member_suffix = f" {member_suffix}" if member_suffix else ""
        return f"con{debug_suffix}{help_suffix}{member_suffix}"

    bottombar.register_bottombar_fragment(_console_right_fragment)
    try:
        bottombar.setbottombar(args, left, **kwargs)
    finally:
        bottombar.unregister_bottombar_fragment(_console_right_fragment)
    return


# @since 20260223 - Argparse subcommand support
def build_subcommand_parser(parser=None, **kwargs):
    """Create or extend parser with subcommands for console modules.

    Console-only subcommands come from ``CONSOLE_SUBCOMMANDS``. The
    backend subcommands (listed in ``BACKEND_SUBCOMMANDS``) are also
    routable via ``console <subcommand>``; they are dispatched in
    ``handle_subcommand`` to ``bbsengine6.backend.<subcommand>``.

    Global flags (``--debug``, ``--verbose``, ``--databasename``, etc.)
    are defined on the top-level parser only. argparse's design requires
    flags to appear before the subcommand name; flags after the
    subcommand are rejected. This is a deliberate trade-off to avoid
    the duplicate-definition gotcha where a flag would silently be
    clobbered by the subparser's default.
    """
    if parser is None:
        parser = argparse.ArgumentParser(
            prog="console",
            description="BBS Engine 6 Console - Manage your BBS system",
            add_help=True,
        )
        _add_console_args(parser)

    subparsers = parser.add_subparsers(dest="subcommand", help="Available modules")

    for cmd_name in (*CONSOLE_SUBCOMMANDS, *sorted(BACKEND_SUBCOMMANDS)):
        subparsers.add_parser(cmd_name, add_help=True)

    return parser, subparsers


def handle_subcommand(args, subcommand, **kwargs):
    """Route a subcommand to the right package.

    Backend utility subcommands (checks, bank, createdatabase) live in
    ``bbsengine6.backend``. Everything else is in ``bbsengine6.console``.
    """
    if subcommand in BACKEND_SUBCOMMANDS:
        return runmodule(args, subcommand, package="bbsengine6.backend", **kwargs)
    if subcommand in CONSOLE_SUBCOMMANDS:
        return runmodule(args, subcommand, **kwargs)
    from bbsengine6 import io

    io.echo(f"Unknown subcommand: {subcommand}", level="error")
    return False
