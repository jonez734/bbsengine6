import sys
import argparse
import importlib
import inspect

import ttyio6 as ttyio

# @since 20220826
def check(args, module, op="run", **kw):
  debug = args.debug if args is not None and args.debug is True else False

  if debug is True:
    ttyio.echo(f"bbsengine.module.check.120: module={module!r}", level="debug")

  try:
    m = importlib.import_module(module)
  except ModuleNotFoundError:
    if debug is True:
      ttyio.echo(f"module {module=} not found", level="debug")
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
      ttyio.echo("no access function", level="error")
    return False

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
#    if buildargs is True:
#      return False

  # required
  if (hasattr(m, "main") and callable(m.main)) is False:
    ttyio.echo("no main function", level="error")
    return False

  for f in ("init", "access", "buildargs", "main"):
#    argspec = inspect.getargspec(eval("m.{f}"))
#    ttyio.echo(f"bbsengine6.module.check.100: {argspec=}", level="debug")
    sig = inspect.signature(eval(f"m.{f}"))
    params = sig.parameters

    if args.debug is True:
      ttyio.echo(f"{sig=} {params=}", level="debug")

    if f == "access" and "op" not in params:
      ttyio.echo("missing 'op' in access()", level="error")
    if "args" not in params:
      ttyio.echo(f"missing 'args' from {f}()", level="error")
    if "kw" not in params and "kwargs" not in params:
      ttyio.echo(f"missing 'keyword args' in {f}()", level="error")
#    if "args" not in sig:
#      ttyio.echo(f"{f}() is missing 'args' parameter", level="warn")

  return True

#@since 20230510 copied from bbsengine5
def load(args:object, modulepath:str):
  try:
      m = importlib.import_module(modulepath)
  except ModuleNotFoundError:
      ttyio.echo(f"bbsengine6.module.load.180: module {modulepath} not found", level="error")
      raise
  return m
  
# @since 20230510 copied from bbsengine5
def runcallback(args:object, callback, optional=False, **kwargs): # s:argparse.Namespace, callback, argparser=None, **kwargs):
  debug = args.debug if args is not None else False
  if debug is True:
    ttyio.echo(f"bbsengine6.runcallback.100: {args=} {kwargs=}", level="debug")
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
  debug = args.debug if "debug" in args else True
  buildargs = True

  if check(args, module) is False:
    ttyio.echo(f"check of {module=} failed. module not run.", level="error")
    return False

  if debug is True:
    ttyio.echo(f"bbsengine6.runmodule.100: {args=}", level="debug")

  res = runcallback(args, f"{module}.init", **kwargs)
  if debug is True:
    ttyio.echo(f"{module}.init() result={res}", level="debug")

  if buildargs is True:
    argv = kwargs["argv"] if "argv" in kwargs else []
    if debug is True:
      ttyio.echo(f"bbsengine6.runmodule.120: {argv=}", level="debug")
    prgargparser = runcallback(args, f"{module}.buildargs", **kwargs)

    if debug is True:
      ttyio.echo(f"bbsengine6.runmodule.130: {prgargparser=}")

    if prgargparser is not None:
      try:
        argv = [a.strip() for a in argv[1:]]
        prgargs = prgargparser.parse_args(argv) # argv[1:])
        if debug is True:
          ttyio.echo(f"bbsengine6.module.runmodule: {prgargs=} {argv=}")
#        prgargs = [s.strip() for s in prgargs]
      except SystemExit:
        return False
      except argparse.ArgumentError:
        ttyio.echo("argument error", level="error")
        return False

      if debug is True:
        ttyio.echo(f"bbsengine.runmodule.220: {prgargs=}", level="debug")

      return runcallback(prgargs, f"{module}.main", **kwargs)

  res = runcallback(args, f"{module}.main", **kwargs)

  if debug is True:
    ttyio.echo(f"{module}.main() result={res}", level="debug")
  return res

# @since 20220828
def runsubmodule(args, module, **kw):
  if args.debug is True:
    ttyio.echo("bbsengine6.module.runsubmodule.100: trace", level="debug")
  return runmodule(args, module, **kw)
