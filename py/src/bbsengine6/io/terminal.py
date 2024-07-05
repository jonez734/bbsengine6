import re
import sys
import fcntl
import termios

from .const import *

_streamout = sys.stdout
_streamin = sys.stdin

MAXWIDTH = None # 100

# @since 20200917
def detectansi(): #streamout=_streamout, streamin=_streamout):
  global _streamin, _streamout

  streaminfd = _streamin.fileno()
  streamoutfd = _streamout.fileno()

  if _streamout.isatty() is False:
    return False

  oldtermios = termios.tcgetattr(streaminfd)
  oldflags = fcntl.fcntl(streaminfd, fcntl.F_GETFL)

  newattr = termios.tcgetattr(streaminfd)
  newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
  termios.tcsetattr(streaminfd, termios.TCSANOW, newattr)

  # fcntl.fcntl(stdinfd, fcntl.F_SETFL, oldflags)

  print(f"{ESC}[5n", end="", flush=True)

  buf = ""
  try:
    for x in range(0, 4):
      ch = _streamin.read(1)
      buf += ch
      if ch == "n":
        break
  finally:
    termios.tcsetattr(streaminfd, termios.TCSAFLUSH, oldtermios)
    fcntl.fcntl(streaminfd, fcntl.F_SETFL, oldflags)
  if buf == f"{ESC}[0n":
    return True
  else:
    print(f"ttyio6.terminal.detectansi.100: {buf=}", level="debug")
    return None

def getcursorposition():
  fd = _streamin.fileno()
  oldtermios = termios.tcgetattr(fd)
  oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)

  newattr = termios.tcgetattr(fd)
  newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
  termios.tcsetattr(fd, termios.TCSANOW, newattr)

  print(CSI+"6n", end="", flush=True)
  buf = ""
  try:
    for x in range(0,10):
      ch = _streamin.read(1)
      buf += ch
      if ch == "R":
        break
  finally:
    termios.tcsetattr(fd, termios.TCSAFLUSH, oldtermios)
    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)

  m = re.search(r'\033\[(?P<row>\d{,4});(?P<col>\d{,4})R', buf)
  row, column = m.group("row"), m.group("col")
  return (int(row), int(column))

# @since 20210411
def size():
  import shutil
  return shutil.get_terminal_size()

# http://www.brandonrubin.me/2014/03/18/python-snippet-get-terminal-width/
# https://www.programcreek.com/python/example/1922/termios.TIOCGWINSZ
def width():
  if MAXWIDTH is None:
    return size().columns

  w = size().columns
  return MAXWIDTH if w > MAXWIDTH else w
#  return size().columns

columns = width

def height():
  return size().lines

def lines():
  return size().lines

# @see https://tldp.org/HOWTO/Xterm-Title-3.html
def title(name):
  if _streamout.isatty() is False:
    return False

  style = getoption("style", "ttyio")
  if style == "noansi":
    return

  print(f"{ESC}]0;{name}\007", end="", flush=True)
  return

cursorpositions = []
# @since 20231027
def savecursor():
  global cursorpositions
  row, col = getcursorposition()
  cursorpositions.append((row, col),)
  return

def restorecursor():
  global cursorpositions

  (row, col) = cursorpositions.pop()
  return f"{CSI}{row};{col}H"
