import os
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
    if k in ("datecreatedepoch", "dateapprovedepoch", "dateupdatedepoch", "lastloginepoch", "attrs"):
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

def build(args, row={}):
    member = {}
    default_values = {
        "refcode": None,
        "flags": getflags(args),  # Use libmember.getflags() for default flags
        "id": None,
        "loginid": None,
        "moniker": None,
        "credits": 100,
        "attrs": {},
        "emailverified": False,
        "dateemailverified": None,
        "emailverifiedbymoniker": None,
        "email": None,
        "password": None,
        "datecreated": "now()",
        "ui": []
    }

    for k in default_values.keys():
        if k in row:
          if k == "ui":
            import re
            member["ui"] = sorted([item.strip() for item in re.split(r"[ ,]+", row["ui"]) if item])
          else:
            member[k] = row[k]
        else:
          member[k] = default_values[k]

    if args.debug is True:
      io.echo(f"bbsengine6.member.build.100: {member=}", level="debug")
    return member

currentid = None
def getcurrentmoniker(args):
  loginid = os.getlogin() # works on windows, too. @project:8158

  sql = "select moniker from engine.member where loginid=%s"
  dat = (loginid,)
  try:
    with database.connect(args) as conn:
      with database.transaction(conn, readonly=True) as txn:
        with database.cursor(conn) as cur:
          cur.execute(sql, dat)
          if cur.rowcount == 0:
            return None
          row = cur.fetchone()
          return row["moniker"]
  except psycopg.DatabaseError as e:
    io.echo(f"bbsengine6.member.getcurrentmoniker.100: database error: {e}", level="error")
    raise

# @since 20230517 copied from bbsengine5
def getcurrentid(args):
  global currentid

  if args.debug is True:
    io.echo(f"bbsengine6.member.getcurrentid.100: {currentid=}", level="debug")

  if currentid is not None:
    return currentid

  loginid = os.getlogin() # works on windows, too. @project:8158
#  loginid = pwd.getpwuid(os.geteuid())[0]

  if args.debug is True:
    io.echo(f"bbsengine6.member.getcurrentid.100: {loginid=}", level="debug")

  try:
    with database.connect(args) as conn:
      with database.transaction(conn, readonly=True) as txn:
        with database.cursor(conn) as cur:
          sql = "select id from engine.member where loginid=%s"
          dat = (loginid,)

  #        if args.debug is True:
  #          io.echo(f"bbsengine6.member.getcurrentid.120: {cur.mogrify(sql, dat)=}", level="debug")

          cur.execute(sql, dat)

          if cur.rowcount == 0:
            return None
          rec = cur.fetchone()

          # if args.debug is True:
          currentid = rec["id"]
          if args.debug is True:
            io.echo(f"getcurrentid.120: {currentid=}", level="debug")
          return currentid
  except psycopg.DatabaseError as e:
    io.echo(f"bbsengine6.member.getcurrentid.100: database error: {e}", level="error")
    raise

# @since 20170303
#def getcurrentlogin(args):
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
def setcredits(args, amount: int, moniker: str = None):
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

    if amount is None or int(amount) < 0:
        return None

    if moniker is None:
        moniker = getcurrentmoniker(args)
        if moniker is None:
            io.echo("You do not exist! Go Away!", level="error")
            return None

    try:
        with database.connect(args) as conn:
          with database.transaction(conn, readonly=False) as txn:
            with database.cursor(conn) as cur:
              sql = "update engine.__member set credits=%s where moniker=%s"
              dat = (int(amount), moniker)
              return cur.execute(sql, dat)
    except psycopg.DatabaseError as e:
        io.echo(f"Database error: {e}", level="error")
        raise

# @since 20230517 copied from bbsengine5
def getcredits(args, membermoniker:str=None) -> int:
  """Retrieves the credits for a member.

    Args:
        args: A dictionary containing database connection parameters.
        membermoniker (optional): The unique identifier of the member.
            If None, uses the current member's moniker.

    Returns:
        The member's credits, or None if the member does not exist.
  """
  if membermoniker is None:
    membermoniker = getcurrentmoniker(args)
    if membermoniker is None:
      io.echo("You do not exist! Go Away!", level="error")
      return None

  try:
    with database.connect(args) as conn:
      with database.transaction(conn, readonly=True) as txn:
        with database.cursor(conn) as cur:
          sql = "select credits from engine.member where moniker=%s"
          dat = (membermoniker,)
          cur.execute(sql, dat)
          if cur.rowcount == 0:
            return None
          row = cur.fetchone()
          return row["credits"] if "credits" in res else None
  except psycopg.DatabaseError as e:
    io.echo(f"Database error: {e}", level="error")
    raise

#def getcurrentmembercredits(args:argparse.Namespace) -> int:
#  memberid = getcurrentmemberid(args)
#  return getmembercredits(args, memberid)

#def getname(args, memberid:int=None) -> str:
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
  
#def getcurrentmembername(args:argparse.Namespace) -> str:
#  currentmemberid = getcurrentmemberid(args)
##  ttyio.echo(f"getcurrentmembername.100: currentmemberid={currentmemberid!r}", level="debug")
#  return getmembername(args, currentmemberid)

# @since 20221111
def update(args, member, memberid=None):
  if memberid is None:
    memberid = getcurrentid(args)

  if "password" in member:
    del member["password"]

  rec = buildrec(member)
  if "flags" in rec:
    flags = rec["flags"]
    del rec["flags"]

  database.update(args, "engine.__member", memberid, rec, mogrify=True)
  for name, data in member["flags"].items():
    io.echo(f"bbsengine6.member.update.100: {name=} {data=}", level="debug")
    setflag(args, name, data["value"], moniker=member["moniker"])

  return

# @since 20210203
def getcurrent(args, fields="*") -> dict:
  currentid = getcurrentid(args)
  return getbyid(args, currentid, fields)

# @since 20190924
# @since 20210203
def getbymoniker(args, moniker:str, fields="*") -> dict:
  sql = f"select {fields}, timezone(tz, lastlogin) from engine.member where moniker=%s"
  dat = (moniker,)
  with database.connect(args) as conn:
    with database.transaction(conn, readonly=True) as txn:
      with database.cursor(conn) as cur:
        cur.execute(sql, dat)
        if cur.rowcount == 0:
          return None
        rec = cur.fetchone()
        return build(args, rec)

# @since 20200731
def getbyid(args, memberid:int, fields:str="*") -> dict:
  sql = f"select {fields} from engine.member where id=%s"
  dat = (memberid,)
  with database.connect(args) as conn:
    with database.transaction(conn, readonly=True) as txn:
      with database.cursor(conn) as cur:
        cur.execute(sql, dat)
        if cur.rowcount == 0:
          io.echo("bbsengine6.member.getbyid: no rows returned")
          return None
        res = cur.fetchone()
        return build(args, res)

# @since 20230521 copied from bbsengine5
def checkflag(args, flag:str, membermoniker:str=None, mogrify:bool=False, **kw):
#  mogrify = kw["mogrify"] if "mogrify" in kw else False
  if membermoniker is None:
    membermoniker = getcurrentmoniker(args)
    if membermoniker is None:
      io.echo("You do not exist! Go away!", level="error")
      return None

  try:
    with database.connect(args) as conn:
      with database.transaction(conn, readonly=True) as txn:
        with database.cursor(conn) as cur:
          sql = "select f.name, coalesce(mmf.value, f.defaultvalue) as value from engine.flag as f left outer join engine.map_member_flag as mmf on (f.name=mmf.name and mmf.moniker=%s) where f.name=%s"
          dat = (membermoniker, flag)
          cur.execute(sql, dat)
          if cur.rowcount == 0:
            return None
          rec = cur.fetchone()
          return util.tobool(rec["value"])
  except psycopg.DatabaseError as e:
    io.echo("bbsengine6.member.checkflag.100: database error {e}", level="error")
    raise

# @since 20230523 copied from bbsengine5
def setflag(args, name, value, **kwargs): # moniker=None, mogrify=False,):
  moniker = kwargs.get("moniker", None)
  mogrify = kwargs.get("mogrify", False)
#  conn = kwargs.get("conn", database.connect(args))
  if moniker is None:
    moniker = getcurrentmoniker(conn)
  util.logentry(f"setflag({name=}, {value=}, {moniker=})")

  sql = "delete from engine.map_member_flag where moniker=%s and name=%s"
  dat = (moniker, name)
  with database.connect(args, readonly=False) as conn:
    with database.cursor(conn) as cur:
#      if mogrify is True:
#        io.echo(cur.mogrify(sql, dat), level="debug")

      cur.execute(sql, dat)

      mmf = {}
      mmf["moniker"] = moniker
      mmf["name"] = name
      mmf["value"] = value
  
      database.insert(args, "engine.map_member_flag", mmf, returnid=False)
      return None

def getflag(args, name, moniker=None):
  if moniker is None:
    moniker = getcurrentmoniker(args)
    if moniker is None:
      io.echo("You do not exist! Go away!", level="error")
      return None
  
  sql = "select flag.name as name, coalesce(mmf.value, flag.defaultvalue) as value from engine.flag left outer join engine.map_member_flag as mmf on flag.name = mmf.name where flag.name=%s"
  dat = (name,)
  sql +="  and mmf.moniker=%s"
  dat.append(moniker)

  try:
    with database.connect(args) as conn:
      with database.transaction(conn, readonly=True):
        with database.cursor(conn) as cur:
          cur.execute(sql, dat)
          if cur.rowcount == 0:
            return None
          rec = cur.fetchone()
          return rec["value"]
  except psycopg.DatabaseError as e:
    io.echo(f"bbsengine6.member.getflag.100: database error: {e}", level="error")
    raise

def updateflag(args, flag, **kwargs):
  mogrify = kwargs.get("mogrify", False)
#  conn = kwargs.get("conn", database.connect(args))

  sql = "update flag set defaultvalue=%s, description=%s where name=%s"
  dat = (flag["defaultvalue"], flag["description"], flag["name"])
  try:
    with database.connect(args, readonly=False) as conn:
      with database.cursor(conn) as cur:
        cur.execute(sql, dat)
        return
  except psycopg.DatabaseError as e:
    io.echo(f"bbsengine6.member.updateflag.100: database error: {e}", level="error")
    raise

def getflags(args, membermoniker=None):
    """Retrieves a dictionary of flags for a member.

    Args:
        args: A dictionary containing database connection parameters.
        membermoniker (optional): The unique identifier of the member.
            If None, returns the flags with default values.

    Returns:
        A dictionary of flags, where the key is the flag name and the value is
        a dictionary containing the description and the value (either the member-specific value or the default value from the database, converted to True or False as appropriate).
    """

    sql = """
        SELECT flag.name, flag.description,
               coalesce(engine.map_member_flag.value, flag.defaultvalue) AS value
        FROM engine.flag
        LEFT OUTER JOIN engine.map_member_flag ON flag.name = engine.map_member_flag.name
        AND engine.map_member_flag.moniker = %s
    """

    try:
        with database.connect(args) as conn:
          with database.transaction(conn, readonly=True):
            with database.cursor(conn) as cur:
                if membermoniker is None:
                    # Use None as the parameter when membermoniker is None
                    cur.execute(sql, (None,))
                else:
                    cur.execute(sql, (membermoniker,))
                flags = {}
                for row in cur.fetchall():
#                    name, description, value = row
                    if row["value"].lower() in ('t', 'true', '1'):
                        value = True
                    else:
                        value = False
                    flags[row["name"]] = {"description": row["description"], "value": row["value"]}
    except psycopg.DatabaseError as e:
        io.echo(f"bbsengine6.member.getflags.120: Database error: {e}", level="error")
        raise

    if args.debug is True:
      io.echo(f"bbsengine6.member.getflags.100: {flags=}", level="debug")
    return flags

# @since 20230523 copied from bbsengine5
def setpassword(args, plaintextpassword:str, membermoniker:str=None) -> bool:
  if membermoniker is None:
    membermoniker = getcurrentmoniker(args)
    if membermoniker is None:
      io.echo("You do not exist! Go away!", level="error")
      return False
  try:
    with database.connect(args, readonly=False) as conn:
      with database.cursor(conn) as cur:
        sql = "update engine.__member set password=crypt(%s, gen_salt('bf')) where moniker=%s"
        dat = (plaintextpassword, membermoniker)
        rows = cur.execute(sql, dat)
        io.echo(f"member.setpassword.100: {rows} row updated", level="debug")
        if cur.rowcount == 0:
          return False
        return True
  except psycopg.DatabaseError as e:
    io.echo(f"engine.member.setpassword.100: Database error: {e}")
    raise

# @since 20240901
def checkpassword(args, plaintextpassword:str, membermoniker:str=None) -> bool:
    if membermoniker is None:
      membermoniker = getcurrentmoniker(args)
      if membermoniker is None:
        io.echo("You do not exist! Go away!", level="error")
        return False

    io.echo(f"{plaintextpassword=} {membermoniker=}", level="debug")
    with database.connect(args) as conn:
      with database.transaction(conn, readonly=True):
        with database.cursor(conn) as cur:
          sql = "select 1 from engine.member where password=crypt(%s, password) and moniker=%s"
          dat = (plaintextpassword, membermoniker)
          cur.execute(sql, dat)
          io.echo(f"{cur.rowcount=}", level="debug")
          if cur.rowcount > 0:
            return True
    return False

# @since 20230523 copied from bbsengine5
def setattrs(args, attrs:dict, moniker=None, **kwargs): #reset:bool=False, moniker=None, conn=None):
#  conn = kwargs.get("conn", database.connect(args))
  reset = kwargs.get("reset", False)
#  moniker = kwargs.get("moniker", None)

  if moniker is None:
    moniker = getcurrentmoniker(conn)
    if moniker is None:
      io.echo("You do not exist! Go Away!", level="error")
      return None

  with database.connect(args, readonly=False) as conn:
    with database.cursor(conn) as cur:
      if reset is False:
        q = sql.SQL("update engine.__member set attrs=attrs||%s where moniker=%s")
      else:
        q = sql.SQL("update engine.__member set attrs=%s where moniker=%s")

      dat = (database.Jsonb(attrs), moniker) # {"attrs":attrs, "moniker":moniker}
      return cur.execute(q, dat)

def verifyMemberNotFound(args, name, column="loginid", **kw):
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

def verifyMemberFound(args, name, column="loginid", **kw):
    io.echo(f"{args=}", level="debug")
    try:
      with database.connect(args, readonly=True) as conn:
        with database.transaction(conn, readonly=True):
          with database.cursor(conn) as cur:
            sql = f"select 1 from engine.member where {column}=%s"
            dat = (name,)
            cur.execute(sql, dat)
            return cur.fetchone() is not None
    except psycopg.DatabaseError as e:
      io.echo(f"bbsengine6.member.verifyMemberFound.100: database error {e}", level="error")

def insert(conn, member, **kwargs):
  if member is None:
    io.echo(f"bbsengine6.member.insert.120: no member present", level="warn")
    return None
  table = kwargs.get("table", "engine.__member")
  primarykey = kwargs.get("primarykey", "moniker")
  returnid = kwargs.get("returnid", True)
  mogrify = kwargs.get("mogrify", True)

  cols = copy.copy(member)
  if "flags" in cols:
    del cols["flags"]
    io.echo(f"bbsengine6.insert.160: removed 'flags' from member")
  if "attrs" in cols:
    del cols["attrs"]
    io.echo(f"bbsengine6.insert.140: removed 'attrs' from member")
  if "id" in cols:
    del cols["id"]
    io.echo(f"bbsengine6.insert.200: removed 'id' from member")

  io.echo(f"bbsengine6.member.insert.100: {member=}", level="debug")
  return database.insert(conn, table, cols, **kwargs) # table, member, returnid=returnid, primarykey=primarykey, mogrify=mogrify)

# @since 20230619
def getcurrentmoniker(args, memberid=None, **kwargs):
  mogrify = kwargs.get("mogrify", False)

  if memberid is None:
    memberid = getcurrentid(args)
    if memberid is None:
      io.echo("You do not exist! Go Away!", level="error")
      return None

  try:
    with database.connect(args) as conn:
      with database.transaction(conn, readonly=True):
        with database.cursor(conn) as cur:
          sql = "select moniker from engine.member where id=%s"
          dat = (memberid,)
          cur.execute(sql, dat)
          if cur.rowcount == 0:
            return None
          rec = cur.fetchone()
          return rec["moniker"]
  except psycopg.DatabaseError as e:
    io.echo(f"bbsengine6.member.getcurrentmoniker.120: {e}", level="error")
    raise
# @since 20240217
# temporary! <heh>
def checksysop(conn, memberid=None):
  io.echo("bbsengine6.member.checksysop({memberid=}) called", level="warning")
  return checkflag(args, "sysop", memberid)
