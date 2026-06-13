import os
import uuid
import threading
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from typing import Any

import copy

from psycopg import sql

from . import database, member, io


_threadlocal = threading.local()


def _table_identifier(table: str) -> sql.Identifier:
    """Create proper SQL identifier for schema-qualified table names.

    Args:
      table: Table name, optionally qualified with schema (e.g., 'engine.__session')

    Returns:
      sql.Identifier for the table
    """
    if "." in table:
        schema, table_name = table.split(".", 1)
        return sql.Identifier(schema, table_name)
    return sql.Identifier(table)


def getcurrentsessionid() -> str | None:
    return getattr(_threadlocal, "currentsessionid", None)


def setcurrentsessionid(sessionid: str | int | bool | None) -> None:
    _threadlocal.currentsessionid = sessionid


def is_valid(session: dict | None) -> bool:
    if session is None:
        return False
    if not isinstance(session, dict):
        return False
    expiry = session.get("expiry")
    if expiry is None:
        return False
    if isinstance(expiry, str):
        return False
    return expiry > datetime.now(timezone.utc)


def build(rec: dict) -> dict:
    session = {}
    for s in (
        "id",
        "expiry",
        "lastactivity",
        "data",
        "ipaddress",
        "useragent",
        "datecreated",
        "dateupdated",
        "moniker",
    ):
        session[s] = rec[s]
    return session


def start(args: Namespace, **kwargs: Any) -> bool:
    def _work(conn: Any) -> bool:
        currentsessionid = getcurrentsessionid()

        garbagecollect(args, conn=conn)

        if currentsessionid is None:
            io.echo("session.start.100: currentsessionid is None", level="debug")
            session = getmembersession(args, conn=conn)
            if session is False:
                io.echo("multiple sessions detected", level="error")
                return False
            if session is None:
                io.echo("session.start.120: creating new session", level="debug")
                session = buildsession(args, **kwargs)
                if session is None:
                    io.echo("session.start.130: buildsession failed", level="error")
                    return False
                mogrify = True if args.debug else False
                currentsessionid = database.insert(
                    args, "engine.__session", session, mogrify=mogrify, conn=conn
                )
                setcurrentsessionid(currentsessionid)
                conn.commit()
                return True
            else:
                io.echo(f"bbsengine6.session.start.140: {session=}", level="debug")
                if not isinstance(session, dict):
                    io.echo(
                        "session.start.142: session is not a valid dict", level="error"
                    )
                elif not is_valid(session):
                    io.echo(
                        "session.start.145: session expired, will create new session",
                        level="debug",
                    )
                else:
                    currentsessionid = session["id"]
                    setcurrentsessionid(currentsessionid)
                    conn.commit()
                    return True
                io.echo("session.start.150: creating new session", level="debug")
                session = buildsession(args, **kwargs)
                if session is None:
                    io.echo("session.start.160: buildsession failed", level="error")
                    return False
                mogrify = True if args.debug else False
                currentsessionid = database.insert(
                    args, "engine.__session", session, mogrify=mogrify, conn=conn
                )
                setcurrentsessionid(currentsessionid)
                conn.commit()
                return True
        else:
            io.echo(
                f"bbsengine6.session.start.160: reading {currentsessionid=}",
                level="debug",
            )
            session = read(args, currentsessionid, conn=conn)
            if session is None:
                io.echo("read of session returned None", level="debug")
                session = buildsession(args, **kwargs)
                if session is None:
                    io.echo("session.start.170: buildsession failed", level="error")
                    return False
                mogrify = True if args.debug else False
                database.insert(
                    args, "engine.__session", session, mogrify=mogrify, conn=conn
                )
                conn.commit()
                return True
            if isinstance(session, list) and len(session) > 1:
                current_moniker = member.getcurrentmoniker(args, conn=conn)
                io.echo(
                    f"multiple sessions for member moniker={current_moniker} detected",
                    level="error",
                )
                return False
            currentsessionid = session["id"]
            setcurrentsessionid(currentsessionid)

        return True

    conn = kwargs.get("conn", None)
    if conn is not None:
        return _work(conn)

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo("bbsengine6.session.start.100: no conn or pool", level="error")
        return False

    with database.connect(args, pool=pool) as conn:
        return _work(conn)


def getmembersession(
    args: Namespace, moniker: str | None = None, **kwargs: Any
) -> dict | bool | None:
    def _work(conn: Any) -> dict | bool | None:
        query = (
            sql.SQL("SELECT * FROM ")
            + _table_identifier("engine.__session")
            + sql.SQL(" WHERE ")
            + sql.Identifier("moniker")
            + sql.SQL(" = %s")
        )
        dat = (moniker,)
        with database.cursor(conn) as cur:
            cur.execute(query, dat)
            if cur.rowcount == 0:
                return None
            elif cur.rowcount > 1:
                io.echo(f"multiple sessions for member {moniker=} found", level="error")
                return False
            rec = cur.fetchone()
            return build(rec)

    conn = kwargs.pop("conn", None)
    if moniker is None:
        moniker = member.getcurrentmoniker(args, conn=conn, **kwargs)
        if moniker is None:
            io.echo("getmembersession.100: You do not exist! Go Away!", level="error")
            return None
    else:
        kwargs["conn"] = conn  # restore for later use

    if conn is not None:
        result = _work(conn)
        conn.commit()
        return result

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo("bbsengine6.getmembersession.100: no conn or pool", level="error")
        return None

    with database.connect(args, pool=pool) as conn:
        return _work(conn)


def updatelastactivity(args: Namespace, sessionid: str, **kwargs: Any) -> bool:
    def _work(conn: Any) -> bool:
        import os

        session = read(args, sessionid, conn=conn)
        if session is None:
            return False

        io.echo(f"bbsengine.session.updatelastactivity.120: {session=}", level="debug")

        session["lastactivity"] = "now()"
        session["expiry"] = datetime.now(timezone.utc) + timedelta(minutes=15)
        session["useragent"] = os.environ.get("TERM", "NEEDINFO")
        write(args, session, sessionid, conn=conn)
        conn.commit()
        return True

    conn = kwargs.get("conn", None)
    if conn is not None:
        return _work(conn)

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo("bbsengine.updatelastactivity.100: no conn or pool", level="error")
        return False

    with database.connect(args, pool=pool) as conn:
        return _work(conn)


def read(args: Namespace, sessionid: str | None = None, **kwargs: Any) -> dict | None:
    def _work(conn: Any) -> dict | None:
        with database.cursor(conn) as cur:
            sql = "select * from engine.session where id=%s"
            dat = (sessionid,)
            cur.execute(sql, dat)
            if args.debug is True:
                io.echo(f"bbsengine6.session.140: {cur.rowcount=}", level="debug")
            if cur.rowcount == 0:
                if args.debug is True:
                    io.echo(
                        "bbsengine6.session.read.120: returning None", level="debug"
                    )
                return None
            rec = cur.fetchone()
            session = build(rec)
            if not is_valid(session):
                io.echo("session.read.130: session expired or invalid", level="debug")
                return None
            return session

    if sessionid is None:
        currentsessionid = getcurrentsessionid()
        if currentsessionid is None:
            io.echo("session not initialized", level="error")
            return None
        sessionid = currentsessionid

    if args.debug is True:
        io.echo(f"bbsengine6.session.read.100: {sessionid=}", level="debug")

    conn = kwargs.get("conn", None)
    if conn is not None:
        result = _work(conn)
        conn.commit()
        return result

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo("bbsengine6.session.read.100: no conn or pool", level="error")
        return None

    with database.connect(args, pool=pool) as conn:
        return _work(conn)


def write(
    args: Namespace, session: dict, sessionid: str | None = None, **kwargs: Any
) -> bool:
    io.echo(f"bbsengine.session.write.220: {kwargs=}", level="debug")

    if sessionid is None:
        currentsessionid = getcurrentsessionid()
        if currentsessionid is None:
            return False
        sessionid = currentsessionid

    existing_session = read(args, sessionid, **kwargs)
    if not is_valid(existing_session):
        io.echo("session.write.110: session expired or invalid", level="error")
        return False

    _session = copy.deepcopy(session)
    _session["dateupdated"] = "now()"
    _session["lastactivity"] = "now()"

    if args.debug is True:
        io.echo(f"bbsengine6.session.write.100: {_session=}", level="debug")

    if "data" in _session and isinstance(_session["data"], dict):
        _session["data"] = database.Jsonb(_session["data"])

    mogrify = True if args.debug else False

    def _work(conn: Any) -> bool:
        database.update(
            args, "engine.__session", sessionid, _session, mogrify=mogrify, conn=conn
        )
        return True

    conn = kwargs.get("conn", None)
    if conn is not None:
        return _work(conn)

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo("bbsengine6.session.write.100: no conn or pool", level="error")
        return False

    with database.connect(args, pool=pool) as conn:
        return _work(conn)


def buildsession(
    args: Namespace,
    sessionid: str | None = None,
    data: dict | None = None,
    **kwargs: Any,
) -> dict | None:
    if data is None:
        data = {}
    if sessionid is None:
        sessionid = str(uuid.uuid4())

    moniker = member.getcurrentmoniker(args, **kwargs)
    if moniker is None:
        io.echo("buildsession.100: You do not exist! Go Away!", level="error")
        return None

    session = {}
    session["id"] = sessionid
    session["moniker"] = moniker
    session["expiry"] = datetime.now(timezone.utc) + timedelta(hours=2)
    session["lastactivity"] = "now()"
    session["data"] = database.Jsonb(data)
    session["datecreated"] = "now()"
    session["useragent"] = os.environ.get("TERM", "xterm")

    if args.debug is True:
        io.echo(f"bbsengine6.session.buildsession.100: {session=}", level="debug")
    return session


def get(
    args: Namespace,
    name: str,
    default: Any = None,
    memberid: str | None = None,
    **kwargs: Any,
) -> Any:
    session = getmembersession(args, memberid, **kwargs)
    if args.debug is True:
        io.echo(f"bbsengine6.session.get.100: {session=}", level="debug")

    if session is False or session is None:
        io.echo("session does not exist", level="error")
        return False

    if not isinstance(session, dict):
        io.echo("session.get.105: session is not a valid dict", level="error")
        return False

    if not is_valid(session):
        io.echo("session.get.110: session expired or invalid", level="error")
        return False

    if name in session["data"]:
        return session["data"][name]

    return default


def set(
    args: Namespace,
    name: str,
    value: Any,
    sessionid: str | None = None,
    memberid: str | None = None,
    reset: bool = False,
    mogrify: bool = True,
    **kwargs: Any,
) -> Any:
    def _work(conn: Any) -> Any:
        data = {name: value}

        if args.debug is True:
            io.echo(f"bbsengine6.session.set.100: {data=}", level="debug")

        if reset is False:
            query = (
                sql.SQL("UPDATE ")
                + _table_identifier("engine.__session")
                + sql.SQL(" SET ")
                + sql.Identifier("data")
                + sql.SQL(" = ")
                + sql.Identifier("data")
                + sql.SQL(" || %s WHERE ")
                + sql.Identifier("id")
                + sql.SQL(" = %s")
            )
        else:
            query = (
                sql.SQL("UPDATE ")
                + _table_identifier("engine.__session")
                + sql.SQL(" SET ")
                + sql.Identifier("data")
                + sql.SQL(" = %s WHERE ")
                + sql.Identifier("id")
                + sql.SQL(" = %s")
            )

        with database.cursor(conn) as cur:
            cur.execute(query, (database.Jsonb(data), sessionid))
        return value

    if sessionid is None:
        currentsessionid = getcurrentsessionid()
        if currentsessionid is None:
            return False
        sessionid = currentsessionid

    existing_session = read(args, sessionid, **kwargs)
    if not is_valid(existing_session):
        io.echo("session.set.110: session expired or invalid", level="error")
        return False

    pool = kwargs.get("pool", None)
    if memberid is None:
        memberid = (
            member.getcurrentid(args, pool=pool) if pool else member.getcurrentid(args)
        )
        if memberid is None:
            io.echo(
                "bbsengine6.session.set.100: You do not exist! Go Away!", level="error"
            )
            return None

    conn = kwargs.get("conn", None)
    if conn is not None:
        return _work(conn)

    if pool is None:
        io.echo("bbsengine6.session.set.100: no conn or pool", level="error")
        return False

    with database.connect(args, pool=pool) as conn:
        return _work(conn)


def garbagecollect(args: Namespace, **kwargs: Any) -> bool:
    def _work(conn: Any) -> bool:
        with database.cursor(conn) as cur:
            query = (
                sql.SQL("DELETE FROM ")
                + _table_identifier("engine.__session")
                + sql.SQL(" WHERE ")
                + sql.Identifier("expiry")
                + sql.SQL(" < now()")
            )
            cur.execute(query)
        return True

    conn = kwargs.get("conn", None)
    if conn is not None:
        return _work(conn)

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo("bbsengine.session.garbagecollect.100: no conn or pool", level="error")
        return False

    with database.connect(args, pool=pool) as conn:
        return _work(conn)


def count(args: Namespace, **kwargs: Any) -> int:
    def _work(conn: Any) -> int:
        sql = "select count(*) from engine.session"
        with database.cursor(conn) as cur:
            cur.execute(sql)
            if cur.rowcount == 0:
                return 0
            rec = cur.fetchone()
            return rec["count"] if rec else 0

    conn = kwargs.get("conn", None)
    if conn is not None:
        result = _work(conn)
        conn.commit()
        return result

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo("bbsengine.session.count.100: no conn or pool", level="error")
        return 0

    with database.connect(args, pool=pool) as conn:
        result = _work(conn)
        return result
