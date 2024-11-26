from . import io
#import ttyio6 as ttyio

bottombarstack = []

# updatebottombar() - imported from bbsengine
# @since 20210222
# @since 20230512 copied from bbsengine5
def updatebottombar(buf:str) -> None:
  terminalheight = io.getterminalheight()
#  ttyio.echo("updatebottombar.100: buf=%r" % (buf), level="debug")
  io.echo(f"{{decsc}}{{/all}}{{curpos:{terminalheight},0}}{buf}{{eraseline}}{{decrc}}", wordwrap=False, end="")
  return

# @since 20230512 copied from bbsengine5
def initbottombar(height:int=1):
  terminalheight = io.getterminalheight()
  io.echo("{decsc}{decstbm:0,%d}{decrc}" % (terminalheight-height))

# @since 20230512 copied from bbsengine5
def init(topmargin=0, bottommargin=1):
  io.echo("{f6:3}{cursorup:3}", end="", flush=True)
  initbottombar(height=bottommargin)

#  terminalheight = ttyio.getterminalheight()
#  ttyio.echo(f"{{decsc}}{{decstbm:{topmargin},{terminalheight-bottommargin}}}{{decrc}}") #  % (topmargin, terminalheight-bottommargin)) #  % (topmargin, terminalheight-bottommargin))

  return

# @since 20230523 copied from bbsengine5
def setbottombar(left, right=None, stack:bool=False, width:int=None):
    global bottombarstack

    terminalwidth = width if width is not None else io.getterminalwidth()-2
#    io.echo(f"{terminalwidth=} {width=}")

    if callable(left):
        leftbuf = left()
    elif type(left) == str:
        leftbuf = left
    else:
        leftbuf = f"{type(left)=}" # "ERROR"

    l = io.tostr(leftbuf, strip=True, wordwrap=False)

    if callable(right):
        rightbuf = right()
    elif type(right) == str:
        rightbuf = right
    elif right is None:
        rightbuf = ""
    else:
        io.echo("setarea.100: type(right)=%r" % (right), level="debug")
        rightbuf = "ERROR" # type(right)

    r = io.tostr(rightbuf, wordwrap=False, exclude=("COMMAND", "COLOR"))
    t = terminalwidth - len(r) - 4
    leftbuf = leftbuf[:t] + (leftbuf[t:] and '...')

    buf = f" {leftbuf.ljust(terminalwidth-len(r)-1)}{rightbuf} "
#    io.echo(f"{buf=} {len(buf)=}")
    updatebottombar(f"{{areacolor}}{buf}{{/all}}")
    if stack is True:
        bottombarstack.insert(0, buf) # append(buf)
    return

# @since 20240708
setarea = setbottombar

# @since 20230523 copied from bbsengine5
def popbottombar():
  global bottombarstack

  if len(bottombarstack) == 0:
    return

  terminalwidth = io.getterminalwidth()

  if len(bottombarstack) > 0:
    buf = bottombarstack.pop()
    if buf != "":
      updatebottombar(f"{{var:areacolor}}{buf.ljust(terminalwidth-2, '')}{{/all}}")

  return

# @since 20240708
poparea = popbottombar

# @since 20230523
def title(buf):
  return io.terminal.title(buf)

# @since 20210301
# @see https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console
# @since 20240102 copied to bbsengine6
def updateprogress(iteration, total, fill="#"):
  terminalwidth = io.terminal.width()
  decimals = 0
  length = terminalwidth-20
  percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
  filledLength = length * iteration // total
  bar = fill * filledLength + '.' * (length - filledLength)
  buf = f"{{var:labelcolor}}Progress [{{var:valuecolor}}{percent:3s}%{{var:labelcolor}}]: [{bar}]{{/fgcolor}}"
  updatebottombar(buf)
  return
