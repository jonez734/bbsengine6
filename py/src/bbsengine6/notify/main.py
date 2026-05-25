# notify/main.py
# TUI entry point for python -m bbsengine6.notify

from __future__ import annotations

import argparse
from argparse import Namespace
from typing import Optional

from .. import database
from .. import member
from .. import screen
from .. import session
from ..io.echo import echo
from ..io import terminal

from . import tui as tuinotify


def buildargs(args: Optional[Namespace] = None, **kwargs) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bbsengine6-notify",
        description="bbsengine6 notification TUI",
    )
    parser.add_argument(
        "--user",
        dest="user",
        metavar="MONIKER",
        help="User moniker (overrides current session lookup)",
        default=None,
    )
    database.buildargs(parser)
    return parser


def init(args: Namespace, **kwargs) -> bool:
    screen.init(args)
    return True


def access(args: Namespace, op: str, **kwargs) -> bool:
    return True


def main() -> int:
    parser = buildargs()
    args = parser.parse_args()

    init(args)

    try:
        user_pool = None
        if args.databasename:
            system_pool = database.getpool(
                args, dbname="postgres", host=args.databasehost, port=args.databaseport
            )
            if not database.exists(args, args.databasename, pool=system_pool):
                echo(
                    f"Database '{args.databasename}' does not exist.", level="error"
                )
                return 1
            user_pool = database.getpool(
                args, dbname=args.databasename, host=args.databasehost, port=args.databaseport
            )

        try:
            moniker: Optional[str] = None

            if args.user:
                moniker = args.user
            elif user_pool:
                session.start(args, pool=user_pool)
                moniker = member.getcurrentmoniker(args, pool=user_pool)

            if not moniker:
                echo(
                    "No moniker found. Run with --user <name> or log in first.",
                    level="error",
                )
                return 1

            db_args = args if args.databasename else None
            return tuinotify.run(args, moniker, pool=user_pool, db_args=db_args)

        finally:
            if user_pool:
                user_pool.close()

    except KeyboardInterrupt:
        echo("{/all}*INTR*")
    except EOFError:
        echo("{/all}*EOF*")
    finally:
        echo(f"{{decsc}}{{curpos:{terminal.height()},0}}{{el}}{{reset}}{{decrc}}")

    return 0
