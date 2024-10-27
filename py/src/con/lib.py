import argparse

from bbsengine6 import io, database, session, screen, module

# @since 20230518 copied from teos
def buildargs(args=None, **kw):
    parser = argparse.ArgumentParser("con")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    defaults = {"databasename": "zoid6", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None}
    database.buildargs(parser, defaults)
    
    return parser

# @since 20230523
def runmodule(args, submodule, **kw):
  return module.runmodule(args, f"con.{submodule}", **kw)

# @since 20230523 copied from teos
def setarea(args, left, **kw):
    def right():
        help = " | F1: Help" if "help" in kw and kw["help"] is True else ""
        debug = " | debug" if args.debug is True else ""
        return f"con{debug}{help}"

    screen.setbottombar(left, right)
    return

def checkroles(args):
  roles = ("bbs", "web", "sysop", "term")
  for r in roles:
    io.echo(f"checking for {r}: ", end="")
    if database.rolexists(args, r) is False:
      database.createrol(args, r)
      io.echo("created")
    else:
      io.echo("exists")
