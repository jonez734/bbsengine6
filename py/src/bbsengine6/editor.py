# @since 20230801 it's about time

import ttyio6 as ttyio

from . import util
from . import screen

def init(args, **kwargs):
    return True

def access(args, op, **kwargs):
    return True

def buildargs(args, **kwargs):
    return

def main(args, **kwargs):
    terminalwidth = ttyio.getterminalwidth()

    util.heading("line editor")
    done = False
    pos = 0
    command = False
    while not done:
        ch = ttyio.getch()
        if ch == "." and pos == 0:
            ttyio.echo("command: ", end="", flush=False)
            command = True
            continue
        elif ch == "KEY_HELP":
            ttyio.echo("help here")
            continue
        elif ch == "KEY_ENTER":
            pos = 0
            ttyio.echo()
            continue
        elif command is True:
            if ch == "x":
                done = True
                ttyio.echo("eXit")
                break
            elif ch == "e":
                editline = ttyio.inputinteger("Edit line: ")
                if editline > len(buffer):
                    ttyio.echo("invalid line number")
                    continue
                ttyio.echo(f"editing line {editline!r}", level="debug")
        else:
            if pos < terminalwidth-2:
                ttyio.echo(ch, end="", flush=True)
                pos += 1
            else:
                pass
                # find last whitespce, erase to it, then start a new line
