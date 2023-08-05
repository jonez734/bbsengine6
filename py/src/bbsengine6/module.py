import sys
import importlib

import ttyio6 as ttyio

# @since 20220826
def check(args, module, op="run", buildargs=False, **kw):
  debug = False # args.debug if args is not None else False

  if debug is True:
    ttyio.echo(f"bbsengine.module.check.120: module={module!r}", level="debug")

  try:
    m = importlib.import_module(module)
  except ModuleNotFoundError:
    return False

  if debug is True:
    ttyio.echo("bbsengine6.module.check.100: m=%r" % (m), level="debug")

  # required
  if (hasattr(m, "init") and callable(m.init)) is False:
    if debug is True:
      ttyio.echo("no init function", level="warn")
      return False

  if hasattr(m, "access") is False:
    if debug is True:
      ttyio.echo("no access function, returning True anyway")
    return True
  if (hasattr(m, "access") and callable(m.access)) is False:
    if debug is True:
      ttyio.echo("no callable access function", level="debug")
    return False

  if m.access(args, op) is True:
    if debug is True:
      ttyio.echo("access check passed", level="debug")
  else:
    ttyio.echo("access check failed", level="error")
    return False

  if (hasattr(m, "buildargs") and callable(m.buildargs)) is False:
    if debug is True:
      ttyio.echo("no callable buildargs function", level="debug")
    if buildargs is True:
      return False

  # required
  if (hasattr(m, "main") and callable(m.main)) is False:
    ttyio.echo("no main function", level="error")
    return False

  return True

#@since 20230510 copied from bbsengine5
def load(args:object, modulepath:str):
  try:
      m = importlib.import_module(modulepath)
  except ModuleNotFoundError:
      ttyio.echo("bbsengine6.module.load.180: module %s not found" % (modulepath), level="error")
      raise
  return m
  
# @since 20230510 copied from bbsengine5
def runcallback(args:object, callback, optional=False, **kwargs): # s:argparse.Namespace, callback, argparser=None, **kwargs):
  debug = args.debug if args is not None else False
  if debug is True:
    ttyio.echo("bbsengine5.runcallback.100: args=%r kwargs=%r" % (args, kwargs), level="debug")
#  if argparser is not None:
#    args = argparser.parse_args()

  if callback is None:
    if debug is True:
      ttyio.echo("runcallback.140: callback is None", level="debug")
    return None

  if callable(callback) is True:
    if debug is True:
      ttyio.echo("runcallback.160: callback is callable", level="debug")
    return callback(args, **kwargs)

  s = callback.split(".")
  if len(s) > 1:
    modulepath = ".".join(s[:-1])
    funcname = s[len(s)-1:][0]
  else:
    modulepath = s[0] # None
    funcname = "main" # s[0]

  if debug is True:
    ttyio.echo("runcallback.160: modulepath=%r funcname=%r" % (modulepath, funcname), level="debug")

  if modulepath is None:
    try:
      func = eval(funcname)
      ttyio.echo("runcallback.320: func=%r" % (func))
    except NameError:
      ttyio.echo("runcallback.340: %r not found." % (funcname), level="error")
      return None

    if callable(func) is True:
      if debug is True:
        ttyio.echo("runcallback.260: callable", level="debug")
      return func(args, **kwargs)
    else:
      if debug is True:
        ttyio.echo("runcallback.280: not callable", level="debug")
      return None

  m = load(args, modulepath)
  if debug is True:
    ttyio.echo("runcallback.200: m=%r funcname=%r" % (m, funcname), level="debug")

  try:
    func = getattr(m, funcname)
  except AttributeError:
#    ttyio.echo("runcallback.240: function %s.%s() not found" % (modulepath, funcname))
    return None
  else:
    if debug is True:
      ttyio.echo("runcallback.220: func=%r" % (func), level="debug")
    if callable(func) is True:
      return func(args, **kwargs)

  return None

# @since 20220727
# @since 20230508 added to bbsengine6
def runmodule(args, module, **kwargs):
  buildargs = kwargs["buildargs"] if "buildargs" in kwargs else True
  if check(args, module, buildargs=buildargs) is False:
    ttyio.echo("check module failed. permission denied", level="error")
    return False

  if args.debug is True:
    ttyio.echo("bbsengine6.runmodule.100: args=%r" % (args), level="debug")

  res = runcallback(args, module + ".init", **kwargs)
  if args.debug is True:
    ttyio.echo("%s.init() result=%r" % (module, res), level="debug")

  if buildargs is True:
    argv = kwargs["argv"] if "argv" in kwargs else []
    if args.debug is True:
      ttyio.echo("bbsengine6.runmodule.120: argv=%r" % (argv), level="debug")
    prgargparser = runcallback(args, module + ".buildargs", **kwargs)
    if prgargparser is not None:
      try:
        argv = [a.strip() for a in argv[1:]]
        prgargs = prgargparser.parse_args(argv) # argv[1:])
#        prgargs = [s.strip() for s in prgargs]
      except SystemExit:
        return
      except argparse.ArgumentError:
        ttyio.echo("argument error", level="error")
        return

      if args.debug is True:
        ttyio.echo("bbsengine.runmodule.220: prgargs=%r" % (prgargs), level="debug")

#      res = runcallback(prgargs, module+".main", **kwargs)
#  else:
#    res = runcallback(args, module+".main", **kwargs)
  res = runcallback(args, module+".main", **kwargs)

  if args.debug is True:
    ttyio.echo("%s.main() result=%r" % (module, res), level="debug")
  return res

# @since 20220828
def runsubmodule(args, module, **kw):
  ttyio.echo("bbsengine6.module.runsubmodule.100: trace", level="debug")
  return runmodule(args, module, buildargs=False, **kw)
