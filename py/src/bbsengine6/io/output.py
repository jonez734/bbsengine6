# DEPRECATED: This module is not used. Use bbsengine6.io.echo instead.
# @since 20260429
import warnings

warnings.warn(
    "bbsengine6.io.output is deprecated. Use bbsengine6.io.echo instead.",
    DeprecationWarning,
    stacklevel=2,
)

import re
import time

from typing import NamedTuple
from argparse import Namespace
# from tzlocal import tzlocal

from . import echovars, terminal

# from .vars import *
# from .terminal import getterminalwidth, savecursor, restorecursor
from .const import *
from .lib import *

width = terminal.width()
wordwrap = True
end = "\n"
indent = 0
exclude = ()
speed = 0
pos = 0
# strip = False -- unused


class Token(NamedTuple):
    kind: str
    value: str = None


#    uncooked: str


def tokenize(buf: str, exclude=()):  # -> generator:
    # print(f"{buf=}")
    if type(buf) is not str:
        return buf

    tok_regex = "|".join("(?P<%s>%s)" % pair for pair in token_specification)

    for mo in re.finditer(tok_regex, buf, re.IGNORECASE):
        kind = mo.lastgroup
        value = mo.group()
        if kind in exclude:
            #          print(f"tokenize.100: excluded {kind=}")
            continue

        if kind == "F6":
            value = mo.group("F6repeat") or 1  # group 11
        #        elif kind == "WHITESPACE":
        #            yield Token(kind, value) # yield token # result += token.value
        elif kind == "NL":
            value = " "
        elif kind == "OPENBRACE":
            value = "{"
        elif kind == "CLOSEBRACE":
            value = "}"
        elif kind == "EMPTYBRACES":
            value = "{}"
        elif kind == "BELL":
            value = mo.group("BELLrepeat") or 1  # 33) or 1
        elif kind == "DECSTBM":
            top = mo.group("topmarginnum") or 0  # 28
            bot = mo.group("botmarginnum") or 0  # 30
            value = (int(top), int(bot))
        elif kind == "DECSLRM":
            left = mo.group("leftmarginnum") or 1  # 28
            right = mo.group("rightmarginnum") or 0  # 30
            yield Token("CURSOR", f"{CSI}{left};{right}s")
        elif kind == "CURPOS":
            y = mo.group("curposy")  # 13
            x = mo.group("curposx") or 0  # 15
            value = (int(y), int(x))
        elif kind == "CHA":
            value = mo.group("chanum") or 1
        #          yield Token("CURSOR", f"{CSI}{value}G")
        elif kind == "ERASELINE":
            value = mo.group("elmode") or 0  # mo.group(3)
        elif kind == "ACS":
            name = mo.group("acsname")
            repeat = mo.group("acsrepeat") or 1
            value = (name, repeat)
        elif kind == "VAR":
            var = mo.group("varname")  # 35
            value = echovars.get(var)
            for t in tokenize(value, exclude=exclude):
                # print(f"tokenize.120: {t=}")
                yield t
            continue
        elif kind == "CURSORUP":
            value = mo.group("cuunum") or 1  # \x1b[<repeat>A 38
        elif kind == "CURSORRIGHT":
            value = mo.group("cufnum") or 1  # 41
        elif kind == "CURSORLEFT":
            value = mo.group("cubnum") or 1  # 44
        elif kind == "CURSORDOWN":
            value = mo.group("cudnum") or 1  # 47
        elif kind == "WAIT":
            value = int(mo.group("waitduration")) or 1  # 49) or 1)
        elif kind == "UNICODE":
            name = mo.group("unicodename")  # 52
            repeat = mo.group("unicoderepeat") or 1  # 54
            value = (name, int(repeat))
        elif kind == "EMOJI":
            value = mo.group("emoji")
        elif kind == "ERASEDISPLAY":
            value = mo.group("edmode")  # 64
            if value == "tobottom":
                value = 1
            elif value == "totop":
                value = 2
            else:
                value = 0
        elif kind == "CURSORHPOS":
            value = int(mo.group("hpos")) or 1  # group 68
            yield Token("CURSOR", value)  # this is wrong. check 'cha' instead
        elif kind == "RGB":
            rgbval = mo.group("rgbval")  # 70
            if rgbval is not None:
                value = tuple(bytes.fromhex(rgbval))
            else:
                value = rgbval
        elif kind == "SPEED":
            value = int(mo.group("speednum")) or 0
        elif kind == "INDENT":
            value = int(mo.group("indentnum")) or 0  # 74
        elif kind == "TAG":
            value = (mo.group("tagkind"), mo.group("tagparam"))
        elif kind == "BOLD":
            kind = "ATTRIBUTE"
            value = f"*{CSI}1m{mo.group('bold')}{CSI}22m*"
        elif kind == "ITALIC":
            kind = "ATTRIBUTE"
            value = f"/{CSI}3m{mo.group('italic')}{CSI}23m/"
        elif kind == "STRIKE":
            kind = "ATTRIBUTE"
            value = f"~{CSI}9m{mo.group('strike')}{CSI}29m~"
        elif kind == "UNDERLINE":
            kind = "ATTRIBUTE"
            value = f"_{CSI}4m{mo.group('underline')}{CSI}24m_"
        elif kind == "DCH":
            dchnum = mo.group("dchnum") or 1
            yield Token("CURSOR", f"{CSI}{dchnum}P")
        elif kind == "AT":
            value = "@"
        elif kind == "COMMAND":
            if value in attributes:
                kind = "ATTRIBUTE"
            elif value in colors:
                kind = "COLOR"
            elif value in acs:
                kind = "ACS"  # yield Token("ACS", token.value) # f"{CSI}{acs[token.value]}")
            elif value in emoji:
                kind = "EMOJI"
            else:
                v = value.replace("{", "").replace("}", "")
                if v in echovars.variables:
                    for t in tokenize(echovars.variables[v]):
                        # print(f"VAR: {t=}")
                        yield t
                    continue
                    # yield Token("EMOJI", f"{emoji[token.value]}")
        # print(f"--> {kind=} {value=}")
        yield Token(kind, value)


def interpret(tokens, **kwargs: dict):
    # from wcwidth import wcswidth
    wcswidth = len
    # def interpret(buf:str, **kwargs) -> str: #wordwrap:bool=True, end:str="\n", args=Namespace(), indent:str="---") -> str:
    global width, strip, wordwrap, end, indent, exclude, speed, pos

    width = kw["width"] if "width" in kw else width
    # strip = kw["strip"] if "strip" in kw else False
    wordwrap = kw["wordwrap"] if "wordwrap" in kw else wordwrap
    end = kw["end"] if "end" in kw else end
    args = kw["args"] if "args" in kw else Namespace()
    indent = kw["indent"] if "indent" in kw else indent
    exclude = kw["exclude"] if "exclude" in kw else exclude

    style = getoption("style", "ttyio")

    if tokens is None:
        yield None

    # if buf is None or buf == "":
    #    return ""

    result = ""
    # firstword = True -- unused
    # pos = 0
    for token in tokens:
        # print(f"{token=}")
        if type(token) is str:
            yield Token("WORD", token)
            continue

        if token in exclude:
            print("interpret.100: {token=}")
            continue
        ##  for token in tokenize(buf):
        if token.kind == "DECSTBM":
            yield token
            # top, bot = token.value
            # if bot == 0:
            # 	yield f"{CSI}{top}r" # result += CSI+"%dr" % (top)
            # else:
            # 	yield f"{CSI}{top};{bot}r" # result += CSI+"%d;%dr" % (top, bot)
        elif token.kind == "SLASHALL":
            yield Token(
                "COLOR", f"{CSI}0;39;49m"
            )  # yield f"{CSI}0;39;49m" # result += CSI+"0;39;49m"
            yield Token("SPEED", 0)
        elif token.kind == "RESET":
            yield Token("DECSC")
            # ESC [ 0 ; 0 r)  is used to reset the cursor position to the top left corner of the terminal (row 0, column 0) and  clear all formatting applied to the cursor.
            # yield Token("RESET", f"{ESC}[0;0r")
            yield Token("DECSTBM", (0, 0))
            yield Token("SLASHALL")
            yield Token("SPEED", 0)
            yield Token("INDENT", 0)
            yield Token("DECRC")  # restore cursor position
        elif (
            token.kind == "ERASELINE"
        ):  # Erases part of the line. If token.value is 0 (or missing), clear from cursor to the end of the line. If n is 1, clear from cursor to beginning of the line. If n is 2, clear entire line. Cursor position does not change.
            yield f"{CSI}{token.value}K"  # result += CSI+"%dK" % (token.value)
        elif token.kind == "ACS":  # use alternate character set
            command, repeat = token.value
            if command is not None and command.upper() in acs:
                char = acs[command.upper()]
                pos += wcswidth(char * int(repeat))
                yield Token(
                    "ACS", f"{ESC}(0{char * int(repeat)}{ESC}(B"
                )  # result += "\033(0%s\033(B" % (char*int(repeat))
        elif token.kind == "DECSC":
            yield token
        elif token.kind == "DECRC":
            yield token
        elif token.kind == "CURPOS":
            y, x = token.value
            yield Token(
                "CURSOR", f"{CSI}{y};{x}H"
            )  # f"{CSI}{y};{x}H" # result += CSI+"%d;%dH" % (y, x)
        elif token.kind == "CHA":  # Moves the cursor to column n (default 1)
            yield Token("CURSOR", f"{ESC}[{token.value}G")
        elif token.kind == "CURSORUP":  # {cursorup:10}
            repeat = int(token.value)
            if repeat > 0:
                yield Token(
                    "CURSOR", f"{ESC}[{repeat}A"
                )  # result += CSI+"%dA" % (repeat)
        elif token.kind == "CURSORDOWN":
            repeat = int(token.value)
            if repeat > 0:
                yield Token(
                    "CURSOR", f"{ESC}[{repeat}B"
                )  # result += CSI+"%dB" % (repeat)
        elif token.kind == "CURSORRIGHT":
            repeat = int(token.value)
            if repeat > 0:
                yield Token(
                    "CURSOR", f"{ESC}[{repeat}C"
                )  # result += CSI+"%dC" % (repeat)
        elif token.kind == "CURSORLEFT":
            repeat = int(token.value)
            yield Token("CURSORLEFT", repeat)
        elif token.kind == "WAIT":
            yield token
        elif token.kind == "HIDECURSOR":
            yield Token("CURSOR", f"{CSI}?25l")  # result += CSI+"?25l"
        elif token.kind == "SHOWCURSOR":
            yield Token("CURSOR", f"{CSI}?25h")
        elif token.kind == "CURSORHPOS":
            yield Token("CURSOR", f"{CSI}{token.value}G")
        elif token.kind == "UNICODE":
            (name, repeat) = token.value
            name = name.upper()
            if name in unicode:
                yield Token("UNICODE", unicode[name] * repeat)
        elif token.kind == "WORD":
            yield Token("WORD", token.value)
        elif token.kind == "OPENBRACE" or token.kind == "CLOSEBRACE":
            yield token  # result += token.value
        elif token.kind == "EMPTYBRACES":
            yield token
            # pos += 1
        elif token.kind == "COLOR":
            yield f"{ESC}[{colors[token.value]}"

        # @see https://en.wikipedia.org/wiki/ANSI_escape_code
        # 0 = entire display (default) all
        # 1 = cursor to end of display tobottom
        # 2 = cursor to top of display totop
        elif token.kind == "ERASEDISPLAY":
            yield f"{CSI}{token.value}"  # result += f"{CSI}{token.value}J" # CSI+"%dJ" % (token.value)
        elif token.kind == "RGBCOLOR":
            yield Token(
                "RGBCOLOR", f"{CSI}{rgb(38, token.value)}"
            )  # result += CSI+rgb(38, token.value) # (255, 255, 255))}, # )"38;2;255;255;255m", "rgb": (255,255,255) }, # 37m
        elif token.kind == "SPEED":
            yield token
        elif token.kind == "AT":
            yield "@"
            # pos += 1
        elif token.kind == "TAG":
            handler = getoption("taghandler", None)
            if handler is None:
                print(f"--> {token.value=}")
            else:
                if callable(handler) is True:
                    yield handler(args, token)
        elif token.kind == "VAR":
            for t in tokenize(token.value):
                yield t
            # v = token.value.replace("{", "").replace("}", "")
            # if v in vars.variables:
            #    for t in interpret(tokenize(vars.variables[v], exclude=exclude)):
            #        print(f"interpret.120: {t=}")
            #        yield t
            # else:
            #    yield token.value
        elif token.kind == "COMMAND":
            # print(f"interpret COMMAND {token.value=} ")
            yield token.value
            # if token.value in attributes:
            #    yield Token("ATTRIBUTE", f"{CSI}{attributes[token.value]}")
            # elif token.value in colors:
            #    yield Token("COLOR", f"{CSI}{colors[token.value]}")
            # elif token.value in acs:
            #    yield Token("ACS", f"{CSI}{acs[token.value]}")
            # elif token.value in emoji:
            #    yield Token("EMOJI", f"{emoji[token.value]}")
            # else:
            #  yield token.value
            # print(f"unknown command: {token.value=}")
            #  v = token.value.replace("{", "").replace("}", "")
            #  if v in vars.variables:
            #    for t in tokenize(vars.variables[v]):
            #      # print(f"{t=} ")
            #      for i in interpret(t):
            #        # print(f"{i=} ")
            #        yield i
            #  else:
            #    yield token.value
        # elif token.kind == "COLOR":
        #  # print(f"yielding {token.value=}")
        #  yield Token("COLOR", f"{CSI}{colors[token.value]}")
        else:
            yield token


def echo(buf: str = "", **kwargs):
    wcswidth = len
    # from wcwidth import wcswidth

    global pos, indent, end, wordwrap, strip, width, speed
    # width = kw["width"] if "width" in kw else terminal.width() # getterminalwidth()
    level = kwargs["level"] if "level" in kw else None
    # strip = kw["strip"] if "strip" in kw else strip
    wordwrap = kw["wordwrap"] if "wordwrap" in kw else wordwrap
    flush = kw["flush"] if "flush" in kw else True
    end = kw["end"] if "end" in kw else "\n"
    indent = kw["indent"] if "indent" in kw else indent
    args = kw["args"] if "args" in kw else Namespace()
    interp = kw["interpret"] if "interpret" in kw else True
    file = kw["file"] if "file" in kw else terminal._streamout  # sys.stdout
    exclude = kw["exclude"] if "exclude" in kw else ()
    # pos = 0 # needed?

    if level is not None:
        prefix = ""
        if level == "debug":
            prefix = "{level.debug}D: "  # {bglightblue}{blue}"
        elif level == "warn" or level == "warning":
            prefix = "{level.warning}W: "  # {bgyellow}{black}"
        elif level == "error":
            prefix = "{level.error}E: "  # {bgred}{black}"
        elif level == "success" or level == "ok":
            prefix = "{level.ok}"  # {bggreen}{black}"
        elif level == "info":
            prefix = "{level.info}I: "  # {bgwhite}{blue}"
        print(
            tostr(f"{prefix} ") + tostr(buf, interpret=False) + tostr(" {normalcolor}"),
            flush=True,
        )
        return

    if interp is True:
        # speed = 0
        mode = getoption("mode", "ttyio")

        if mode == "ttyio":
            tokensallowed = (
                "ACS",
                "CURSOR",
                "EMOJI",
                "COLOR",
                "BGCOLOR",
                "RGBCOLOR",
                "RESET",
                "UNICODE",
                "ATTRIBUTE",
                "COMMAND",
                "WORD",
                "WHITESPACE",
                "CONTROL",
            )
        elif mode == "noansi":
            tokensallowed = ("UNICODE", "WORD", "WHITESPACE", "F6")
        else:
            tokensallowed = ("WORD", "WHITESPACE", "F6")

        for token in interpret(tokenize(buf, exclude=exclude)):
            # for token in interpret(buf, **kwargs):
            if isinstance(token, Token):
                if token.kind == "WHITESPACE":
                    pos += wcswidth(token.value)
                    print(token.value, end="", flush=True)
                elif token.kind == "CURSOR":
                    print(token.value, end="", flush=True)
                elif token.kind == "WAIT":
                    time.sleep(WAIT * int(token.value))
                elif token.kind == "F6":
                    print(f"\n" * int(token.value), flush=True, end="")
                    pos = 0
                    # firstword = True
                elif token.kind == "SPEED":
                    speed = token.value
                elif token.kind == "INDENT":
                    indent = token.value
                elif token.kind == "TAG":
                    kind, param = token.value
                    print(f"--> test: {kind} {param}")
                elif token.kind == "WORD":
                    if pos + wcswidth(token.value) >= width - 1 and wordwrap is True:
                        pos = 0
                        print(f"\n", end="")
                    print(token.value, end="", flush=True)
                    pos += wcswidth(token.value)
                    time.sleep(SPEED * speed)
                elif token.kind == "COLOR":
                    print(
                        token.value, end="", flush=True
                    )  # token.value, end="", flush=True)
                elif token.kind == "EMOJI":
                    print(emoji[token.value], end="", flush=True)
                elif token.kind == "ATTRIBUTE":
                    print(token.value, end="", flush=True)
                elif token.kind == "NL":
                    print(token.value, end="", flush=True)
                elif token.kind == "ACS":
                    print(token.value, end="", flush=True)
                elif token.kind == "VAR":
                    pass
                elif token.kind == "SLASHALL":
                    print(token.value, end="", flush=True)
                elif token.kind == "RESET":
                    print(token.value, end="", flush=True)
                elif token.kind == "DECSC":
                    terminal.savecursor()
                elif token.kind == "DECRC":
                    print(f"{terminal.restorecursor()}", end="", flush=True)
                elif token.kind == "CURSORLEFT":
                    if token.value > 0:
                        pos -= token.value
                        print(f"{ESC}[{token.value}D", end="")
                elif token.kind == "BELL":
                    print("\007" * int(token.value), end="", flush=True)
                elif token.kind == "DECSTBM":
                    top, bot = token.value
                    # print(f"{token.value=}")
                    if bot == 0:
                        print(
                            f"{CSI}{top}r", end="", flush=True
                        )  # result += CSI+"%dr" % (top)
                    else:
                        print(
                            f"{CSI}{top};{bot}r", end="", flush=True
                        )  # result += CSI+"%d;%dr" % (top, bot)
                elif token.kind == "OPENBRACE" or token.kind == "CLOSEBRACE":
                    print(token.value, end="", flush=True)
                elif token.kind == "EMPTYBRACES":
                    print(token.value, end="", flush=True)
                else:
                    print(f"--> Token({token.kind!r}, {token.value!r})", flush=True)
            else:
                print(f"{token}", end="", flush=True)
    else:
        print(f"{buf}", end=end, flush=flush)
    # print(f"{end=}", end=end, flush=flush)
    # if end == "\n":
    print(end=end, flush=flush)
    return


def tostr(buf: str, **kwargs: dict):
    # strip = kw["strip"] if "strip" in kw else False
    interp: bool = kw["interpret"] if "interpret" in kw else True
    exclude: tuple = kw["exclude"] if "exclude" in kw else ()

    if interp is False:
        return buf

    res = ""

    for tok in interpret(tokenize(buf, exclude=exclude), exclude=exclude):
        #        print(f"{tok=}")
        if type(tok) is str:
            res += tok
        elif tok.kind in exclude or tok.kind in (
            "SPEED",
            "WAIT",
            "SLASHALL",
        ):  #  or tok.kind not in ("WORD", "WHITESPACE"):
            continue
        elif type(tok) is Token:
            res += tok.value
    return res


def set_terminal_background_color(r, g, b):
    """Sets the terminal background color using ANSI escape codes."""
    print(f"\033]11;rgb:{r:02x}/{g:02x}/{b:02x}\a", end="", flush=True)


# Example: Set the background color to light blue
# set_terminal_color(173, 216, 230)


def reset_terminal_background_color():
    """Resets the terminal background color to default."""
    print(f"\033]11;\a", end="", flush=True)


def strip_commands(s: str) -> str:
    import re

    # Remove {...} formatting commands
    s = re.sub(r"\{[^}]+\}", "", s)
    # Remove :emoji: style placeholders
    s = re.sub(r":[a-zA-Z0-9_+\-]+:", "", s)
    return s
