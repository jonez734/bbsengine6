import os
import random
import syslog

import ttyio6 as ttyio

def hr(color="{var:engine.title.hrcolor}", chars="-", width=None, padding=" "):
    if width is None:
        width = ttyio.getterminalwidth()-2
    if ttyio.getoption("style", "ttyio") == "ttyio":
        return f"{{/all}}{padding}{color}{{acs:hline:{width}}}{{/all}}" # % (color, width)
    return f"{padding}{chars*width}"

# titlecolor = "{reverse}"
# hrcolor = ""
# hrchars = "{acs:hline}"
# llcorner="{acs:llcorner}"
# lrcorner="{acs:lrcorner}"
# ulcorner="{acs:ulcorner}"
# urcorner="{acs:urcorner}"
def heading(title:str, level=1, **kw): # hrchar:str="{acs:hline}", llcorner="{acs:llcorner}", lrcorner="{acs:lrcorner}", ulcorner="{acs:ulcorner}", urcorner="{acs:urcorner}", vline="{acs:vline}", width=None, fillchar=" ", center=True):
  if ttyio.getoption("style", "ttyio") == "noansi":
      width = 100
      hline="-"*width
      llcorner="+"
      lrcorner="+"
      ulcorner="+"
      urcorner="+"
      vline="|"
      boxcolor = ""
      titlecolor = ""
      reset = ""
  else:
      width = ttyio.getterminalwidth() - 4
      hline = f"{{acs:hline:{width}}}"
      llcorner = "{acs:llcorner}"
      lrcorner = "{acs:lrcorner}"
      vline = "{acs:vline}"
      urcorner = "{acs:urcorner}"
      ulcorner = "{acs:ulcorner}"
      boxcolor = "{darkgreen}" # var:engine.title.hrcolor}"
      titlecolor = "{white}{bggray}" # {var:engine.title.color}"
      reset = "{/all}"

  w = width - len(title)
#  print(f"w={w!r}")
  if int(w % 2) == 0:
    repeat = int(w/2)
    leftpadding  = " "*int(repeat)
    rightpadding = " "*int(repeat)
  else:
    repeat = int(w-1)/2
    leftpadding  = " "*int(repeat+2)
    rightpadding = " "*int(repeat-1)

  ttyio.echo(f" {boxcolor}{ulcorner}{hline}{urcorner}", wordwrap=False)
  ttyio.echo(f" {boxcolor}{vline}{titlecolor}{leftpadding}{title}{rightpadding}{reset}{boxcolor}{vline}{reset}", wordwrap=False)
  ttyio.echo(f" {boxcolor}{llcorner}{hline}{lrcorner}{reset}", wordwrap=False)
  return

  style = ttyio.getoption("style", "ttyio")
  if style == "noansi":
    width = 100
    hrchar = "-"
    llcorner = "+"
    lrcorner = "+"
    ulcorner = "+"
    urcorner = "+"
    vline = "|"
  else:
    width = getterminalwidth()-2

  if width is None:
    width = ttyio.getterminalwidth()-2
#  buf = ttyio.center(title, width)
  buf = title.center(width) # ttyio.center(title, width)
#  b = title.center(width) # ttyio.center(title)

  ttyio.echo("{/all}{var:engine.title.hrcolor}%s{acs:hline:%s}%s" % (ulcorner, width, urcorner), wordwrap=False)
  ttyio.echo("{var:engine.title.hrcolor}{acs:vline}{/all}{var:engine.title.color}%s{/all}{var:engine.title.hrcolor}{acs:vline}{/all}" % (buf), wordwrap=False)
  # ttyio.echo("{f6}{acs:vline}{/all}%s%s{/all}%s{acs:vline}{/all}" % (titlecolor, i.center(width), hrcolor), end="")
  ttyio.echo("{var:engine.title.hrcolor}%s{acs:hline:%s}%s{/all}" % (llcorner, width, lrcorner), wordwrap=False)
  return

# @since 20230509 copied from bbsengine5.py
def pluralize(amount:int, singular:str, plural:str, quantity=True, emoji:str="") -> str:
  if amount is None or amount == 0:
    if quantity is True:
      return f"no {emoji} {plural}"
    return plural

  if quantity is True:
    if amount == 1:
      return f"{emoji} {amount} {singular}"
    buf = "{:n}".format(amount)
    return f"{emoji} {buf} {plural}"
  if amount == 1:
    return f"{emoji} {singular}"
  else:
    return f"{emoji} {plural}"

# @since 20230510 copied from bbsengine5
def datestamp(t=None, format:str="%Y-%m-%d %I:%M%P %Z (%a)") -> str:
  import getdate3 as getdate

  from dateutil.tz import tzlocal
  from datetime import datetime
  from time import tzset

  # ttyio.echo("bbsengine.datestamp.100: type(t)=%r" % (type(t)), level="debug")

  tzset()

  if type(t) == int or type(t) == float:
    t = datetime.fromtimestamp(t, tzinfo=tzlocal())
  elif t is None:
    t = datetime.now(tzlocal())
  elif type(t) == str:
    t = getdate.getdate(t)
#    ttyio.echo(f"after getdate: {t=} {type(t)=}")
    if type(t) is str:
#      ttyio.echo(f"after getdate(), {type(t)=}")
      return t

  return t.strftime(format)

# @since 20230523 copied from bbsengine5
def inputpassword(prompt:str="password: ", mask="X", **kw) -> str:
  return ttyio.inputstring(prompt, "", mask=mask, **kw)

  buf = ""
  done = False
  ttyio.echo(prompt, end="", flush=True)
  while not done:
    ch = ttyio.getch()
#    ttyio.echo("ch=%r" % (ch))
    if ch == "KEY_ENTER":
      done = True
      break
    if len(ch) == 1:
      buf += ch
      ttyio.echo(mask, end="", flush=True)
  # ttyio.echo(buf)
  return buf

# @see https://stackoverflow.com/a/53981846
# @since 20230523 copied from bbsengine5
def oxfordcomma(seq, conjunction:str="and") -> str:
    """Return a grammatically correct human readable string (with an Oxford comma)."""
    if seq is None:
      return None

    seq = [str(s) for s in seq]

#    ttyio.echo("seq=%r" % (seq))
    if len(seq) == 0:
      return ""

    if len(seq) < 3:
      buf = f"{{var:sepcolor}} {conjunction} {{var:valuecolor}}"
      return f"{{var:valuecolor}}{buf.join(seq)}" # itemcolor+buf.join(seq) # " and ".join(seq)

    buf = f"{{var:sepcolor}}, {{var:valuecolor}}"
    return f"{{var:valuecolor}}{buf.join(seq[:-1])}{{var:sepcolor}}, {conjunction} {{var:valuecolor}}{seq[-1]}"

def logentry(message, output=True, level=None, priority=syslog.LOG_INFO, stripcommands=False, datestamp=True):
  if level is not None:
    if level == "debug":
      message = "{blue}** debug ** "+message+"{/all}"
    elif level == "warn":
      message = "{yellow}** warn ** "+message+"{/all}"
    elif level == "error":
      message = "{red}** error ** "+message+"{/all}"

  message = ttyio.interpretecho(message, strip=True)
  syslog.syslog(priority, message)

  if output is True:
    ttyio.echo(message, stripcommands=stripcommands, datestamp=datestamp, interpret=False)

  return

# @since 20230612 copied from bbsengine5
# @see https://rosettacode.org/wiki/Range_extraction#Python
def collapserange(lst:list):
    'Yield 2-tuple ranges or 1-tuple single elements from list of increasing ints'
    lenlst = len(lst)
    i = 0
    while i < lenlst:
        low = lst[i]
        while i <lenlst-1 and lst[i]+1 == lst[i+1]: i +=1
        hi = lst[i]
        if   hi - low >= 2:
            yield (low, hi)
        elif hi - low == 1:
            yield (low,)
            yield (hi,)
        else:
            yield (low,)
        i += 1

# @since 20230612 copied from bbsengine5
def expandrange(txt:str) -> list:
  "accepts an str with a range expression, returns a list"
  elle = []
  for r in txt.split(','):
    if '-' in r[1:]:
      r0, r1 = r[1:].split('-', 1)
      elle += range(int(r[0] + r0), int(r1) + 1)
    else:
      elle.append(int(r))
  return list(set(elle))

def rangestr(ranges):
    return ','.join( (('%i-%i' % r) if len(r) == 2 else '%i' % r) for r in ranges )

def printr(ranges):
  print(rangestr(ranges))

# @since 20230618 copied from bbsengine5
def filedisplay(res, **kw) -> None: #more=True, width=None) -> None:
  more = kw["more"] if "more" in kw else True
  width = kw["width"] if "width" in kw else None
  indent = kw["indent"] if "indent" in kw else 0
  args = kw["args"] if "args" in kw else None

#  ttyio.echo("filename=%r" % (filename), level="debug")
  if width is None:
    width = ttyio.getterminalwidth()

  buf = ""
  with res as r:
    for elle in r:
      buf += elle # rstrip
#  fp = open(filename, "r")
#  buf = fp.read()
#  fp.close()
  ttyio.echo(buf, width=width, indent=indent, wordwrap=True)
#  height = ttyio.getterminalheight()-1
#  ttyio.echo("filedisplay.100: filename=%r type=%r" % (filename, type(filename)), level="debug")
#  with filename as f:
#    for line in f:
#      ttyio.echo(line)

#    pager(f, width=width, height=height, indent=indent)
  ttyio.echo("{/all}{f6}")

# @since 20230715 copied from bbsengine5
# mode = single, average, mean, list, ....?
def diceroll(sides:int=6, count:int=1, mode:str="single"):
  if mode == "single":
    return random.randint(1, sides)

  result = []
  for x in range(1, count+1):
    result.append(random.randint(1, sides))

  if mode == "list":
    return result
  elif mode == "average":
    avg = 0.0
    total = 0
    for x in result:
      total += x
    return total/len(result)
  elif mode == "median":
    median = 0.0
    # ttyio.echo("result=%r" % (result))
    result.sort()
    # ttyio.echo("result=%r" % (result))
    middle = int(len(result)//2)
    if len(result) % 2 == 1:
      return result[middle]
    else:
      return int((result[middle-1] + result[middle]) / 2.0)
  else:
    return None

def verifyDirExistsWritable(dirname:str, **kw) -> bool:

  dirname = os.path.expanduser(dirname)
  dirname = os.path.expandvars(dirname)
  ttyio.echo(f"verifyDirExistsWritable.100: {dirname=}", level="debug")

  if os.path.exists(dirname) is False:
    ttyio.echo(f"{dirname!r} does not exist", level="error")
    return False

  if os.path.isdir(dirname) is False:
    ttyio.echo(f"{dirname!r} is not a directory", level="error")
    return False

  if os.access(dirname, os.W_OK) is False:
    ttyio.echo(f"{dirname!r} is not writable", level="error")
    return False

  return True

def verifyFileExistsReadable(filename:str, **kw) -> bool:
  args = kw["args"] if "args" in kw else None

  filename = os.path.expanduser(filename)
  filename = os.path.expandvars(filename)
  if args is not None and args.debug is True:
    ttyio.echo(f"{filename=}", level="debug")
  if os.path.exists(filename) is True and os.access(filename, os.R_OK) is True:
    return True
  return False

def verifyFileExistsReadableWritable(filename, **kw):
  args = kw["args"] if "args" in kw else None

  filename = os.path.expanduser(filename)
  filename = os.path.expandvars(filename)
  if args is not None and "debug" in args and args.debug is True:
    ttyio.echo(f"bbsengine6.util.verifyFileExistsReadableWritable.100: {args=} {filename=}")

  if os.path.exists(filename) is False:
    ttyio.echo(f"{filename!r} does not exist")
    return False

  if os.access(filename, os.W_OK) is False:
    ttyio.echo(f"{filename!r} is not writable")
    return False

  if os.access(filename, os.R_OK) is False:
    ttyio.echo(f"{filename!r} is not readable")
    return False

  return True

# @since 20230923 copied from bbsengine5
def inputfilename(prompt, currentvalue, verify=verifyFileExistsReadable, **kw):
  path = os.path.expanduser(currentvalue)
  path = os.path.expandvars(path)
#  dirname = os.path.dirname(path)
#  if dirname is not None and dirname != "":
#    os.chdir(dirname)
  return ttyio.inputstring(prompt, currentvalue, verify=verify, **kw)
