# DEPRECATED: Use inputstring.py instead. This module is not used.
import os
import tty
import time
import fcntl
import termios
from argparse import Namespace

###from .output import *
from .echo import echo
from .const import *


# @since 20110323
# @since 20190913
# @since 20200626
# @since 20200729
# @since 20200901
def gnuinputstring(prompt: str, oldvalue=None, **kwargs) -> str:
    import readline

    args = kw["args"] if "args" in kw else Namespace()
    debug = args.debug if "debug" in args else False

    def preinputhook():
        if debug is True:
            echo("inputstring.preinputhook.80: trace")

        multiple = kw["multiple"] if "multiple" in kw else False
        if debug is True:
            echo(f"inputstring.preinputhook.100: oldvalue={oldvalue!r}", level="debug")
        if type(oldvalue) is list:
            if debug is True:
                echo("inputstring.preinputhook.140: oldvalue is list", level="debug")
            for i in range(len(oldvalue)):
                oldvalue[i] = str(oldvalue[i])
            val = ", ".join(oldvalue)
        else:
            if debug is True:
                echo(
                    "inputstring.preinputhook.160: oldvalue is not list", level="debug"
                )
            val = oldvalue
        if debug is True:
            echo(f"inputstring.preinputhook.120: oldvalue={oldvalue!r}", level="debug")
        readline.insert_text(str(val))
        readline.redisplay()

        if debug is True:
            echo(f"inputstring.100: oldvalue={oldvalue!r}", level="debug")

    if oldvalue is not None:
        readline.set_pre_input_hook(preinputhook)
    #    echo("inputstring.120: pre_input_hook set", level="debug")

    inputfunc = input

    args = kw["args"] if "args" in kw else Namespace()

    filter = kw["filter"] if "filter" in kw else None

    returnseq = kw["returnseq"] if "returnseq" in kw else False

    multiple = kw["multiple"] if "multiple" in kw else None

    oldcompleter = readline.get_completer()
    completer = kw["completer"] if "completer" in kw else oldcompleter

    oldcompleterdelims = readline.get_completer_delims()
    completerdelims = (
        kw["completerdelims"] if "completerdelims" in kw else oldcompleterdelims
    )

    verify = kw["verify"] if "verify" in kw else None

    #  if args is not None and "debug" in args and args.debug is True:
    #    echo("inputstring.100: completerdelims=%r" % (completerdelims), interpret=False)
    #    echo("completer is %r" % (completer))

    readline.parse_and_bind("tab: complete")
    if (
        completer is not None
        and hasattr(completer, "complete")
        and callable(completer.complete) is True
    ):
        if args is not None and "debug" in args and args.debug is True:
            echo("setting completer function", level="debug")
        readline.set_completer(completer.complete)
        if multiple is True:
            completerdelims += ", "
        readline.set_completer_delims(completerdelims)
    else:
        if args is not None and "debug" in args and args.debug is True:
            echo("completer is none or is not callable.")

    done = False
    while not done:
        #    prompt = rl_escape_prompt(prompt)
        buf = inputfunc(tostr(prompt))  # interpretecho(prompt))

        if oldvalue is not None:
            readline.set_pre_input_hook(None)

        if buf is None or buf == "":
            if "noneok" in kw and kw["noneok"] is True:
                return None
            else:
                return oldvalue

        if filter is not None:
            if args is not None and "debug" in args and args.debug is True:
                echo(re.match(filter, buf), level="debug")

            if re.match(filter, buf) is None:
                echo("invalid input", level="error")
                continue

        if multiple is True:
            #      echo("completerdelims=%r" % (completerdelims), interpret=False)
            foo = re.split("|".join(", "), buf)
            foo = [f.strip() for f in foo]  # strip whitespace from items
            foo = [f for f in foo if f]  # remove empty items
        else:
            foo = str(buf)

        if callable(verify) is True and verify(foo, **kwargs) is False:
            echo("verify is callable, verify() returned false", level="debug")
            done = False
            continue

        break

    readline.set_completer(oldcompleter)
    readline.set_completer_delims(oldcompleterdelims)

    return foo


def getchinputstring(prompt, originalvalue=None, **kwargs):
    args = kwargs.get("args", Namespace())
    debug = args.debug if "debug" in args else False
    mask = kwargs.get("mask", None)
    maxlen = kwargs.get("maxlen", None)
    filter = kwargs.get("filter", None)
    preinputhook = kwargs.get("preinputhook", None)
    help = kwargs.get("help", None)
    noneok = kwargs.get("noneok", False)
    verify = kwargs.get("verify", None)
    multiple = kwargs.get("multiple", False)

    completer = kwargs.get("completer", None)
    if debug is True:
        echo(f"ttyio6.input.getchinputstring.100: {kwargs=}", level="debug")

    if originalvalue is None:
        buf = ""
    else:
        buf = str(originalvalue)

    pos = len(buf)

    def currentword():
        words = buf.split(" ")
        wordindex = 0
        for x in range(0, len(buf)):
            if x == pos:
                break
            if buf[x] == " ":
                wordindex += 1
        return words[wordindex]

    def currentwordindex():  # buf, pos):
        return buf.index(currentword())  # words[wordindex])

    olddisplay = ""

    def display():
        nonlocal olddisplay
        if mask is not None:
            b = mask * len(buf)
        else:
            b = buf
        curdisplay = f"{{cha:1}}{{eraseline}}{prompt}{b}{{cursorleft:{len(buf) - pos}}}"
        if curdisplay != olddisplay:
            echo(
                curdisplay, flush=True, end=""
            )  # f"{{cursorhpos:1}}{{eraseline}}{prompt}{b}{{cursorleft:{len(buf)-pos}}}", flush=True, end="")
            olddisplay = curdisplay

    ##        echo(f"{{cursorhpos:1}}{{eraseline}}{prompt}{b}#        echo(f"{{cursorhpos:1}}{{eraseline}}{prompt}*{b}", flush=True, end="")
    #        bbsengine.screen.setarea(f"pos: {pos} len(buf): {len(buf)} len(prompt): {len(prompt)}")
    #        echo(f"pos: {pos} len(buf): {len(buf)} len(prompt): {len(prompt)}")

    if type(preinputhook) is str:
        echo(preinputhook)
    elif callable(preinputhook) is True:
        echo(preinputhook())

    state = 0

    done = False
    while not done:
        if len(buf) - pos < 0:
            pos = 0

        display()

        ch = getch()
        #        print(f"{ch=}")

        if ch is None:
            continue
        elif ch == "KEY_ENTER":
            echo()
            if noneok is True and buf == "":
                return None

            if multiple is True:
                foo = re.split("|".join(", "), buf)
                foo = [f.strip() for f in foo]  # strip whitespace from items
                foo = [f for f in foo if f]  # remove empty items
            else:
                foo = str(buf)

            if callable(verify) is True and verify(foo, **kwargs) is False:
                if debug is True:
                    echo("verify is callable, verify() returned false", level="debug")
                done = False
                continue
            return foo
        elif ch == "KEY_CUTTOBOL":  # ^U erase from point to bol, copy to clipboard
            buf = buf[pos:]
            pos = 0
            continue
        elif ch == "KEY_BACKSPACE":  # del from cursor towards left
            if pos > 0:
                #                ttyio.echo(chr(8)+" "+chr(8), flush=True, end="")
                buf = buf[: pos - 1] + buf[pos:]
                pos -= 1
            else:
                echo("{bell}", end="", flush=True)
                pos = 0
            continue
        elif ch == "KEY_LEFT":
            if pos == 0:
                echo("{bell}", end="", flush=True)
            else:
                echo("{cursorleft}", end="", flush=True)
                pos -= 1
            continue
        elif ch == "KEY_RIGHT":
            if pos < len(buf):
                pos += 1
                echo("{cursorright}", end="", flush=True)
            else:
                echo("{bell}", end="", flush=True)
            continue
        elif ch == "KEY_HOME":
            echo(f"{{cursorleft:{pos}}}", end="", flush=True)
            pos = 0
            continue
        elif ch == "KEY_END":
            if pos < len(buf):
                z = len(buf) - pos
                echo(f"{{cursorright:{len(buf) - pos}}}", end="", flush=True)
                pos = len(buf)
            continue
        elif ch == "KEY_TAB":
            #            state = 0
            if completer is None:
                echo("{bell}", flush=True, end="")
                continue
            if callable(completer) is False:
                echo("{bell:2}", flush=True, end="")
                continue
            #            c = completerclass(**kw)
            #            c = completerclass(args)
            if callable(completer) is True:
                if debug is True:
                    echo(f"completer is callable: {args=} {kwargs=}", level="debug")
                res = completer(currentword(), state=state, **kwargs)
                # echo(f"--> {res=}", level="debug")
                if len(res) == 0:
                    echo("{bell}", end="", flush=True)
                elif len(res) == 1:
                    p = abs(len(res[0]) - len(currentword()))
                    pos += p  # +1
                    buf = buf.replace(currentword(), res[0], 1)  # res[0]+" "
                    echo(f"{{cursorright:{p}}}", end="", flush=True)
                #                    echo(f"{{f6:2}}len(currentword)={len(currentword())} len(res[0])={len(res[0])} right p={p}{{f6:2}}", end="", flush=True)
                else:
                    echo(" ".join(res))
                    if debug is True:
                        echo(f"--> {len(res)=}")
                        echo(f"tab: {res=}")
                state += 1
                continue
        elif (ch == "KEY_HELP" or ch == "?") and help is not None:
            if type(help) is str:
                echo(help)
            elif callable(help):
                echo(help(**kwargs))
                continue
        elif ch == "KEY_DEL":
            if len(buf) == 0 or pos + 1 > len(buf):
                echo("{bell}")
                continue
            buf = buf[:pos] + buf[pos + 1 :]
            echo("{cursorright:2}", end="", flush=True)
            continue
        elif ch[:4] == "KEY_":
            echo("key=%r" % (ch), level="debug")
            continue

        if maxlen is not None and len(buf) >= maxlen:
            echo("{bell}", end="", flush=True)
            continue

        # echo(f"mask={mask!r}", level="debug")
        if mask is None:
            echo(ch, flush=True, end="")
        else:
            echo(mask, flush=True, end="")

        buf = buf[:pos] + ch + buf[pos:]
        pos += 1


def inputstring(*argv, style="ttyio", **kwargs):
    if style == "gnu":
        return gnuinputstring(*argv, **kwargs)
    return getchinputstring(*argv, **kwargs)


# @since 20230621
##inputchar = inputchoice

terinallock = None

KEYS = {
    "[A": "KEY_UP",
    "[B": "KEY_DOWN",
    "[C": "KEY_RIGHT",
    "[D": "KEY_LEFT",
    "[H": "KEY_HOME",
    "[F": "KEY_END",
    "[5~": "KEY_PAGEUP",  # ncurses:KEY_PPAGE
    "[6~": "KEY_PAGEDOWN",  # ncurses:KEY_NPAGE
    "[2~": "KEY_INS",
    "[3~": "KEY_DEL",
    "OP": "KEY_HELP",
    "OQ": "KEY_F2",
    "OR": "KEY_F3",
    "OS": "KEY_F4",
    "[15~": "KEY_F5",
    "[17~": "KEY_F6",
    "[18~": "KEY_F7",
    "[19~": "KEY_F8",
    # "[20~": "KEY_F9",
    # "[21~": "KEY_F10",
    ">": "KEY_DECPNM",  # @see https://vt100.net/docs/vt220-rm/chapter4.html#S4.6.18 numeric or application keypad mode
    "=": "KEY_DECPAM",
}


def ctrl_key_name(ch):
    ctrl_map = {
        "\x01": "CTRL_A",
        "\x02": "CTRL_B",
        "\x03": "CTRL_C",  # Already handled separately
        "\x04": "CTRL_D",  # Already handled separately
        "\x05": "CTRL_E",
        "\x06": "CTRL_F",
        "\x07": "CTRL_G",
        "\x08": "CTRL_H",  # Often backspace
        "\x09": "CTRL_I",  # Tab
        "\x0a": "CTRL_J",  # Line feed
        "\x0b": "CTRL_K",
        "\x0c": "CTRL_L",
        "\x0d": "CTRL_M",  # Carriage return
        "\x0e": "CTRL_N",
        "\x0f": "CTRL_O",
        "\x10": "CTRL_P",
        "\x11": "CTRL_Q",
        "\x12": "CTRL_R",
        "\x13": "CTRL_S",
        "\x14": "CTRL_T",
        "\x15": "CTRL_U",
        "\x16": "CTRL_V",
        "\x17": "CTRL_W",
        "\x18": "CTRL_X",
        "\x19": "CTRL_Y",
        "\x1a": "CTRL_Z",
        "\x1b": "ESC",  # Already handled separately
        "\x1c": "CTRL_BACKSLASH",
        "\x1d": "CTRL_CLOSEBRACKET",
        "\x1e": "CTRL_CARET",
        "\x1f": "CTRL_UNDERSCORE",
        "\x7f": "DEL",
    }
    return ctrl_map.get(ch)


def ctrl_key_name(ch):
    value = ord(ch)
    if 1 <= value <= 26 and value not in ("\x15", "\x04", "\x03", "\x1a"):
        return f"KEY_CTRL_{chr(value + 64)}"
    return None


# @since 20250527 rewrite to use select instead of time.sleep()
def getch(keytimeout=0.125, **kwargs):
    """Reads a single character from standard input non-blocking, handling escape sequences with a timeout."""
    import time, platform, tty, fcntl, termios, sys, os, select

    stream = kwargs.get("stream", sys.stdin)
    fd = stream.fileno()
    old_settings = termios.tcgetattr(fd)
    old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)

    CTRLKEYSEQ = {
        "\x7f": "KEY_BACKSPACE",
        "\t": "KEY_TAB",
        "\n": "KEY_NEWLINE",
        "\r": "KEY_ENTER",
        "\x0c": "KEY_FF",
        "\x15": "KEY_CUTTOBOL",  # ^U
    }

    # Define known escape sequences (example KEYS map)
    KEYS = {
        "[A": "KEY_UP",
        "[B": "KEY_DOWN",
        "[C": "KEY_RIGHT",
        "[D": "KEY_LEFT",
        "OH": "KEY_HOME",  # Some terminals send this
        "OF": "KEY_END",
    }

    def ctrl_key_name(ch):
        # Optionally add custom control character mapping
        return None

    try:
        tty.setraw(fd)  # Raw mode
        if platform.system() != "Darwin":
            fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)

        start_time = time.time()

        while time.time() - start_time < keytimeout:
            rlist, _, _ = select.select(
                [stream], [], [], keytimeout - (time.time() - start_time)
            )
            if not rlist:
                break

            try:
                ch = stream.read(1)
            except (IOError, OSError):
                continue
            except KeyboardInterrupt:
                raise

            if not ch:
                continue

            if ch in CTRLKEYSEQ:
                return CTRLKEYSEQ[ch]
            elif ch == "\x03":
                raise KeyboardInterrupt
            elif ch == "\x04":
                raise EOFError
            elif ch == "\x1b":
                # Handle escape sequence
                seq = ""
                esc_start = time.time()

                while time.time() - esc_start < 0.05:
                    rlist, _, _ = select.select([stream], [], [], 0.01)
                    if rlist:
                        try:
                            next_ch = stream.read(1)
                        except (IOError, OSError):
                            break
                        if not next_ch:
                            break
                        seq += next_ch
                        if seq in KEYS:
                            return KEYS[seq]
                    else:
                        break

                if not seq:
                    return "KEY_ESC"
                return "\x1b" + seq  # Raw unknown escape sequence

            ctrl_name = ctrl_key_name(ch)
            if ctrl_name:
                return ctrl_name

            return ch  # Normal character

        return None  # Timeout
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)


def accept(prompt: str, options: str, default: str = "", debug: bool = False) -> str:
    #  if debug is True:
    #    echo("ttyio4.accept.100: options=%s" % (options), level="debug")

    default = default.upper() if default is not None else ""
    options = options.upper()
    echo(prompt, end="", flush=True)

    while 1:
        ch = getch().upper()

        if ch == "KEY_ENTER":
            return default
            if default is not None:
                return default
            else:
                return ch
        elif ch in options:
            return ch
