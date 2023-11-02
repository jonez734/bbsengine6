import argparse

import ttyio6 as ttyio
import bbsengine6 as bbsengine

parser = argparse.ArgumentParser("testing line editor")
args = parser.parse_args()
args.debug = False
args.databasename = "zoid6"

bbsengine.session.start(args)

bbsengine.screen.init()
bbsengine.screen.setarea("line editor")

try:
    bbsengine.module.runsubmodule(args, "bbsengine6.editor")
except KeyboardInterrupt:
    ttyio.echo("{/all}{bold}INTR{bold}")
except EOFError:
    ttyio.echo("{/all}{bold}EOF{/bold}")
finally:
    ttyio.echo("{decsc}{curpos:%d,0}{el}{decrc}{reset}{/all}" % (ttyio.getterminalheight()))
