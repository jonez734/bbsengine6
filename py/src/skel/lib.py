PACKAGENAME = "skel"

from bbsengine6 import module


def checkmodule(args, module, **kw):
    module = PACKAGENAME + "." + module
    return bbsengine.checkmodule(args, module, **kw)


def runmodule(args, modulename, **kw):
    return module.runmodule(args, f"{PACKAGENAME}.{modulename}", **kw)


def buildargs(args=None, **kw):
    parser = argparse.ArgumentParser(PACKAGENAME)
    parser.add_argument("--verbose", action="store_true", dest="verbose")
    parser.add_argument("--debug", action="store_true", dest="debug")

    #    defaults = {"databasename": "zoid6", "databasehost":"localhost", "databaseuser": None, "databaseport":5432, "databasepassword":None}
    #    database.buildargs(parser, defaults)

    return parser
