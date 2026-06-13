# @since 20230801 it's about time
import os
import tempfile
from . import util, screen, io, member

buf = []
currentline = 0


def init(args, **kwargs):
    return True


def access(args, op, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def help(**kw):
    util.heading("editor help")
    io.echo(".A -- abort")
    io.echo(".X -- exit")
    io.echo(".S -- save")
    io.echo(".E -- edit line")
    io.echo(".D -- delete line or range")
    io.echo(".I -- insert at line")
    io.echo(".V -- version")


def line(args, **kwargs):
    terminalwidth = io.getterminalwidth()

    util.heading("line editor")
    done = False
    pos = 0
    linebuf = ""
    currentlinenumber = 0
    command = False

    while not done:
        screen.setarea(f"editor: {pos=} {len(buf)=} {currentlinenumber=}")

        ch = io.getch()
        if ch == "." and pos == 0 and command is False:
            io.echo(
                "{var:promptcolor}command: {var:inputcolor}",
                end="",
                flush=True,
                help=help,
            )
            command = True
            continue
        elif ch == "KEY_HELP":
            help()
            continue
        elif ch == "KEY_ENTER":
            pos = 0
            io.echo()
            currentlinenumber += 1
            if currentlinenumber > len(buf):
                buf.append(linebuf)
            continue
        elif command is True:
            if ch == ".":
                io.echo("{cursorhpos:1}.{eraseline:0}", end="", flush=True)
                linebuf = "."
                pos += 1
            elif ch == "x":
                done = True
                io.echo("eXit")
                break
            elif ch == "e":
                if len(buf) == 0:
                    io.echo("{bell}")
                    continue
                editline = io.inputinteger("Edit line: ")
                if editline > len(buf):
                    io.echo("invalid line number")
                    continue
                io.echo(f"editing line {editline=}", level="debug")
            elif ch == "s":
                filename = io.inputstring(
                    f"Save. {{var:promptcolor}}filename: {{var:inputcolor}}"
                )
            elif ch == "d":
                if len(buf) == 0:
                    io.echo("{bell}")
                    continue
                deleteline = io.inputstring(f"Delete. Range: {var:inputcolor}")
            else:
                io.echo("{bell}", flush=True, end="")
        else:
            if pos < terminalwidth - 2:
                io.echo(ch, end="", flush=True, interpret=False)
                linebuf += ch
                pos += 1
            else:
                pass
                # find last whitespce, erase to it, then start a new line


def visual(args, text: str = "", suffix: str = "noteupdate"):
    filefp, fn = tempfile.mkstemp(suffix=suffix)

    with open(fn, "w") as fp:
        fp.writelines(text)

    if "VISUAL" in os.environ:
        editor = os.environ["VISUAL"]
    elif "EDITOR" in os.environ:
        editor = os.environ["EDITOR"]
    else:
        editor = "joe -r"

    os.system(f"{editor} {diaryfn}")
    if os.access(diaryfn, os.F_OK | os.R_OK | os.W_OK):
        fp = open(diaryfn, "r")
        notes = fp.readlines()
        fp.close()

    notes = "\n".join(notes)
    notes = notes.strip()

    diary = {}
    diary["lastmodified"] = "now()"
    diary["lastmodifiedbymoniker"] = member.getcurrentid(args)
    diary["notes"] = notes

    io.echo(f"{diary=}", level="debug")


def main(args, **kw):
    kind = kw["kind"] if "kind" in kw else None

    if kind == "line":
        line(args)
    elif kind == "visual":
        visual(args)
    return True
