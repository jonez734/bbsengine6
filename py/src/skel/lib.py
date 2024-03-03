PACKAGENAME = "PACKAGENAME"

from bbsengine6 import module

def runmodule(args, modulename, **kw):
    return module.runmodule(args, f"{PACKAGENAME}.{modulename}", **kw)
