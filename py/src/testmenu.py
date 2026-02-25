import argparse

from bbsengine6 import io, menu

def main():
    parser = argparse.ArgumentParser("menu")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    io.setvar("engine.menu.boxcharcolor", "{bglightgray}{darkgreen}")
    io.setvar("engine.menu.color", "{bggray}")
    io.setvar("engine.menu.shadowcolor", "{bgdarkgray}")
    io.setvar("engine.menu.cursorcolor", "{bglightgray}{blue}")
    io.setvar("engine.menu.boxcolor", "{bgblue}{green}")
    io.setvar("engine.menu.itemcolor", "{blue}{bglightgray}")
    io.setvar("engine.menu.titlecolor", "{black}{bglightgray}")
    io.setvar("engine.menu.promptcolor", "{promptcolor}")
    io.setvar("engine.menu.inputcolor", "{inputcolor}")
    io.setvar("engine.menu.disableditemcolor", "{darkgray}")
    io.setvar("engine.menu.resultfailedcolor", "{bgred}{white}")

    io.setvar("itemcolor", "{blue}{bglightgray}")
    io.setvar("currentitemcolor", "{bgwhite}{black}")

    menuitems = []
    for x in range(0, 15):
        menuitems.append(menu.Item(chr(65+x), f"item {chr(65+x)}", blah))

    m = menu.Menu(args, "testing bbsengine.menu", menuitems, pagesize=20)
    done = False
    while not done:
        op = m.run()
        if op.kind == "select":
            io.echo(f"{{var:inputcolor}}selected option {op.menuitem.key=}")
            if io.inputboolean("continue: ") is False:
                done = True
                break

def blah(args, menuitem):
    io.echo(f"running 'blah': {menuitem=}", level="debug")

#bbsengine.screen.init()
#bbsengine.screen.setarea("testing")


try:
    main()
#    elif op.kind == "exit":
#        ttyio.echo(f"{{var:inputcolor}}exit")
#    elif op.kind == "enter":
#        ttyio.echo(f"enter on {op.menuitem.key=}", level="debug")
except KeyboardInterrupt:
    io.echo("{/all}{restorecursor}*INTR*")
except EOFError:
    io.echo("{/all}{restorecursor}*EOF*")
finally:
    io.echo(f"{{savecursor}}{{curpos:{io.getterminalheight()},0}}{{/all}}{{el}}{{restorecursor}}{{reset}}")

# ttyio.echo(f"{ttyio.terminal.cursorpositions=}", level="debug")
