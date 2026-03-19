import os
import uuid
from datetime import datetime, timedelta
import copy

from . import database, member, io


currentsessionid = None


def build(rec):
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


def start(args, **kwargs):
    global currentsessionid

    def _work(conn):
        global currentsessionid

        if currentsessionid is None:
            io.echo("session.start.100: currentsessionid is None", level="debug")
            session = getmembersession(args, conn=conn)
            if session is False:
                io.echo("multiple sessions detected", level="error")
                return False
            if session is None:
                io.echo("session.start.120: creating new session", level="debug")
                session = buildsession(args, **kwargs)
                mogrify = True if args.debug else False
                currentsessionid = database.insert(
                    args, "engine.__session", session, mogrify=mogrify, conn=conn
                )
                conn.commit()
                return True
            else:
                io.echo(f"bbsengine6.session.start.140: {session=}", level="debug")
                currentsessionid = session["id"]
                conn.commit()
        else:
            io.echo(
                f"bbsengine6.session.start.160: reading {currentsessionid=}",
                level="debug",
            )
            session = read(args, currentsessionid, conn=conn)
            if session is None:
                io.echo("read of session returned None", level="debug")
                session = buildsession(args, **kwargs)
                mogrify = True if args.debug else False
                database.insert(
                    args, "engine.__session", session, mogrify=mogrify, conn=conn
                )
                conn.commit()
                return True
            if isinstance(session, list) and len(session) > 1:
                io.echo(
                    f"multiple sessions for member {member.moniker=} detected",
                    level="error",
                )
                return False
            currentsessionid = session["id"]

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


def getmembersession(args, moniker=None, **kwargs):
    def _work(conn):
        sql = "select * from engine.__session where moniker=%s"
        dat = (moniker,)
        with database.cursor(conn) as cur:
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                return None
            elif cur.rowcount > 1:
                io.echo(f"multiple sessions for member {moniker=} found", level="error")
                return False
            rec = cur.fetchone()
            return build(rec)

    if moniker is None:
        moniker = member.getcurrentmoniker(args, **kwargs)
        if moniker is None:
            io.echo("getmembersession.100: You do not exist! Go Away!", level="error")
            return None

    conn = kwargs.get("conn", None)
    if conn is not None:
        result = _work(conn)
        conn.commit()
        return result

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo("bbsengine6.getmembersession.100: no conn or pool", level="error")
        return None

    with database.connect(args, pool=pool) as conn:
        result = _work(conn)
        conn.commit()
        return result


def updatelastactivity(args, sessionid, **kwargs):
    def _work(conn):
        import os

        session = read(args, sessionid, conn=conn)
        if session is None:
            return False

        io.echo(f"bbsengine.session.updatelastactivity.120: {session=}", level="debug")

        session["lastactivity"] = "now()"
        session["expiry"] = datetime.now() + timedelta(minutes=15)
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


def read(args, sessionid=None, **kwargs):
    global currentsessionid

    def _work(conn):
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
            return build(rec)

    if sessionid is None:
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
        result = _work(conn)
        conn.commit()
        return result


def write(args, session, sessionid=None, **kwargs):
    global currentsessionid
    io.echo(f"bbsengine.session.write.220: {kwargs=}", level="debug")

    if sessionid is None:
        if currentsessionid is None:
            return False
        sessionid = currentsessionid

    session["dateupdated"] = "now()"
    session["lastactivity"] = "now()"

    _session = copy.copy(session)

    if args.debug is True:
        io.echo(f"bbsengine6.session.write.100: {session=}", level="debug")

    if "data" in _session and isinstance(_session["data"], dict):
        _session["data"] = database.Jsonb(_session["data"])

    mogrify = True if args.debug else False

    def _work(conn):
        database.update(
            args, "engine.__session", sessionid, _session, mogrify=mogrify, conn=conn
        )
        conn.commit()
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


def buildsession(args, sessionid=None, data={}, **kwargs):
    if sessionid is None:
        sessionid = str(uuid.uuid1())

    moniker = member.getcurrentmoniker(args, **kwargs)
    if moniker is None:
        io.echo("buildsession.100: You do not exist! Go Away!", level="error")
        return None

    session = {}
    session["id"] = sessionid
    session["moniker"] = moniker
    session["expiry"] = datetime.now() + timedelta(hours=2)
    session["lastactivity"] = "now()"
    session["data"] = database.Jsonb(data)
    session["datecreated"] = "now()"
    session["useragent"] = os.environ.get("TERM", "xterm")

    if args.debug is True:
        io.echo(f"bbsengine6.session.buildsession.100: {session=}", level="debug")
    return session


def get(args, name: str, default=None, memberid: int = None, **kwargs):
    session = getmembersession(args, memberid, **kwargs)
    if args.debug is True:
        io.echo(f"bbsengine6.session.get.100: {session=}", level="debug")

    if session is False or session is None:
        io.echo("session does not exist", level="error")
        return False

    if name in session["data"]:
        return session["data"][name]

    return default


def set(
    args,
    name,
    value,
    sessionid=None,
    memberid=None,
    reset=False,
    mogrify=True,
    **kwargs,
):
    def _work(conn):
        data = {name: value}

        if args.debug is True:
            io.echo(f"bbsengine6.session.set.100: {data=}", level="debug")

        if reset is False:
            sql = "update engine.__session set data=data||%s where id=%s"
        else:
            sql = "update engine.__session set data=%s where id=%s"

        with database.cursor(conn) as cur:
            cur.execute(sql, (data, sessionid))
        conn.commit()
        return value

    if sessionid is None:
        if currentsessionid is None:
            return False
        sessionid = currentsessionid

    if memberid is None:
        memberid = member.getcurrentid(args)
        if memberid is None:
            io.echo(
                "bbsengine6.session.set.100: You do not exist! Go Away!", level="error"
            )
            return None

    conn = kwargs.get("conn", None)
    if conn is not None:
        return _work(conn)

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo("bbsengine6.session.set.100: no conn or pool", level="error")
        return False

    with database.connect(args, pool=pool) as conn:
        return _work(conn)


def garbagecollect(args, **kwargs):
    def _work(conn):
        with database.cursor(conn) as cur:
            sql = "delete from engine.__session where expiry < now()"
            cur.execute(sql)
        conn.commit()
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


def count(args, **kwargs):
    def _work(conn):
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
        conn.commit()
        return result
