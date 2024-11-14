import json
import copy
import argparse

from bbsengine6 import io, database, util
from bbsengine6 import member as libmember

from . import lib

def init(*args, **kw):
  return True

def buildargs(args, **kw):
  return lib.buildargs(args, **kw)

def access(args, op, **kw):
  return True

def editflags(args, moniker=None):
    """Edits flags for a member.

    Args:
        args: An argparse.ArgumentParser object.
        moniker (optional): The unique identifier of the member.
            If None, returns the flags with default values.
    """

    flags = libmember.getflags(args, moniker)
    updated_flags = {flag_name: {"value":flag_data["value"]} for flag_name, flag_data in flags.items()}

    for flag_name, flag_data in flags.items():
        description = flag_data["description"]
        current_value = flag_data["value"]
        default_value = "Y" if util.toboolean(current_value) else "N"
        io.echo(f"{default_value=} {current_value=}", level="debug")
        prompt = f"{{var:promptcolor}}{description} "
        if default_value == "Y":
          prompt += f"[{{var:currentoptioncolor}}Y{{var:optioncolor}}n{{var:promptcolor}}]"
        else:
          prompt += f"[{{var:optioncolor}}y{{var:currentoptioncolor}}N{{var:promptcolor}}]"
        prompt += f"{{promptcolor}}: {{var:inputcolor}}"
        new_value = io.inputboolean(f"{prompt}", default=default_value)
        io.echo("{/all}", end="")
        if new_value != current_value:
            # TODO: Implement logic to update the flag in the database
            io.echo(f"{{var:labelcolor}}Updating flag '{{var:valuecolor}}{flag_name}{{var:labelcolor}}' to {{var:valuecolor}}{new_value}{{/all}}")
            updated_flags[flag_name] = {"value":new_value}
    return updated_flags

def showui(args, ui, _ui):
  io.echo(f"{ui=} {_ui=}", level="debug")
  if ui is None or len(ui) == 0:
    io.echo(f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: None", end="")
    if _ui is not None:
      _ui.sort()
      io.echo(f" (was: {', '.join(_ui)})")
    else:
      io.echo()
    return

  if ui is not None:
    ui.sort()
  if _ui is not None:
    _ui.sort()

  if ui != _ui:
      if _ui is None:
        io.echo(f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: {', '.join(ui)} (was: None)")
      else:
        io.echo(f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: {', '.join(ui)} (was: {', '.join(_ui)})")
  else:
    io.echo(f"  {{var:optioncolor}}[U]{{var:labelcolor}} UI: {', '.join(ui)}")
  return

def help(*args, **kw):
  io.echo(f"{kw=}", level="debug")

  member = kw["member"] if "member" in kw else {}
  _member = kw["_member"] if "_member" in kw else {}

  if member["moniker"] is None:
    io.echo(f"{{red}} *{{var:optioncolor}}[M]{{var:labelcolor}} Moniker")
  elif member["moniker"] != _member["moniker"]:
    io.echo(f"{{red}} *{{var:optioncolor}}[M]{{var:labelcolor}} Moniker: {{var:valuecolor}}{member['moniker']} {{var:labelcolor}}(was: {{var:valuecolor}}{_member['moniker']}{{var:labelcolor}})")
  else:
    io.echo(f"{{red}} *{{var:optioncolor}}[M]{{var:labelcolor}} Moniker: {{var:valuecolor}}{member['moniker']}")

  if member["loginid"] is None:
    io.echo(f"{{red}} *{{var:optioncolor}}[L]{{var:labelcolor}} Loginid{{/all}}")
  elif member["loginid"] != _member["loginid"]:
    io.echo(f"{{red}} *{{var:optioncolor}}[L]{{var:labelcolor}} Loginid: {{var:valuecolor}}{member['loginid']} {{var:labelcolor}}(was: {{var:labelcolor}}{_member['loginid']}{{var:labelcolor}})")
  else:
    io.echo(f"{{red}} *{{var:optioncolor}}[L]{{var:labelcolor}} Loginid: {{var:valuecolor}}{member['loginid']}")

  if member["email"] is None:
    io.echo(f"{{red}} *{{var:optioncolor}}[E]{{var:labelcolor}} Email")
  elif member["email"] != _member["email"]:
    io.echo(f"{{red}} *{{var:optioncolor}}[E]{{var:labelcolor}}mail: {{var:valuecolor}}{member['email']} {{var:labelcolor}}(was: {{var:valuecolor}}{_member['email']})")
  else:
    io.echo(f"{{red}} *{{var:optioncolor}}[E]{{var:labelcolor}}mail: {member['email']}")

  if member["password"] is None:
    io.echo("  {var:optioncolor}[P]{var:labelcolor} Password{/all}")

  if member["credits"] is None:
    io.echo(f"  {{var:optioncolor}}[C]{{var:labelcolor}} Credits")
  elif member["credits"] != _member["credits"]:
    io.echo(f"  {{var:optioncolor}}[C]{{var:labelcolor}} Credits: {{var:valuecolor}}{member['credits']} (was: {_member['credits']})")
  else:
    io.echo(f"  {{var:optioncolor}}[C]{{var:labelcolor}} Credits: {{var:valuecolor}}{member['credits']}")
    
  showui(args, member["ui"], _member["ui"])
    
#  flags = member["flags"] or {}
  set_flags = [flag for flag, data in member["flags"].items() if data["value"] is True]
  if len(set_flags) > 0:
    io.echo(f"  {{var:optioncolor}}[F]{{var:labelcolor}} Flags:{{var:valuecolor}} {', '.join(set_flags)}")
  else:
    io.echo(f"  {{var:optioncolor}}[F]{{var:labelcolor}} Flags{{var:valuecolor}}")

  if "refcode" not in member:
    member["refcode"] = None
  if "refcode" not in _member:
    _member["refcode"] = None

  if member["refcode"] is None:
    io.echo(f"  {{var:optioncolor}}[R]{{var:labelcolor}} Refcode", end="")
    if _member["refcode"] is not None:
      io.echo(f"  {{var:labelcolor}} (was: {{var:valuecolor}}{_member['refcode']}{{var:labelcolor}})")
    else:
      io.echo()
  elif member["refcode"] != _member["refcode"]:
    io.echo(f"  {{var:optioncolor}}[R]{{var:labelcolor}} Refcode: {member['refcode']} {{var:labelcolor}}(was: {{var:valuecolor}}{_member['refcode']}{{var:labelcolor}})")

def _edit(args, mode, member, **kw):
  _member = copy.deepcopy(member)

  util.heading(f"{mode} member")

  done = False
  while not done:
    help(args, member=member, _member=_member)
#    flags = member["flags"]
    ch = io.inputchoice(f"{{var:promptcolor}}{mode} member {{var:optioncolor}}[MECPFUQ]{{var:promptcolor}}: {{var:inputcolor}}", "LMECPFURQ", "", help=help, member=member, _member=_member)
    if ch == "M":
      io.echo("Moniker")
      _moniker = member["moniker"]
      moniker = io.inputstring("{var:promptcolor}moniker: {var:inputcolor}", _moniker, args=args) # verify=bbsengine.member.verifyMemberFound, args=args)
      if _moniker != moniker:
        if libmember.verifyMemberFound(args, moniker, column="moniker") is True:
          io.echo(f"{moniker} is already in use.", level="error")
        else:
          member["moniker"] = moniker
    elif ch == "F":
      io.echo("Flags")
      member["flags"] = editflags(args, member["moniker"])
    elif ch == "L":
      io.echo("Loginid")
      member["loginid"] = io.inputstring("{var:promptcolor}loginid: {var:inputcolor}", member["loginid"], args=args)
    elif ch == "C":
      io.echo("Credits")
      member["credits"] = io.inputinteger("{var:promptcolor}credits: {var:inputcolor}", member["credits"], args=args)
    elif ch == "U":
      io.echo("User Interface")
      member["ui"] = editui(args, member["loginid"]) # io.inputstring("{var:promptcolor}ui: {var:inputcolor}", member["ui"], args=args, multiple=True)
    elif ch == "P":
      io.echo("Password")
      member["password"] = util.inputpassword("Password: ")
    elif ch == "E":
      io.echo("E-mail address")
      member["email"] = io.inputstring("{var:promptcolor}e-mail address: {var:inputcolor}")
      if member["email"] != _member["email"]:
        member["emailverified"] = False
        member["emailverifiedbymoniker"] = None
        member["dateemailverified"] = None
    elif ch == "A":
      io.echo("Alerts")
      alerts(args)
    elif ch == "R":
      io.echo("Refcode")
      refcode = io.inputstring("{var:promptcolor}refcode: {var:inputcolor}", member["refcode"])
      if refcode == "":
        refcode = None
      member["refcode"] = refcode
      done = False
    elif ch == "Q":
      io.echo("Quit")

      errcount = 0
      for f in ("loginid", "moniker", "email"):
        if member[f] is None or member[f] == "":
          io.echo(f"{{valuecolor}}{f} {{labelcolor}}is a required field")
          errcount += 1
      if errcount > 0:
        if io.inputboolean(f"{{var:promptcolor}}go back and fix it? {{optioncolor}}[{{currentoptioncolor}}Y{{optioncolor}}n]{{promptcolor}}: {{var:inputcolor}}", "Y") is False:
          done = True
          break
      else:
        done = True

  return member

def editui(args, rolename):
  ui = []
  if io.inputboolean(f"{{var:promptcolor}}allow {{var:valuecolor}}web{{var:promptcolor}} interface? {{var:optioncolor}}[Yn]{{var:promptcolor}}: {{var:inputcolor}}", "Y") is True:
#    database.manage_secondary_role(args, rolename, "add", "web")
    ui += ["web"]
#  else:
#    database.manage_secondary_role(args, rolename, "remove", "web")

  if io.inputboolean(f"{{var:promptcolor}}allow {{var:valuecolor}}terminal{{var:promptcolor}} interface? {{var:optioncolor}}[Yn]{{var:promptcolor}}: {{var:inputcolor}}", "Y") is True:
#    database.manage_secondary_role(args, rolename, "add", "term")
    ui += ["term"]
#  else:
#    database.manage_secondary_role(args, rolename, "remove", "term")
  return ui

def setui(args, rolename, ui):
  if ui is None:
    ui = []
  if "term" in ui:
    database.manage_secondary_role(args, rolename, "add", "term")
  else:
    database.manage_secondary_role(args, rolename, "remove", "term")

  if "web" in ui:
    database.manage_secondary_role(args, rolename, "add", "web")
  else:
    database.manage_secondary_role(args, rolename, "remove", "web")

def configurerole(args, rolename):
  io.echo(f"{{var:labelcolor}}checking for database role {{var:valuecolor}}{rolename}")
  if database.rolexists(args, rolename) is False:
    if io.inputboolean(f"{{var:promptcolor}}role {{var:valuecolor}}{rolename}{{var:promptcolor}} does not exist. create it? {{var:optioncolor}}[Yn]{{var:promptcolor}}: {{var:inputcolor}}", "Y") is False:
      io.echo("role not created.")
      return False
    database.createrol(args, rolename)

  database.manage_role_privs(args, rolename, "grant", "login")
  database.manage_role_privs(args, rolename, "grant", "inherit")
  return True

def edit(args, **kw):
  buf = io.inputstring("{var:promptcolor}loginid or moniker: {var:inputcolor}", "", noneok=True)
  io.echo("{/all}")
  if buf is None:
    return None
  sql = "select * from engine.__member where loginid=%s or moniker=%s"
  dat = (buf, buf)
  
  with database.connect(args) as conn:
    with database.cursor(conn) as cur:
      cur.execute(sql, dat)
      if cur.rowcount == 0:
        io.echo(f"{buf!r} not found", level="error")
        return False

      rec = cur.fetchone()

      m = libmember.build(args, rec)
      m["flags"] = libmember.getflags(args, m["moniker"])

      io.echo(f"bbsengine6.con.member.edit.120: {rec=} {m=}", level="debug")

      _m = _edit(args, "edit", m)

      loginid = m["loginid"]
      moniker = m["moniker"]
      memberid = m["id"]
      password = m["password"]
      ui = m["ui"]
#      flags = libmember.getflags(args, moniker)
#      sysop = flags["SYSOP"]["value"]

      configurerole(args, loginid)

      if io.inputboolean(f"{{var:promptcolor}}save changes? {{var:optioncolor}}[Yn]{{var:promptcolor}}: {{var:inputcolor}}", "Y"):
        io.echo("Yes")
        setui(args, loginid, ui)

        if _m["email"] != m["email"]:
          libmember.setflag(args, "EMAILVERIFIED", False, moniker=m["moniker"], mogrify=True)
          m["emailverifiedbymoniker"] = None
          m["dateemailverified"] = None

        libmember.update(args, m, memberid)
        libmember.setpassword(args, moniker, password)

        conn.commit() # database.commmit(args)
      else:
        io.echo("changes not saved.")
        conn.rollback()

      return True


def add(args):
  _member = libmember.build(args)

  io.echo(f"con.member.add.160: {_member=}", level="debug")
  member = _edit(args, "add", _member)
  io.echo(f"con.member.add.140: {member=}", level="debug")
  if member is None:
    io.echo(f"con.member.add.180: _edit returned None", level="error")
    return False

  if io.inputboolean("{var:promptcolor}add member? {var:optioncolor}[yN]{var:promptcolor}: {var:inputcolor}", "N") is False:
    io.echo("{/all}member not added.")
    return True

  with database.connect(args) as conn:
    member["datecreated"] = "now()"
    member["createdbymoniker"] = libmember.getcurrentmoniker(args)
    io.echo(f"con.member.add.100: {member=}", level="debug")

    if args.debug is True:
      io.echo(f"con.member.add.120: {member=}", level="debug")

    moniker = libmember.insert(args, member, primarykey="moniker") # =member, mogrify=True, returnid=True, primarykey="moniker")

    for name, data in member["flags"].items():
      io.echo(f"{name=} {data=}", level="debug")
      libmember.setflag(args, name, data["value"], moniker=moniker)

    setui(args, member["loginid"], member["ui"])
  #  for name, data in flags.items():
  #    io.echo(f"{name=} {data=}", level="debug")
  #    libmember.setflag(args, name, data["value"], membermoniker)

    if args.debug is True:
      io.echo(f"{moniker=}", level="debug")

    libmember.setattrs(args, {"foo":42}, moniker, reset=True)
    libmember.setpassword(args, member["password"], moniker)
    libmember.setcredits(args, member["credits"], moniker)

    loginid = member["loginid"]
    configurerole(args, loginid)
    if member["flags"]["SYSOP"]["value"] is True:
      database.manage_secondary_role(args, loginid, "add", "sysop")
      database.manage_role_privs(args, loginid, "grant", "createdb")
      database.manage_role_privs(args, loginid, "grant", "superuser")
      database.manage_role_privs(args, loginid, "grant", "createrole")
    else:
      database.manage_secondary_role(args, loginid, "remove", "sysop")
      database.manage_role_privs(args, loginid, "revoke", "createdb")
      database.manage_role_privs(args, loginid, "revoke", "superuser")
      database.manage_role_privs(args, loginid, "revoke", "createrole")

    conn.commit()

#  database.commit(args)
  io.echo("{/all}member added.")

  return True

def main(args, **kw):
    parser = lib.buildargs(args, **kw)
    args = parser.parse_args()

    done = False
    while not done:
        util.heading("member")
        io.echo(f"{{f6}}{{var:labelcolor}}database: {{var:valuecolor}}{args.databasename} {{var:labelcolor}}host: {{var:valuecolor}}{args.databasehost}:{args.databaseport}{{f6}}")
        io.echo(f"{{var:optioncolor}}[E]{{var:labelcolor}} Edit")
        io.echo(f"{{var:optioncolor}}[N]{{var:labelcolor}} New user")
        io.echo(f"{{var:optioncolor}}[A]{{var:labelcolor}} Approvals")
        io.echo(f"{{f6}}{{var:optioncolor}}[Q]{{var:labelcolor}} Quit")
        ch = io.inputchoice(f"{{var:promptcolor}}member:{{var:inputcolor}} ", "NAEQ", "Q")
        if ch == "E":
          io.echo("Edit")
          edit(args)
          continue
        elif ch == "N":
          io.echo("New User")
          if add(args) is False:
            io.echo(f"con.member.main.100: add failed", level="error")
        elif ch == "Q" or ch == "X":
          io.echo("Quit")
          done = True
          break
