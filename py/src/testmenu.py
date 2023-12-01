import argparse

import ttyio6 as ttyio
import bbsengine6 as bbsengine

parser = argparse.ArgumentParser("menu")
parser.add_argument("--debug", action="store_true")

args = parser.parse_args()

ttyio.setvar("engine.menu.boxcharcolor", "{bglightgray}{darkgreen}")
ttyio.setvar("engine.menu.color", "{bggray}")
ttyio.setvar("engine.menu.shadowcolor", "{bgdarkgray}")
ttyio.setvar("engine.menu.cursorcolor", "{bglightgray}{blue}")
ttyio.setvar("engine.menu.boxcolor", "{bgblue}{green}")
ttyio.setvar("engine.menu.itemcolor", "{blue}{bglightgray}")
ttyio.setvar("engine.menu.titlecolor", "{black}{bglightgray}")
ttyio.setvar("engine.menu.promptcolor", "")
ttyio.setvar("engine.menu.inputcolor", "{white}")
ttyio.setvar("engine.menu.disableditemcolor", "{darkgray}")
ttyio.setvar("engine.menu.resultfailedcolor", "{bgred}{white}")

ttyio.setvar("itemcolor", "{blue}{bglightgray}")
ttyio.setvar("currentitemcolor", "{bgwhite}{black}")

menuitems = []

def blah(args, menuitem):
    ttyio.echo(f"{menuitem=}", level="debug")

#bbsengine.screen.init()
#bbsengine.screen.setarea("testing")

for x in range(0, 10):
    menuitems.append(bbsengine.menu.Item(chr(65+x), f"item {chr(65+x)}", "blah"))

try:
    menu = bbsengine.menu.Menu(args, "title here", menuitems, pagesize=20)
    op = menu.run()
#    ttyio.echo(f"{Op=}")
    if op.kind == "select":
        ttyio.echo(f"{{var:inputcolor}}selected option {op.menuitem.key=}")
#    elif op.kind == "exit":
#        ttyio.echo(f"{{var:inputcolor}}exit")
#    elif op.kind == "enter":
#        ttyio.echo(f"enter on {op.menuitem.key=}", level="debug")
except KeyboardInterrupt:
    ttyio.echo("{/all}{restorecursor}*INTR*")
except EOFError:
    ttyio.echo("{/all}{restorecursor}*EOF*")
finally:
    ttyio.echo(f"{{savecursor}}{{curpos:{ttyio.getterminalheight()},0}}{{/all}}{{el}}{{restorecursor}}{{reset}}")

ttyio.echo(f"{ttyio.terminal.cursorpositions=}", level="debug")
