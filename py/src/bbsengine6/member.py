import pwd
import time
import json
import copy

import psycopg
from psycopg import sql

from . import database, io, util


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
            m[k] = json.dumps(v)
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


currentmoniker = None


def getcurrentmoniker(args, **kwargs):
    def _work(conn):
        # io.echo(f"engine.member.getcurrentmoniker.200: {loginid=}", level="debug")
        try:
            with database.cursor(conn) as cur:
                sql = "select moniker from engine.member where loginid=%s"
                dat = (loginid,)
                cur.execute(sql, dat)
                if cur.rowcount == 0:
                    return None
                row = cur.fetchone()
                return row["moniker"]
        except psycopg.DatabaseError as e:
            io.echo(
                f"bbsengine6.member.getcurrentmoniker.100: database error: {e}",
                level="error",
            )
            raise
        return None

    loginid = util.getcurrentloginid(
        args, **kwargs
    )  # works on windows, too. @project:8158

    conn = kwargs.get("conn", None)
    io.echo(f"getcurrentmoniker: {conn=}", level="debug")
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(f"bbsengine.member.getcurrentmoniker.120: {pool=}", level="error")
            return None
        with database.connect(args, pool=pool) as conn:
            return _work(conn)
    return _work(conn)


# @since 20230517 copied from bbsengine5
# @since 20241205 upgraded to psycopg3 (connection pooling)
currentid = None


def getcurrentid(args, **kwargs):
    def _work(cur):
        sql = "select id from engine.member where loginid=%s"
        dat = (loginid,)
        cur.execute(sql, dat)

        if cur.rowcount == 0:
            return None
        rec = cur.fetchone()

        currentid = rec["id"]
        if args.debug is True:
            io.echo(f"getcurrentid.120: {currentid=}", level="debug")
        return currentid

    if args.debug is True:
        io.echo(f"bbsengine6.member.getcurrentid.120: {currentid=}", level="debug")

    if currentid is not None:
        return currentid

    loginid = util.getcurrentloginid(args)

    if args.debug is True:
        io.echo(f"bbsengine6.member.getcurrentid.140: {loginid=}", level="debug")

    try:
        conn = kwargs.get("conn", None)
        if conn is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                return None
            conn = database.connect(args, pool=pool)
        with database.cursor(conn) as cur:
            return _work(cur)
    except psycopg.DatabaseError as e:
        io.echo(
            f"bbsengine6.member.getcurrentid.180: database error: {e}", level="error"
        )
        raise


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


# @since 20230517 copied from bbsengine5
def setcredits(args, amount: int, moniker: str = None, **kwargs):
    """Sets the credits for a member.

    Args:
        args: A dictionary containing database connection parameters.
        amount: The amount of credits to set.
        membermoniker (optional): The unique identifier of the member.
            If None, uses the current member's moniker.

    Returns:
        The number of rows affected by the update.

    History:
      gemini, 2024-10-12
      jam, 2024-10-12 added a database.transaction() call
    """

    def _work(conn):
        sql = "update engine.__member set credits=%s where moniker=%s"
        dat = (int(amount), moniker)
        with database.cursor(conn) as cur:
            return cur.execute(sql, dat)

    conn = kwargs.get("conn", None)
    if conn is None:
        io.echo(f"bbsengine.member.setcredits.100: {conn=}", level="error")
        return False

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
    except psycopg.DatabaseError as e:
        io.echo(f"Database error: {e}", level="error")
        raise


# @since 20230517 copied from bbsengine5
def getcredits(args, membermoniker: str = None, **kwargs) -> int:
    """Retrieves the credits for a member.

    Args:
        args: A dictionary containing database connection parameters.
        membermoniker (optional): The unique identifier of the member.
            If None, uses the current member's moniker.

    Returns:
        The member's credits, or None if the member does not exist.
    """

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
    except psycopg.DatabaseError as e:
        io.echo(f"Database error: {e}", level="error")
        raise


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


# @since 20221111
def update(args, member, moniker=None, **kwargs):
    conn = kwargs.get("conn", None)
    if conn is None:
        io.echo(f"bbsengine.member.update.140: {conn=}", level="error")
        return False

    if moniker is None:
        moniker = getcurrentmoniker(args, **kwargs)

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
        for name, data in member["flags"].items():
            io.echo(f"bbsengine6.member.update.100: {name=} {data=}", level="debug")
            setflag(args, name, data["value"], moniker=member["moniker"], conn=conn)
        return

    if "password" in member:
        del member["password"]

    rec = buildrec(member)
    flags = rec.pop("flags", getflags(args, moniker, conn=conn))
    #  if "flags" in rec:
    #    flags = rec["flags"]
    #    del rec["flags"]

    try:
        return _work(conn)
    except Exception as e:
        io.echo(f"bbsengine6.member.update.120: exception {e}", level="error")
        raise

    return


# @since 20210203
def getcurrent(args, fields="*", **kwargs) -> dict:
    currentid = getcurrentid(args, **kwargs)
    io.echo(f"bbsengine.member.getcurrent.100: {currentid=}", level="debug")
    return getbyid(args, currentid, fields, **kwargs)


# @since 20190924
# @since 20210203
def getbymoniker(args, moniker: str = None, fields: str = "*", **kwargs) -> dict:
    def _work(cur):
        sql = f"select {fields}, timezone(tz, lastlogin) from engine.member where moniker=%s"
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
        io.echo(f"bbsengine.member.getbymoniker.100: {pool=}", level="error")
        return None

    with database.connect(args, pool=pool) as conn:
        with database.cursor(conn) as cur:
            return _work(cur)


# @since 20200731
def getbyid(args, memberid: int, fields: str = "*", **kwargs) -> dict:
    def _work(cur):
        sql = f"select {fields} from engine.member where id=%s"
        dat = (memberid,)
        cur.execute(sql, dat)
        if cur.rowcount == 0:
            io.echo("bbsengine6.member.getbyid: no rows returned")
            return None
        res = cur.fetchone()
        return build(args, res, **kwargs)

    cur = kwargs.get("cur", None)
    if cur is None:
        pool = kwargs.get("pool", None)
        with database.connect(args, pool=pool) as conn:
            with database.cursor(conn) as cur:
                return _work(cur)
    else:
        return _work(cur)


# @since 20230521 copied from bbsengine5
def checkflag(args, flag: str, moniker: str = None, mogrify: bool = False, **kwargs):
    def _work(conn):
        sql = "select * from engine.checkflag(%s, %s)"
        dat = (flag, moniker)
        with database.cursor(conn) as cur:
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                return None
            return cur.fetchone()["checkflag"]

    if moniker is None:
        ##    io.echo(f"bbsengine6.member.checkflag.220: getcurrentmoniker", level="debug")
        moniker = getcurrentmoniker(args, **kwargs)
        ##    io.echo(f"getcurrentmoniker done {moniker=}", level="debug")
        if moniker is None:
            io.echo(
                "bbsengine.member.checkflag.100: You do not exist! Go away!",
                level="error",
            )
            return None

    if flag is None:
        ##    io.echo("bbsengine.member.checkflag.120: {flag=}", level="error")
        return None

    ##  io.echo(f"bbsengine.member.checkflag.140: {flag=} {moniker=}", level="debug")
    try:
        conn = kwargs.get("conn", None)
        if conn is None:
            pool = kwargs.get("pool", None)
            if pool is None:
                io.echo(f"bbsengine.member.checkflag.200: {pool=}", level="critical")
                return None
            with database.connect(args, pool=pool) as conn:
                return _work(conn)
        else:
            return _work(conn)
    except psycopg.DatabaseError as e:
        io.echo(f"bbsengine6.member.checkflag.100: database error {e}", level="error")
        raise


def getflags(args, moniker=None, **kwargs):
    ##  if moniker is None:
    ##    moniker = getcurrentmoniker(args)

    io.echo(f"bbsengine.member.getflags.240: {moniker=}", level="debug")

    def _work(conn):
        sql = "select * from engine.getflags(%s)"
        dat = (moniker,)
        try:
            with database.cursor(conn) as cur:
                cur.execute(sql, dat)
                # Return a dict with flag name as the key and description + value as nested dict
                flags = {
                    flag["name"]: {
                        "description": flag["description"],
                        "value": flag["value"],
                    }
                    for flag in cur.fetchall()
                }
                io.echo(f"bbsengine.member.getflags.200: {flags=}", level="debug")
                return flags
                # return {flag['name']: flag['value'] for flag in cur.fetchall()}
        except Exception as e:
            io.echo(f"bbsengine.member.getflags.220: {e}", level="error")
            raise

    io.echo(f"bbsengine.member.getflags.140: {kwargs=}", level="debug")
    try:
        conn = kwargs.get("conn", None)
        if conn is None:
            io.echo(f"bbsengine.member.getflags.160: {conn=}", level="error")
            pool = kwargs.get("pool", None)
            if pool is None:
                io.echo(f"bbsengine.member.getflags.200: {pool=}", level="error")
                conn = database.connect(pool)
                if conn is None:
                    io.echo(
                        f"bbsengine.member.getflags.220: unable to connect()",
                        level="error",
                    )
                    return None
                with conn:
                    return _work(conn)
        return _work(conn)
    except Exception as e:
        io.echo(f"bbsengine6.member.getflags.100: {e}", level="error")
        raise


# @since 20230523 copied from bbsengine5
def setflag(args, name, value, **kwargs):  # moniker=None, mogrify=False,):
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

    #  conn = kwargs.get("conn", database.connect(args))
    if moniker is None:
        moniker = getcurrentmoniker(args, conn=conn)
        if moniker is None:
            return False

    util.logentry(f"setflag({name=}, {value=}, {moniker=})")

    with database.cursor(conn) as cur:
        return _work(cur)


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


# @since 20230523 copied from bbsengine5
def setpassword(args, plaintextpassword: str, moniker: str, **kwargs) -> bool:
    def _setpw(conn):
        with database.cursor(conn=conn) as cur:
            sql = "update engine.__member set password=crypt(%s, gen_salt('bf')) where moniker=%s"
            dat = (plaintextpassword, moniker)
            rows = cur.execute(sql, dat)
            io.echo(f"member.setpassword.100: {rows} row updated", level="debug")
            if cur.rowcount == 0:
                return False
            return True

    conn = kwargs.get("conn")
    if conn is None:
        pool = kwargs.get("pool")
        if pool is None:
            io.echo("bbsengine6.setpassword.160: {pool=}", level="error")
            return False

        with database.connect(args, pool=pool) as conn:
            return _setpw(conn)
    return _setpw(conn)


# @since 20240901
def checkpassword(
    args, plaintextpassword: str, membermoniker: str = None, **kwargs
) -> bool:
    def _work(cur):
        sql = "select 1 from engine.member where password=crypt(%s, password) and moniker=%s"
        dat = (plaintextpassword, membermoniker)
        cur.execute(sql, dat)
        io.echo(f"{cur.rowcount=}", level="debug")
        return False if cur.rowcount == 0 else True

        if membermoniker is None:
            membermoniker = getcurrentmoniker(args)
            if membermoniker is None:
                io.echo("You do not exist! Go away!", level="error")
                return False

        io.echo(f"{plaintextpassword=} {membermoniker=}", level="debug")
        cur = kwargs.get("cur", None)
        if cur is None:
            pool = kwargs.get("pool", None)
            with database.connect(args, pool=pool) as conn:
                with database.cursor(conn) as cur:
                    return _work(cur)
        else:
            return _work(cur)


# @since 20230523 copied from bbsengine5
def setattrs(
    args, attrs: dict, moniker=None, **kwargs
):  # reset:bool=False, moniker=None, conn=None):
    reset = kwargs.get("reset", False)

    if moniker is None:
        moniker = getcurrentmoniker(conn)
        if moniker is None:
            io.echo("You do not exist! Go Away!", level="error")
            return None

    cur = kwargs.get("cur", None)
    if cur is None:
        io.echo("bbsengine.member.setattrs.100: {cur=}", level="error")
        return False

    if reset is False:
        q = sql.SQL("update engine.__member set attrs=attrs||%s where moniker=%s")
    else:
        q = sql.SQL("update engine.__member set attrs=%s where moniker=%s")

    dat = (database.Jsonb(attrs), moniker)  # {"attrs":attrs, "moniker":moniker}
    return cur.execute(q, dat)


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
    except Exception as e:
        io.echo(f"bbsengine6.member.verifyMemberNotFound.100: {e}", level="error")
        raise


def verifyMemberFound(args, name, **kwargs):
    io.echo(f"verifyMemberFound.100: {kwargs=}", level="debug")
    column = kwargs.get("column", "loginid")
    conn = kwargs.get("conn", None)
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(f"bbsengine.verifyMemberFound.160: {pool=}", level="error")
            return None
        conn = database.connect(args, pool=pool)
    try:
        with database.cursor(conn) as cur:
            sql = f"select 1 from engine.member where {column}=%s"
            dat = (name,)
            cur.execute(sql, dat)
            return False if cur.rowcount == 0 else True
    except psycopg.DatabaseError as e:
        io.echo(
            f"bbsengine6.member.verifyMemberFound.100: database error {e}",
            level="error",
        )


def insert(args, member, **kwargs):
    if member is None:
        io.echo(f"bbsengine6.member.insert.120: no member present", level="warn")
        return None
    table = kwargs.get("table", "engine.__member")
    primarykey = kwargs.get("primarykey", "moniker")
    returnid = kwargs.get("returnid", True)
    mogrify = kwargs.get("mogrify", True)
    #  conn = kwargs.get("conn", None)

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
    return database.insert(
        args, table, cols, **kwargs
    )  # table, member, returnid=returnid, primarykey=primarykey, mogrify=mogrify)


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
    with database.cursor(conn) as cur:
        return _work(cur)
