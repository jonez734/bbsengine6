import os
import tty
import time
import fcntl
import termios
import argparse

from .output import *
from .const import *

keys = {
  "[A":   "KEY_UP",
  "[B":   "KEY_DOWN",
  "[C":   "KEY_RIGHT",
  "[D":   "KEY_LEFT",
  "[H":   "KEY_HOME",
  "[F":   "KEY_END",
  "[5~":  "KEY_PAGEUP",
  "[6~":  "KEY_PAGEDOWN",
  "[2~":  "KEY_INS",
  "[3~":  "KEY_DEL",
  "OP":   "KEY_HELP",
  "OQ":   "KEY_F2",
  "OR":   "KEY_F3",
  "OS":   "KEY_F4",
  "[15~": "KEY_F5",
  "[17~": "KEY_F6",
  "[18~": "KEY_F7",
  "[19~": "KEY_F8",
  # "[20~": "KEY_F9",
  # "[21~": "KEY_F10",
  ">":    "KEY_DECPNM", # @see https://vt100.net/docs/vt220-rm/chapter4.html#S4.6.18 numeric or application keypad mode
  "=":    "KEY_DECPAM",
}

# @see https://stackoverflow.com/questions/9043551/regex-that-matches-integers-only
def inputinteger(prompt, oldvalue=None, **kw) -> int:
  oldvalue = int(oldvalue) if oldvalue is not None else ""
  filter = kw["filter"] if "filter" in kw else r"^([+-]?[1-9]\d*|0)[ ,]?$"
  buf = inputstring(prompt, oldvalue, filter=filter, **kw)

  if buf is None or buf == "":
    return None
  
#  print(f"type(buf)={type(buf)!r}")
  if type(buf) is list:
    res = []
    for b in buf:
      try:
        res.append(int(b))
      except:
        return
#    echo(f"res={res!r}", level="debug")
    return res
  else:
#    echo("inputinteger.100: plain int, not a list", level="debug")
    try:
      res = int(buf)
    except:
      return
    else:
      return res

# @since 20110323
# @since 20190913
# @since 20200626
# @since 20200729
# @since 20200901
def gnuinputstring(prompt:str, oldvalue=None, **kw) -> str:
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
        echo("inputstring.preinputhook.160: oldvalue is not list", level="debug")
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
  completerdelims = kw["completerdelims"] if "completerdelims" in kw else oldcompleterdelims
  
  verify = kw["verify"] if "verify" in kw else None

#  if args is not None and "debug" in args and args.debug is True:
#    echo("inputstring.100: completerdelims=%r" % (completerdelims), interpret=False)
#    echo("completer is %r" % (completer))

  readline.parse_and_bind("tab: complete")
  if completer is not None and hasattr(completer, "complete") and callable(completer.complete) is True:
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
    buf = inputfunc(tostr(prompt)) # interpretecho(prompt))

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
      foo = [f.strip() for f in foo] # strip whitespace from items
      foo = [f for f in foo if f] # remove empty items
    else:
      foo = str(buf)
    
    if callable(verify) is True and verify(foo, **kw) is False:
      echo("verify is callable, verify() returned false", level="debug")
      done = False
      continue

    break

  readline.set_completer(oldcompleter)
  readline.set_completer_delims(oldcompleterdelims)

  return foo

def getchinputstring(prompt, originalvalue=None, **kw):
    args = kw["args"] if "args" in kw else Namespace()
    debug = args.debug if "debug" in args else False
    mask = kw["mask"] if "mask" in kw else None
    maxlen = kw["maxlen"] if "maxlen" in kw else None
    filter = kw["filter"] if "filter" in kw else None
    preinputhook = kw["preinputhook"] if "preinputhook" in kw else None
    help = kw["help"] if "help" in kw else None
    noneok = kw["noneok"] if "noneok" in kw else False
    verify = kw["verify"] if "verify" in kw else None
    multiple = kw["multiple"] if "multiple" in kw else False

    completer = kw["completer"] if "completer" in kw else None
    if debug is True:
        echo(f"ttyio6.input.getchinputstring.100: {kw=}", level="debug")

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

    def currentwordindex(): # buf, pos):
        return buf.index(currentword()) # words[wordindex])

    def display():
        if mask is not None:
            b = mask*len(buf)
        else:
            b = buf
        echo(f"{{cursorhpos:1}}{{eraseline}}{prompt}{b}{{cursorleft:{len(buf)-pos}}}", flush=True, end="")
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
        if len(buf)-pos < 0:
          pos = 0

        display()

        ch = getch()

        if ch == "KEY_ENTER":
            echo()
            if noneok is True and buf == "":
                return None

            if multiple is True:
              foo = re.split("|".join(", "), buf)
              foo = [f.strip() for f in foo] # strip whitespace from items
              foo = [f for f in foo if f] # remove empty items
            else:
              foo = str(buf)

            if callable(verify) is True and verify(foo, **kw) is False:
                if debug is True:
                    echo("verify is callable, verify() returned false", level="debug")
                done = False
                continue
            return foo
        elif ch == "KEY_CUTTOBOL": # ^U erase from point to bol, copy to clipboard
            buf = buf[pos:]
            pos = 0
            continue
        elif ch == "KEY_BACKSPACE": # del from cursor towards left
            if pos > 0:
#                ttyio.echo(chr(8)+" "+chr(8), flush=True, end="")
                buf = buf[:pos-1]+buf[pos:]
                pos -= 1
            else:
                echo("{bell}", end="",flush=True)
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
              echo(f"{{cursorright:{len(buf)-pos}}}", end="", flush=True)
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
                    echo(f"completer is callable: {args=} {kw=}", level="debug")
                res = completer(currentword(), state=state, **kw)
                echo(f"--> res={res!r}", level="debug")
                if len(res) == 0:
                    echo("{bell}", end="", flush=True)
                elif len(res) == 1:
                    p = abs(len(res[0])-len(currentword()))
                    pos += p+1
                    buf = buf.replace(currentword(), res[0]+" ", 1)
                    echo(f"{{cursorright:{p}}}", end="", flush=True)
#                    echo(f"{{f6:2}}len(currentword)={len(currentword())} len(res[0])={len(res[0])} right p={p}{{f6:2}}", end="", flush=True)
                else:
                    echo(" ".join(res))
                    if debug is True:
                        echo(f"--> len(res)={len(res)}")
                        echo(f"tab: {res!r}")
                state += 1
                continue
        elif (ch == "KEY_HELP" or ch == "?") and help is not None:
            if type(help) is str:
                echo(help)
            elif callable(help):
                echo(help(**kw))
                continue
        elif ch == "KEY_DEL":
            if len(buf) == 0 or pos+1 > len(buf):
                echo("{bell}")
                continue
            buf = buf[:pos]+buf[pos+1:]
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

def inputstring(*argv, style="ttyio", **kw):
  if style == "gnu":
    return gnuinputstring(*argv, **kw)
  return getchinputstring(*argv, **kw)

# @since 20230105 backported from ttyio6 (bugfix)
# @see https://ballingt.com/nonblocking-stdin-in-python-3/
# @since 20230512 renamed from 'inputchar' in ttyio5 @BCBREAK
def inputchoice(prompt:str, options:str, default:str="", **kw) -> str: #default:str="", args:object=Namespace(), noneok:bool=False, helpcallback=None) -> str:
  args = kw["args"] if "args" in kw else None # Namespace()
  noneok = kw["noneok"] if "noneok" in kw else False
  help = kw["help"] if "help" in kw else None

  default = default.upper() if default is not None else ""

  options = options.upper()
  options = "".join(sorted(options))

  echo(prompt, end="", flush=True)

  done = False
  while not done:
    ch = getch() # .decode("UTF-8")
    if ch is not None:
      ch = ch.upper()

    if ch == "KEY_ENTER":
      if noneok is True:
        return None
      elif default is not None and default != "":
        return default
      else:
        echo("{bell}", end="", flush=True)
        continue
    elif (ch == "?" or ch == "KEY_HELP"): #  and callable(helpcallback) is True:
      echo("help")
      if callable(help):
        help(**kw)
      elif type(help) is str:
        echo(help)
      echo(prompt, end="", flush=True)
    elif ch is not None:
        if ch[:4] == "KEY_" or ch in options:
            break
        echo("{bell}", end="", flush=True)
        continue
     
  return ch

# @since 20230621
inputchar = inputchoice

# @since 20210203
def inputboolean(prompt:str, default:str=None, options="YN", **kw) -> bool:
  ch = inputchoice(prompt, options, default, **kw)
  if ch is not None:
    ch = ch.upper()
  if ch == "Y":
          echo("Yes")
          return True
  elif ch == "T":
          echo("True")
          return True
  elif ch == "N":
          echo("No")
          return False
  elif ch == "F":
          echo("False")
          return False
  return


terinallock = None

# @since 20231017
# @inspiredby https://ballingt.com/nonblocking-stdin-in-python-3/
def getch(*args, **kwargs):
#    noneok = kwargs["noneok"] if "noneok" in kwargs else False
    file = kwargs["file"] if "file" in kwargs else sys.stdin
    keytimeout = kwargs["keytimeout"] if "keytimeout" in kwargs else None
#    echo(f"{keytimeout=}", level="debug")

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

    thetick = 0
    done = False
    sleeptime = 0.0042
    kt = 0 # keytimeout ticks
    with raw(file):
        with nonblocking(file):
            while not done:
                try:
                    ch = file.read(1) # sys.stdin.read(1)
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

                    if ch == "\x01":
                        ch = "KEY_HOME"
                        break
                    elif ch == "\x04":
                        raise EOFError
                    elif ch == "\x05":
                        ch = "KEY_END"
                        break
                    elif ch == "\x15": # ^U
                        ch = "KEY_CUTTOBOL"
                        break
#                    elif ch == "\x08":
#                        ch = "KEY_BACKSPACE"
#                        break
                    elif ch == "\x7F": # or ch == \x08
                        ch = "KEY_BACKSPACE"
                        break
                    elif ch == "\t":
                        ch = "KEY_TAB"
                        break
                    elif ch == "\n":
                        ch = "KEY_ENTER"
                        break
                    elif ch == "\x0C":
                        ch = "KEY_FF"
                        break
                    elif ch != "" and ord(ch) >= 1 and ord(ch) < 27:
                        ch = "KEY_CTRL_"+chr(ord(ch)+ord("A")-1)
                        break
                    if esc is True:
                        thetick += 1
                        buf += ch # bytes(ch, "utf-8")
                        # print(repr(buf))
                        if buf in keys:
                          # print("found")
                          ch = keys[buf]
                          done = True
                          esc = False
                          buf = ""
                          break
                        if thetick > 3:
                          if len(buf) == 0:
                            ch = "KEY_ESC"
                            break
                          ch = buf
                          esc = False
                          buf = ""
                          thetick = 0
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

def accept(prompt:str, options:str, default:str="", debug:bool=False) -> str:
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

