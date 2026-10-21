"""Run a member's database work as that member's PostgreSQL role.

bed's connection logs in as the ``bed`` role, which has broad rights. A query
made on behalf of a member should run as that member's own ``m_<moniker>``
role, so the database enforces what the member may read and write.

``as_member(args, moniker, conn=...)`` switches the connection to the member's
role for the duration of a ``with`` block and restores the login role after.
It fails closed: if the member has no role, or the login role may not switch to
it, ``PermissionError`` is raised before the block runs, so nothing executes as
the login role on the member's behalf.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from bbsengine6 import database, pgrole


@contextmanager
def as_member(args: Any, moniker: str, **kwargs: Any) -> Generator[None, None, None]:
    """Enter the member's ``m_<moniker>`` role for the block.

    Args:
        args: application args.
        moniker: the authenticated member.
        conn= or pool=: the connection to switch on.

    Raises:
        PermissionError: the member has no role, or the switch is refused.
    """
    conn = kwargs.get("conn")
    pool = kwargs.get("pool")
    if conn is None and pool is None:
        raise ValueError("as_member: conn or pool is required")

    # Lookup only: a request must never provision a database role. A member
    # gets a role when the approval or console flow creates it.
    if conn is not None:
        rolname = pgrole.lookup_login_role(args, moniker, conn=conn)
    else:
        with database.connect(args, pool=pool) as lookup_conn:
            rolname = pgrole.lookup_login_role(args, moniker, conn=lookup_conn)
    if not rolname:
        raise PermissionError(f"no database role for member {moniker!r}")

    try:
        with database.switch_role(args, rolname, **kwargs):
            yield
    except ValueError as exc:
        # switch_role raises ValueError when set_role refuses the switch.
        raise PermissionError(
            f"member {moniker!r} cannot run as {rolname!r}: {exc}"
        ) from exc
