from bbsengine6 import session, util, io
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

  done = False
  while not done:
    session.updatelastactivity(args, session.currentsessionid)

    util.heading("con")
    io.echo("{f6}{var:labelcolor}database: {var:valuecolor}%s {var:labelcolor}host: {var:valuecolor}%s:%s{f6}" % (args.databasename, args.databasehost, args.databaseport))

    io.echo("{var:optioncolor}[M]{var:labelcolor} Members")
    io.echo("{var:optioncolor}[S]{var:labelcolor} Sessions")
#    ttyio.echo("[E]mail")
    io.echo("{f6}{var:optioncolor}[X]{var:labelcolor} Quit{f6}")
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
    elif ch == "Q" or ch == "X":
      io.echo("Exit")
      break
    else:
      io.echo("{bell}", end="", flush=True)
      done = True
      break
