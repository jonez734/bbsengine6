import os
import re
import random
import syslog

#import ttyio6 as ttyio
from . import io, input, database

def hr(color="{var:engine.title.hrcolor}", chars="-", width=None, padding=" "):
    if width is None:
        width = io.getterminalwidth()-2
    if io.getoption("style", "ttyio") == "ttyio":
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
  if io.getoption("style", "ttyio") == "noansi":
      width = 100
      hline="-"*width
      llcorner="+"
      lrcorner="+"
      ulcorner="+"
      urcorner="+"
      vline="|"
      #boxcolor = ""
      #titlecolor = ""
      #reset = ""
  else:
      width = io.getterminalwidth() - 4
      hline = f"{{acs:hline:{width}}}"
      llcorner = "{acs:llcorner}"
      lrcorner = "{acs:lrcorner}"
      vline = "{acs:vline}"
      urcorner = "{acs:urcorner}"
      ulcorner = "{acs:ulcorner}"
      #boxcolor = "{darkgreen}" # var:engine.title.hrcolor}"
      #titlecolor = "{white}{bggray}" # {var:engine.title.color}"
      # reset = "{/all}"

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

  io.echo(f"{{/all}}{{normalcolor}} {{boxcolor}}{ulcorner}{hline}{urcorner}", wordwrap=False)
  io.echo(f" {{boxcolor}}{vline}{{titlecolor}}{leftpadding}{title}{rightpadding}{{/all}}{{boxcolor}}{vline}{{/all}}", wordwrap=False)
  io.echo(f" {{boxcolor}}{llcorner}{hline}{lrcorner}{{/all}}", wordwrap=False)
  return

  style = io.getoption("style", "ttyio")
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
    width = io.getterminalwidth()-2
#  buf = ttyio.center(title, width)
  buf = title.center(width) # ttyio.center(title, width)
#  b = title.center(width) # ttyio.center(title)

  io.echo("{/all}{var:engine.title.hrcolor}%s{acs:hline:%s}%s" % (ulcorner, width, urcorner), wordwrap=False)
  io.echo("{var:engine.title.hrcolor}{acs:vline}{/all}{var:engine.title.color}%s{/all}{var:engine.title.hrcolor}{acs:vline}{/all}" % (buf), wordwrap=False)
  # ttyio.echo("{f6}{acs:vline}{/all}%s%s{/all}%s{acs:vline}{/all}" % (titlecolor, i.center(width), hrcolor), end="")
  io.echo("{var:engine.title.hrcolor}%s{acs:hline:%s}%s{/all}" % (llcorner, width, lrcorner), wordwrap=False)
  return

# @since 20230509 copied from bbsengine5.py
def pluralize(amount:int, singular:str="singular", plural:str="plural", quantity:bool=True, emoji:str="", determiner:str="a", **kw) -> str:
  if amount is None or amount == 0:
    if quantity is True:
      return f"no {emoji}{plural}"
    return plural

  if quantity is True:
    if amount == 1:
      if determiner != "":
        return f"{emoji} {determiner} {singular}"
      else:
        return f"{emoji}{amount} {singular}"
    return f"{emoji}{amount:n} {plural}"

  if amount == 1:
    return f"{emoji}{singular}"
  else:
    return f"{emoji}{plural}"

# @since 20230510 copied from bbsengine5
def datestamp(t=None, format:str="%Y-%m-%d %I:%M%P %Z (%a)") -> str:
#  import getdate3 as getdate

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
    t = input.getdate(t)
#    ttyio.echo(f"after getdate: {t=} {type(t)=}")
    if type(t) is str:
#      ttyio.echo(f"after getdate(), {type(t)=}")
      return t

  return t.strftime(format)

# @since 20230523 copied from bbsengine5
def inputpassword(prompt:str="password: ", mask:str="X", **kwargs) -> str:
  return io.inputstring(prompt, "", mask=mask, **kwargs)

  buf = ""
  done = False
  io.echo(prompt, end="", flush=True)
  while not done:
    ch = io.getch()
#    ttyio.echo("ch=%r" % (ch))
    if ch == "KEY_ENTER":
      done = True
      break
    if len(ch) == 1:
      buf += ch
      io.echo(mask, end="", flush=True)
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

def logentry(message, output=True, level=None, priority=syslog.LOG_INFO, strip=False, datestamp=True, prg=None):
  import logging

  if level is not None:
    if level == "debug":
      logging.debug(message)
      message = f"{{var:level.debug}}** debug ** {message}{{/all}}"
    elif level == "info":
      logging.info(message)
      message = f"{{var:level.info}}** info ** {message}{{/all}}"
    elif level == "warn" or level == "warning":
      logging.warning(message)
      message = f"{{var:level.warn}}** warn ** {message}{{/all}}"
    elif level == "error":
      logging.error(message)
      message = f"{{var:level.error}}** error ** {message}{{/all}}"
    elif level == "critical" or level == "crit":
      logging.critical(message)
      message = f"{{var:level.crit}}** critical ** {message}{{/all}}"

  syslog.syslog(priority, io.tostr(message, strip=True))

  if output is True:
    io.echo(message, strip=strip, datestamp=datestamp)
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
    width = io.getterminalwidth()

  buf = ""
  with res as r:
    for elle in r:
      buf += elle # rstrip
#  fp = open(filename, "r")
#  buf = fp.read()
#  fp.close()
  io.echo(buf, width=width, indent=indent, wordwrap=True)
#  height = ttyio.getterminalheight()-1
#  ttyio.echo("filedisplay.100: filename=%r type=%r" % (filename, type(filename)), level="debug")
#  with filename as f:
#    for line in f:
#      ttyio.echo(line)

#    pager(f, width=width, height=height, indent=indent)
  io.echo("{/all}{f6}")

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
  io.echo(f"verifyDirExistsWritable.100: {dirname=}", level="debug")

  if os.path.exists(dirname) is False:
    io.echo(f"{dirname!r} does not exist", level="error")
    return False

  if os.path.isdir(dirname) is False:
    io.echo(f"{dirname!r} is not a directory", level="error")
    return False

  if os.access(dirname, os.W_OK) is False:
    io.echo(f"{dirname!r} is not writable", level="error")
    return False

  return True

def verifyFileExistsReadable(filename:str, **kw) -> bool:
  args = kw["args"] if "args" in kw else None

  filename = os.path.expanduser(filename)
  filename = os.path.expandvars(filename)
  if args is not None and args.debug is True:
    io.echo(f"{filename=}", level="debug")
  if os.path.exists(filename) is True and os.access(filename, os.R_OK) is True:
    return True
  return False

def verifyFileExistsReadableWritable(filename, **kw):
  args = kw["args"] if "args" in kw else None

  filename = os.path.expanduser(filename)
  filename = os.path.expandvars(filename)
  if args is not None and "debug" in args and args.debug is True:
    io.echo(f"bbsengine6.util.verifyFileExistsReadableWritable.100: {args=} {filename=}")

  if os.path.exists(filename) is False:
    io.echo(f"{filename!r} does not exist")
    return False

  if os.access(filename, os.W_OK) is False:
    io.echo(f"{filename!r} is not writable")
    return False

  if os.access(filename, os.R_OK) is False:
    io.echo(f"{filename!r} is not readable")
    return False

  return True

# @since 20240105
def timedelta(delta):
  buf = ""

  seconds = delta.total_seconds()
  minutes = seconds // 60
  seconds -= minutes * 60
  hours = minutes // 60
  minutes -= hours * 60
  days = hours // 24
  hours -= days*24

#  if weeks != 0:
#    buf += f"{weeks}w"
#  if days != 0:
#    buf += f"{days}d"
  if days != 0:
    buf += f"{days:02.0f}d"
  if hours != 0:
    buf += f"{hours:02.0f}h"
  if minutes != 0:
    buf += f"{minutes:02.0f}m"
  if seconds != 0:
    buf += f"{seconds:02.0f}s"
  return buf

# @since 20240113
# copied from bbsengine5
def getencryptedpassword(args, plaintextpassword:str) -> str:
  io.echo(f"getencryptedpassword.100: {plaintextpassword=}", level="debug")
  sql = "select crypt(%s, gen_salt('md5'))" # previously 'bf' which does not work with dovecot
  dat = (plaintextpassword,)
  with database.connect(args) as conn:
    with conn.cursor() as cur:
      cur.execute(sql, dat)
      if cur.rowcount == 0:
        return None

      res = cur.fetchone()
      return res["crypt"]

def init(args=None, **kw):
  import time, locale

  locale.setlocale(locale.LC_ALL, "")
  time.tzset()

#
# @since 20140831 bbsengine5.php
# @since 20221107 bbsengine5.py
# @since 20240509 copied from bbsengine5.py
# @since 20241125 moved to member
#def checkpassword(args, plaintext, memberid=None):

# @since 20240921 generated by chatgpt.com
def checksum(data):
  crc = 0xffffffff
  for byte in data:
    crc ^= byte
    for _ in range(8):
      crc = (crc >> 1) ^ (0xedb88320 if (crc & 1) else 0)
  crc ^= 0xffffffff
  return f"{crc:08X}"

# @since 20240921 generated by chatgpt.com
def ltree_to_path(ltree):
  # Split the ltree path by periods
  labels = ltree.split('.')

  # Remove the reference to 'top'
  if labels[0] == 'top':
    labels.pop(0)

  # Join the remaining labels into a filesystem path with slashes
  return '/'.join(labels)

def chop_last_element(ltree):
    labels = ltree.split('.')

#    # If there's only one element, return the original ltree
#    if len(labels) <= 1:
#        return ltree

    labels.pop()
    return '.'.join(labels)

def tobool(value):
  if value is True or value.lower() == "true" or value.lower() == "t":
    return True
  return False

def getremoteaddr():
  import os
  if "SSH_CONNECTION" in os.environ:
    return os.environ.get("SSH_CONNECTION", None).split()[0]
  return None

def getcurrentloginid(args):
  import os
  # loginid = os.getlogin()
  # io.echo(f"bbsengine.util.getcurrentloginid.100: {loginid=}", level="debug")
  return os.getlogin()

# @since 20241212
def get_safe_path(args, *components, **kwargs):
    """
    Constructs a safe path by joining multiple path components.
    Expands environment variables and user home director and normalizes
    """
    if not components:
        raise ValueError("At least one path component must be provided.")

    # Expand environment variables and `~` in all components
    components = [os.path.expandvars(os.path.expanduser(component)) for component in components]

    # Join all components
    joined_path = os.path.join(*components)

    # Normalize the resulting path
    safe_path = os.path.normpath(joined_path)

    # Ensure the resulting path is absolute
    base_dir = os.path.abspath(components[0])
    if not safe_path.startswith(base_dir):
        raise ValueError("Invalid path: directory traversal detected.")

#    # Ensure the file exists
#    if not os.path.isfile(safe_path):
#        raise FileNotFoundError(f"File not found: {safe_path}")

    return safe_path

def load_sql(args, resource_name: str, *, package: str = None) -> str:
    """
    Loads an SQL resource file and returns its contents as a string.
    """

    try:
      from importlib.resources import files
    except ImportError:
      try:
          from importlib_resources import files  # backport
      except ImportError:
          files = None  # will error later if used

#    import importlib.resources as resources
    import pathlib
    from typing import Optional

    def _resolve_package(package: Optional[str]) -> str:
        if package is not None:
            return package
        if __package__:
            return __package__ + ".sql"

        # Walk up the directory tree to find the root package (by detecting the first `__init__.py`)
        base_path = pathlib.Path(__file__).resolve()
        while base_path.parent != base_path:
            # Check if the current directory has an __init__.py (indicating it's a package)
            if (base_path / "__init__.py").exists():
                return base_path.name + ".sql"
            base_path = base_path.parent

        # If we reached here, we couldn't determine the package — raise an error
        raise ValueError("Unable to determine the package for resource loading")

    resolved_package = _resolve_package(package)
    return files(resolved_package).joinpath(resource_name).read_text(encoding='utf-8')

from datetime import datetime

def serialize_datetimes(data):
    result = {}
    for key, subdict in data.items():
        val = subdict.get("value")
        if isinstance(val, datetime):
            # Use ISO format or str(val) if you prefer
            result[key] = {"value": val.isoformat()}
        else:
            result[key] = subdict
    return result

ANSI_ESCAPE_RE = re.compile(r'\x1b\[[0-9;]*m')

def strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences from a string for display width measurement."""
    return ANSI_ESCAPE_RE.sub('', s)
