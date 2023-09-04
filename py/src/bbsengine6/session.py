import uuid
from datetime import datetime, timedelta

from psycopg2.extras import Json

import ttyio6 as ttyio

from . import database
from . import member

# same as php version

currentsessionid = None

def build(rec):
    session = {}
    for s in ("id", "expiry", "lastactivity", "data", "ipaddress", "useragent", "datecreated", "dateupdated", "memberid" ):
        session[s] = rec[s]

    print(f"bbsengine6.session.build.100: session={session!r}")

    return session

def start(args):
    global currentsessionid

    garbagecollect(args)

    if currentsessionid is None: # and exists in the database
        session = getmembersession(args)
        if session is False:
            ttyio.echo("multiple sessions detected", level="error")
            return False
        if session is None:
            session = buildsession(args)
            database.insert(args, "engine.__session", session, mogrify=True)
            database.commit(args)
            return True
        else:
            print(f"bbsengine6.session.start.100: session={session!r}")
            currentsessionid = session["id"]
    else:
        session = read(args, currentsessionid) # getmembersession(args, member.getcurrentid())
        if session is None:
            session = buildsession(args)
            database.insert(args, session, sessionid)
            database.commit(args)
            return True
        if type(session) is list and len(session) > 1:
            ttyio.echo(f"multiple sessions for member {member.moniker!r} detected", level="error")
            return False

        currentsessionid = session["id"]

    return True

def getmembersession(args, memberid=None):
    if memberid is None:
        memberid = member.getcurrentid(args)

#    garbagecollect(args)

    dbh = database.connect(args)
    sql = "select * from engine.__session where memberid=%s"
    dat = (memberid,)
    cur = dbh.cursor()
    cur.execute(sql, dat)
    if cur.rowcount == 0:
        return None
    elif cur.rowcount > 1:
        ttyio.echo(f"multiple sessions for member {member.moniker!r} found")
        return False
    rec = cur.fetchone()
    print(f"getmembersession.100: rec={rec!r}")
    return build(rec)

def updatelastactivity(args, sessionid):
    session = read(args, sessionid)
    if session is None:
        return False

    session["lastactivity"] = "now()" # datetime.ctime()
    write(args, session, sessionid)
    dataabase.commit(args)
    return True

def read(args, sessionid=None):
    global currentsessionid

    if sessionid is None:
        if currentsessionid is None:
            ttyio.echo("session not initialized")
            return False
        sessionid = currentsessionid

#    garbagecollect(args)

    ttyio.echo(f"bbsengine6.session.read.100: sessionid={sessionid!r}", level="debug")

    dbh = database.connect(args)
    sql = "select * from engine.session where id=%s"
    dat = (sessionid,)
    cur = dbh.cursor()
    cur.execute(sql, dat)
    if cur.rowcount == 0:
        return None
    rec = cur.fetchone()
    return build(rec)

def write(args, session, sessionid=None):
    global currentsessionid

#    garbagecollect(args)

    if sessionid is None:
        if currentsessionid is None:
            return False
        sessionid = currentsessionid

    ttyio.echo("bbsengine6.session.write.100: session={session!r}")

    session["dateupdated"] = "now()" # datetime.ctime()
    session["lastactivity"] = "now()"

    database.update(args, "engine.__session", sessionid, session, mogrify=True)
    database.commit(args)

def buildsession(args, sessionid=None, data={}):
    if sessionid is None:
        sessionid = str(uuid.uuid1())

    session = {}
    session["id"] = sessionid
    session["memberid"] = member.getcurrentid(args)
    session["expiry"] = datetime.now()+timedelta(days=5) # "now()" # +'42 days'::interval"
    session["lastactivity"] = "now()" # datetime.ctime()
    session["data"] = Json(data)
    session["datecreated"] = "now()"

    if args.debug is True:
        ttyio.echo(f"bbsengine6.session.buildsession.100: session={session!r}", level="debug")
    return session

def get(args, name, memberid=None, default=None):
    session = read(args, memberid)
    ttyio.echo(f"bbsengine6.session.get.100: {session=}", level="debug")
    if session is False or session is None:
        ttyio.echo("session does not exist", level="error")
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

    data = {}
    if type(value) is dict:
        data[name] = Json(value)
    else:
        data[name] = value

    print(f"bbsengine6.session.set.100: data={data!r}")

    if reset is False:
        sql = "update engine.__session set data=data||%%s where id='%s'" % (str(sessionid),)
    else:
        sql = "update engine.__session set data=%%s where id='%s'" % (str(sessionid),)

#    print(f"bbsengine6.session.set.120: data={data!r}")

    dat = (Json(data),)
    dbh = database.connect(args)
    cur = dbh.cursor()
#    if mogrify is True:
#        ttyio.echo("bbsengine6.session.set.100: %s" % (cur.mogrify(sql, dat)), level="debug")
    cur.execute(sql, dat)
    database.commit(args)
    return value

def garbagecollect(args):
    ttyio.echo("bbsengine6.session.garbagecollect.100: running", level="debug")
    sql = "delete from engine.__session where expiry < now()"
    dat = ()
    dbh = database.connect(args)
    cur = dbh.cursor()
    cur.execute(sql)
    database.commit(args)
    return
