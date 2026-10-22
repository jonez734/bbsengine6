#!/usr/bin/env python3
"""Create test accounts that exist in engine.__member and have a bank account.

Usage:
    python scripts/make_test_accounts.py --database zoid6test [-n 3]
        [--credentials PATH] [--allow-database] [--reset-passwords] [--with-bank]

Passwords are random (secrets module) and are written only to the credentials
file, never to stdout or the log. The file is created with mode 0600 inside a
0700 directory. Existing accounts keep their password on a rerun; pass
--reset-passwords to change them.

Creates the first N names of: alice, bob, charles, dana, eve, frank, ...
(a generated ``tester<k>`` name is used beyond the named list). For each name:

  * engine.__member row (approved, with an email under @test.local), created
    through the same member path the app uses;
  * a bcrypt password set with member.setpassword, so the account can log in;
  * a bank.__account row, only with --with-bank (bank is skipped by default).

Idempotent: rerunning updates the existing rows rather than failing, and
does not change an existing password unless --reset-passwords is given.

Safety: refuses any database whose name does not start with ``zoid6test``
unless ``--allow-database`` is given, so the script cannot seed the live
database by accident. Pass ``--database zoid6test`` explicitly.

Requires the database to be bootstrapped (engine.__member and bank.__account
must exist). Run ``bbsengine6.startup`` against the target first.
"""

from __future__ import annotations

import argparse
import os
import secrets
import stat
import string
import sys
import types
from pathlib import Path

from bbsengine6 import database, io, member

NAMED = ("alice", "bob", "charles", "dana", "eve", "frank", "grace", "heidi")
EMAIL_DOMAIN = "test.local"
SAFE_PREFIX = "zoid6test"
PASSWORD_LENGTH = 20
PASSWORD_ALPHABET = string.ascii_letters + string.digits
DEFAULT_CREDENTIALS = Path.home() / ".config" / "zoid6" / "test-accounts.md"


def generate_password(length: int = PASSWORD_LENGTH) -> str:
    """A random password from the OS CSPRNG. Never logged; only written to the credentials file."""
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))


def write_credentials(path, creds: dict) -> None:
    """Write moniker/password pairs to ``path``: directory 0700, file 0600."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    lines = [
        "# zoid6 test accounts",
        "",
        "Plaintext passwords for test accounts. Do not commit this file.",
        "",
        "| moniker | password |",
        "| --- | --- |",
    ]
    lines += [f"| {m} | {pw} |" for m, pw in creds.items()]
    lines.append("")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        fh.write("\n".join(lines))
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def member_exists(args, moniker: str, *, pool) -> bool:
    """True if ``moniker`` already has an engine.__member row."""
    with database.connect(args, pool=pool) as conn, database.cursor(conn) as cur:
        cur.execute("SELECT 1 FROM engine.__member WHERE moniker = %s", (moniker,))
        return cur.fetchone() is not None


def names(n: int) -> list[str]:
    """The first ``n`` test account monikers."""
    if n < 1:
        raise ValueError("count must be at least 1")
    out = list(NAMED[:n])
    k = 1
    while len(out) < n:
        out.append(f"tester{k}")
        k += 1
    return out


def _args(database_name: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        debug=False,
        databasename=database_name,
        databasehost=_env("BBSENGINE6_DBHOST", "/var/run/postgresql"),
        databaseport=int(_env("BBSENGINE6_DBPORT", "5432")),
        databaseuser=_env("BBSENGINE6_DBUSER", None),
        databasepassword=_env("BBSENGINE6_DBPASSWORD", None),
        databaseschema="engine",
    )


def _env(key: str, default):
    import os

    return os.environ.get(key, default)


def make_member(args, moniker: str, password: str, *, pool) -> None:
    """Upsert the member row, then set its password through the app path."""
    with database.connect(args, pool=pool) as conn, database.cursor(conn) as cur:
        cur.execute(
            "INSERT INTO engine.__member (moniker, email, approved, loginid) "
            "VALUES (%s, %s, true, %s) "
            "ON CONFLICT (moniker) DO UPDATE SET "
            "email = EXCLUDED.email, approved = true, loginid = EXCLUDED.loginid",
            (moniker, f"{moniker}@{EMAIL_DOMAIN}", moniker),
        )
    if member.setpassword(args, password, moniker, pool=pool) is not True:
        raise RuntimeError(f"setpassword failed for {moniker}")


def make_bank_account(args, moniker: str, *, pool, balance: int = 0) -> None:
    """Open the bank account for ``moniker`` if it does not exist."""
    with database.connect(args, pool=pool) as conn, database.cursor(conn) as cur:
        cur.execute(
            "INSERT INTO bank.__account (moniker, balance) VALUES (%s, %s) "
            "ON CONFLICT (moniker) DO NOTHING",
            (moniker, balance),
        )


def verify(args, moniker: str, password: str, *, pool, with_bank: bool = False) -> bool:
    """Confirm the member exists and can log in; check bank only when it was requested."""
    ok_pw = member.checkpassword(args, password, membermoniker=moniker, pool=pool) is True
    has_bank = True
    with database.connect(args, pool=pool) as conn, database.cursor(conn) as cur:
        cur.execute("SELECT 1 FROM engine.__member WHERE moniker = %s", (moniker,))
        is_member = cur.fetchone() is not None
        if with_bank:
            cur.execute("SELECT 1 FROM bank.__account WHERE moniker = %s", (moniker,))
            has_bank = cur.fetchone() is not None
    return ok_pw and is_member and has_bank


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database", required=True, help="target database name")
    parser.add_argument("-n", "--count", type=int, default=3, help="accounts to create (default 3)")
    parser.add_argument(
        "--credentials",
        default=str(DEFAULT_CREDENTIALS),
        help=f"credentials file to write (default {DEFAULT_CREDENTIALS})",
    )
    parser.add_argument(
        "--allow-database",
        action="store_true",
        help=f"allow a database whose name does not start with {SAFE_PREFIX!r}",
    )
    parser.add_argument(
        "--reset-passwords",
        action="store_true",
        help="give existing accounts a new random password",
    )
    parser.add_argument(
        "--with-bank",
        action="store_true",
        help="also open a bank account for each test member (default: skip bank)",
    )
    parser.add_argument(
        "--bank-balance",
        type=int,
        default=0,
        help="starting balance for bank rows this run creates (default 0; an existing row keeps its balance)",
    )
    opts = parser.parse_args(argv)

    if not opts.database.startswith(SAFE_PREFIX) and not opts.allow_database:
        io.echo(
            f"refusing to seed {opts.database!r}: test accounts are only created in "
            f"databases named {SAFE_PREFIX}*. Pass --allow-database to override.",
            level="error",
        )
        return 2

    args = _args(opts.database)
    try:
        wanted = names(opts.count)
    except ValueError as e:
        io.echo(str(e), level="error")
        return 2

    pool = database.getpool(args)
    failed = []
    creds: dict = {}
    try:
        for moniker in wanted:
            try:
                exists = member_exists(args, moniker, pool=pool)
                if exists and not opts.reset_passwords:
                    io.echo(f"kept {moniker} (exists; password unchanged)", level="ok")
                    # The password is kept, but the bank row is still opened if asked for.
                    if opts.with_bank:
                        make_bank_account(args, moniker, pool=pool, balance=opts.bank_balance)
                    continue
                password = generate_password()
                make_member(args, moniker, password, pool=pool)
                if opts.with_bank:
                    make_bank_account(args, moniker, pool=pool, balance=opts.bank_balance)
                if verify(args, moniker, password, pool=pool, with_bank=opts.with_bank):
                    creds[moniker] = password
                    io.echo(f"ok {moniker}", level="ok")
                else:
                    io.echo(f"verify failed for {moniker}", level="error")
                    failed.append(moniker)
            except Exception as e:
                io.echo(f"{moniker}: {e}", level="error")
                failed.append(moniker)
    finally:
        pool.close()

    if creds:
        write_credentials(opts.credentials, creds)
        io.echo(f"credentials for {len(creds)} account(s) written to {opts.credentials} (mode 0600)", level="ok")
    if failed:
        io.echo(f"failed: {', '.join(failed)}", level="error")
        return 1
    io.echo(f"{len(wanted)} test account(s) ready in {opts.database}: {', '.join(wanted)}", level="ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
