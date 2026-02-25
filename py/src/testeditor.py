import argparse

from bbsengine6 import io, screen, session, module

parser = argparse.ArgumentParser("testing line editor")
args = parser.parse_args()
args.debug = False
args.databasename = "zoid6"

session.start(args)

screen.init()
screen.setarea("line editor")

try:
    module.runmodule(args, "bbsengine6.editor", kind="line")
except KeyboardInterrupt:
    io.echo("{/all}{bold}INTR{bold}")
except EOFError:
    io.echo("{/all}{bold}EOF{/bold}")
finally:
    io.echo("{decsc}{curpos:%d,0}{el}{decrc}{reset}{/all}" % (io.getterminalheight()))
