import argparse

import bbsengine6 as bbsengine

from . import lib

def init(args=None, **kw):
    return True

def access(args=None, op="run", **kw):
    return True

def buildargs(args=None, **kw):
    parser = argparse.ArgumentParser("vulcan")
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    defaults = {"databasename": "zoid6", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None}
    bbsengine.database.buildargdatabasegroup(parser, defaults)

    return parser

def main(args, **kw):
    return lib.runsubmodule(args, "main", **kw)
