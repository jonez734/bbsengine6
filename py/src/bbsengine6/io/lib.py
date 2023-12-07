def darken(prefix, rgb, percentage):
  if len(rgb) == 3:
    (r, g, b) = rgb
    a = 1
  elif len(rgb) == 4:
    (r, g, b, a) = rgb
  r *= 1-percentage
  g *= 1-percentage
  b *= 1-percentage
  return "%s;2;%d;%d;%d;%dm" % (prefix, r, g, b, a)

def rgb(prefix, rgb):
  if len(rgb) == 3:
    (r, g, b) = rgb
    a = 1
  elif len(rgb) == 4:
    (r, g, b, a) = rgb
  ansi = "%s;2;%s;%s;%s;%sm" % (prefix, r, g, b, a)
  return ansi

options = {}
def setoption(opt:str, value):
  global options
  options[opt] = value
  return value

def getoption(opt:str, default=None):
  global options

  return options[opt] if opt in options else default
