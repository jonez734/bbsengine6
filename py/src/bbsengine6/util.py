import ttyio6 as ttyio

def hr(color="{var:engine.title.hrcolor}", chars="-=", width=None):
    if width is None:
        width = ttyio.getterminalwidth()
    style = ttyio.getoption("style", "ttyio")
    if style == "ttyio":
        return f"{{/all}}{color}{{acs:hline:{width}}}{{/all}}" # % (color, width)
    return "-"*width

# titlecolor = "{reverse}"
# hrcolor = ""
# hrchars = "{acs:hline}"
# llcorner="{acs:llcorner}"
# lrcorner="{acs:lrcorner}"
# ulcorner="{acs:ulcorner}"
# urcorner="{acs:urcorner}"
def title(title:str, **kw): # hrchar:str="{acs:hline}", llcorner="{acs:llcorner}", lrcorner="{acs:lrcorner}", ulcorner="{acs:ulcorner}", urcorner="{acs:urcorner}", vline="{acs:vline}", width=None, fillchar=" ", center=True):
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
  else:
      width = ttyio.getterminalwidth()-2
      hline = f"{{acs:hline:{width}}}"
      llcorner = "{acs:llcorner}"
      lrcorner = "{acs:lrcorner}"
      vline = "{acs:vline}"
      urcorner = "{acs:urcorner}"
      ulcorner = "{acs:ulcorner}"
      boxcolor = "{darkgreen}" # var:engine.title.hrcolor}"
      titlecolor = "{white}{bggray}" # {var:engine.title.color}"

  reset = "{/all}"
  w = int((width-len(title)-4)/2)
  padding = " "*(int(w))

  ttyio.echo(f"{boxcolor}{ulcorner}{hline}{urcorner}", wordwrap=False)
  ttyio.echo(f"{boxcolor}{vline}{reset} {titlecolor}{padding} {title} {padding}{reset} {boxcolor}{vline}", wordwrap=False)
  ttyio.echo(f"{boxcolor}{llcorner}{hline}{lrcorner}{reset}", wordwrap=False)
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
      return "no %s%s" % (emoji, plural)
    return plural

  if quantity is True:
    if amount == 1:
      return "%s%s %s" % (emoji, amount, singular)
    buf = "{:n}".format(amount)
    return "%s%s %s" % (emoji, buf, plural)
  if amount == 1:
    return "%s%s" % (emoji, singular)
  else:
    return "%s%s" % (emoji, plural)

# @since 20230510 copied from bbsengine5
def datestamp(t=None, format:str="%Y/%m/%d %I:%M%P %Z (%a)") -> str:
  from getdate import getdate, error

  from dateutil.tz import tzlocal
  from datetime import datetime
  from time import strftime, tzset

  # ttyio.echo("bbsengine.datestamp.100: type(t)=%r" % (type(t)), level="debug")

  tzset()

  if type(t) == int or type(t) == float:
    t = datetime.fromtimestamp(t, tzlocal())
  elif t is None:
    t = datetime.now(tzlocal())
  elif type(t) == str:
    epoch = getdate(t)
    t = datetime.fromtimestamp(epoch, tzlocal())

  stamp = strftime(format, t.timetuple())
  return stamp
