# bbsengine6/invite.py
# Generic Invite Code System DAL
#
# Phase 4 of the bbsengine6 modular architecture: a shared invite code
# system in engine.__invite that any module (casino, empyre, murdermotel,
# member) can use to gate access to its resources via short alphanumeric
# codes.
#
# All functions follow the _work(conn) + kwargs.pop("conn") pattern used
# elsewhere in bbsengine6 (see session.py). When called without a conn,
# they open one from the pool attached to args.

from __future__ import annotations

import secrets
from argparse import Namespace
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import database, io


TABLE = "engine.__invite"
VIEW = "engine.invite"


def _generate_code() -> str:
    """Generate a random, URL-safe, hard-to-guess 8-character invite code."""
    return secrets.token_urlsafe(6)


def _row(invite: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a raw invite row from the engine.invite view.

    The view exposes `*epoch` (integer seconds) and `*local` (timestamp in
    caller's timezone) fields alongside the base columns. We keep all of
    them and let callers pick what they need.
    """
    return dict(invite) if invite is not None else invite


def create_invite(
    args: Namespace,
    module: str,
    resourceid: str,
    createdbymoniker: str,
    dateexpires: Optional[Any] = None,
    code: Optional[str] = None,
    casinotablemoniker: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create a new invite code for a module/resource.

    Args:
        args: Application args (used to get a connection/pool).
        module: Owning module name (e.g. 'casino', 'empyre', 'member').
        resourceid: ID of the resource being protected (table, island, etc.).
        createdbymoniker: Moniker of the member creating the invite.
        dateexpires: Optional expiry timestamp (datetime, ISO string, or None).
        code: Optional explicit code. If None, a random 8-char code is generated.
        casinotablemoniker: When module='casino', the casino table moniker.
            Used as a FK to casino.__table so invites are cleaned up when
            the table is deleted.

    Returns:
        Dict with success status. On success, includes id, code,
        datecreated, dateexpires.
    """
    if not module or not resourceid or not createdbymoniker:
        return {
            "success": False,
            "message": "module, resourceid, and createdbymoniker are required",
        }

    if code is None:
        code = _generate_code()

    def _work(conn: Any) -> Dict[str, Any]:
        with database.cursor(conn) as cur:
            cur.execute(
                database.query(
                    """INSERT INTO $engine.__invite
                           (module, resourceid, code, createdbymoniker,
                            datecreated, dateexpires, casinotablemoniker)
                       VALUES (:module, :resourceid, :code, :createdbymoniker,
                               NOW(), :dateexpires, :casinotablemoniker)
                       RETURNING id, module, resourceid, code, createdbymoniker,
                                 datecreated, dateexpires, casinotablemoniker""",
                    module=module,
                    resourceid=resourceid,
                    code=code,
                    createdbymoniker=createdbymoniker,
                    dateexpires=dateexpires,
                    casinotablemoniker=casinotablemoniker,
                )
            )
            row = cur.fetchone()
            if not row:
                return {
                    "success": False,
                    "message": "Insert returned no row",
                }
            return {
                "success": True,
                "message": "Invite created",
                "id": row["id"],
                "code": row["code"],
                "module": row["module"],
                "resourceid": row["resourceid"],
                "datecreated": row["datecreated"],
                "dateexpires": row["dateexpires"],
            }

    conn = kwargs.pop("conn", None)
    if conn is not None:
        return _work(conn)

    try:
        with database.connect(args) as conn:
            return _work(conn)
    except Exception as e:
        io.echo_traceback(f"bbsengine6.invite.create_invite.100: {e}")
        return {"success": False, "message": str(e)}


def get_invites(
    args: Namespace,
    module: str,
    resourceid: str,
    include_revoked: bool = False,
    include_used: bool = False,
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """List invites for a module/resource.

    By default, revoked and already-used invites are filtered out so the
    result contains only currently-usable codes.

    Args:
        args: Application args.
        module: Owning module name.
        resourceid: Resource ID.
        include_revoked: If True, include invites whose `revoked` is set.
        include_used: If True, include invites whose `dateused` is set.

    Returns:
        List of invite dicts ordered by datecreated desc. Empty list on
        error or no matches.
    """
    if not module or not resourceid:
        return []

    def _work(conn: Any) -> List[Dict[str, Any]]:
        clauses = ["module = :module", "resourceid = :resourceid"]
        if not include_revoked:
            clauses.append("revoked IS NULL")
        if not include_used:
            clauses.append("dateused IS NULL")

        where_sql = " AND ".join(clauses)
        template = (
            "SELECT id, module, resourceid, code, createdbymoniker, "
            "datecreated, dateexpires, dateused, usedbymoniker, revoked, "
            "casinotablemoniker, "
            "extract(epoch from datecreated) AS datecreatedepoch, "
            "extract(epoch from dateexpires) AS dateexpiresepoch, "
            "extract(epoch from dateused) AS dateusedepoch, "
            "extract(epoch from revoked) AS revokedepoch "
            "FROM $engine.__invite "
            f"WHERE {where_sql} "
            "ORDER BY datecreated DESC"
        )
        with database.cursor(conn) as cur:
            cur.execute(
                database.query(
                    template,
                    module=module,
                    resourceid=resourceid,
                )
            )
            return [_row(r) for r in cur.fetchall()]

    conn = kwargs.pop("conn", None)
    if conn is not None:
        return _work(conn)

    try:
        with database.connect(args) as conn:
            return _work(conn)
    except Exception as e:
        io.echo_traceback(f"bbsengine6.invite.get_invites.100: {e}")
        return []


def validate_invite(
    args: Namespace,
    module: str,
    resourceid: str,
    code: str,
    **kwargs: Any,
) -> Optional[Dict[str, Any]]:
    """Look up an invite and check whether it is currently valid.

    An invite is valid if:
      - it exists for the given (module, resourceid, code)
      - it has not been revoked (revoked IS NULL)
      - it has not been used (dateused IS NULL)
      - it has not expired (dateexpires IS NULL OR dateexpires > now())

    Returns:
        Invite dict (with id, datecreated, dateexpires, ...) on success,
        or None if not found / not currently valid.
    """
    if not module or not resourceid or not code:
        return None

    def _work(conn: Any) -> Optional[Dict[str, Any]]:
        with database.cursor(conn) as cur:
            cur.execute(
                database.query(
                    """SELECT id, module, resourceid, code, createdbymoniker,
                              datecreated, dateexpires, dateused, usedbymoniker,
                              revoked, casinotablemoniker
                       FROM $engine.__invite
                       WHERE module = :module
                         AND resourceid = :resourceid
                         AND code = :code""",
                    module=module,
                    resourceid=resourceid,
                    code=code,
                )
            )
            row = cur.fetchone()
            if not row:
                return None

            if row.get("revoked") is not None:
                return None
            if row.get("dateused") is not None:
                return None
            expires = row.get("dateexpires")
            if expires is not None:
                now = datetime.now(timezone.utc)
                if hasattr(expires, "tzinfo") and expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if expires <= now:
                    return None
            return _row(row)

    conn = kwargs.pop("conn", None)
    if conn is not None:
        return _work(conn)

    try:
        with database.connect(args) as conn:
            return _work(conn)
    except Exception as e:
        io.echo_traceback(f"bbsengine6.invite.validate_invite.100: {e}")
        return None


def mark_used(
    args: Namespace,
    invite_id: int,
    usedbymoniker: str,
    **kwargs: Any,
) -> bool:
    """Mark an invite as used.

    Refuses to mark an invite that is already used or revoked (idempotent
    guard). Returns True on success, False otherwise.
    """
    if not invite_id or not usedbymoniker:
        return False

    def _work(conn: Any) -> bool:
        with database.cursor(conn) as cur:
            cur.execute(
                database.query(
                    """UPDATE $engine.__invite
                          SET dateused = NOW(),
                              usedbymoniker = :usedbymoniker
                        WHERE id = :id
                          AND dateused IS NULL
                          AND revoked IS NULL""",
                    id=invite_id,
                    usedbymoniker=usedbymoniker,
                )
            )
            return cur.rowcount > 0

    conn = kwargs.pop("conn", None)
    if conn is not None:
        return _work(conn)

    try:
        with database.connect(args) as conn:
            return _work(conn)
    except Exception as e:
        io.echo_traceback(f"bbsengine6.invite.mark_used.100: {e}")
        return False


def revoke_invite(
    args: Namespace,
    invite_id: int,
    **kwargs: Any,
) -> bool:
    """Soft-revoke an invite by setting its `revoked` timestamp.

    Refuses to revoke an invite that is already revoked or already used
    (a code that has been redeemed cannot be un-redeemed; it can only be
    made unusable by leaving it as used). Returns True on success, False
    if the invite is missing, already revoked, or already used.
    """
    if not invite_id:
        return False

    def _work(conn: Any) -> bool:
        with database.cursor(conn) as cur:
            cur.execute(
                database.query(
                    """UPDATE $engine.__invite
                          SET revoked = NOW()
                        WHERE id = :id
                          AND revoked IS NULL
                          AND dateused IS NULL""",
                    id=invite_id,
                )
            )
            return cur.rowcount > 0

    conn = kwargs.pop("conn", None)
    if conn is not None:
        return _work(conn)

    try:
        with database.connect(args) as conn:
            return _work(conn)
    except Exception as e:
        io.echo_traceback(f"bbsengine6.invite.revoke_invite.100: {e}")
        return False
