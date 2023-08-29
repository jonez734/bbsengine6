# @since 20230801 it's about time

import ttyio6 as ttyio

from . import util
from . import screen

tt = []
currentline = 0

def init(args, **kwargs):
    return True

def access(args, op, **kwargs):
    return True

def buildargs(args, **kwargs):
    return

def help(**kw):
    bbsengine.util.heading("editor help")
    ttyio.echo(".A -- abort")
    ttyio.echo(".X -- exit")
    ttyio.echo(".S -- save")
    ttyio.echo(".E -- edit line")
    ttyio.echo(".D -- delete line or range")
    ttyio.echo(".I -- insert at line")
    ttyio.echo(".V -- version")

def main(args, **kwargs):
    terminalwidth = ttyio.getterminalwidth()

    util.heading("line editor")
    done = False
    pos = 0
    command = False
    while not done:
        ch = ttyio.getch()
        if ch == "." and pos == 0 and command is False:
            ttyio.echo("{var:promptcolor}command: {var:inputcolor}", end="", flush=True, help=help)
            command = True
            continue
        elif ch == "KEY_HELP":
            help()
            continue
        elif ch == "KEY_ENTER":
            pos = 0
            ttyio.echo()
            currentline += 1
            continue
        elif command is True:
            if ch == ".":
                ttyio.echo("{cursorhpos:1}.{eraseline:0}", end="", flush=True)
            elif ch == "x":
                done = True
                ttyio.echo("eXit")
                break
            elif ch == "e":
                if len(buffer) == 0:
                    ttyio.echo("{bell}")
                    continue
                editline = ttyio.inputinteger("Edit line: ")
                if editline > len(buffer):
                    ttyio.echo("invalid line number")
                    continue
                ttyio.echo(f"editing line {editline!r}", level="debug")
            elif ch == "s":
                filename = ttyio.inputstring(f"Save. {var:promptcolor}filename: {var:inputcolor}")
            elif ch == "d":
                if len(buffer) == 0:
                    ttyio.echo("{bell}")
                    continue
                deleteline = ttyio.inputstring(f"Delete. Range:{var:inputcolor}")
            else:
                ttyio.echo("{bell}", flush=True, end="")
        else:
            if pos < terminalwidth-2:
                ttyio.echo(ch, end="", flush=True)
                pos += 1
            else:
                pass
                # find last whitespce, erase to it, then start a new line
