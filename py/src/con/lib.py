import argparse

import bbsengine6 as bbsengine

# @since 20230518 copied from teos
def buildargs(args=None, **kw):
    parser = argparse.ArgumentParser("teos")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    defaults = {"databasename": "zoid6", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None}
    bbsengine.database.buildargdatabasegroup(parser, defaults)
    
    return parser

# @since 20230523
def runsubmodule(args, submodule, **kw):
  return bbsengine.module.runmodule(args, f"con.{submodule}", **kw)

# @since 20230523 copied from teos
def setarea(args, left, **kw):
    def right():
        help = " | F1: Help" if "help" in kw and kw["help"] is True else ""
        debug = " | debug" if args.debug is True else ""
        return f"con{debug}{help}"

    bbsengine.screen.setarea(left, right)
    return
