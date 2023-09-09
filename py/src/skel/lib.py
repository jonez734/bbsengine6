PACKAGENAME = "PACKAGENAME"

import bbsengine6 as bbsengine

def runsubmodule(args, submodule, **kw):
    return bbsengine.module.runsubmodule(args, f"{PACKAGENAME}.{submodule}", **kw)
