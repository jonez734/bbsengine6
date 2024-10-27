from bbsengine6 import session, util, io, database
#import bbsengine6 as bbsengine

from . import lib

def init(*args, **kw):
    return True

def buildargs(*args, **kw):
    return lib.buildargs(*args, **kw)

def access(args, op, **kw):
    return True

def main(args, **kw):
  parser = lib.buildargs()
  args = parser.parse_args()

  if session.start(args) is False:
    io.echo("con.__main__.100: could not start session", level="error")
    return False

  lib.checkroles(args)

  done = False
  while not done:
    session.updatelastactivity(args, session.currentsessionid)

    util.heading("con")
    io.echo(f"{{f6}}{{var:labelcolor}}database: {{var:valuecolor}}{args.databasename} {{var:labelcolor}}host: {{var:valuecolor}}{args.databasehost}{{var:labelcolor}}:{{var:valuecolor}}{args.databaseport}{{f6}}")

    io.echo("{var:optioncolor}[M]{var:labelcolor} Members")
    io.echo("{var:optioncolor}[S]{var:labelcolor} Sessions")
#    io.echo("{var:optioncolor}[A]{var:labelcolor} Member Approval")
#    ttyio.echo("[E]mail")
    io.echo("{f6}{var:optioncolor}[X]{var:labelcolor} Exit{f6}")
    ch = io.inputchoice("{var:promptcolor}console: {var:inputcolor}", "MSEXQ", "X")
    if ch == "M":
      io.echo("Members")
      lib.runmodule(args, "member")
      continue
#    elif ch == "E":
#      ttyio.echo("E-Mail")
#      email(args)
#      continue
    elif ch == "S":
      io.echo("Sessions")
      lib.runmodule(args, "session")
      continue
    elif ch == "A":
      io.echo("Member Approval")
      lib.runmodule(args, "memberapproval")
    elif ch == "Q" or ch == "X":
      io.echo("Exit")
      break
    else:
      io.echo("{bell}", end="", flush=True)
      done = True
      break
