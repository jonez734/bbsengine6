import ttyio6 as ttyio

areastack = []

# updatebottombar() - imported from bbsengine
# @since 20210222
# @since 20230512 copied from bbsengine5
def updatebottombar(buf:str) -> None:
  terminalheight = ttyio.getterminalheight()
#  ttyio.echo("updatebottombar.100: buf=%r" % (buf), level="debug")
  ttyio.echo(f"{{decsc}}{{/all}}{{curpos:{terminalheight},0}}{buf}{{eraseline}}{{decrc}}", wordwrap=False, end="")
  return

# @since 20230512 copied from bbsengine5
def initbottombar(height:int=1):
  terminalheight = ttyio.getterminalheight()
  ttyio.echo("{decsc}{decstbm:0,%d}{decrc}" % (terminalheight-height))

# @since 20230512 copied from bbsengine5
def init(topmargin=0, bottommargin=1):
  ttyio.echo("{f6:3}{cursorup:3}", end="", flush=True)
  initbottombar(height=bottommargin)

#  terminalheight = ttyio.getterminalheight()
#  ttyio.echo(f"{{decsc}}{{decstbm:{topmargin},{terminalheight-bottommargin}}}{{decrc}}") #  % (topmargin, terminalheight-bottommargin)) #  % (topmargin, terminalheight-bottommargin))

  return

# @since 20230523 copied from bbsengine5
def setarea(left, right=None, stack:bool=False):
  global areastack

  terminalwidth = ttyio.getterminalwidth()-2

  if callable(left):
    leftbuf = left()
  elif type(left) == str:
    leftbuf = left
  else:
    leftbuf = type(left) # "ERROR"

  l = ttyio.interpret(leftbuf, strip=True)

  if callable(right):
    rightbuf = right()
  elif type(right) == str:
    rightbuf = right
  elif right is None:
    rightbuf = ""
  else:
    ttyio.echo("setarea.100: type(right)=%r" % (right), level="debug")
    rightbuf = "ERROR" # type(right)

  r = ""
  for i in ttyio.interpret(rightbuf, strip=True):
    r += i
  t = terminalwidth - len(r) - 4
  leftbuf = leftbuf[:t] + (leftbuf[t:] and '...')

#  ttyio.echo("r=%r rightbuf=%r" % (r, rightbuf), interpret=False)

#  buf = "%s%s" % (ttyio.ljust(leftbuf, terminalwidth-len(r)), rightbuf) # leftbuf.ljust(terminalwidth-len(r), " "), rightbuf)
  buf = " %s%s " % (leftbuf.ljust(terminalwidth-len(r)), rightbuf)
  #ttyio.ljust(leftbuf, terminalwidth-len(r)), rightbuf) # leftbuf.ljust(terminalwidth-len(r), " "), rightbuf)
  updatebottombar("{var:areacolor}%s{/all}" % (buf))
  if stack is True:
    areastack.insert(0, buf) # append(buf)
  return

# @since 20230523 copied from bbsengine5
def poparea():
  global areastack

  if len(areastack) == 0:
    return

  terminalwidth = ttyio.getterminalwidth()

  if len(areastack) > 0:
    buf = areastack.pop()
    if buf != "":
      updatebottombar("{var:areacolor}%s{/all}" % (buf.ljust(terminalwidth-2, " ")))

  return

# @since 20230523
def title(buf):
  return ttyio.terminal.title(buf)
