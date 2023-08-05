import argparse

import bbsengine6 as bbsengine

parser = argparse.ArgumentParser("testing session handling in bbsengine6")
bbsengine.database.buildarggroup(parser)
args = parser.parse_args()
args.debug = False
bbsengine.screen.init()
bbsengine.session.start(args)
bbsengine.session.set(args, "name", 42)
print(bbsengine.session.get(args, "name", default="defaulthere"))
print(bbsengine.session.get(args, "xname", default="needinfo"))
