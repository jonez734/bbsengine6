#!/usr/bin/env python3
"""Logged-in terminal session that shows the notification bell.

Usage (run as the account that can reach the database, from the venv):

    python scripts/bell_harness.py --database zoid6 --moniker alice

It asks for the password at a prompt (never on argv, never echoed), logs the
member in with member.checkpassword, and then waits for keys with getch_str.
getch_str rings the bell when there are unread messages for the logged-in
moniker, so this is a real bell test. Press q to quit.

Polling only: a session here has no bed push subscription, so the bell comes
from the 2-second poll in getch_str, not from a server push.
"""

from __future__ import annotations

import argparse
import getpass
import sys
import types

from bbsengine6 import database, io, member
from bbsengine6.member import _threadlocal
from bbsengine6.io.getch import getch_str


def _args(database_name: str) -> types.SimpleNamespace:
    import os

    return types.SimpleNamespace(
        debug=False,
        databasename=database_name,
        databasehost=os.environ.get("BBSENGINE6_DBHOST", "/var/run/postgresql"),
        databaseport=int(os.environ.get("BBSENGINE6_DBPORT", "5432")),
        databaseuser=os.environ.get("BBSENGINE6_DBUSER"),
        databasepassword=os.environ.get("BBSENGINE6_DBPASSWORD"),
        databaseschema="engine",
    )


def login(args, moniker: str, password: str):
    """Check the password through the member path. On success, set the session moniker.

    Returns the moniker, or None when the login is refused. The password is not logged.
    """
    ok = member.checkpassword(args, password, membermoniker=moniker)
    if ok is not True:
        return None
    _threadlocal.moniker = moniker
    return moniker


def wait_loop(*, timeout: float, max_iterations: int) -> int:
    """Wait for keys until q is pressed or the iteration bound is reached.

    Returns how many getch_str calls were made.
    """
    count = 0
    while count < max_iterations:
        count += 1
        key = getch_str(timeout=timeout)
        if key in ("q", "Q"):
            break
    return count


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database", required=True)
    parser.add_argument("--moniker", required=True)
    parser.add_argument("--max-iterations", type=int, default=3600)
    opts = parser.parse_args(argv)

    args = _args(opts.database)
    password = getpass.getpass(f"password for {opts.moniker}: ")
    moniker = login(args, opts.moniker, password)
    del password
    if moniker is None:
        io.echo("login refused", level="error")
        return 1

    io.echo(f"logged in as {moniker}. Press q to quit. Waiting for messages.", level="ok")
    calls = wait_loop(timeout=2.0, max_iterations=opts.max_iterations)
    io.echo(f"session ended after {calls} wait(s)", level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
