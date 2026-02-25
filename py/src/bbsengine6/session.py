import os
import uuid
from datetime import datetime, timedelta
import copy

import psycopg
#from psycopg.types.json import Json
#from psycopg2.extras import Json

#import ttyio6 as ttyio

from . import database, member, io

# same as php version

currentsessionid = None

def build(rec):
#    io.echo(f"bbsengine6.session.120: {rec=} {type(rec)=}", level="debug")

    session = {}
    for s in ("id", "expiry", "lastactivity", "data", "ipaddress", "useragent", "datecreated", "dateupdated", "moniker" ):
#        io.echo(f"{s=}", level="debug")
        session[s] = rec[s]

#    io.echo(f"bbsengine6.session.build.100: {session=}", level="debug")

    return session

def start(args, **kwargs):
    global currentsessionid

    def _work(conn):
        global currentsessionid

###        garbagecollect(args, **kwargs)

        if currentsessionid is None: # and exists in the database
            io.echo("session.start.100: currentsessionid is None", level="debug")
            session = getmembersession(args, **kwargs)
            if session is False:
                io.echo("multiple sessions detected", level="error")
                return False
            if session is None:
                io.echo("session.start.120: creating new session", level="debug")
                session = buildsession(args, **kwargs)
                if args.debug is True:
                    mogrify = True
                else:
                    mogrify = False
                    # io.echo(f"bbsengine6.session.start.120: {session=}", level="debug")
                currentsessionid = database.insert(args, "engine.__session", session, mogrify=mogrify, **kwargs)
                conn.commit()
                return True
            else:
                io.echo(f"bbsengine6.session.start.140: {session=}", level="debug")
                currentsessionid = session["id"]
        else:
            io.echo(f"bbsengine6.session.start.160: reading {currentsessionid=}", level="debug")
            session = read(args, currentsessionid, **kwargs) # getmembersession(args, member.getcurrentid())
            if session is None:
                io.echo(f"read of session returned None", level="debug")
                session = buildsession(args, **kwargs)
                database.insert(args, session, sessionid, **kwargs)
                conn.commit()
                return True
            if type(session) is list and len(session) > 1:
                io.echo(f"multiple sessions for member {member.moniker=} detected", level="error")
                return False

            currentsessionid = session["id"]

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(f"bbsengine6.session.start.180: {pool=}", level="critical")
            return False
        with database.connect(args, pool=pool) as conn:
            return _work(conn)
    return _work(args, conn)

    return True

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
###            io.echo(f"getmembersession.100: {rec=}", level="debug")
            return build(rec)

    if moniker is None:
        moniker = member.getcurrentmoniker(args, **kwargs)
        if moniker is None:
            io.echo("getmembersession.100: You do not exist! Go Away!", level="error")
            return None

#    garbagecollect(args)

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(f"getmembersession.140: {pool=}", level="error")
            return False
        with database.connect(args, pool=pool) as conn:
            return _work(conn)
    else:
        return _work(conn)

def updatelastactivity(args, sessionid, **kwargs):
    def _work(conn):
        import os

        session = read(args, sessionid, **kwargs)
        if session is None:
            return False

        io.echo(f"bbsengine.session.updatelastactivity.120: {session=}", level="debug")

        session["lastactivity"] = "now()" # datetime.ctime()
        session["expiry"] = datetime.now() + timedelta(minutes=15)
        session["useragent"] = os.environ["TERM"] if "TERM" in os.environ else "NEEDINFO"
        write(args, session, sessionid, **kwargs)
        conn.commit()
        return True


    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(f"bbsengine.updatelastactivity.100: {pool=}", level="error")
            return False
        with database.connect(args, pool=pool) as conn:
            return _work(conn)
    else:
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
                    io.echo("bbsengine6.session.read.120: returning None", level="debug")
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

    conn = kwargs.pop("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(f"bbsengine6.session.read.140: {pool=}", level="critical")
            return None
        conn = database.connect(args, pool=pool)
        if conn is False:
            io.echo("bbsengine6.session.read.160: unable to connect to pool", level="critical")
            return None
        return _work(conn)
    
    return _work(conn)

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

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            return False
        with database.connect(pool=pool) as conn:
            return _work(conn)

    if args.debug is True:
        io.echo(f"bbsengine6.session.write.100: {session=}", level="debug")

    if "data" in _session and type(_session["data"]) is dict:
        _session["data"] = database.Jsonb(_session["data"])

    mogrify = True if args.debug is True else False
    database.update(args, "engine.__session", sessionid, _session, mogrify=mogrify, **kwargs)
    conn.commit()

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
    session["expiry"] = datetime.now()+timedelta(hours=2) # "now()" # +'42 days'::interval"
    session["lastactivity"] = "now()" # datetime.ctime()
    session["data"] = database.Jsonb(data)
    session["datecreated"] = "now()"
    session["useragent"] = os.environ["TERM"]

    if args.debug is True:
        io.echo(f"bbsengine6.session.buildsession.100: {session=}", level="debug")
    return session

def get(args, name:str, default=None, memberid:int=None, **kwargs):
    session = getmembersession(args, memberid, **kwargs)
    if args.debug is True:
        io.echo(f"bbsengine6.session.get.100: {session=}", level="debug")

    if session is False or session is None:
        io.echo("session does not exist", level="error")
        return False

    if name in session["data"]:
        return session["data"][name]

    return default

def set(args, name, value, sessionid=None, memberid=None, reset=False, mogrify=True, **kwargs):
    def _work(cur):
        data = {}
        data[name] = value

        if args.debug is True:
            io.echo(f"bbsengine6.session.set.100: {data=}", level="debug")

        if reset is False:
            sql = "update engine.__session set data=data||%s where id=%s"
        else:
            sql = "update engine.__session set data=%s where id=%s"

        dat = (data, sessionid)
        cur.execute(sql, dat)

    if sessionid is None:
        if currentsessionid is None:
            return False
        sessionid = currentsessionid

    if memberid is None:
        memberid = member.getcurrentid(args)
        if memberid is None:
            io.echo("bbsengine6.session.set.100: You do not exist! Go Away!", level="error")
            return None

    conn = kwargs.get("conn", None)
    with database.cursor(conn) as cur:
        _work(cur)
#        conn.commit()
    return value

def garbagecollect(args, **kwargs):
    conn = kwargs.pop("conn", None)
    if conn is None:
        io.echo(f"bbsengine.session.garbagecollect.100: {conn=}", level="error")
        return False
    with database.cursor(conn, **kwargs) as cur:
        sql = "delete from engine.__session where expiry < now()"
        dat = ()
        cur.execute(sql)
        conn.commit()
    return True

def count(args, **kwargs):
    def _work(conn):
        sql:str = "select count(*) from engine.session"
        dat:tuple = ()
        with database.cursor(conn, **kwargs) as cur:
            cur.execute(sql)
            if cur.rowcount == 0:
                return 0

    conn = kwargs.pop("conn", None)
    if conn is None:
        return False
    