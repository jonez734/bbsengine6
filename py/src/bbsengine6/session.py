from datetime import datetime

from . import database
from . import member

# same as php version

currentsessionid = None

def build(rec):
    session = {}
    for s in ("expiry", "lastactivity", "data", "ipaddress", "useragent", "datecreated", "dateupdated", "memberid" ):
        session[s] = rec[s]
    return session

def start(args):
    if currentsessionid is None: # and exists in the database
        sessionid = "something"
        session = {}
        session["expiry"] = 0
        session["lastactivity"] = datetime.ctime()
        session["data"] = {}
        session["memberid"] = member.getcurrentid(args)
    return False

def updatelastactivity(args, sessionid):
    dbh = database.connect(args)
    session = read(args, sessionid)
    if session is None:
        return False

    session["lastactivity"] = datetime.ctime()
    return write(args, sessionid, session)

def get(args, sessionid):
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
    if sessionid is None:
        sessionid = currentsessionid
    if sessionid is None:
        return False
    session["dateupdated"] = datetime.ctime()
    database.update(args, "engine.__session", sessionid, session)
