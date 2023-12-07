import os
import re
import sys
import fcntl
import termios

from .const import *

# @since 20200917
def detectansi(streamout=sys.stdout, streamin=sys.stdin):
  if streamout.isatty() is False:
    return False

  streaminfd = streamin.fileno()
  streamoutfd = streamout.fileno()

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
      ch = streamin.read(1)
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

def getcursorposition(fd=sys.stdin.fileno()):
  oldtermios = termios.tcgetattr(fd)
  oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)

  newattr = termios.tcgetattr(fd)
  newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
  termios.tcsetattr(fd, termios.TCSANOW, newattr)

  print(CSI+"6n", end="", flush=True)
  buf = ""
  try:
    for x in range(0,10):
      ch = sys.stdin.read(1)
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
  return size().columns
  #try:
  #  res = os.get_terminal_size()
  #except:
  #  return 80
  #else:
  #  return res.columns
#  import subprocess
#
#  command = ['tput', 'cols']
#
#  if sys.stdout.isatty() is False:
#    return False

#  try:
#    width = int(subprocess.check_output(command))
#  except OSError as e:
#    print("Invalid Command '{0}': exit status ({1})".format(command[0], e.errno))
#    return False
#  except subprocess.CalledProcessError as e:
#    print("Command '{0}' returned non-zero exit status: ({1})".format(command, e.returncode))
#    return False
#  else:
#    return width
def height():
# def getterminalheight():
  return size().lines
#  if sys.stdout.isatty() is False:
#    return False
#
#  res = os.get_terminal_size()
#  return res.lines


# @see https://tldp.org/HOWTO/Xterm-Title-3.html
def title(name):
  if sys.stdout.isatty() is False:
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
#  print(f"*** savecursor: {cursorpositions=} {row=},{col=}")
  cursorpositions.append((row, col),)
#  print(f"*** savecursor: {cursorpositions=} {row=},{col=}")
  return

def restorecursor():
  global cursorpositions

#  print(f"*** restore: {cursorpositions=}")
  (row, col) = cursorpositions.pop()
#  print(f"*** restore: {row=},{col=}")
#  yield Token("CURSOR", f"{CSI}{y};{x}H") # f"{CSI}{y};{x}H" # result += CSI+"%d;%dH" % (y, x)
#  ttyio.echo(f"{CURPOS:{{row}},{{col}}}", end="", flush=True)
  return f"{CSI}{row};{col}H"
