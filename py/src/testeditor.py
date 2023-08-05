import argparse

import bbsengine6 as bbsengine

parser = argparse.ArgumentParser("testing line editor")
args = parser.parse_args()
args.debug = False
bbsengine.screen.init()

bbsengine.module.runsubmodule(args, "bbsengine6.editor")

