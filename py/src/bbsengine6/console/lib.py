import argparse

from bbsengine6 import io, database, session, screen, module

SQLDIR = "$HOME/projects/bbsengine6/sql/"

# @since 20230518 copied from teos
def buildargs(args=None, **kwargs):
    parser = argparse.ArgumentParser("con")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    defaults = {"databasename": "zoid6", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None}
    database.buildargs(parser, defaults)
    
    return parser

# @since 20230523
def runmodule(args, submodule, **kwargs):
#  io.echo(f"con.lib.runmodule.100: {kwargs=}", level="debug")
  return module.runmodule(args, f"con.{submodule}", **kwargs)

# @since 20230523 copied from teos
def setbottombar(args, left, **kwargs):
    def right():
        help = " | F1: Help" if "help" in kwargs and kwargs["help"] is True else ""
        debug = " | debug" if args.debug is True else ""
        return f"con{debug}{help}"

    screen.setbottombar(left, right, **kwargs)
    return

def checkroles(args, **kwargs):
  return runmodule(args, "checkroles", **kwargs)

def checkextensions(args, **kwargs):
  return runmodule(args, "checkextensions", **kwargs)

def checkdatabase(args, **kwargs):
  return runmodule(args, "checkdatabase", **kwargs)

def checksuperuser(args, **kwargs):
  return runmodule(args, "checksuperuser", **kwargs)

def createdatabase(args, **kwargs):
  return runmodule(args, "createdatabase", **kwargs)

def checkfunctions(args, **kwargs):
  return runmodule(args, "checkfunctions", **kwargs)

def checkclasses(args, **kwargs):
  return runmodule(args, "checkclasses", **kwargs)

def checkschema(args, **kwargs):
  return runmodule(args, "checkschema", **kwargs)

def checkflag(args, **kwargs):
  return runmodule(args, "checkflag", **kwargs)
