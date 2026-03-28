from __future__ import annotations

import threading
import json
import copy

import psycopg
from psycopg import sql

from . import database, io, util


_threadlocal = threading.local()


def _get_thread_id() -> int:
    return threading.get_ident()


ALLOWED_MEMBER_COLUMNS = frozenset(
    [
        "id",
        "loginid",
        "moniker",
        "name",
        "email",
        "password",
        "credits",
        "attrs",
        "flags",
        "ui",
        "refcode",
        "datecreated",
        "createdbyid",
        "dateupdated",
        "updatedbyid",
        "approvedbyid",
        "dateapproved",
        "lastlogin",
        "lastloginfrom",
    ]
)


def _validate_fields(fields: str, allowed: frozenset = ALLOWED_MEMBER_COLUMNS) -> str:
    if fields == "*":
        return fields
    cols = [c.strip() for c in fields.split(",")]
    for col in cols:
        if col not in allowed:
            raise ValueError(f"Invalid column: {col}")
    return fields


# @since 20221113
def buildrec(member):
    #  rec = {}
    #  for k in ("credits", "attributes", "id", "name", "email", "password", "datecreated", "createdbyid", "dateupdated", "updatedbyid", "approvedbyid", "dateapproved", "lastlogin", "lastloginfrom"): # , "datecreatedepoch", "lastloginepoch", "dateapprovedepoch", "dateupdatedepoch"): # attributes, datecreated, createdbyid
    #    if k == "attributes":
    #      rec[k] = json.dumps(row[k])
    #    else:
    #      rec[k] = row[k]
    #  return rec

    m = {}
    for k, v in member.items():
        if k in (
            "datecreatedepoch",
            "dateapprovedepoch",
            "dateupdatedepoch",
            "lastloginepoch",
            "attrs",
        ):
            continue
        elif type(v) is dict:
            m[k] = json.dumps(database.convert_for_jsonb(v))
            continue
        elif k == "ui" and type(v) is list:
            m[k] = ", ".join(v)
            continue
        else:
            m[k] = v
    return m


def build(args, row={}, **kwargs):
    pool = kwargs.get("pool", None)
    io.echo(f"bbsengine.member.build.140: {kwargs=} {pool=}", level="debug")
    if pool is None:
        return None

    moniker = row.get("moniker", None)
    #    io.echo(f"bbsengine.member.build.400: {row=}", level="debug")
    default_values = {
        "refcode": None,
        "flags": getflags(args, moniker, **kwargs),
        #        "id": None,
        "loginid": None,
        "moniker": None,
        "credits": 100,
        "attrs": {},
        #        "emailverified": False,
        #        "dateemailverified": None,
        #        "emailverifiedbymoniker": None,
        "email": None,
        "password": None,
        "datecreated": "now()",
        "ui": [
            "term",
        ],
    }

    member = {}
    for k in default_values.keys():
        #        io.echo(f"bbsengine.member.build.200: {k=}", level="debug")
        if k in row:
            if k == "ui":
                if row["ui"] is not None:
                    import re

                    member["ui"] = sorted(
                        [item.strip() for item in re.split(r"[ ,]+", row["ui"]) if item]
                    )
                else:
                    member["ui"] = None
            else:
                member[k] = row[k]
        else:
            member[k] = default_values[k]

    io.echo(f"bbsengine6.member.build.100: {member=}", level="debug")
    return member


def getcurrentmoniker(args, **kwargs):
    cached = getattr(_threadlocal, "moniker", None)
    if cached is not None:
        return cached

    def _work(conn):
        loginid = util.getcurrentloginid(args, **kwargs)
        if loginid is None:
            return None
        try:
            with database.cursor(conn) as cur:
                sql = "select moniker from engine.member where loginid=%s"
                dat = (loginid,)
                cur.execute(sql, dat)
                if cur.rowcount == 0:
                    return None
                row = cur.fetchone()
                moniker = row["moniker"]
                _threadlocal.moniker = moniker
                return moniker
        except psycopg.DatabaseError:
            io.echo_traceback(f"bbsengine6.member.getcurrentmoniker.100:")
            return None

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(f"bbsengine.member.getcurrentmoniker.120: pool=None", level="error")
            return None
        with database.connect(args, pool=pool) as conn:
            return _work(conn)
    return _work(conn)


def notifycount(args, **kwargs) -> int:
    """Get total unread notification count for current user.

    Returns:
        Number of unread notifications (queue + database), or 0 if not logged in.
    """
    from bbsengine6 import notify

    moniker = getcurrentmoniker(args, **kwargs)
    if not moniker:
        return 0

    return notify.count(moniker)


def getcurrentid(args, **kwargs):
    cached = getattr(_threadlocal, "id", None)
    if cached is not None:
        return cached

    def _work(cur):
        loginid = util.getcurrentloginid(args)
        if loginid is None:
            return None
        try:
            sql = "select id from engine.member where loginid=%s"
            dat = (loginid,)
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                return None
            rec = cur.fetchone()
            member_id = rec["id"]
            _threadlocal.id = member_id
            if args.debug is True:
                io.echo(f"getcurrentid.120: {member_id=}", level="debug")
            return member_id
        except psycopg.DatabaseError:
            io.echo_traceback(f"bbsengine6.member.getcurrentid.180:")
            return None

    if args.debug is True:
        io.echo(f"bbsengine6.member.getcurrentid.120: cached={cached}", level="debug")

    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            return None
        with database.connect(args, pool=pool) as conn:
            with database.cursor(conn) as cur:
                return _work(cur)
    else:
        with database.cursor(conn) as cur:
            return _work(cur)


# @since 20170303
# def getcurrentlogin(args):
#  # membermap = {"jam" : 1}
#  loginid = pwd.getpwuid(os.geteuid())[0]
#
#  dbh = database.connect(args)
#  cur = dbh.cursor()
#  sql = "select 1 from engine.member where loginid=%s"
#  dat = (loginid,)
#  cur.execute(sql, dat)
#  if cur.rowcount == 0:
#    return None
#  return loginid


def setcredits(args, amount: int, moniker: str | None = None, **kwargs):
    def _work(conn):
        sql = "update engine.__member set credits=%s where moniker=%s"
        dat = (int(amount), moniker)
        with database.cursor(conn) as cur:
            return cur.execute(sql, dat)

    conn = kwargs.get("conn", None)
    if conn is None:
        io.echo(f"bbsengine.member.setcredits.100: conn=None", level="error")
        return None

    if amount is None or int(amount) < 0:
        return None

    if moniker is None:
        moniker = getcurrentmoniker(args, **kwargs)
        if moniker is None:
            io.echo(
                "bbsengine.member.setcredits.120: You do not exist! Go Away!",
                level="error",
            )
            return None

    try:
        return _work(conn)
    except psycopg.DatabaseError:
        io.echo_traceback("bbsengine6.member.setcredits.200:")
        return None


def getcredits(args, membermoniker: str | None = None, **kwargs) -> int | None:
    def _work(conn):
        sql = "select credits from engine.member where moniker=%s"
        dat = (membermoniker,)
        with database.cursor(conn) as cur:
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                return None
            row = cur.fetchone()
            return row["credits"] if "credits" in row else None

    if membermoniker is None:
        membermoniker = getcurrentmoniker(args, **kwargs)
        io.echo(f"bbsengine6.member.getcredits.300: {membermoniker=}", level="debug")
        if membermoniker is None:
            io.echo(
                "bbsengine.member.getcredits.100: You do not exist! Go Away!",
                level="error",
            )
            return None

    try:
        conn = kwargs.get("conn", None)
        if conn is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                io.echo(
                    f"bbsengine6.member.getcredits.200: pool is None", level="error"
                )
                return None
            with database.connect(args, pool=pool) as conn:
                return _work(conn)
        return _work(conn)
    except psycopg.DatabaseError:
        io.echo_traceback("bbsengine6.member.getcredits.200:")
        return None


# def getcurrentmembercredits(args:argparse.Namespace) -> int:
#  memberid = getcurrentmemberid(args)
#  return getmembercredits(args, memberid)

# def getname(args, memberid:int=None) -> str:
#  if memberid is None:
#    memberid = getcurrentid(args)
#
#  dbh = database.connect(args)
#  sql = "select name from engine.member where id=%s"
#  dat = (memberid,)
#  cur = dbh.cursor()
#  cur.execute(sql, dat)
#  res = cur.fetchone()
#  if res is not None and "name" in res:
#    return res["name"]
#  return None

# def getcurrentmembername(args:argparse.Namespace) -> str:
#  currentmemberid = getcurrentmemberid(args)
##  ttyio.echo(f"getcurrentmembername.100: currentmemberid={currentmemberid!r}", level="debug")
#  return getmembername(args, currentmemberid)


def update(args, member, moniker: str | None = None, **kwargs):
    conn = kwargs.get("conn", None)
    if conn is None:
        io.echo(f"bbsengine.member.update.140: conn=None", level="error")
        return None

    if moniker is None:
        moniker = getcurrentmoniker(args, **kwargs)
        if moniker is None:
            io.echo("bbsengine.member.update.150: moniker is None", level="error")
            return None

    def _work(conn):
        database.update(
            args,
            "engine.__member",
            moniker,
            rec,
            primarykey="moniker",
            mogrify=True,
            conn=conn,
        )
        if member.get("flags"):
            for name, data in member["flags"].items():
                io.echo(f"bbsengine6.member.update.100: {name=} {data=}", level="debug")
                setflag(args, name, data["value"], moniker=member["moniker"], conn=conn)

    if "password" in member:
        del member["password"]

    rec = buildrec(member)
    rec.pop("flags", None)

    try:
        return _work(conn)
    except Exception:
        io.echo_traceback("bbsengine6.member.update.120:")
        return None


def getcurrent(args, fields="*", **kwargs) -> dict | None:
    currentid = getcurrentid(args, **kwargs)
    io.echo(f"bbsengine.member.getcurrent.100: {currentid=}", level="debug")
    if currentid is None:
        return None
    return getbyid(args, currentid, fields, **kwargs)


def getbymoniker(
    args, moniker: str | None = None, fields: str = "*", **kwargs
) -> dict | None:
    def _work(cur):
        if moniker is None:
            return None
        validated_fields = _validate_fields(fields)
        sql = f"select {validated_fields}, timezone(tz, lastlogin) from engine.member where moniker=%s"
        dat = (moniker,)
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            return None
        rec = cur.fetchone()
        io.echo(f"bbsengine.member.getbymoniker.120: {rec=}", level="debug")
        return build(args, rec, **kwargs)

    if moniker is None:
        moniker = getcurrentmoniker(args, **kwargs)

    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo(f"bbsengine.member.getbymoniker.100: pool=None", level="error")
        return None

    try:
        with database.connect(args, pool=pool) as conn:
            with database.cursor(conn) as cur:
                return _work(cur)
    except Exception:
        io.echo_traceback("bbsengine6.member.getbymoniker.100:")
        return None


def getbyid(args, memberid: int, fields: str = "*", **kwargs) -> dict | None:
    def _work(cur):
        validated_fields = _validate_fields(fields)
        sql = f"select {validated_fields} from engine.member where id=%s"
        dat = (memberid,)
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            io.echo("bbsengine6.member.getbyid: no rows returned")
            return None
        res = cur.fetchone()
        return build(args, res, **kwargs)

    cur = kwargs.get("cur", None)
    try:
        if cur is None:
            pool = kwargs.get("pool", None)
            with database.connect(args, pool=pool) as conn:
                with database.cursor(conn) as cur:
                    return _work(cur)
        else:
            return _work(cur)
    except Exception:
        io.echo_traceback("bbsengine6.member.getbyid.100:")
        return None


def checkflag(
    args, flag: str, moniker: str | None = None, mogrify: bool = False, **kwargs
):
    def _work(conn):
        if moniker is None:
            return None
        sql = "select * from engine.checkflag(%s, %s)"
        dat = (flag, moniker)
        with database.cursor(conn) as cur:
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                return None
            return cur.fetchone()["checkflag"]

    if moniker is None:
        moniker = getcurrentmoniker(args, **kwargs)
        if moniker is None:
            io.echo(
                "bbsengine.member.checkflag.100: You do not exist! Go away!",
                level="error",
            )
            return None

    if flag is None:
        return None

    try:
        conn = kwargs.get("conn", None)
        if conn is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                io.echo(f"bbsengine.member.checkflag.200: pool=None", level="critical")
                return None
            with database.connect(args, pool=pool) as conn:
                return _work(conn)
        return _work(conn)
    except Exception:
        io.echo_traceback("bbsengine6.member.checkflag.100:")
        return None


def getflags(args, moniker=None, **kwargs):
    io.echo(f"bbsengine.member.getflags.240: {moniker=}", level="debug")

    def _work(conn):
        sql = "select * from engine.getflags(%s)"
        dat = (moniker,)
        with database.cursor(conn) as cur:
            cur.execute(sql, dat)
            flags = {
                flag["name"]: {
                    "description": flag["description"],
                    "value": flag["value"],
                }
                for flag in cur.fetchall()
            }
            io.echo(f"bbsengine.member.getflags.200: {flags=}", level="debug")
            return flags

    io.echo(f"bbsengine.member.getflags.140: {kwargs=}", level="debug")
    try:
        conn = kwargs.get("conn", None)
        if conn is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                io.echo(f"bbsengine.member.getflags.200: pool=None", level="error")
                return None
            with database.connect(args, pool=pool) as conn:
                return _work(conn)
        return _work(conn)
    except Exception:
        io.echo_traceback("bbsengine6.member.getflags.100:")
        return None


def setflag(args, name, value, **kwargs):
    moniker = kwargs.get("moniker", None)
    mogrify = kwargs.get("mogrify", False)
    conn = kwargs.get("conn", None)

    def _work(cur):
        sql = "delete from engine.map_member_flag where moniker=%s and name=%s"
        dat = (moniker, name)

        if mogrify is True:
            io.echo(database.mogrifysql(cur, sql, dat), level="debug")

        cur.execute(sql, dat)

        mmf = {}
        mmf["moniker"] = moniker
        mmf["name"] = name
        mmf["value"] = value

        database.insert(args, "engine.map_member_flag", mmf, returnid=False, conn=conn)
        return None

    if moniker is None:
        moniker = getcurrentmoniker(args, conn=conn)
        if moniker is None:
            return None

    util.logentry(f"setflag({name=}, {value=}, {moniker=})")

    try:
        with database.cursor(conn) as cur:
            return _work(cur)
    except Exception:
        io.echo_traceback("bbsengine6.member.setflag.100:")
        return None


# def getflag(args, name, moniker=None, **kwargs):
#  if moniker is None:
#    moniker = getcurrentmoniker(args)
#    if moniker is None:
#      io.echo("You do not exist! Go away!", level="error")
#      return None
#
#  sql = "select flag.name as name, coalesce(mmf.value, flag.defaultvalue) as value from engine.flag left outer join engine.map_member_flag as mmf on flag.name = mmf.name where flag.name=%s"
#  dat = (name,)
#  sql +="  and mmf.moniker=%s"
#  dat.append(moniker)
#
#  try:
#    with database.connect(args, pool=pool) as conn:
#      with database.cursor(conn) as cur:
#        cur.execute(sql, dat)
#        if cur.rowcount == 0:
#          return None
#        rec = cur.fetchone()
#        return rec["value"]
#  except psycopg.DatabaseError as e:
#    io.echo(f"bbsengine6.member.getflag.100: database error: {e}", level="error")
#    raise

# def updateflag(args, flag, **kwargs):
##  mogrify = kwargs.get("mogrify", False)
##  conn = kwargs.get("conn", database.connect(args))
#
#  sql = "update flag set defaultvalue=%s, description=%s where name=%s"
#  dat = (flag["defaultvalue"], flag["description"], flag["name"])
#  try:
#    with database.connect(args, readonly=False) as conn:
#      with database.cursor(conn) as cur:
#        cur.execute(sql, dat)
#        return
#  except psycopg.DatabaseError as e:
#    io.echo(f"bbsengine6.member.updateflag.100: database error: {e}", level="error")
#    raise

# def getflags(args, membermoniker=None):
#    """Retrieves a dictionary of flags for a member.
#
#    Args:
#        args: A dictionary containing database connection parameters.
#        membermoniker (optional): The unique identifier of the member.
#            If None, returns the flags with default values.
#
#    Returns:
#        A dictionary of flags, where the key is the flag name and the value is
#        a dictionary containing the description and the value (either the member-specific value or the default value from the database, converted to True or False as appropriate).
#    """
#
#    sql = """
#        SELECT flag.name, flag.description,
#               coalesce(engine.map_member_flag.value, flag.defaultvalue) AS value
#        FROM engine.flag
#        LEFT OUTER JOIN engine.map_member_flag ON flag.name = engine.map_member_flag.name
#        AND engine.map_member_flag.moniker = %s
#    """
#
#    try:
#        with database.connect(args) as conn:
#          with database.transaction(conn, readonly=True):
#            with database.cursor(conn) as cur:
#                if membermoniker is None:
#                    # Use None as the parameter when membermoniker is None
#                    cur.execute(sql, (None,))
#                else:
#                    cur.execute(sql, (membermoniker,))
#                flags = {}
#                for row in cur.fetchall():
##                    name, description, value = row
#                    if row["value"].lower() in ('t', 'true', '1'):
#                        value = True
#                    else:
#                        value = False
#                    flags[row["name"]] = {"description": row["description"], "value": row["value"]}
#    except psycopg.DatabaseError as e:
#        io.echo(f"bbsengine6.member.getflags.120: Database error: {e}", level="error")
#        raise
#
#    if args.debug is True:
#      io.echo(f"bbsengine6.member.getflags.100: {flags=}", level="debug")
#    return flags


def setpassword(args, plaintextpassword: str, moniker: str, **kwargs):
    def _setpw(conn):
        with database.cursor(conn=conn) as cur:
            sql = "update engine.__member set password=crypt(%s, gen_salt('bf')) where moniker=%s"
            dat = (plaintextpassword, moniker)
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                return None
            return True

    conn = kwargs.get("conn")
    if conn is None:
        pool = kwargs.get("pool")
        if pool is None:
            io.echo("bbsengine6.setpassword.160: pool=None", level="error")
            return None

        with database.connect(args, pool=pool) as conn:
            return _setpw(conn)
    return _setpw(conn)


def checkpassword(
    args, plaintextpassword: str, membermoniker: str | None = None, **kwargs
):
    def _work(cur):
        if membermoniker is None:
            return None
        sql = "select 1 from engine.member where password=crypt(%s, password) and moniker=%s"
        dat = (plaintextpassword, membermoniker)
        cur.execute(sql, dat)
        io.echo(f"{cur.rowcount=}", level="debug")
        return False if cur.rowcount == 0 else True

    if membermoniker is None:
        membermoniker = getcurrentmoniker(args)
        if membermoniker is None:
            io.echo("You do not exist! Go away!", level="error")
            return None

    io.echo(f"{plaintextpassword=} {membermoniker=}", level="debug")
    try:
        cur = kwargs.get("cur", None)
        if cur is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                io.echo("bbsengine6.checkpassword.100: pool=None", level="error")
                return None
            with database.connect(args, pool=pool) as conn:
                with database.cursor(conn) as cur:
                    return _work(cur)
        return _work(cur)
    except Exception:
        io.echo_traceback("bbsengine6.member.checkpassword.100:")
        return None


def setattrs(args, attrs: dict, moniker=None, **kwargs):
    reset = kwargs.get("reset", False)

    if moniker is None:
        moniker = getcurrentmoniker(args)
        if moniker is None:
            io.echo("You do not exist! Go Away!", level="error")
            return None

    cur = kwargs.get("cur", None)
    if cur is None:
        io.echo("bbsengine.member.setattrs.100: cur=None", level="error")
        return None

    if reset is False:
        q = sql.SQL("update engine.__member set attrs=attrs||%s where moniker=%s")
    else:
        q = sql.SQL("update engine.__member set attrs=%s where moniker=%s")

    dat = (database.Jsonb(attrs), moniker)
    try:
        return cur.execute(q, dat)
    except Exception:
        io.echo_traceback("bbsengine6.member.setattrs.100:")
        return None


def verifyMemberNotFound(args, name, column="loginid", **kwargs):
    io.echo(f"{args=}", level="debug")
    try:
        with database.connect(args, readonly=True) as conn:
            with database.transaction(conn, readonly=True):
                with database.cursor(conn) as cur:
                    sql = f"select 1 from engine.member where {column}=%s"
                    dat = (name,)
                    cur.execute(sql, dat)
                    if cur.rowcount == 0:
                        return True
                    return False
    except Exception:
        io.echo_traceback("bbsengine6.member.verifyMemberNotFound.100:")
        return None


def verifyMemberFound(args, name, **kwargs):
    io.echo(f"verifyMemberFound.100: {kwargs=}", level="debug")
    column = kwargs.get("column", "loginid")
    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(f"bbsengine.verifyMemberFound.160: pool=None", level="error")
            return None
        conn = database.connect(args, pool=pool)
    try:
        with database.cursor(conn) as cur:
            sql = f"select 1 from engine.member where {column}=%s"
            dat = (name,)
            cur.execute(sql, dat)
            return False if cur.rowcount == 0 else True
    except Exception:
        io.echo_traceback("bbsengine6.member.verifyMemberFound.100:")
        return None


def insert(args, member, **kwargs):
    if member is None:
        io.echo(f"bbsengine6.member.insert.120: no member present", level="warn")
        return None
    table = kwargs.get("table", "engine.__member")

    cols = copy.copy(member)
    if "flags" in cols:
        del cols["flags"]
        io.echo(f"bbsengine6.insert.160: removed 'flags' from member", level="warn")
    if "attrs" in cols:
        del cols["attrs"]
        io.echo(f"bbsengine6.insert.140: removed 'attrs' from member")
    if "id" in cols:
        del cols["id"]
        io.echo(f"bbsengine6.insert.200: removed 'id' from member")

    io.echo(f"bbsengine6.member.insert.100: {member=}", level="debug")
    return database.insert(args, table, cols, **kwargs)


def count(args, **kwargs):
    def _work(cur):
        sql = "select count(moniker) from engine.member"
        cur.execute(sql)
        if cur.rowcount == 0:
            return None
        res = cur.fetchone()
        count = res["count"]
        return count

    conn = kwargs.get("conn", None)
    if conn is None:
        io.echo("bbsengine6.member.count.100: conn=None", level="error")
        return None
    try:
        with database.cursor(conn) as cur:
            return _work(cur)
    except Exception:
        io.echo_traceback("bbsengine6.member.count.100:")
        return None
