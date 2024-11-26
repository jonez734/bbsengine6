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

def start(args):
    global currentsessionid

    with database.connect(args) as conn:
        garbagecollect(args)
        if currentsessionid is None: # and exists in the database
            if args.debug is True:
                io.echo("session.start.100: currentsessionid is None")
            session = getmembersession(args)
            if session is False:
                io.echo("multiple sessions detected", level="error")
                return False
            if session is None:
                if args.debug is True:
                    io.echo("session.start.120: creating new session")
                session = buildsession(args)
                if args.debug is True:
                    mogrify = True
                else:
                    mogrify = False
#                io.echo(f"bbsengine6.session.start.120: {session=}", level="debug")
                currentsessionid = database.insert(args, "engine.__session", session, mogrify=mogrify)
                conn.commit()
                return True
            else:
                if args.debug is True:
                    io.echo(f"bbsengine6.session.start.140: {session=}", level="debug")
                currentsessionid = session["id"]
        else:
            if args.debug is True:
                io.echo(f"bbsengine6.session.start.160: reading {currentsessionid=}", level="debug")
            session = read(args, currentsessionid) # getmembersession(args, member.getcurrentid())
            if session is None:
                if args.debug is True:
                    io.echo(f"read of session returned None", level="debug")
                session = buildsession(args)
                database.insert(args, session, sessionid)
                conn.commit()
                return True
            if type(session) is list and len(session) > 1:
                io.echo(f"multiple sessions for member {member.moniker!r} detected", level="error")
                return False

            currentsessionid = session["id"]

    return True

def getmembersession(args, moniker=None):
    if moniker is None:
        moniker = member.getcurrentmoniker(args)
        if moniker is None:
            io.echo("getmembersession.100: You do not exist! Go Away!", level="error")
            return None

#    garbagecollect(args)

    with database.connect(args) as conn:
        with database.cursor(conn) as cur:
            sql = "select * from engine.__session where moniker=%s"
            dat = (moniker,)
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                return None
            elif cur.rowcount > 1:
                io.echo(f"multiple sessions for member {moniker=} found", level="warn")
                return False
            rec = cur.fetchone()
            io.echo(f"getmembersession.100: {rec=}", level="debug")
            return build(rec)

def updatelastactivity(args, sessionid):
    import os

    with database.connect(args) as conn:
        session = read(args, sessionid)
        if session is None:
            return False

        if args.debug is True:
            io.echo(f"{session=}", level="log")

        session["lastactivity"] = "now()" # datetime.ctime()
        session["expiry"] = datetime.now() + timedelta(minutes=15)
        session["useragent"] = os.environ["TERM"] if "TERM" in os.environ else "NEEDINFO"
        write(args, session, sessionid)
        conn.commit()
        return True

def read(args, sessionid=None):
    global currentsessionid

    if sessionid is None:
        if currentsessionid is None:
            io.echo("session not initialized", level="error")
            return None
        sessionid = currentsessionid

#    garbagecollect(args)

    if args.debug is True:
        io.echo(f"bbsengine6.session.read.100: {sessionid=}", level="debug")

    sql = "select * from engine.session where id=%s"
    dat = (sessionid,)
    with database.connect(args) as conn:
        with database.cursor(conn) as cur:
            cur.execute(sql, dat)
            if args.debug is True:
                io.echo(f"bbsengine6.session.140: {cur.rowcount=}", level="debug")
            if cur.rowcount == 0:
                if args.debug is True:
                    io.echo("bbsengine6.session.read.120: returning None", level="debug")
                return None
            rec = cur.fetchone()
            return build(rec)

def write(args, session, sessionid=None):
    global currentsessionid

#    garbagecollect(args)

    session["dateupdated"] = "now()"
    session["lastactivity"] = "now()"

    _session = copy.copy(session)

    with database.connect(args) as conn:
        if sessionid is None:
            if currentsessionid is None:
                return False
            sessionid = currentsessionid

        if args.debug is True:
            io.echo(f"bbsengine6.session.write.100: {session=}", level="debug")

        if "data" in _session and type(_session["data"]) is dict:
            _session["data"] = database.Jsonb(_session["data"])

        mogrify = True if args.debug is True else False
        database.update(args, "engine.__session", sessionid, _session, mogrify=mogrify)
        conn.commit()

def buildsession(args, sessionid=None, data={}):
    if sessionid is None:
        sessionid = str(uuid.uuid1())

    moniker = member.getcurrentmoniker(args)
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

def get(args, name:str, default=None, memberid:int=None):
    session = getmembersession(args, memberid)
    if args.debug is True:
        io.echo(f"bbsengine6.session.get.100: {session=}", level="debug")

    if session is False or session is None:
        io.echo("session does not exist", level="error")
        return False

    if name in session["data"]:
        return session["data"][name]

    return default

def set(args, name, value, sessionid=None, memberid=None, reset=False, mogrify=True):
    if sessionid is None:
        if currentsessionid is None:
            return False
        sessionid = currentsessionid

    if memberid is None:
        memberid = member.getcurrentid(args)
        if memberid is None:
            io.echo("bbsengine6.session.set.100: You do not exist! Go Away!", level="error")
            return None

    data = {}
#    if type(value) is dict:
#        data[name] = Json(value)
#    else:
    data[name] = value

    if args.debug is True:
        io.echo(f"bbsengine6.session.set.100: {data=}", level="debug")

    if reset is False:
        sql = "update engine.__session set data=data||%s where id=%s"
    else:
        sql = "update engine.__session set data=%s where id=%s"

    dat = (data, sessionid)
    with database.connect(args) as conn:
        with database.cursor(conn) as cur:
            cur.execute(sql, dat)
            conn.commit()
    return value

def garbagecollect(args):
    io.echo("bbsengine6.session.garbagecollect.100: running", level="debug")
    sql = "delete from engine.__session where expiry < now()"
    dat = ()
    with database.connect(args) as conn:
        with database.cursor(conn) as cur:
            cur.execute(sql)
        conn.commit()
    return
