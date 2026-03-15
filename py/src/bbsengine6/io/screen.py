from .echo import echo, rendered_length
from . import terminal
#terminal import lines as terminal_lines, columns as terminal_columns
from .util import logentry

from typing import Callable, Any

# ------------------------
# screen related functions
# ------------------------

bottombarstack = []

def init(args=None, topmargin=1, bottommargin=1):
  echo("{f6:3}{cursorup:3}", end="", flush=True)
  h = terminal.lines() - bottommargin
  logentry(f"asimov.io.util.screen_init.100: {topmargin=} {h=}", level="debug")
  echo(f"{{savecursor}}", end="")
  echo(f"{{decstbm:{topmargin},{h}}}", end="")
  echo(f"{{restorecursor}}", flush=True, end="")

#  terminalheight = ttyio.getterminalheight()
#  ttyio.echo(f"{{decsc}}{{decstbm:{topmargin},{terminalheight-bottommargin}}}{{decrc}}") #  % (topmargin, terminalheight-bottommargin)) #  % (topmargin, terminalheight-bottommargin))

  return

def updatebottombar(buf: str) -> None:
    """Render the bottom bar on the last terminal line without line wrapping."""
    echo(f"{{savecursor}}{{bottombarcolor}}{{curpos:{terminal.lines()},0}}{buf}{{restorecursor}}", wordwrap=False, end="", flush=True)
    return

# @since 20230523 copied from bbsengine5
# @since 20250517 rewrite
#from wcwidth import wcswidth, wcwidth
def setbottombar(left, right=None, **kwargs):
    terminalwidth = terminal.width() - 2

    if callable(left) is True:
      left_buf = left(**kwargs)
    else:
      left_buf = left

    if callable(right) is True:
      right_buf =  right(**kwargs)
      echo(f"called right({kwargs=})", level="debug")
    else:
      right_buf = right

    left_len = rendered_length(left_buf)
    right_len = rendered_length(right_buf)
    max_left_len = terminalwidth - right_len
    if left_len > max_left_len:
      left_buf = left_buf[:max_left_len-5]+"..."
    padding = " " * (terminalwidth - left_len - right_len)
    updatebottombar(f"{{bottombarcolor}}{left_buf}{padding}{right_buf}{{/all}}")
    return True

# @since 20240708
# @since 20240517
# @since 20251208
setarea = setbottombar

# @since 20230523 copied from bbsengine5
def popbottombar():
  global bottombarstack

  if len(bottombarstack) == 0:
    return

  if len(bottombarstack) > 0:
    buf = bottombarstack.pop()
    if buf != "":
      updatebottombar(f"{{var:areacolor}}{buf}{{/all}}")

  return

# @since 20240708
poparea = popbottombar

# @since 20230523
##def title(buf):
##  return io.terminal.title(buf)

# @since 20210301
# @see https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
# @since 20240102 copied to bbsengine6
def updateprogress(iteration, total, fill="#"):
  terminalwidth = terminal.width()
  decimals = 0
  length = terminalwidth-20
  percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
  filledLength = length * iteration // total
  bar = fill * filledLength + '.' * (length - filledLength)
  buf = f"{{var:labelcolor}}Progress [{{var:valuecolor}}{percent:3s}%{{var:labelcolor}}]: [{bar}]{{/fgcolor}}"
  updatebottombar(buf)
  return
