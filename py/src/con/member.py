import json
import copy
import argparse

import ttyio6 as ttyio
import bbsengine6 as bbsengine

from . import lib

def init(*args, **kw):
  return True

def buildargs(args, **kw):
  return lib.buildargs(args, **kw)

def access(args, op, **kw):
  return True

def help(*args, **kw):
  member = kw["member"] if "member" in kw else {}
  _member = kw["_member"] if "_member" in kw else {}

  if member["moniker"] is None:
    ttyio.echo(f"{{var:optioncolor}}[M]{{var:labelcolor}}oniker")
  elif member["moniker"] != _member["moniker"]:
    ttyio.echo(f"{{var:optioncolor}}[M]{{var:labelcolor}}oniker: {member['moniker']!r} (was: {_member['moniker']!r})")
  else:
    ttyio.echo(f"{{var:optioncolor}}[M]{{var:labelcolor}}oniker: {member['moniker']!r}")

  if member["loginid"] is None:
    ttyio.echo(f"{{var:optioncolor}}[L]{{var:labelcolor}}oginid{{/all}}")
  elif member["loginid"] != _member["loginid"]:
    ttyio.echo(f"{{var:optioncolor}}[L]{{var:labelcolor}}oginid: {{var:valuecolor}}{member['loginid']!r} (was: {_member['loginid']!r})")
  else:
    ttyio.echo(f"{{var:optioncolor}}[L]{{var:labelcolor}}oginid: {{var:valuecolor}}{member['loginid']!r}")

  if member["email"] is None:
    ttyio.echo("{var:optioncolor}[E]{var:labelcolor}mail")
  elif member["email"] != _member["email"]:
    ttyio.echo(f"{{var:optioncolor}}[E]{{var:labelcolor}}mail: {member['email']!r} (was: {_member['email']!r})")
  else:
    ttyio.echo(f"{{var:optioncolor}}[E]{{var:labelcolor}}mail: {member['email']!r}")

  if member["password"] is None:
    ttyio.echo("{var:optioncolor}[P]{var:labelcolor}assword{/all}")
  if member["credits"] is None:
    ttyio.echo(f"{{var:optioncolor}}[C]{{var:labelcolor}}redits")
  elif member["credits"] != _member["credits"]:
    ttyio.echo(f"{{var:optioncolor}}[C]{{var:labelcolor}}redits: {member['credits']!r} (was: {_member['credits']!r})")
  else:
    ttyio.echo(f"{{var:optioncolor}}[C]{{var:labelcolor}}redits: {member['credits']!r}")
    
  if member["ui"] is None:
    ttyio.echo(f"{{var:optioncolor}}[U]I")
  elif member["ui"] != _member["ui"]:
    ttyio.echo(f"{{var:optioncolor}}[U]{{var:labelcolor}}I: {member['ui']!r} (was: {_member['ui']!r})")
  else:
    ttyio.echo(f"{{var:optioncolor}}[U]{{var:labelcolor}}I: {member['ui']!r}")
    
  ttyio.echo(f"{{var:optioncolor}}[F]{{var:labelcolor}}lags{{var:normalcolor}}")

def _edit(args, mode, member, **kw):
  _member = copy.deepcopy(member)

  bbsengine.util.heading(f"{mode} member")

  done = False
  while not done:
    help(args, member=member, _member=_member)

    ch = ttyio.inputchoice(f"{{var:promptcolor}}{mode} member {{var:optioncolor}}[MECPFUQ]{{var:promptcolor}}: {{var:inputcolor}}", "LMECPFUQ", "", help=help, member=member, _member=_member)
    if ch == "M":
      ttyio.echo("Moniker")
      _moniker = member["moniker"]
      moniker = ttyio.inputstring("{var:promptcolor}moniker: {var:inputcolor}", _moniker, args=args) # verify=bbsengine.member.verifyMemberFound, args=args)
      if _moniker != moniker:
        if bbsengine.member.verifyMemberFound(moniker, args=args, column="moniker") is True:
          ttyio.echo(f"{moniker!r} is already in use.")
        else:
          member["moniker"] = moniker
    elif ch == "L":
      ttyio.echo("Loginid")
      member["loginid"] = ttyio.inputstring("{var:promptcolor}loginid: {var:inputcolor}", member["loginid"], args=args)      
    elif ch == "C":
      ttyio.echo("Credits")
      member["credits"] = ttyio.inputinteger("{var:promptcolor}credits: {var:inputcolor}", member["credits"], args=args)
    elif ch == "U":
      ttyio.echo("User Interface(s)")
      member["ui"] = ttyio.inputstring("{var:promptcolor}ui: {var:inputcolor}", member["ui"], args=args, multiple=True)
    elif ch == "P":
      ttyio.echo("Password")
      member["password"] = bbsengine.util.inputpassword("Password: ")
    elif ch == "Q":
      ttyio.echo("Quit")
      done = True
  
  return member

  memberid = member["id"]
  ttyio.echo(f"memberid={memberid!r} member={member!r}", level="debug")

  sysop = ttyio.inputboolean("sysop? [yN]: ", "N")
  bbsengine.member.setflag(args, "SYSOP", sysop, memberid)

  magician = ttyio.inputboolean("magician? [yN]: ", "N")
  bbsengine.member.setflag(args, memberid, "MAGIC", magician)
  
  ansalum = ttyio.inputboolean("ANS Alum? [yN]: ", "N")

  credits = ttyio.inputinteger("credits: ", member["credits"])
  member["credits"] = credits if credits > 0 else 0

  m = buildrecord(member)
  ttyio.echo(f"con.member.100: m={m!r}", level="debug")
  bbsengine.member.update(args, memberid, m)
  bbsengine.database.commit(args)
  ttyio.echo("member %r updated." % (name), level="success")
  return

def edit(args, **kw):
  buf = ttyio.inputstring("{var:promptcolor}loginid or moniker: {var:inputcolor}", "", noneok=True)
  ttyio.echo("{/all}")
  if buf is None:
    return None
  sql = "select * from engine.__member where loginid=%s or moniker=%s"
  dat = (buf, buf)
  
  dbh = bbsengine.database.connect(args)

  cur = dbh.cursor()
  cur.execute(sql, dat)
  if cur.rowcount == 0:
    ttyio.echo(f"{buf!r} not found", level="error")
    return False

  rec = cur.fetchone()

  member = bbsengine.member.build(rec)
  
  ttyio.echo(f"bbsengine6.con.member.edit.120: rec={rec!r} member={member!r}", level="debug")

  _edit(args, "edit", member)

  return True

def add(args):
  _member = bbsengine.member.build()
  member =  _edit(args, "add", _member)
  ttyio.echo(f"con.member.add.100: member={member!r}", level="debug")
  memberid = bbsengine.member.insert(args, member, mogrify=True)

  if args.debug is True:
    ttyio.echo("memberid=%r" % (memberid), level="debug")

  attributes = {}
  bbsengine.member.setattributes(args, memberid, attributes, reset=True)
  bbsengine.member.setpassword(args, memberid, plaintextpassword)
  bbsengine.member.setflag(args, "SYSOP", sysop, memberid)
  bbsengine.member.setcredits(args, memberid, member["credits"])
  bbsengine.database.commit(args)
  ttyio.echo("member added.")

  return True

  name = ttyio.inputstring("name: ", "", verify=bbsengine.member.verifyMemberNotFound, noneok=False, multiple=False, args=args)
  email = ttyio.inputstring("email: ", "", noneok=False, multiple=False, args=args)
  plaintextpassword = bbsengine.util.inputpassword("password: ", "", noneok=False, multiple=False, args=args)
  loginid = ttyio.inputstring("loginid: ", "", noneok=True, multiple=False, args=args)
#  shell = ttyio.inputstring("shell: ", "", noneok=True, multiple=False, args=args)
  sysop = ttyio.inputboolean("sysop?: ", "N", "YN")
  credits = ttyio.inputinteger("credits: ", "42", noneok=True, multiple=False, args=args)

  if ttyio.inputboolean("{var:promptcolor}add member?: {var:inputcolor}", "N") is False:
    ttyio.echo("{f6}member not added.")
    return

  member = {}
  member["mokiker"] = moniker
  member["email"] = email
  member["datecreated"] = "now()"
  member["dateapproved"] = "now()"
  member["loginid"] = loginid

  memberid = bbsengine.member.insert(args, member)

  if args.debug is True:
    ttyio.echo("memberid=%r" % (memberid), level="debug")

  attributes = {}
  bbsengine.member.setattributes(args, memberid, attributes, reset=True)
  bbsengine.member.setpassword(args, memberid, plaintextpassword)
  bbsengine.member.setflag(args, "SYSOP", sysop, memberid)
  bbsengine.member.setcredits(args, memberid, credits)
  bbsengine.database.commit(args)
  ttyio.echo("member added.")

def main(args, **kw):
    parser = lib.buildargs(args, **kw)
    args = parser.parse_args()

    done = False
    while not done:
        bbsengine.util.heading("member")
        ttyio.echo("{f6}{var:labelcolor}database: {var:valuecolor}%s {var:labelcolor}host: {var:valuecolor}%s:%s{f6}" % (args.databasename, args.databasehost, args.databaseport))
        ttyio.echo("{var:optioncolor}[E]{var:labelcolor}dit")
        ttyio.echo("{var:optioncolor}[A]{var:labelcolor}dd")
        ttyio.echo("{f6}{var:optioncolor}[Q]{var:labelcolor}uit")
        ch = ttyio.inputchoice("{var:promptcolor}member:{var:inputcolor} ", "AEQ", "Q")
        if ch == "E":
          ttyio.echo("Edit")
          edit(args)
          continue
        elif ch == "A":
          ttyio.echo("Add")
          add(args)
        elif ch == "Q":
          ttyio.echo("Quit")
          done = True
          break
