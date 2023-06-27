import ttyio6 as ttyio
import bbsengine6 as bbsengine

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
    bbsengine.util.heading("con")
    ttyio.echo("{f6}{var:labelcolor}database: {var:valuecolor}%s {var:labelcolor}host: {var:valuecolor}%s:%s{f6}" % (args.databasename, args.databasehost, args.databaseport))
    ttyio.echo("{var:optioncolor}[M]{var:labelcolor}embers")
#    ttyio.echo("[E]mail")
    ttyio.echo("{f6}{var:optioncolor}[Q]{var:labelcolor}uit")
    ch = ttyio.inputchoice("{var:promptcolor}engine: {var:inputcolor}", "MEQ", "Q")
    if ch == "M":
      ttyio.echo("Members")
      lib.runsubmodule(args, "member")
      continue
#    elif ch == "E":
#      ttyio.echo("E-Mail")
#      email(args)
#      continue
    else:
      ttyio.echo("Quit")
      done = True
      break
