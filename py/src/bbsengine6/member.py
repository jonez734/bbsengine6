import os
import pwd
import time

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
    if k in ("datecreatedepoch", "dateapprovedepoch", "dateupdatedepoch", "lastloginepoch", "flags"):
      continue
    if type(v) == dict:
      m[k] = json.dumps(v)
      continue
    m[k] = v
  return m

# @since 20230527
def build(rec={}):
  member = {}
  for k in ("loginid", "moniker", "credits", "attributes", "email", "password", "datecreated", "createdbyid", "dateupdated", "updatedbyid", "approvedbyid", "dateapproved", "lastlogin", "lastloginfrom", "ui", "tz"):
    if k in rec:
      if k == "credits":
        member[k] = int(rec[k])
      else:
        member[k] = rec[k]
    else:
      if k == "attributes":
        member[k] = {}
      else:
        member[k] = None
  return member

currentid = None
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

  sql = "select id from engine.member where loginid=%s"
  dat = (loginid,)
  dbh = database.connect(args)
  cur = dbh.cursor()

  if args.debug is True:
    io.echo(f"mogrify={cur.mogrify(sql, dat)=}", level="debug")

  cur.execute(sql, dat)
  if cur.rowcount == 0:
    return None
  rec = cur.fetchone()

  # if args.debug is True:
  currentid = rec["id"]
  if args.debug is True:
    io.echo(f"getcurrentid.120: {currentid=}", level="debug")
  return currentid

  if res is None:
    return None
  #if loginid in membermap:
  #  currentmemberid = membermap[loginid]
  #else:
  #  currentmemberid = None
  #return currentmemberid

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
def setcredits(args, memberid:int, amount:int):
  if amount is None or amount < 0:
    return None

  dbh = database.connect(args)
  cur = dbh.cursor()
  sql = "update engine.__member set credits=%s where id=%s"
  dat = (amount, memberid)
  return cur.execute(sql, dat)

# @since 20230517 copied from bbsengine5
def getcredits(args, memberid:int=None) -> int:
  if memberid is None:
    memberid = getcurrentid(args)

  dbh = database.connect(args)
  sql = "select credits from engine.member where id=%s" 
  dat = (memberid,)
  cur = dbh.cursor()
  cur.execute(sql, dat)
  if cur.rowcount == 0:
    return None
  res = cur.fetchone()
  return res["credits"] if "credits" in res else None

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

  rec = buildrec(member)
  dbh = database.connect(args)
  database.update(dbh, "engine.__member", memberid, rec, mogrify=True)
  # setmemberflags(args, member["flags"], memberid)
  return

# @since 20210203
def getcurrent(args, fields="*") -> dict:
  currentid = getcurrentid(args)
  return getbyid(args, currentid, fields)

# @since 20190924
# @since 20210203
def getbymoniker(args, moniker:str, fields="*") -> dict:
  sql = f"select {fields}, timezone(tz, lastlogin) from engine.member where moniker=%s"
  dat = (name,)
  dbh = database.connect(args)
  cur = dbh.cursor()
  cur.execute(sql, dat)
  if cur.rowcount == 0:
    return None
  rec = cur.fetchone()
  cur.close()
  return build(rec)

# @since 20200731
def getbyid(args, memberid:int, fields:str="*") -> dict:
  dbh = database.connect(args)
  sql = f"select {fields} from engine.member where id=%s"
  dat = (memberid,)
  cur = dbh.cursor()
  cur.execute(sql, dat)
  io.echo(f"{cur.mogrify(sql, dat)=}")
  if cur.rowcount == 0:
    io.echo("bbsengine6.member.getbyid: no rows returned")
    return None
  res = cur.fetchone()
  cur.close()
  return build(res)

# @since 20230521 copied from bbsengine5
def checkflag(args, flag:str, memberid:int=None):
  if memberid is None:
    memberid = getcurrentid(args)

  dbh = database.connect(args)
  sql = "select f.name, coalesce(mmf.value, f.defaultvalue) as value from engine.flag as f left outer join engine.map_member_flag as mmf on (f.name=mmf.name and mmf.memberid=%s) where f.name ilike %s"
  dat = (memberid, flag)
  cur = dbh.cursor()
  cur.execute(sql, dat)
  if cur.rowcount == 0:
    return None
  rec = cur.fetchone()
  return rec["value"]

# @since 20230523 copied from bbsengine5
def setflag(args, flag, value, memberid=None, mogrify=False):
  if memberid is None:
    memberid = getcurrentid(args)
  util.logentry(f"setflag({flag}, {value}, {memberid})")
#  if flag == "AUTHENTICATED":
#    return

  sql = "delete from engine.map_member_flag where memberid=%s and name=%s"
  dat = (memberid, flag)
  dbh = database.connect(args)
  cur = dbh.cursor()

  if mogrify is True:
    io.echo(cur.mogrify(sql, dat), level="debug")

  cur.execute(sql, dat)
  cur.close()

  mmf = {}
  mmf["memberid"] = memberid
  mmf["name"] = flag
  mmf["value"] = value
  
  return database.insert(args, "engine.map_member_flag", mmf, returnid=False)

def getflag(args, name, memberid=None):
  if memberid is None:
    memberid = getcurrentid(args)

  dbh = database.connect(args)
  sql = """
select flag.name as name, coalesce(mmf.value, flag.defaultvalue) as value
from engine.flag left outer join engine.map_member_flag as mmf on flag.name = mmf.name
where flag.name=%s
"""
  dat = [name,]
  if memberid is not None:
    sql +="  and mmf.memberid=%s"
    dat.append(memberid)

#  sql += "limit 1"
  
  cur = dbh.cursor()
  cur.execute(sql, dat)
  if cur.rowcount == 0:
    return None
  rec = cur.fetchone()
  return rec["value"]

def updateflag(args, flag):
  dbh = database.connect(args)
  sql = "update flag set defaultvalue=%s, description=%s where name=%s"
  dat = (flag["defaultvalue"], flag["description"], flag["name"])
  cur = dbh.cursor()
  cur.execute(sql, dat)
  cur.close()
  return

# @since 20210106
def checkflag(args, flag:str, memberid:int=None):
  if memberid is None:
    memberid = getcurrentid(args)

  dbh = database.connect(args)
  sql = "select f.name, coalesce(mmf.value, f.defaultvalue) as value from engine.flag as f left outer join engine.map_member_flag as mmf on (f.name=mmf.name and mmf.memberid=%s) where f.name=%s"
  dat = (memberid, flag)
  cur = dbh.cursor()
  cur.execute(sql, dat)
  res = cur.fetchone()
  # ttyio.echo("bbsengine.checkflag.100: %s=%s" % (flag, res), level="debug")
  if res is None:
    return None
  return res["value"]

# @since 20230523 copied from bbsengine5
def setpassword(args, memberid, plaintextpassword):
  dbh = database.connect(args)
  cur = dbh.cursor()
  sql = "update engine.__member set password=crypt(%s, gen_salt('bf')) where id=%s"
  dat = (plaintextpassword, memberid)
  cur.execute(sql, dat)
  if cur.rowcount == 0:
    return False
  return True

# @since 20230523 copied from bbsengine5
def setattributes(args, memberid, attributes, reset=False):
  dbh = database.connect(args)
  cur = dbh.cursor()
  if reset is False:
    sql = "update engine.__member set attributes=attributes||%%s where id=%s" % (memberid)
  else:
    sql = "update engine.__member set attributes=%%s where id=%s" % (memberid)

  dat = (database.Json(attributes),)
  return cur.execute(sql, dat)

def verifyMemberNotFound(name, args=None, column="loginid", **kw):
    io.echo(f"{args=}", level="debug")
    dbh = database.connect(args)
    cur = dbh.cursor()
    sql = f"select 1 from engine.member where {column}=%s"
    dat = (name)
    cur.execute(sql, dat)
    if cur.rowcount == 0:
        return True
    return False

def verifyMemberFound(name, args=None, column="loginid", **kw):
    io.echo(f"{args=}", level="debug")
    dbh = database.connect(args)
    cur = dbh.cursor()
    sql = f"select 1 from engine.member where {column}=%s"
    dat = (name,)
    cur.execute(sql, dat)
    if cur.rowcount == 1:
        return True
    return False

def insert(args, member, table="engine.__member", mogrify=False):
  return database.insert(args, table, member, returnid=True, mogrify=mogrify)

# @since 20230619
def getcurrentmoniker(args, memberid=None, **kw):
  mogrify = kw["mogrify"] if "mogrify" in kw else False

  if memberid is None:
    memberid = getcurrentid(args)

  dbh = database.connect(args)
  cur = dbh.cursor()
  sql = "select moniker from engine.member where id=%s"
  dat = (memberid,)
  cur.execute(sql, dat)
  if mogrify is True:
    io.echo(f"bbsengine6.member.getcurrentmoniker.100: {cur.mogrify(sql, dat)=}", level="debug")
  if cur.rowcount == 0:
    return None
  rec = cur.fetchone()
  return rec["moniker"]

# @since 20240217
# temporary! <heh>
def checksysop(args, memberid=None):
  io.echo("bbsengine6.member.checksysop({memberid=}) called", level="warning")
  return checkflag(args, "sysop", memberid)
