# @since 20231017
# @inspiredby https://ballingt.com/nonblocking-stdin-in-python-3/
def getch(*args, **kwargs):
    #    noneok = kwargs["noneok"] if "noneok" in kwargs else False
    file = kwargs.get("file", sys.stdin)
    keytimeout = kwargs.get("keytimeout", None)

    esc = False
    buf = ""

    class raw(object):
        def __init__(self, stream):
            self.stream = stream
            self.fd = self.stream.fileno()

        def __enter__(self):
            self.original_stty = termios.tcgetattr(self.stream)

            newattr = termios.tcgetattr(self.fd)

            self.new_stty = termios.tcgetattr(self.stream)
            tty.setcbreak(self.stream)

        def __exit__(self, type, value, traceback):
            termios.tcsetattr(self.stream, termios.TCSANOW, self.original_stty)

    class nonblocking(object):
        def __init__(self, stream):
            self.stream = stream
            self.fd = self.stream.fileno()

        def __enter__(self):
            self.orig_fl = fcntl.fcntl(self.fd, fcntl.F_GETFL)
            fcntl.fcntl(self.fd, fcntl.F_SETFL, self.orig_fl | os.O_NONBLOCK)

        def __exit__(self, *args):
            fcntl.fcntl(self.fd, fcntl.F_SETFL, self.orig_fl)

    KEY_SEQUENCES = {
        "\x01": "KEY_HOME",
        "\x05": "KEY_END",
        "\x15": "KEY_CUTTOBOl",
        "\x7f": "KEY_BACKSPACE",
        "\t": "KEY_TAB",
        "\n": "KEY_ENTER",
        "\x0c": "KEY_FF",
    }
    tick = 0
    done = False
    sleeptime = 0.0042
    kt = 0  # keytimeout ticks
    with raw(file):
        with nonblocking(file):
            while not done:
                try:
                    ch = file.read(1)  # sys.stdin.read(1)
                    if keytimeout is not None:
                        kt += 1
                        if kt >= keytimeout:
                            kt = 0
                            break

                    #                    echo(f"ttyio6.input.getch.120: ch={ch!r} type(ch)={type(ch)!r}", level="debug")
                    if ch == ESC:
                        esc = True
                        buf = ""
                        # print("ESC")
                        continue

                    #                    if ch == "\x01":
                    #                        ch = "KEY_HOME"
                    #                        break
                    elif ch == "\x04":
                        raise EOFError
                    #                    elif ch == "\x05":
                    #                        ch = "KEY_END"
                    #                        break
                    #                    elif ch == "\x15": # ^U
                    #                        ch = "KEY_CUTTOBOL"
                    #                        break
                    ##                    elif ch == "\x08":
                    ##                        ch = "KEY_BACKSPACE"
                    ##                        break
                    #                    elif ch == "\x7F": # or ch == \x08
                    #                        ch = "KEY_BACKSPACE"
                    #                        break
                    #                    elif ch == "\t":
                    #                        ch = "KEY_TAB"
                    #                        break
                    #                    elif ch == "\n":
                    #                        ch = "KEY_ENTER"
                    #                        break
                    #                    elif ch == "\x0C":
                    #                        ch = "KEY_FF"
                    #                        break
                    elif ch != "" and ord(ch) >= 1 and ord(ch) < 27:
                        ch = "KEY_CTRL_" + chr(ord(ch) + ord("A") - 1)
                        break
                    if esc is True:
                        tick += 1
                        buf += ch  # bytes(ch, "utf-8")
                        # print(repr(buf))
                        if buf in keys:
                            # print("found")
                            ch = keys[buf]
                            done = True
                            esc = False
                            buf = ""
                            break
                        if tick > 3:
                            if len(buf) == 0:
                                ch = "KEY_ESC"
                                break
                            ch = buf
                            esc = False
                            buf = ""
                            tick = 0
                            break
                    else:
                        if len(ch) > 0:
                            break

                except IOError:
                    echo("*IDLE*", level="info")
                finally:
                    #                    echo(f"ttyio6.input.getch.100: {ch=}", level="debug")
                    if ch is not None and len(ch) > 1:
                        break

                    time.sleep(sleeptime)
    #    echo(f"{ch=}", level="debug")

    return ch
