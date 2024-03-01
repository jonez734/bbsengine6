import sys
import argparse
import importlib
import inspect

#import ttyio6 as ttyio
from . import io

# @since 20220826
def check(args, modulename, op="run", **kw):
  debug = args.debug if args is not None and args.debug is True else False

  if modulename in sys.modules:
    io.echo(f"{modulename!r} is in sys.modules. reloading.", level="debug")
    importlib.reload(sys.modules[modulename])

  if debug is True:
    io.echo(f"bbsengine.module.check.120: {modulename=}", level="debug")

  try:
    m = importlib.import_module(modulename)
  except ModuleNotFoundError:
    if debug is True:
      io.echo(f"module {modulename=} not found", level="debug")
    return False

  if debug is True:
    io.echo(f"bbsengine6.module.check.100: {type(m)=} {m=}", level="debug")

  if (hasattr(m, "init") and callable(m.init)) is False:
    if debug is True:
      io.echo("no init function", level="warn")
    return False

  if hasattr(m, "access") is False:
    if debug is True:
      io.echo("no access function", level="error")
    return False

  if (hasattr(m, "access") and callable(m.access)) is False:
    io.echo("no callable access function", level="error")
    return False

  if m.access(args, op) is True:
    if debug is True:
      io.echo("access check passed", level="debug")
  else:
    io.echo("access check failed", level="error")
    return False

  if (hasattr(m, "buildargs") and callable(m.buildargs)) is False:
    if debug is True:
      io.echo("no callable buildargs function", level="debug")
#    if buildargs is True:
#      return False

  if hasattr(m, "main"):
    io.echo(f"module has main attribute {type(m)=} {type(m.main)=}", level="debug")
  if callable(m.main):
    io.echo("main attribute is callable", level="debug")

  # required
  if (hasattr(m, "main") and callable(m.main)) is False:
    io.echo("no working main function", level="error")
    return False

  io.echo("checking signatures", level="debug")
  for f in ("init", "access", "buildargs", "main"):
#    argspec = inspect.getargspec(eval("m.{f}"))
#    ttyio.echo(f"bbsengine6.module.check.100: {argspec=}", level="debug")
    sig = inspect.signature(eval(f"m.{f}"))
    params = sig.parameters

    if args.debug is True:
      io.echo(f"{sig=} {params=}", level="debug")

    if f == "access" and "op" not in params:
      io.echo("missing 'op' in access()", level="error")
    # check to be sure 'op' is an str @ty ryan

    if "args" not in params:
      io.echo(f"missing 'args' from {f}()", level="error")
    if "kw" not in params and "kwargs" not in params:
      io.echo(f"missing 'keyword args' in {f}()", level="error")
#    if "args" not in sig:
#      ttyio.echo(f"{f}() is missing 'args' parameter", level="warn")

  return True

#@since 20230510 copied from bbsengine5
def load(args:object, modulepath:str):
  try:
      m = importlib.import_module(modulepath)
  except ModuleNotFoundError:
      io.echo(f"bbsengine6.module.load.180: module {modulepath} not found", level="error")
      raise
  return m
  
# @since 20230510 copied from bbsengine5
def runcallback(args:object, callback, optional=False, **kwargs): # s:argparse.Namespace, callback, argparser=None, **kwargs):
  debug = args.debug if args is not None else True
  if debug is True:
    io.echo(f"bbsengine6.runcallback.100: {args=} {kwargs=}", level="debug")
#  if argparser is not None:
#    args = argparser.parse_args()

  if callback is None:
    if debug is True:
      io.echo("runcallback.140: callback is None", level="debug")
    return None

  if callable(callback) is True:
    if debug is True:
      io.echo("runcallback.160: callback is callable", level="debug")
    return callback(args, **kwargs)

  s = callback.split(".")
  if len(s) > 1:
    modulepath = ".".join(s[:-1])
    funcname = s[len(s)-1:][0]
  else:
    modulepath = s[0] # None
    funcname = "main" # s[0]

  if debug is True:
    io.echo("runcallback.160: modulepath=%r funcname=%r" % (modulepath, funcname), level="debug")

  if modulepath is None:
    try:
      func = eval(funcname)
      io.echo("runcallback.320: func=%r" % (func))
    except NameError:
      io.echo("runcallback.340: %r not found." % (funcname), level="error")
      return None

    if callable(func) is True:
      if debug is True:
        io.echo("runcallback.260: callable", level="debug")
      return func(args, **kwargs)
    else:
      if debug is True:
        io.echo("runcallback.280: not callable", level="debug")
      return None

  m = load(args, modulepath)
  if debug is True:
    io.echo(f"runcallback.200: {m=} {funcname=}", level="debug")

  try:
    func = getattr(m, funcname)
  except AttributeError:
#    ttyio.echo("runcallback.240: function %s.%s() not found" % (modulepath, funcname))
    return None
  else:
    if debug is True:
      io.echo("runcallback.220: func=%r" % (func), level="debug")
    if callable(func) is True:
      return func(args, **kwargs)

  return None

# @since 20220727
# @since 20230508 added to bbsengine6
def runmodule(args, module, **kwargs):
  debug = args.debug if "debug" in args else True
  buildargs = True

  if check(args, module) is False:
    io.echo(f"check of {module=} failed. module not run.", level="error")
    return False

  if debug is True:
    io.echo(f"bbsengine6.runmodule.100: {args=}", level="debug")

  res = runcallback(args, f"{module}.init", **kwargs)
  if debug is True:
    io.echo(f"{module}.init() result={res}", level="debug")

  if buildargs is True:
    argv = kwargs["argv"] if "argv" in kwargs else []
    if debug is True:
      io.echo(f"bbsengine6.runmodule.120: {argv=}", level="debug")
    prgargparser = runcallback(args, f"{module}.buildargs", **kwargs)

    if debug is True:
      io.echo(f"bbsengine6.runmodule.130: {prgargparser=}")

    if prgargparser is not None:
      try:
        argv = [a.strip() for a in argv[1:]]
        prgargs = prgargparser.parse_args(argv) # argv[1:])
        if debug is True:
          io.echo(f"bbsengine6.module.runmodule: {prgargs=} {argv=}")
#        prgargs = [s.strip() for s in prgargs]
      except SystemExit:
        return False
      except argparse.ArgumentError:
        io.echo("argument error", level="error")
        return False

      if debug is True:
        io.echo(f"bbsengine.runmodule.220: {prgargs=}", level="debug")

      return runcallback(prgargs, f"{module}.main", **kwargs)

  res = runcallback(args, f"{module}.main", **kwargs)

  if debug is True:
    io.echo(f"{module}.main() result={res}", level="debug")
  return res

# @since 20220828
#def runsubmodule(args, module, **kw):
#  if args.debug is True:
#    io.echo("bbsengine6.module.runsubmodule.100: trace", level="debug")
#  return runmodule(args, module, **kw)
