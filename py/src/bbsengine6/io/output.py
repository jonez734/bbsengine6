import re
import sys
import time

from typing import NamedTuple
from argparse import Namespace
from .terminal import _streamout, _streamin
#from tzlocal import tzlocal

from . import vars
from . import terminal

#from .vars import *
#from .terminal import getterminalwidth, savecursor, restorecursor
from .const import *
from .lib import *

class Token(NamedTuple):
    kind: str
    value: str
#    uncooked: str


def tokenize(buf:str, args:object=Namespace()):
    global tok_regex_c

    if type(buf) is not str:
      return buf

    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)

    for mo in re.finditer(tok_regex, buf, re.IGNORECASE):
        kind = mo.lastgroup
        value = mo.group()

        if kind == "NL":
          pass
        elif kind == "F6":
          value = mo.group("F6repeat") or 1 # group 11
        elif kind == "MISMATCH":
            pass
            # raise RuntimeError(f'{value!r} unexpected on line {line_num}')
        elif kind == "OPENBRACE":
          value = "{"
        elif kind == "CLOSEBRACE":
          value = "}"
        elif kind == "BELL":
          value = mo.group("BELLrepeat") or 1 # 33) or 1
        elif kind == "DECSTBM":
          top = mo.group("topmarginnum") or 0 # 28
          bot = mo.group("botmarginnum") or 0 # 30
          value = (int(top), int(bot))
        elif kind == "DECSLRM":
          left = mo.group("leftmarginnum") or 1 # 28
          right = mo.group("rightmarginnum") or 0 # 30
          yield Token("CURSOR", f"{CSI}{left};{right}s")
#          value = (int(top), int(bot))
        elif kind == "CURPOS":
          y = mo.group("curposy") # 13
          x = mo.group("curposx") or 0 # 15
          value = (int(y), int(x))
        elif kind == "DECSC":
          pass
        elif kind == "DECRC":
          pass
        elif kind == "CHA":
          value = mo.group("chanum") or 1
#          yield Token("CURSOR", f"{CSI}{value}G")
        elif kind == "ERASELINE":
          value = mo.group("elmode") or 0 # mo.group(3)
        elif kind == "ACS":
          # print(mo.groups())
          # @FIX: why the huge offset?
#          command = mo.group(2)
#          repeat = mo.group(4) or 1
          name = mo.group("acsname")
          repeat = mo.group("acsrepeat") or 1
          value = (name, repeat)
          # print("value.command=%r, value.repeat=%r" % (command, repeat))
        elif kind == "VAR":
#          print("var! mo.groups=%r" % (repr(mo.groups())))
          try:
            var = mo.group("varname") # 35
            value = vars.get(var)
          except RecursionError:
            print("** too much recursion **")
            continue
#          print("var=%r value=%r" % (var, value))
          for t in tokenize(str(value)):
            # print("{var} yielding token %r" % (t,))
            yield t
          # print("__tokenizemci.100: var=%r value=%r" % (var, value))
        elif kind == "CURSORUP":
          value = mo.group("cuunum") or 1 # \x1b[<repeat>A 38
        elif kind == "CURSORRIGHT":
          value = mo.group("cufnum") or 1 # 41
        elif kind == "CURSORLEFT":
          value = mo.group("cubnum") or 1 # 44
        elif kind == "CURSORDOWN":
          value = mo.group("cudnum") or 1 # 47
        elif kind == "WAIT":
          value = int(mo.group("waitduration")) or 1 # 49) or 1)
        elif kind == "UNICODE":
          name = mo.group("unicodename") # 52
          repeat = mo.group("unicoderepeat") or 1 # 54
#          print("unicode.100: name=%s repeat=%r" % (name, repeat))
          value = (name, int(repeat))
        elif kind == "EMOJI":
          value = mo.group("emoji")
#        elif kind == "HIDECURSOR":
#          pass
#        elif kind == "SHOWCURSOR":
#          pass
        elif kind == "ERASEDISPLAY":
          value = mo.group("edmode") # 64
          if value == "tobottom":
            value = 1
          elif value == "totop":
            value = 2
          else:
            value = 0
        elif kind == "CURSORHPOS":
          value = int(mo.group("hpos")) or 1 # group 68
          yield Token("CURSOR", value) # this is wrong. check 'cha' instead
        elif kind == "RGB":
          g = mo.group("rgbval") # 70
          if g is not None:
            value = tuple(bytes.fromhex(g))
          else:
            value = g
        elif kind == "SPEED":
          value = int(mo.group("speednum")) or 0
        elif kind == "INDENT":
          value = int(mo.group("indentnum")) or 0 # 74
        elif kind == "TAG":
          value = (mo.group("tagkind"), mo.group("tagparam"))
        elif kind == "BOLD":
          yield Token("ATTRIBUTE", f"*{CSI}1m{mo.group('bold')}{CSI}22m*")
        elif kind == "ITALIC":
          yield Token("ATTRIBUTE", f"/{CSI}3m{mo.group('italic')}{CSI}23m/")
        elif kind == "STRIKE":
          yield Token("ATTRIBUTE", f"~{CSI}9m{mo.group('strike')}{CSI}29m~")
        elif kind == "UNDERLINE":
          yield Token("ATTRIBUTE", f"_{CSI}4m{mo.group('underline')}{CSI}24m_")
        elif kind == "DCH":
          dchnum = mo.group("dchnum") or 1
          yield Token("CURSOR",    f"{CSI}{dchnum}P")
        elif kind == "AT":
          value = "@"

        yield Token(kind, value)

def interpret(buf:str, **kw) -> str: #wordwrap:bool=True, end:str="\n", args=Namespace(), indent:str="---") -> str:
  width = kw["width"] if "width" in kw else None
  strip = kw["strip"] if "strip" in kw else False
  wordwrap = kw["wordwrap"] if "wordwrap" in kw else True
  end = kw["end"] if "end" in kw else "\n"
  args = kw["args"] if "args" in kw else Namespace()
#  indent = kw["indent"] if "indent" in kw else ""
  indent = kw["indent"] if "indent" in kw else 0
  
  style = getoption("style", "ttyio")

  def handlecommand(kind, table, value):
#    print(f"handlecommand.100: style={style!r}")
    for item in table:
      if value == item["command"]:
        if style == "noansi":
          return ""
        return Token(kind.upper(), f"{CSI}{item['ansi']}") # "\033[%s" % (item["ansi"])
    return False

  if buf is None or buf == "":
    return ""

  if strip is True:
    result = ""
    for token in tokenize(buf):
      if token.kind in ("WORD", "WHITESPACE", "NL", "F6"):
        yield token.value # result += token.value
    return result

  if width is None:
    width = terminal.width()

  result = ""
  pos = 0
  for token in tokenize(buf):
      if token.kind == "F6":
#          v = token.value if token.value is not None else 1
          pos = 0
          yield token # result += "\n"*int(v)# +indent
      elif token.kind == "WHITESPACE":
          pos += len(token.value)
          yield token # result += token.value
      elif token.kind == "BELL":
        for b in range(0,int(token.value)):
          yield f"{BELL}"
#        yield "\007"*int(token.value) # result += "\007"*int(token.value)
      elif token.kind == "COMMAND":
        if strip is False:
          res = False
          commands = {"command":echocommands, "attribute":attributes, "color":colors, "bgcolor":bgcolors}
          value = token.value.lower()
          for kind, table in commands.items():
            res = handlecommand(kind, table, value)
            if res is not False:
              if type(res) is Token:
                yield Token(kind.upper(), res.value)
              else:
                yield Token(kind.upper(), res)
              break
      elif token.kind == "DECSTBM":
        top, bot = token.value
        if bot == 0:
          yield f"{CSI}{top}r" # result += CSI+"%dr" % (top)
        else:
          yield f"{CSI}{top};{bot}r" # result += CSI+"%d;%dr" % (top, bot)
      elif token.kind == "SLASHALL":
          yield Token("COLOR", f"{CSI}0;39;49m") # yield f"{CSI}0;39;49m" # result += CSI+"0;39;49m"
          yield Token("SPEED", 0)
      elif token.kind == "RESET":
          yield Token("RESET", f"{CSI}0;39;49m{ESC}[s{ESC}[0;0r{ESC}[u")
      elif token.kind == "ERASELINE": # Erases part of the line. If token.value is 0 (or missing), clear from cursor to the end of the line. If n is 1, clear from cursor to beginning of the line. If n is 2, clear entire line. Cursor position does not change.
        yield f"{CSI}{token.value}K" # result += CSI+"%dK" % (token.value)
      elif token.kind == "ACS": # use alternate character set
        # print("acs. value=%s" % (str(token.value)))
        command, repeat = token.value
        # print("command=%r, repeat=%r" % (command, repeat))
        if command is not None and command.upper() in acs:
          char = acs[command.upper()]
          pos += len(char*int(repeat))
          yield Token("ACS", f"{ESC}(0{char*int(repeat)}{ESC}(B") # result += "\033(0%s\033(B" % (char*int(repeat))
      elif token.kind == "DECSC":
#        print("** DECSC")
        terminal.savecursor()
#        yield f"{CSI}s" # result += CSI+"s"
      elif token.kind == "DECRC":
#        print("** DECRC")
        yield terminal.restorecursor()
#        yield f"{CSI}u" # result += CSI+"u"
      elif token.kind == "CURPOS":
        y, x = token.value
        yield Token("CURSOR", f"{CSI}{y};{x}H") # f"{CSI}{y};{x}H" # result += CSI+"%d;%dH" % (y, x)
      elif token.kind == "CHA": # Moves the cursor to column n (default 1)
          yield Token("CURSOR", f"{ESC}[{token.value}G")
      elif token.kind == "CURSORUP": # {cursorup:10}
        repeat = int(token.value)
        if repeat > 0:
          yield Token("CURSOR", f"{ESC}[{repeat}A") # result += CSI+"%dA" % (repeat)
      elif token.kind == "CURSORDOWN":
        repeat = int(token.value)
        if repeat > 0:
          yield Token("CURSOR", f"{ESC}[{repeat}B") # result += CSI+"%dB" % (repeat)
      elif token.kind == "CURSORRIGHT":
        repeat = int(token.value)
        if repeat > 0:
          yield Token("CURSOR", f"{ESC}[{repeat}C") # result += CSI+"%dC" % (repeat)
      elif token.kind == "CURSORLEFT":
        repeat = int(token.value)
        if repeat > 0:
          yield Token("CURSOR", f"{ESC}[{repeat}D")
      elif token.kind == "WAIT":
        yield token
      elif token.kind == "HIDECURSOR":
        yield Token("CURSOR", f"{CSI}?25l") # result += CSI+"?25l"
      elif token.kind == "SHOWCURSOR":
        yield Token("CURSOR", f"{CSI}?25h")
      elif token.kind == "CURSORHPOS":
        yield Token("CURSOR", f"{CSI}{token.value}G")

      elif token.kind == "UNICODE":
        (name, repeat) = token.value
        name = name.upper()
        if name in unicode:
          yield Token("UNICODE", unicode[name]*repeat)
      elif token.kind == "EMOJI":
        name = token.value # :smile:
        if name in emoji:
          yield Token("EMOJI", emoji[name])
      elif token.kind == "WORD":
        if wordwrap is True:
          if pos+len(token.value) >= width-1:
            yield "\n" # result += "\n"
            if indent > 0:
              yield " "*indent
            pos = len(token.value) # len(indent)+len(token.value)
            yield Token("WORD", token.value)# token.value # result += token.value # indent+token.value
          else:
            pos += len(token.value)
            yield Token("WORD", token.value) # token.value # result += token.value
        else:
          yield token.value # result += token.value
      elif token.kind == "OPENBRACE" or token.kind == "CLOSEBRACE":
        yield token.value # result += token.value
        pos += 1

      # @see https://en.wikipedia.org/wiki/ANSI_escape_code
      # 0 = entire display (default) all
      # 1 = cursor to end of display tobottom
      # 2 = cursor to top of display totop
      elif token.kind == "ERASEDISPLAY":
        yield f"{CSI}{token.value}" # result += f"{CSI}{token.value}J" # CSI+"%dJ" % (token.value)
      elif token.kind == "RGB":
        yield Token("RGBCOLOR", f"{CSI}{rgb(38, token.value)}") # result += CSI+rgb(38, token.value) # (255, 255, 255))}, # )"38;2;255;255;255m", "rgb": (255,255,255) }, # 37m
      elif token.kind == "SPEED":
        yield token
      elif token.kind == "INDENT":
        yield token
#      elif token.kind == "ATPROJECT":
#        (projectid, projectnote) = (token.value)
#        yield f"@project:{projectid} {projectnote}"
      elif token.kind == "AT":
        yield "@"
      elif token.kind == "TAG":
        handler = getoption("taghandler", None)
        if handler is None:
          print(f"--> {token.value=}")
        else:
          if callable(handler) is True:
            yield handler(args, token)
#          else:
#        (kind, param) = token.value
#        yield "test -> {kind} {param}"
      elif token.kind == "NL":
        if wordwrap is True:
          yield " "
        else:
          yield "\n"
      elif token.kind == "ATTRIBUTE":
        yield token.value
      elif token.kind == "CURSOR":
        yield token.value

#        yield token
#        print(f"atproject.120: value={token.value!r}")
#        print(f"atproject.100: {mo.group('ATPROJECT')!r}")

def echo(buf:str="", **kw):
  width = kw["width"] if "width" in kw else terminal.width() # getterminalwidth()
  level = kw["level"] if "level" in kw else None
  strip = kw["strip"] if "strip" in kw else False
  wordwrap = kw["wordwrap"] if "wordwrap" in kw else True
  flush = kw["flush"] if "flush" in kw else True
  end = kw["end"] if "end" in kw else "\n"
  indent = kw["indent"] if "indent" in kw else 0
  args = kw["args"] if "args" in kw else Namespace()
  interp = kw["interpret"] if "interpret" in kw else True
#  datestamp = kw["datestamp"] if "datestamp" in kw else False
#  if datestamp is True:
#    from datetime import datetime
#    now = datetime.now(tzlocal())
#    stamp = strftime("%Y-%b-%d %I:%M:%S%P %Z (%a)", now.timetuple())
#    buf = "%s %s" % (stamp, buf)
  file = kw["file"] if "file" in kw else terminal._streamout # sys.stdout
  
  prefix = ""
  if level is not None:
    if level == "debug":
      prefix = "{var:level.debug}" # {bglightblue}{blue}"
    elif level == "warn" or level == "warning":
      prefix = "{var:level.warning}" # {bgyellow}{black}"
    elif level == "error":
      prefix = "{var:level.error}" # {bgred}{black}"
    elif level == "success" or level == "ok":
      prefix = "{var:level.ok}" # {bggreen}{black}"
    elif level == "info":
      prefix = "{var:level.info}" # {bgwhite}{blue}"

#    echo(prefix, end="", flush=True)
#    echo(f"[{level}] {buf}", interpret=False, flush=True)
#    echo("{/all}")

#    buf = f"{prefix} [{level}] {buf} {{var:normalcolor}}"
#    buf = f"{prefix} {buf} {{var:normalcolor}}"
    print(tostr(f"{prefix} ")+tostr(buf, interpret=False)+tostr(" {var:normalcolor}"), flush=True)
#    print(f"[{level}] {buf}") # interpret(prefix)}{buf}{interpret('{{/all}}')}") # buf = "%s %s %s" % (interpret(prefix), buf, interpret("{/all}"))
    return

  if interp is True:
    speed = 0
    try:
      if indent > 0:
        print(" "*int(indent), end="", flush=True)

      mode = getoption("mode", "ttyio")

      if mode == "ttyio":
        tokensallowed = ("ACS", "CURSOR", "EMOJI", "COLOR", "BGCOLOR", "RGBCOLOR", "RESET", "UNICODE", "ATTRIBUTE", "COMMAND", "WORD", "WHITESPACE", "CONTROL")
      elif mode == "noansi":
        tokensallowed = ("UNICODE", "WORD", "WHITESPACE", "F6")
      else:
        tokensallowed = ("WORD", "WHITESPACE", "F6")

      for tok in interpret(buf, **kw):
        if type(tok) == Token:
          if tok.kind == "WAIT":
            time.sleep(WAIT*int(tok.value))
          elif tok.kind == "F6":
            print(f"\n"*int(tok.value), flush=True, end="")
          elif tok.kind == "NL":
            pass
          elif tok.kind == "SPEED":
            speed = tok.value
          elif tok.kind == "INDENT":
#            print(f"** indent token={tok!r}")
            indent = tok.value
#          elif tok.kind == "ATPROJECT":
#            projectid, projectnote = tok.value
#            print(f"@project:{projectid} {projectnote}")
#          elif tok.kind == "ATSEE":
#            print(f"@see:{tok.value!r}")
          elif tok.kind == "TAG":
            kind, param = tok.value
            print(f"--> test: {kind} {param}")
          elif tok.kind in tokensallowed:
            print(f"{tok.value!s}", end="", flush=True)
          else:
            print(f"--> Token({tok.kind!r}, {tok.value!r})", flush=True)
        else:
          print(tok, end="", flush=True)

        if type(tok) == Token and tok.kind == "WORD":
          time.sleep(SPEED*speed)
    except RecursionError:
      print("recursion error!")
    print(end=end)
  else:
    print(buf, end=end, flush=flush)

  return

def tostr(buf, **kw):
  strip = kw["strip"] if "strip" in kw else False
  interp = kw["interpret"] if "interpret" in kw else True
  if interp is False:
    return buf

  res = ""

  if strip is True:
    allowedtokens = ["WORD", "WHITESPACE", "F6", "NL"]
  else:
    allowedtokens = ["WORD", "WHITESPACE", "F6", "EMOJI", "COLOR", "BGCOLOR", "RGBCOLOR", "RESET", "COMMAND", "ACS", "CONTROL", "CURSOR"]

  for tok in interpret(buf):
    if type(tok) is str:
      res += tok
    elif type(tok) is Token:
      if tok.kind == "F6":
          res += "\n"*int(tok.value)
      elif tok.kind in allowedtokens:
        res += tok.value

  return res
